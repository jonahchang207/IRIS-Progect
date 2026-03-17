---
title: Home
layout: home
nav_order: 1
---

# IRIS — Intelligent Robotic Identification and Sorting
{: .fs-9 }

A 6DOF 3D-printed robotic arm that uses a YOLOv11 vision model to detect screws and autonomously pick and sort them.
{: .fs-6 .fw-300 }

[Get Started]({{ site.baseurl }}/pages/setup){: .btn .btn-primary .fs-5 .mb-4 .mb-md-0 .mr-2 }
[View on GitHub](https://github.com/jonahchang/IRIS-Progect){: .btn .fs-5 .mb-4 .mb-md-0 }

---

## System Architecture

```
┌─────────────┐    USB Serial    ┌──────────────┐    STEP/DIR/EN    ┌─────────────┐
│   Host PC   │ ───────────────► │  Teensy 4.1  │ ────────────────► │  6x DM542T  │
│  (Python)   │ ◄─────────────── │  Firmware    │                   │  Drivers    │
└─────────────┘   OK/DONE/POS    └──────────────┘                   └──────┬──────┘
       │                                                                    │
       │  Camera (USB)                                       NEMA 23 (J1-J2)│
       ▼                                                     NEMA 17 (J3-J6)│
  ┌─────────┐  YOLOv11s   ┌───────────┐  IK Solver   ┌─────────────────────┘
  │  Camera │ ──────────► │ Detection │ ──────────► Joints
  └─────────┘             └───────────┘
```

## What IRIS Does

1. **Detects** screws in a camera feed using a YOLOv11s model trained on Roboflow data
2. **Localises** each screw in 3D space via camera calibration and ray-plane intersection
3. **Plans** a pick trajectory using a closed-form analytical 6DOF IK solver
4. **Executes** the pick-and-place motion by sending degree commands over USB serial to a Teensy 4.1
5. **Controls** 6 DM542T stepper drivers with full homing, soft limits, and E-stop

## Hardware At a Glance

| Component | Details |
|-----------|---------|
| Controller | Teensy 4.1 |
| Stepper Drivers | 6× DM542T |
| Joints 1–2 | NEMA 23 stepper motors |
| Joints 3–6 | NEMA 17 stepper motors |
| Homing | 6× normally-open limit switches |
| Vision | USB camera (calibrated) |
| Host | PC via USB serial |

## Software Stack

| Layer | Technology |
|-------|-----------|
| Vision model | YOLOv11s (Ultralytics) |
| Training | Google Colab (T4 GPU, 2000 epochs) |
| IK solver | Analytical spherical-wrist decomposition |
| Trajectory | Synchronised trapezoidal velocity profiles |
| Firmware | C++17 · AccelStepper · PlatformIO |
| Host | Python 3 · OpenCV · PySerial · PyYAML |

---

## Navigation

- **[Setup Guide]({{ site.baseurl }}/pages/setup)** — install, wire, calibrate, run
- **[Hardware]({{ site.baseurl }}/pages/hardware)** — wiring diagram, DM542T config, pin map
- **[Firmware]({{ site.baseurl }}/pages/firmware)** — Teensy code, serial protocol, homing
- **[Vision]({{ site.baseurl }}/pages/vision)** — YOLO training, dataset, camera calibration
- **[Inverse Kinematics]({{ site.baseurl }}/pages/ik)** — DH parameters, FK/IK math, trajectory
- **[Host Pipeline]({{ site.baseurl }}/pages/host)** — Python orchestration, config reference
