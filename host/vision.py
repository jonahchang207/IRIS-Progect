"""
IRIS — Vision Module
YOLO screw detection + pixel-to-world coordinate projection.
"""

import cv2
import numpy as np
import yaml
import logging
from pathlib import Path
from typing import Optional, List, Tuple
from dataclasses import dataclass
from ultralytics import YOLO

log = logging.getLogger(__name__)


@dataclass
class Detection:
    """One detected screw in world coordinates."""
    x_m: float          # world X (metres, robot base frame)
    y_m: float          # world Y
    z_m: float          # world Z (table surface)
    confidence: float
    bbox_px: Tuple[int, int, int, int]   # (x1, y1, x2, y2) in image


class IRISVision:
    def __init__(self, cfg: dict):
        v = cfg["vision"]
        c = cfg["camera"]

        self._conf   = v["conf_threshold"]
        self._iou    = v["iou_threshold"]
        self._imgsz  = v["imgsz"]
        self._device = v["device"]
        self._table_z = v["table_z_m"]

        # Camera-to-base extrinsic (4x4)
        self._T_cam_base = np.array(v["T_cam_to_base"], dtype=np.float64)

        # Camera intrinsics — loaded from calibration file
        cal_file = Path(v["calibration_file"])
        if cal_file.exists():
            data = np.load(cal_file)
            self._K    = data["K"]
            self._dist = data["dist"]
            log.info(f"Loaded camera calibration from {cal_file}")
        else:
            log.warning(f"Calibration file {cal_file} not found — using identity (PLACEHOLDER)")
            # PLACEHOLDER: identity intrinsics — run calibrate_camera.py first
            fx = fy = c["width"]   # rough guess: focal = image width
            self._K    = np.array([[fx, 0, c["width"]/2],
                                   [0, fy, c["height"]/2],
                                   [0,  0, 1]], dtype=np.float64)
            self._dist = np.zeros(5, dtype=np.float64)

        # Camera capture
        self._cap = cv2.VideoCapture(c["index"])
        self._cap.set(cv2.CAP_PROP_FRAME_WIDTH,  c["width"])
        self._cap.set(cv2.CAP_PROP_FRAME_HEIGHT, c["height"])
        self._cap.set(cv2.CAP_PROP_FPS,          c["fps"])

        # YOLO model
        model_path = Path(v["model_path"])
        if not model_path.exists():
            raise FileNotFoundError(f"Model not found: {model_path} — train and export first")
        self._model = YOLO(str(model_path))
        log.info(f"Loaded YOLO model: {model_path}")

    # ---- frame acquisition ---------------------------------

    def read_frame(self) -> Optional[np.ndarray]:
        ret, frame = self._cap.read()
        return frame if ret else None

    # ---- detection -----------------------------------------

    def detect(self, frame: np.ndarray) -> List[Detection]:
        """
        Run YOLO on frame, project detections to world coordinates.
        Returns list of Detection objects in robot base frame.
        """
        results = self._model(
            frame,
            conf=self._conf,
            iou=self._iou,
            imgsz=self._imgsz,
            device=self._device,
            verbose=False,
        )[0]

        detections = []
        for box in results.boxes:
            x1, y1, x2, y2 = map(int, box.xyxy[0].tolist())
            cx = (x1 + x2) / 2.0
            cy = (y1 + y2) / 2.0
            conf = float(box.conf[0])

            world_pt = self._pixel_to_world(cx, cy)
            if world_pt is not None:
                detections.append(Detection(
                    x_m=world_pt[0], y_m=world_pt[1], z_m=world_pt[2],
                    confidence=conf,
                    bbox_px=(x1, y1, x2, y2),
                ))

        return detections

    # ---- coordinate transform ------------------------------

    def _pixel_to_world(self, px: float, py: float) -> Optional[np.ndarray]:
        """
        Project a pixel centroid onto the table plane (z = table_z_m in base frame).

        Method: ray-plane intersection
          1. Undistort pixel → normalised image coords
          2. Express ray in camera frame
          3. Transform ray to base frame
          4. Intersect with z = table_z plane
        """
        # 1. Undistort
        pt = cv2.undistortPoints(
            np.array([[[px, py]]], dtype=np.float32),
            self._K, self._dist, P=self._K
        )[0][0]

        # 2. Ray in camera frame (normalised)
        K_inv  = np.linalg.inv(self._K)
        ray_c  = K_inv @ np.array([pt[0], pt[1], 1.0])

        # 3. Ray in base frame
        R_cb   = self._T_cam_base[:3, :3]
        t_cb   = self._T_cam_base[:3,  3]
        ray_b  = R_cb @ ray_c
        origin = t_cb   # camera origin in base frame

        # 4. Intersect with z = table_z plane:  origin + lambda * ray_b = [x, y, table_z]
        if abs(ray_b[2]) < 1e-9:
            return None   # ray parallel to table
        lam = (self._table_z - origin[2]) / ray_b[2]
        if lam < 0:
            return None   # intersection behind camera
        pt_world = origin + lam * ray_b
        return pt_world

    # ---- visualisation -------------------------------------

    def annotate_frame(self, frame: np.ndarray, detections: List[Detection]) -> np.ndarray:
        out = frame.copy()
        for d in detections:
            x1, y1, x2, y2 = d.bbox_px
            cv2.rectangle(out, (x1, y1), (x2, y2), (0, 255, 0), 2)
            label = f"screw {d.confidence:.2f} ({d.x_m*100:.1f},{d.y_m*100:.1f})cm"
            cv2.putText(out, label, (x1, y1 - 6),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)
        return out

    # ---- cleanup -------------------------------------------

    def release(self):
        self._cap.release()

    def __del__(self):
        self.release()
