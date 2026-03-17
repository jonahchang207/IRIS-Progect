# IRIS Project — Master TODO
> Intelligent Robotic Identification and Sorting | 6DOF Robotic Arm

---

## Phase 1 — Vision System (YOLO Screw Detection)

- [ ] **1.1** Source screw/fastener dataset (≥1k images, YOLO format)
  - → Go to universe.roboflow.com, search "screw detection", download YOLOv11 format
  - → Paste API key + dataset slug into CONFIG cell in `colab/IRIS_train.ipynb`
- [x] **1.2** Build Google Colab training notebook (`colab/IRIS_train.ipynb`) ✓
  - YOLOv11s | 2000 epochs | patience=100 | Roboflow dataset pull | ONNX export
  - Appendix: Albumentations 3x augmentation if dataset < 1k images
- [ ] **1.3** Train model — run notebook, download `best.pt` + `best.onnx` → `models/`
- [ ] **1.4** Validate: mAP@0.5 ≥ 0.85
- [x] **1.5** PC inference script (`host/vision.py`) ✓
  - OpenCV feed → YOLO → pixel-to-world ray-plane projection

---

## Phase 2 — Inverse Kinematics

- [ ] **2.1** Fill in real DH parameters in `host/config.yaml` (ik.dh_params) once arm is built
- [x] **2.2** Forward kinematics (`ik/forward_kinematics.py`) ✓ — Modified DH, full transform chain
- [x] **2.3** IK solver (`ik/inverse_kinematics.py`) ✓ — Analytical spherical wrist, elbow-up/down, closest-config selection
- [ ] **2.4** Run `python ik/inverse_kinematics.py` after entering real DH params — verify FK/IK round-trip error < 0.5 mm
- [x] **2.5** Trajectory planner (`ik/trajectory.py`) ✓ — synchronised trapezoidal velocity profile

---

## Phase 3 — Teensy 4.1 Firmware

- [x] **3.1** PlatformIO project (`firmware/IRIS_firmware/`) ✓
- [x] **3.2** DM542T driver interface (`src/stepper.h/.cpp`) ✓
  - STEP/DIR/EN per axis | NEMA23 J1-J2 / NEMA17 J3-J6 | degree-based API
- [x] **3.3** AccelStepper control core ✓ — per-axis speed/accel, degree↔step conversion, gear ratio support
- [x] **3.4** Serial protocol (`src/protocol.h/.cpp`) ✓
  - `MOVEA`, `HOME`, `POS`, `STATUS`, `SPEED`, `ENABLE`, `DISABLE`, `ESTOP`
- [x] **3.5** Safety ✓ — soft limits per joint, ESTOP immediate stop, WARN on clamp
- [x] **3.6** Homing state machine (`src/homing.h/.cpp`) ✓ — fast seek → back-off → slow creep → zero
- [ ] **3.7** Fill in real pin numbers in `src/config.h` once wired to breakout board
- [ ] **3.8** Set real microstepping value (STEPS_REV_NEMA23/17) from DM542T dip switches
- [ ] **3.9** Bench test: `pio run -t upload` → open serial monitor → send `STATUS`, `MOVEA 10 0 0 0 0 0`

---

## Phase 4 — Host PC Orchestration

- [x] **4.1** Serial module (`host/serial_comm.py`) ✓ — auto-detect Teensy VID:PID, threaded RX, full command API
- [x] **4.2** Main pipeline (`host/main.py`) ✓ — camera→vision→IK→serial loop, stable-detection filter, full pick-and-place sequence
- [x] **4.3** Camera calibration (`host/calibrate_camera.py`) ✓ — checkerboard intrinsics, reprojection error check
- [x] **4.4** Config (`host/config.yaml`) ✓ — all tunables in one place, all PLACEHOLDERs labelled
- [ ] **4.5** Run `python host/calibrate_camera.py` → fills `models/camera_calibration.npz`
- [ ] **4.6** Hand-eye calibration: measure camera-to-base transform → update `T_cam_to_base` in config.yaml
- [ ] **4.7** Set real `drop_pose_m` coordinates in config.yaml

---

## Phase 5 — Integration & Testing

- [ ] **5.1** Bench test: each joint individually, verify steps/revolution
- [ ] **5.2** End-to-end test: place screw in camera FOV → arm picks and places
- [ ] **5.3** Tune IK solver for real-world accuracy (compare FK prediction vs actual)
- [ ] **5.4** Tune YOLO confidence threshold for production false-positive rate

---

## Open Questions (Need Answers Before Code)

| # | Question | Blocks |
| --- | --- | --- |
| Q1 | What are the arm link lengths (L1–L6 in mm)? | Phase 2 IK |
| Q2 | What microstepping setting on DM542T dip switches? (e.g. 1/4, 1/8, 1/16) | Phase 3 stepper |
| Q3 | Steps/revolution for NEMA 23 and 17 (200 standard, confirm)? | Phase 3 stepper |
| Q4 | Is there a camera model/resolution already chosen? | Phase 1 vision |
| Q5 | Are limit switches / homing sensors installed? | Phase 3 homing |
| Q6 | What is the sort target — one class (screws only) or multiple (screws, bolts, nuts)? | Phase 1 dataset |

---

## Project Structure (Target)

```text
IRIS Progect/
├── colab/
│   └── IRIS_train.ipynb          # YOLOv11 training notebook
├── firmware/
│   └── IRIS_firmware/            # PlatformIO Teensy 4.1 project
│       ├── src/main.cpp
│       ├── src/stepper.h/.cpp
│       ├── src/protocol.h/.cpp
│       └── platformio.ini
├── host/
│   ├── vision.py                 # YOLO inference + camera feed
│   ├── serial_comm.py            # Teensy serial interface
│   ├── calibrate_camera.py       # Camera calibration
│   ├── main.py                   # Master orchestration loop
│   └── config.yaml               # All tunables
├── ik/
│   ├── forward_kinematics.py
│   ├── inverse_kinematics.py
│   └── trajectory.py
├── models/                       # Trained weights (.pt, .onnx)
└── TODO.md
```
