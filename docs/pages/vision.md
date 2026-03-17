---
title: Vision
layout: default
nav_order: 5
---

# Vision System
{: .no_toc }

YOLOv11s screw detection, training pipeline, camera calibration, and world-coordinate projection.
{: .fs-6 .fw-300 }

<details open markdown="block">
  <summary>Table of contents</summary>
  {: .text-delta }
- TOC
{:toc}
</details>

---

## Model Choice — YOLOv11s

YOLOv11s was chosen for IRIS for three reasons:

1. **Small object accuracy** — screws are small relative to the workspace. The `s` variant hits the sweet spot between the nano's poor recall on small objects and the medium's slower inference.
2. **Real-time inference** — 50+ FPS on a mid-range GPU, 15+ FPS on CPU. Well within the 10 Hz pipeline loop rate.
3. **One-step export** — Ultralytics exports directly to ONNX, making the host inference script framework-agnostic.

---

## Dataset

Source your dataset from [Roboflow Universe](https://universe.roboflow.com) — search **"screw detection"** and filter by image count descending.

Requirements:
- ≥ 1 000 images (ideally 2 000–5 000)
- YOLOv11 format (Roboflow exports this natively)
- Annotations: bounding boxes around individual screws

If your dataset is under 1 000 images, the Colab notebook's **Appendix** section uses Albumentations to expand it 3× with realistic industrial augmentations:

| Augmentation | Parameter | Reason |
|-------------|-----------|--------|
| `RandomBrightnessContrast` | p=0.6 | Varies lighting conditions |
| `GaussNoise` | 10–50 var, p=0.4 | Camera sensor noise |
| `MotionBlur` | limit=5, p=0.3 | Camera or arm movement |
| `Perspective` | scale 0.02–0.05, p=0.3 | Varied camera angles |
| `HueSaturationValue` | p=0.4 | Oxidised / painted screws |
| `CLAHE` | p=0.3 | Low-contrast industrial backgrounds |

---

## Training (Google Colab)

Open `colab/IRIS_train.ipynb`. The notebook handles:

1. GPU verification
2. Dependency install (`ultralytics`, `roboflow`)
3. Dataset download from Roboflow
4. Dataset inspection (counts, class names, warns if < 1 000 images)
5. YOLOv11s training — 2 000 epochs, patience=100
6. Validation: mAP@0.5, precision, recall
7. ONNX export (opset 17, batch=1, simplified)
8. Download of `best.pt`, `best.onnx`, and full run zip

### Key training parameters

```python
epochs    = 2000
patience  = 100       # early stop if no improvement for 100 epochs
imgsz     = 640
batch     = 16        # reduce to 8 if OOM on free T4
optimizer = 'AdamW'
lr0       = 0.001
lrf       = 0.01      # final LR = lr0 * lrf = 0.00001
```

### Target metrics

| Metric | Target |
|--------|--------|
| mAP@0.5 | ≥ 0.85 |
| Precision | ≥ 0.80 |
| Recall | ≥ 0.80 |

If mAP falls short, the most effective levers are (in order): more data, longer training, or switching to `yolo11m`.

---

## Camera Calibration

Run `host/calibrate_camera.py` with a printed checkerboard (default 9×6 inner corners, 25 mm squares):

```bash
python host/calibrate_camera.py
```

The script:
1. Opens a live camera feed
2. Detects the checkerboard (green overlay when found)
3. On SPACE: captures the frame (refines corners to sub-pixel accuracy)
4. On ESC (after 15+ captures): runs `cv2.calibrateCamera`, prints reprojection error, saves `models/camera_calibration.npz`

**Good calibration:** reprojection error < 0.5 px
**Acceptable:** < 1.0 px
**Recalibrate if:** > 1.0 px — more captures from varied angles/distances needed

The saved `.npz` contains:
- `K` — 3×3 camera intrinsic matrix
- `dist` — 5-element distortion coefficients

---

## Pixel → World Coordinate Projection

`host/vision.py` projects detected screw centroids to the robot base frame using ray-plane intersection:

```
1. Undistort pixel (px, py) using K and dist
2. Compute normalised ray in camera frame:  r_c = K⁻¹ · [px, py, 1]ᵀ
3. Transform ray to robot base frame:       r_b = R_cb · r_c
4. Intersect ray with table plane (z = table_z_m):
        λ = (table_z - origin_z) / r_b[z]
        p_world = camera_origin + λ · r_b
```

The camera-to-base extrinsic transform `T_cam_to_base` is a 4×4 homogeneous matrix set in `host/config.yaml`.

{: .warning }
`T_cam_to_base` must be measured carefully. A 5 mm error in the camera position translates directly to a 5 mm pick miss. Use a ruler or CAD model to measure; refine by jogging the arm to a known point and comparing.

---

## Detection Stability Filter

The host pipeline does not pick on a single detection. It requires `min_detections` consecutive frames (default: 3) where the same screw appears within 1 cm of the same position:

```python
if len(history) >= min_detections:
    if max(xs) - min(xs) < 0.01 and max(ys) - min(ys) < 0.01:
        trigger_pick()
```

This eliminates false positives and jitter from single-frame detections.
