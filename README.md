# IRIS — Intelligent Robotic Identification and Sorting

<p align="center">
  <img src="docs/assets/iris_banner.png" alt="IRIS Banner" width="800"/>
</p>

<p align="center">
  <a href="https://jonahchang207.github.io/IRIS-Progect"><img src="https://img.shields.io/badge/docs-GitHub%20Pages-blue?style=flat-square" alt="Docs"/></a>
  <img src="https://img.shields.io/badge/platform-Teensy%204.1-orange?style=flat-square" alt="Platform"/>
  <img src="https://img.shields.io/badge/model-YOLOv11s-green?style=flat-square" alt="Model"/>
  <img src="https://img.shields.io/badge/DOF-6-purple?style=flat-square" alt="DOF"/>
  <img src="https://img.shields.io/badge/license-MIT-lightgrey?style=flat-square" alt="License"/>
</p>

A 6DOF 3D-printed robotic arm that uses a YOLOv11 vision model to detect screws and autonomously pick and sort them. Full pipeline from YOLO training on Google Colab through inverse kinematics to stepper motor control on a Teensy 4.1.

---

## System Overview

```
┌─────────────┐    USB Serial    ┌──────────────┐    STEP/DIR/EN    ┌──────────────┐
│   Host PC   │ ───────────────► │  Teensy 4.1  │ ────────────────► │  6x DM542T   │
│  (Python)   │ ◄─────────────── │  Firmware    │                   │  Drivers     │
└─────────────┘   OK/DONE/POS    └──────────────┘                   └──────┬───────┘
       │                                                                    │
       │  Camera                                               ┌────────────┴────────────┐
       ▼                                                       │  J1-J2: NEMA 23         │
  ┌─────────┐   YOLOv11s    ┌──────────┐   IK Solver          │  J3-J6: NEMA 17         │
  │  Camera │ ──────────►   │ Detection│ ──────────► Joints   └─────────────────────────┘
  └─────────┘               └──────────┘
```

**Hardware:** Teensy 4.1 · 6× DM542T drivers · 2× NEMA 23 (J1–J2) · 4× NEMA 17 (J3–J6) · 6× limit switches
**Software:** YOLOv11s · Analytical 6DOF IK · Trapezoidal trajectory · Python orchestration

**[Full documentation →](https://jonahchang207.github.io/IRIS-Progect)**

---

## Repository Structure

```
IRIS Progect/
├── colab/
│   └── IRIS_train.ipynb        # YOLOv11s training notebook (2000 epochs)
├── firmware/
│   └── IRIS_firmware/          # PlatformIO project for Teensy 4.1
│       ├── platformio.ini
│       └── src/
│           ├── main.cpp
│           ├── config.h        # ← fill in pin numbers + motor constants here
│           ├── stepper.h/cpp   # DM542T axis abstraction
│           ├── protocol.h/cpp  # USB serial command protocol
│           └── homing.h/cpp    # Limit switch homing state machine
├── host/
│   ├── main.py                 # Master pipeline (camera → vision → IK → arm)
│   ├── vision.py               # YOLO inference + world-coordinate projection
│   ├── serial_comm.py          # Teensy serial interface
│   ├── calibrate_camera.py     # Checkerboard camera calibration
│   └── config.yaml             # ← all tunables in one place
├── ik/
│   ├── forward_kinematics.py   # Modified DH forward kinematics
│   ├── inverse_kinematics.py   # Analytical IK (spherical wrist)
│   └── trajectory.py           # Synchronised trapezoidal velocity profiles
├── models/                     # Trained weights (not tracked by git)
├── docs/                       # GitHub Pages documentation
└── TODO.md
```

---

## Quick Start

### 1 — Train the vision model

Open `colab/IRIS_train.ipynb` in Google Colab (Runtime → T4 GPU).
Fill in the CONFIG cell with your [Roboflow](https://universe.roboflow.com) dataset details, then run all cells.
Download `best.pt` and `best.onnx` into `models/`.

### 2 — Flash the firmware

```bash
cd firmware/IRIS_firmware
# Edit src/config.h — set your pin numbers, steps/rev, gear ratios
pio run --target upload
```

### 3 — Calibrate the camera

```bash
cd host
python calibrate_camera.py
# Hold a checkerboard in front of the camera
# Press SPACE for 15+ captures, ESC to compute
```

### 4 — Run the pipeline

```bash
cd host
python main.py --home    # --home runs homing sequence on startup
```

---

## Hardware

| Component | Spec |
|-----------|------|
| Controller | Teensy 4.1 |
| Stepper drivers | 6× DM542T |
| Joints 1–2 | NEMA 23 stepper motors |
| Joints 3–6 | NEMA 17 stepper motors |
| Host connection | USB Serial |
| Vision | USB camera (calibrated) |
| Homing | 6× limit switches (NO, active-low) |

---

## Serial Protocol

All commands are ASCII, newline-terminated.

| Command | Description | Response |
|---------|-------------|----------|
| `MOVEA j1 j2 j3 j4 j5 j6` | Absolute move in degrees | `OK` then `DONE` |
| `HOME [n]` | Home all joints, or joint n (1-indexed) | `OK` then `DONE` |
| `POS` | Query joint positions | `POS d1 d2 d3 d4 d5 d6` |
| `STATUS` | Query system state | `STATUS IDLE\|MOVING\|HOMING\|ESTOP` |
| `ESTOP` | Immediate stop all axes | `OK` |
| `ENABLE` | Enable all drivers | `OK` |
| `DISABLE` | Disable all drivers | `OK` |
| `SPEED s1 s2 s3 s4 s5 s6` | Set max speed (steps/sec) | `OK` |

---

## Placeholders

All physical constants that depend on your specific build are marked `// PLACEHOLDER` in `src/config.h` and `# PLACEHOLDER` in `host/config.yaml`. A grep will find them all:

```bash
grep -r "PLACEHOLDER" firmware/ host/
```

Key values to fill in:
- Pin assignments (STEP/DIR/EN/LIMIT per joint)
- Microstepping setting from DM542T dip switches
- Gear/belt reduction ratios
- DH parameters (link lengths) from your CAD
- Camera extrinsic transform (after hand-eye calibration)
- Drop zone pose

---

## License

MIT
