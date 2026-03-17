---
title: Host Pipeline
layout: default
nav_order: 7
---

# Host Pipeline
{: .no_toc }

Python orchestration — camera, vision, IK, serial, and the master pick-and-place loop.
{: .fs-6 .fw-300 }

<details open markdown="block">
  <summary>Table of contents</summary>
  {: .text-delta }
- TOC
{:toc}
</details>

---

## File Overview

| File | Purpose |
|------|---------|
| `main.py` | Master pipeline — start here |
| `vision.py` | YOLO inference + world-coordinate projection |
| `serial_comm.py` | Thread-safe Teensy serial interface |
| `calibrate_camera.py` | Interactive checkerboard calibration tool |
| `config.yaml` | All tunables in one place |

---

## Running the Pipeline

```bash
cd host

# Normal start (assumes arm is already at home)
python main.py

# Start with homing sequence
python main.py --home

# Use a different config file
python main.py --config /path/to/other_config.yaml
```

---

## Pick-and-Place Sequence

Each detected screw goes through this sequence:

```
┌──────────────────────────────────────────────────┐
│  1. APPROACH  — IK to (x, y, z_table + height)  │
│  2. DESCEND   — IK to (x, y, z_table)           │
│  3. GRIP      — J6 rotates to grip_close_deg    │
│  4. LIFT      — IK back to approach height       │
│  5. TRANSPORT — IK to drop_pose                  │
│  6. RELEASE   — J6 rotates to grip_open_deg     │
│  7. HOME      — Return to home_pose_deg          │
└──────────────────────────────────────────────────┘
```

---

## Serial Communication (`serial_comm.py`)

`IRISSerial` spawns a background reader thread that continuously drains the serial port into a `queue.Queue`. This prevents buffer overflow and allows the main thread to block on `wait_done()` without polling.

**Auto-detection:** The Teensy 4.1 is identified by USB VID:PID `16C0:0483`. If not found, falls back to any `/dev/ttyACM*` or `usbmodem` device.

```python
from serial_comm import IRISSerial

with IRISSerial() as arm:
    arm.home()
    arm.wait_done(timeout=120)

    arm.move_absolute([30, -20, 45, 0, 90, 0])
    arm.wait_done()

    pos = arm.get_position()   # [j1..j6] in degrees
    print(pos)
```

---

## Vision (`vision.py`)

```python
from vision import IRISVision

v = IRISVision(cfg)

frame = v.read_frame()
detections = v.detect(frame)

for d in detections:
    print(f"Screw at ({d.x_m:.3f}, {d.y_m:.3f}, {d.z_m:.3f}) m  conf={d.confidence:.2f}")

annotated = v.annotate_frame(frame, detections)
```

Each `Detection` contains:
- `x_m`, `y_m`, `z_m` — world position in robot base frame (metres)
- `confidence` — YOLO confidence score
- `bbox_px` — `(x1, y1, x2, y2)` pixel bounding box

---

## Configuration Reference (`config.yaml`)

All values in one place. Anything marked `# PLACEHOLDER` needs to be set for your specific build.

### `serial`

```yaml
serial:
  port: auto          # 'auto' or explicit e.g. '/dev/ttyACM0', 'COM5'
  baud: 115200
  timeout_s: 5.0
```

### `camera`

```yaml
camera:
  index: 0            # OpenCV camera index
  width: 1280         # PLACEHOLDER — match your camera
  height: 720         # PLACEHOLDER
  fps: 30
  calibration_file: "models/camera_calibration.npz"
```

### `vision`

```yaml
vision:
  model_path: "models/IRIS_best.pt"
  conf_threshold: 0.50
  iou_threshold: 0.45
  T_cam_to_base:      # PLACEHOLDER — 4x4 camera-to-base transform
    - [1, 0, 0, 0]
    - [0, 1, 0, 0]
    - [0, 0, 1, 0.3]
    - [0, 0, 0, 1]
  table_z_m: 0.0      # PLACEHOLDER — z height of table surface in base frame
```

### `ik`

```yaml
ik:
  dh_params:          # PLACEHOLDER — measure from CAD
    - [0.000,  90.0, 0.100, 0.0]   # J1
    - [0.250,   0.0, 0.000, 0.0]   # J2
    - [0.220,   0.0, 0.000, 0.0]   # J3
    - [0.000,  90.0, 0.000, 0.0]   # J4
    - [0.000, -90.0, 0.000, 0.0]   # J5
    - [0.000,   0.0, 0.080, 0.0]   # J6
  joint_limits:
    j1: [-170, 170]
    # ...
  position_tol_mm: 0.5
```

### `arm`

```yaml
arm:
  home_pose_deg: [0, 0, 90, 0, 90, 0]     # PLACEHOLDER
  approach_height_m: 0.08                  # PLACEHOLDER
  grip_close_deg: 45.0                     # PLACEHOLDER
  grip_open_deg: 0.0
  drop_pose_m: [0.20, 0.20, 0.15, 0, 180, 0]  # PLACEHOLDER
```

### `pipeline`

```yaml
pipeline:
  loop_hz: 10           # detection loop rate
  pick_settle_ms: 300   # wait after arm stops before gripping
  place_settle_ms: 300
  min_detections: 3     # frames screw must appear before triggering pick
```

---

## Finding all Placeholders

```bash
grep -rn "PLACEHOLDER" host/ firmware/
```
