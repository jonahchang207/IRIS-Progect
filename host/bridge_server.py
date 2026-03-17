"""
IRIS Bridge Server
FastAPI + WebSocket server that exposes the Python backend to the Flutter UI.
Wraps IRISSerial, IRISVision, IRISPipeline without modifying them.

Endpoints:
  WS  /ws/joints    10 Hz  joint positions + system status
  WS  /ws/camera    15 Hz  annotated JPEG frame + detections
  WS  /ws/log       event  log messages

  POST /cmd/estop
  POST /cmd/home          {"joint": null | 1-6}
  POST /cmd/movej         {"angles": [j1..j6]}
  POST /cmd/jog           {"joint": 0-5, "delta_deg": float}
  POST /cmd/enable
  POST /cmd/disable
  POST /cmd/pipeline/start
  POST /cmd/pipeline/stop
  POST /cmd/arm_sequence  runs full init sequence, locks config on success

  GET  /status
  GET  /config            returns config.yaml as JSON + {"locked": bool}
  PUT  /config            403 if arm sequence complete (config locked)
  GET  /fk                current FK — all 7 frame transforms as flat arrays
"""

from __future__ import annotations

import asyncio
import base64
import json
import logging
import sys
import threading
import time
from pathlib import Path
from typing import Any, Optional

import cv2
import numpy as np
import uvicorn
import yaml
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

# ── project imports ──────────────────────────────────────────────────────────
sys.path.insert(0, str(Path(__file__).parent))
from serial_comm import IRISSerial
from vision import IRISVision

sys.path.insert(0, str(Path(__file__).parent.parent / "ik"))
from forward_kinematics import all_frame_transforms

# ── logging ──────────────────────────────────────────────────────────────────
log = logging.getLogger("iris.bridge")


class _WSLogHandler(logging.Handler):
    """Broadcasts log records to all connected /ws/log clients."""
    def __init__(self):
        super().__init__()
        self._clients: set[WebSocket] = set()

    def register(self, ws: WebSocket):   self._clients.add(ws)
    def unregister(self, ws: WebSocket): self._clients.discard(ws)

    def emit(self, record: logging.LogRecord):
        msg = {"level": record.levelname, "msg": self.format(record)}
        dead = set()
        for ws in self._clients:
            try:
                asyncio.get_event_loop().call_soon_threadsafe(
                    asyncio.ensure_future, ws.send_text(json.dumps(msg))
                )
            except Exception:
                dead.add(ws)
        self._clients -= dead


_ws_log_handler = _WSLogHandler()
_ws_log_handler.setFormatter(logging.Formatter("%(asctime)s %(name)s: %(message)s"))
logging.getLogger().addHandler(_ws_log_handler)
logging.getLogger().setLevel(logging.DEBUG)

# ── config ────────────────────────────────────────────────────────────────────
_CFG_PATH = Path(__file__).parent / "config.yaml"


def _load_cfg() -> dict:
    with open(_CFG_PATH) as f:
        return yaml.safe_load(f)


def _save_cfg(data: dict):
    with open(_CFG_PATH, "w") as f:
        yaml.dump(data, f, default_flow_style=False)


# ── global state ─────────────────────────────────────────────────────────────
_cfg: dict = _load_cfg()
_serial: Optional[IRISSerial] = None
_vision: Optional[IRISVision] = None
_pipeline_thread: Optional[threading.Thread] = None
_pipeline_stop = threading.Event()
_arm_initialized: bool = False   # set True after arm_sequence — config locked
_last_joints: list[float] = [0.0] * 6
_last_status: str = "IDLE"
_last_frame_bytes: Optional[bytes] = None
_last_detections: list[dict] = []
_frame_lock = threading.Lock()
_joints_lock = threading.Lock()

# ── FastAPI app ───────────────────────────────────────────────────────────────
app = FastAPI(title="IRIS Bridge", version="1.0.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"],
                   allow_methods=["*"], allow_headers=["*"])


# ── startup / shutdown ────────────────────────────────────────────────────────
@app.on_event("startup")
async def _startup():
    global _serial, _vision, _cfg
    _cfg = _load_cfg()

    # Serial
    _serial = IRISSerial(
        port=_cfg["serial"]["port"],
        baud=_cfg["serial"]["baud"],
        timeout=_cfg["serial"]["timeout_s"],
    )
    if _serial.connect():
        log.info("Serial connected")
        _serial.enable()
    else:
        log.warning("Serial not connected — continuing without arm")
        _serial = None

    # Vision
    try:
        _vision = IRISVision(_cfg)
        log.info("Vision initialised")
    except FileNotFoundError as e:
        log.warning(f"Vision unavailable: {e}")
        _vision = None

    # Background poller
    asyncio.create_task(_joints_poller())
    asyncio.create_task(_camera_poller())


@app.on_event("shutdown")
async def _shutdown():
    global _serial, _vision
    if _serial:
        _serial.disable()
        _serial.disconnect()
    if _vision:
        _vision.release()


# ── background pollers ────────────────────────────────────────────────────────
async def _joints_poller():
    global _last_joints, _last_status
    while True:
        if _serial and _serial.is_connected():
            pos = _serial.get_position()
            status = _serial.get_status() or "IDLE"
            with _joints_lock:
                if pos:
                    _last_joints = pos
                _last_status = status
        await asyncio.sleep(0.1)   # 10 Hz


async def _camera_poller():
    global _last_frame_bytes, _last_detections
    while True:
        if _vision:
            frame = _vision.read_frame()
            if frame is not None:
                dets = _vision.detect(frame)
                annotated = _vision.annotate_frame(frame, dets)
                ok, buf = cv2.imencode(
                    ".jpg", annotated, [cv2.IMWRITE_JPEG_QUALITY, 72]
                )
                if ok:
                    with _frame_lock:
                        _last_frame_bytes = buf.tobytes()
                        _last_detections = [
                            {"x_m": d.x_m, "y_m": d.y_m, "z_m": d.z_m,
                             "conf": d.confidence,
                             "bbox": list(d.bbox_px)}
                            for d in dets
                        ]
        await asyncio.sleep(1 / 15)   # 15 Hz


# ── WebSocket endpoints ────────────────────────────────────────────────────────
@app.websocket("/ws/joints")
async def ws_joints(ws: WebSocket):
    await ws.accept()
    try:
        while True:
            with _joints_lock:
                payload = {"joints": _last_joints, "status": _last_status,
                           "initialized": _arm_initialized}
            await ws.send_text(json.dumps(payload))
            await asyncio.sleep(0.1)
    except WebSocketDisconnect:
        pass


@app.websocket("/ws/camera")
async def ws_camera(ws: WebSocket):
    await ws.accept()
    try:
        while True:
            with _frame_lock:
                frame_b64 = (
                    base64.b64encode(_last_frame_bytes).decode()
                    if _last_frame_bytes else ""
                )
                dets = list(_last_detections)
            payload = {"frame_b64": frame_b64, "detections": dets}
            await ws.send_text(json.dumps(payload))
            await asyncio.sleep(1 / 15)
    except WebSocketDisconnect:
        pass


@app.websocket("/ws/log")
async def ws_log(ws: WebSocket):
    await ws.accept()
    _ws_log_handler.register(ws)
    try:
        while True:
            await asyncio.sleep(30)   # keep-alive
    except WebSocketDisconnect:
        pass
    finally:
        _ws_log_handler.unregister(ws)


# ── REST helpers ──────────────────────────────────────────────────────────────
def _require_serial():
    if not _serial or not _serial.is_connected():
        raise HTTPException(503, "Serial not connected")


def _require_initialized():
    if not _arm_initialized:
        raise HTTPException(403, "Arm sequence not complete — run /cmd/arm_sequence first")


# ── motion commands ────────────────────────────────────────────────────────────
@app.post("/cmd/estop")
async def cmd_estop():
    """Immediate stop — no serial connection required to call."""
    if _serial and _serial.is_connected():
        _serial.estop()
    log.warning("ESTOP triggered")
    return {"ok": True}


@app.post("/cmd/enable")
async def cmd_enable():
    _require_serial()
    _serial.enable()
    _serial.recv()
    return {"ok": True}


@app.post("/cmd/disable")
async def cmd_disable():
    _require_serial()
    _serial.disable()
    _serial.recv()
    return {"ok": True}


@app.post("/cmd/home")
async def cmd_home(body: dict = {}):
    _require_serial()
    _require_initialized()
    joint = body.get("joint")   # null → home all, 1-6 → specific
    ok = _serial.home(joint=joint)
    if not ok:
        raise HTTPException(500, "Homing command rejected by firmware")
    return {"ok": True}


@app.post("/cmd/movej")
async def cmd_movej(body: dict):
    _require_serial()
    _require_initialized()
    angles = body.get("angles")
    if not angles or len(angles) != 6:
        raise HTTPException(422, "angles must be a list of 6 floats")
    ok = _serial.move_absolute([float(a) for a in angles])
    if not ok:
        raise HTTPException(500, "MOVEA rejected by firmware")
    return {"ok": True}


@app.post("/cmd/jog")
async def cmd_jog(body: dict):
    _require_serial()
    _require_initialized()
    joint = int(body.get("joint", 0))
    delta = float(body.get("delta_deg", 1.0))
    if not 0 <= joint <= 5:
        raise HTTPException(422, "joint must be 0-5")
    with _joints_lock:
        current = list(_last_joints)
    current[joint] = current[joint] + delta
    ok = _serial.move_absolute(current)
    if not ok:
        raise HTTPException(500, "Jog rejected by firmware")
    return {"ok": True, "target": current}


# ── pipeline ──────────────────────────────────────────────────────────────────
@app.post("/cmd/pipeline/start")
async def cmd_pipeline_start():
    global _pipeline_thread
    _require_serial()
    _require_initialized()
    if _pipeline_thread and _pipeline_thread.is_alive():
        raise HTTPException(409, "Pipeline already running")

    _pipeline_stop.clear()

    # Import here to avoid circular at module load
    from main import IRISPipeline

    def _run():
        try:
            p = IRISPipeline()
            p.serial = _serial    # reuse existing connection
            p.vision = _vision    # reuse existing vision
            p.run()
        except Exception as e:
            log.error(f"Pipeline error: {e}")

    _pipeline_thread = threading.Thread(target=_run, daemon=True)
    _pipeline_thread.start()
    log.info("Pipeline started")
    return {"ok": True}


@app.post("/cmd/pipeline/stop")
async def cmd_pipeline_stop():
    _pipeline_stop.set()
    log.info("Pipeline stop requested")
    return {"ok": True}


# ── arm initialisation sequence ───────────────────────────────────────────────
@app.post("/cmd/arm_sequence")
async def cmd_arm_sequence():
    """
    Full arm initialisation sequence:
      1. Enable drivers
      2. Home all joints
      3. Wait for DONE (120s timeout)
      4. Verify all joints ≈ 0°
      5. Move to home_pose_deg
      6. Lock config (_arm_initialized = True)
    """
    global _arm_initialized
    _require_serial()

    if _arm_initialized:
        return {"ok": True, "msg": "Already initialised"}

    log.info("ARM SEQUENCE: starting")

    # 1. Enable
    _serial.enable()
    await asyncio.sleep(0.5)

    # 2. Home all
    log.info("ARM SEQUENCE: homing all joints")
    ok = _serial.home()
    if not ok:
        raise HTTPException(500, "Homing rejected by firmware")

    # Wait for DONE in a non-blocking way
    deadline = time.time() + 120
    while time.time() < deadline:
        await asyncio.sleep(0.5)
        with _joints_lock:
            status = _last_status
        if status == "IDLE":
            break
    else:
        raise HTTPException(504, "Homing timed out after 120s")

    # 3. Verify joints near 0
    with _joints_lock:
        pos = list(_last_joints)
    for i, j in enumerate(pos):
        if abs(j) > 5.0:   # 5° tolerance post-home
            raise HTTPException(500, f"J{i+1} post-home position {j:.1f}° not near 0")

    # 4. Move to home_pose
    home_pose = _cfg["arm"]["home_pose_deg"]
    log.info(f"ARM SEQUENCE: moving to home pose {home_pose}")
    ok = _serial.move_absolute(home_pose)
    if not ok:
        raise HTTPException(500, "Move to home pose rejected")

    deadline = time.time() + 30
    while time.time() < deadline:
        await asyncio.sleep(0.3)
        with _joints_lock:
            status = _last_status
        if status == "IDLE":
            break

    # 5. Lock config
    _arm_initialized = True
    log.info("ARM SEQUENCE: complete — config LOCKED")
    return {"ok": True, "msg": "Arm sequence complete. Config is now locked."}


# ── config endpoints ──────────────────────────────────────────────────────────
@app.get("/config")
async def get_config():
    cfg = _load_cfg()
    return {"config": cfg, "locked": _arm_initialized}


@app.put("/config")
async def put_config(body: dict):
    if _arm_initialized:
        raise HTTPException(403, "Config locked after arm sequence — ESTOP and reset to change")
    cfg = _load_cfg()
    # Deep merge
    def _merge(base, patch):
        for k, v in patch.items():
            if isinstance(v, dict) and isinstance(base.get(k), dict):
                _merge(base[k], v)
            else:
                base[k] = v
    _merge(cfg, body)
    _save_cfg(cfg)
    global _cfg
    _cfg = cfg
    return {"ok": True}


# ── status + FK ───────────────────────────────────────────────────────────────
@app.get("/status")
async def get_status():
    return {
        "serial_connected": bool(_serial and _serial.is_connected()),
        "vision_active": bool(_vision),
        "status": _last_status,
        "joints": _last_joints,
        "initialized": _arm_initialized,
        "pipeline_running": bool(_pipeline_thread and _pipeline_thread.is_alive()),
    }


@app.get("/fk")
async def get_fk():
    """Returns all 7 cumulative frame transforms (4×4) for current joint angles."""
    with _joints_lock:
        joints = list(_last_joints)
    dh = _cfg["ik"]["dh_params"]
    transforms = all_frame_transforms(joints, dh)
    return {
        "joints": joints,
        "transforms": [T.tolist() for T in transforms],
    }


# ── entry point ───────────────────────────────────────────────────────────────
if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8765, log_level="info")
