---
title: Setup Guide
layout: default
nav_order: 2
---

# Setup Guide
{: .no_toc }

End-to-end instructions from a fresh clone to a running arm.
{: .fs-6 .fw-300 }

<details open markdown="block">
  <summary>Table of contents</summary>
  {: .text-delta }
- TOC
{:toc}
</details>

---

## Prerequisites

| Tool | Purpose |
|------|---------|
| Python 3.10+ | Host scripts |
| PlatformIO Core | Firmware build + upload |
| Google Colab account | YOLO training |
| Roboflow account (free) | Dataset download |
| Git | Version control |

Install Python dependencies:

```bash
pip install ultralytics roboflow opencv-python pyserial pyyaml numpy
```

Install PlatformIO:

```bash
pip install platformio
```

---

## Step 1 — Clone the repository

```bash
git clone https://github.com/jonahchang207/IRIS-Progect.git
cd "IRIS-Progect"
```

---

## Step 2 — Train the vision model

1. Open `colab/IRIS_train.ipynb` in Google Colab
2. Set runtime to **T4 GPU**: Runtime → Change runtime type → T4
3. Go to [universe.roboflow.com](https://universe.roboflow.com), search **"screw detection"**, select a dataset with ≥ 1 000 images, click **Download → YOLOv11 format**
4. Fill in the `CONFIG` cell:

   ```python
   ROBOFLOW_API_KEY   = "your_key"
   ROBOFLOW_WORKSPACE = "your_workspace"
   ROBOFLOW_PROJECT   = "screw-detection"
   ROBOFLOW_VERSION   = 1
   ```

5. Run all cells — training takes ~2–4 hours on T4 for 2000 epochs with early stopping
6. Download `IRIS_best.pt` and `IRIS_best.onnx` into the `models/` folder

{: .note }
If your dataset has fewer than 1 000 images, run the **Appendix — Augmented Dataset Builder** cell before training. It uses Albumentations to expand the dataset 3×.

---

## Step 3 — Wire and configure the hardware

See the **[Hardware page]({{ site.baseurl }}/pages/hardware)** for the full wiring diagram.

Once wired, open `firmware/IRIS_firmware/src/config.h` and fill in every line marked `// PLACEHOLDER`:

```cpp
// DM542T dip switches → set microstepping here
constexpr uint16_t STEPS_REV_NEMA23 = 1600;   // e.g. SW1-4 = ON-ON-OFF-OFF

// Pin numbers from your breakout board
constexpr uint8_t PIN_STEP_J1 = 0;
// ... etc.
```

---

## Step 4 — Flash the firmware

```bash
cd firmware/IRIS_firmware
pio run --target upload
```

Verify with the serial monitor:

```bash
pio device monitor --baud 115200
```

Send `STATUS` — you should see `STATUS IDLE`.

---

## Step 5 — Calibrate the camera

Print a checkerboard (default: 9×6 inner corners, 25 mm squares — see `host/calibrate_camera.py` to change).

```bash
cd host
python calibrate_camera.py
```

- Hold the board at varied angles and distances
- Press **SPACE** to capture (need 15+)
- Press **ESC** to compute — target reprojection error < 0.5 px
- Output is saved to `models/camera_calibration.npz`

---

## Step 6 — Set the camera extrinsic transform

{: .warning }
This is the most important calibration step. An incorrect `T_cam_to_base` will cause the arm to miss every pick.

Measure the position and orientation of the camera relative to the robot base frame (origin = J1 axis at table level). Update `host/config.yaml`:

```yaml
vision:
  T_cam_to_base:
    - [1.0, 0.0, 0.0,  0.250]   # x offset (m)
    - [0.0, 1.0, 0.0,  0.000]   # y offset (m)
    - [0.0, 0.0, 1.0,  0.400]   # z (camera height above base)
    - [0.0, 0.0, 0.0,  1.000]
```

---

## Step 7 — Fill in DH parameters

Measure your arm link lengths from the CAD or physical arm and update `host/config.yaml` under `ik.dh_params`. See the **[IK page]({{ site.baseurl }}/pages/ik)** for the DH parameter convention.

---

## Step 8 — Home and run

```bash
cd host
python main.py --home
```

`--home` runs the full homing sequence on startup. Once all joints are homed, place a screw in the camera field of view and the arm will pick and place it.

---

## Verifying the IK solver

Before running the full pipeline, verify your DH parameters round-trip correctly:

```bash
python ik/inverse_kinematics.py
```

Expected output:

```
Input angles  : [30.0, -20.0, 45.0, 10.0, -30.0, 15.0]
IK solution   : [30.0, -20.0, 45.0, 10.0, -30.0, 15.0]
Position error: 0.0000 mm  (PASS)
```

If you see a position error > 0.5 mm, re-check your DH parameters.
