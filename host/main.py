"""
IRIS — Master Orchestration Pipeline
Camera → YOLO → IK → Serial → Arm

Loop:
  1. Capture frame
  2. Detect screws
  3. If stable detection: solve IK for pick pose
  4. Execute pick (approach → grip → lift)
  5. Execute place (move to drop zone → release → home)
"""

import sys
import time
import logging
import yaml
import numpy as np
from pathlib import Path
from collections import deque
from typing import Optional, List

# Add ik/ to path
sys.path.insert(0, str(Path(__file__).parent.parent / "ik"))

from vision import IRISVision, Detection
from serial_comm import IRISSerial
from inverse_kinematics import inverse_kinematics, verify_ik
from trajectory import plan_joint_trajectory

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
log = logging.getLogger("IRIS")


# ============================================================
#  Config helpers
# ============================================================

def load_config(path: str = "config.yaml") -> dict:
    with open(path) as f:
        return yaml.safe_load(f)


def dh_from_cfg(cfg: dict) -> List[List[float]]:
    return cfg["ik"]["dh_params"]


def limits_from_cfg(cfg: dict) -> List[List[float]]:
    lim = cfg["ik"]["joint_limits"]
    keys = ["j1","j2","j3","j4","j5","j6"]
    return [lim[k] for k in keys]


# ============================================================
#  Pose builders
# ============================================================

def pick_approach_pose(x: float, y: float, z_table: float, approach_h: float) -> np.ndarray:
    """4x4 transform: above the screw, gripper pointing straight down."""
    T = np.eye(4)
    T[0, 3] = x
    T[1, 3] = y
    T[2, 3] = z_table + approach_h
    # Gripper pointing down: z-axis of EE = -Z_base
    T[0, 0] =  1; T[1, 1] = -1; T[2, 2] = -1   # 180° about X
    return T


def pick_pose(x: float, y: float, z_table: float) -> np.ndarray:
    """4x4 transform: at the screw, gripper pointing down."""
    T = pick_approach_pose(x, y, z_table, 0.0)
    T[2, 3] = z_table
    return T


def drop_pose_from_cfg(cfg: dict) -> np.ndarray:
    p = cfg["arm"]["drop_pose_m"]
    T = np.eye(4)
    T[:3, 3] = p[:3]
    # Convert RPY to rotation matrix
    rx, ry, rz = [np.deg2rad(v) for v in p[3:6]]
    cx, sx = np.cos(rx), np.sin(rx)
    cy, sy = np.cos(ry), np.sin(ry)
    cz, sz = np.cos(rz), np.sin(rz)
    Rx = np.array([[1,0,0],[0,cx,-sx],[0,sx,cx]])
    Ry = np.array([[cy,0,sy],[0,1,0],[-sy,0,cy]])
    Rz = np.array([[cz,-sz,0],[sz,cz,0],[0,0,1]])
    T[:3,:3] = Rz @ Ry @ Rx
    return T


# ============================================================
#  Motion helpers
# ============================================================

def solve_and_move(
    serial: IRISSerial,
    target_T: np.ndarray,
    dh: List,
    limits: List,
    current_joints: List[float],
    cfg: dict,
    label: str = "move",
) -> Optional[List[float]]:
    """
    IK solve → send MOVEA → wait DONE. Returns new joint angles or None.
    """
    joints = inverse_kinematics(target_T, dh, limits, prefer_config=current_joints)
    if joints is None:
        log.error(f"IK failed for {label}")
        return None

    ok, err = verify_ik(joints, target_T, dh,
                        pos_tol_mm=cfg["ik"]["position_tol_mm"])
    if not ok:
        log.warning(f"IK position error {err:.2f} mm for {label}")

    log.info(f"{label}: {[round(j,2) for j in joints]}")
    if not serial.move_absolute(joints):
        log.error(f"Firmware rejected MOVEA for {label}")
        return None

    if not serial.wait_done(timeout=30.0):
        log.error(f"Timeout waiting for DONE ({label})")
        return None

    time.sleep(cfg["pipeline"]["pick_settle_ms"] / 1000.0)
    return joints


# ============================================================
#  Main pipeline
# ============================================================

class IRISPipeline:
    def __init__(self, cfg_path: str = "config.yaml"):
        self.cfg = load_config(cfg_path)
        self.dh     = dh_from_cfg(self.cfg)
        self.limits = limits_from_cfg(self.cfg)
        self.home_joints = self.cfg["arm"]["home_pose_deg"]
        self.current_joints = list(self.home_joints)
        self.drop_T = drop_pose_from_cfg(self.cfg)

        # Stable detection buffer (require N consecutive frames)
        self._det_history: deque = deque(
            maxlen=self.cfg["pipeline"]["min_detections"]
        )

        self.vision = IRISVision(self.cfg)
        self.serial = IRISSerial(
            port=self.cfg["serial"]["port"],
            baud=self.cfg["serial"]["baud"],
            timeout=self.cfg["serial"]["timeout_s"],
        )

    def connect(self) -> bool:
        if not self.serial.connect():
            return False
        status = self.serial.get_status()
        log.info(f"Firmware status: {status}")
        return True

    def home(self):
        log.info("Homing all joints...")
        if not self.serial.home():
            log.error("Homing command rejected")
            return
        if not self.serial.wait_done(timeout=120.0):
            log.error("Homing timed out")

    def go_home(self):
        log.info("Moving to home pose")
        self.serial.move_absolute(self.home_joints)
        self.serial.wait_done(timeout=30.0)
        self.current_joints = list(self.home_joints)

    def _stable_detection(self, detections: List[Detection]) -> Optional[Detection]:
        """
        Return the most confident detection only if it appears in the last
        min_detections frames at a consistent position (within 1 cm).
        """
        if not detections:
            self._det_history.clear()
            return None

        best = max(detections, key=lambda d: d.confidence)
        self._det_history.append(best)

        if len(self._det_history) < self._det_history.maxlen:
            return None

        # Check positional consistency
        xs = [d.x_m for d in self._det_history]
        ys = [d.y_m for d in self._det_history]
        if max(xs) - min(xs) > 0.01 or max(ys) - min(ys) > 0.01:
            return None   # position still jittering

        return best

    def run(self):
        loop_hz  = self.cfg["pipeline"]["loop_hz"]
        dt       = 1.0 / loop_hz
        approach = self.cfg["arm"]["approach_height_m"]
        table_z  = self.cfg["vision"]["table_z_m"]

        log.info("IRIS pipeline running — press CTRL+C to stop")
        try:
            while True:
                t0 = time.time()

                frame = self.vision.read_frame()
                if frame is None:
                    log.warning("Camera frame failed")
                    time.sleep(dt)
                    continue

                detections = self.vision.detect(frame)
                target = self._stable_detection(detections)

                if target is not None:
                    log.info(f"Stable screw at ({target.x_m:.3f}, {target.y_m:.3f}) m")
                    self._pick_and_place(target, approach, table_z)
                    self._det_history.clear()

                # Throttle
                elapsed = time.time() - t0
                sleep_t = max(0.0, dt - elapsed)
                time.sleep(sleep_t)

        except KeyboardInterrupt:
            log.info("Stopped by user")
        finally:
            self.go_home()
            self.serial.disable()
            self.vision.release()
            self.serial.disconnect()

    def _pick_and_place(self, target: Detection, approach_h: float, table_z: float):
        """Full pick-and-place sequence for one screw."""
        x, y = target.x_m, target.y_m

        # 1. Approach (above screw)
        T_approach = pick_approach_pose(x, y, table_z, approach_h)
        j = solve_and_move(self.serial, T_approach, self.dh, self.limits,
                           self.current_joints, self.cfg, "approach")
        if j is None: return
        self.current_joints = j

        # 2. Descend to pick
        T_pick = pick_pose(x, y, table_z)
        j = solve_and_move(self.serial, T_pick, self.dh, self.limits,
                           self.current_joints, self.cfg, "pick")
        if j is None: return
        self.current_joints = j

        # 3. Close gripper (J6 rotate)
        grip_closed = list(self.current_joints)
        grip_closed[5] = self.cfg["arm"]["grip_close_deg"]
        self.serial.move_absolute(grip_closed)
        self.serial.wait_done(timeout=5.0)
        self.current_joints = grip_closed
        time.sleep(self.cfg["pipeline"]["pick_settle_ms"] / 1000.0)

        # 4. Lift (back to approach height)
        j = solve_and_move(self.serial, T_approach, self.dh, self.limits,
                           self.current_joints, self.cfg, "lift")
        if j is None: return
        self.current_joints = j

        # 5. Move to drop zone
        j = solve_and_move(self.serial, self.drop_T, self.dh, self.limits,
                           self.current_joints, self.cfg, "drop")
        if j is None: return
        self.current_joints = j

        # 6. Open gripper
        grip_open = list(self.current_joints)
        grip_open[5] = self.cfg["arm"]["grip_open_deg"]
        self.serial.move_absolute(grip_open)
        self.serial.wait_done(timeout=5.0)
        self.current_joints = grip_open
        time.sleep(self.cfg["pipeline"]["place_settle_ms"] / 1000.0)

        # 7. Return home
        self.go_home()
        log.info("Pick-and-place complete")


# ============================================================
#  Entry point
# ============================================================

if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default="config.yaml")
    ap.add_argument("--home", action="store_true", help="Run homing sequence on startup")
    args = ap.parse_args()

    pipeline = IRISPipeline(args.config)
    if not pipeline.connect():
        sys.exit(1)

    if args.home:
        pipeline.home()

    pipeline.run()
