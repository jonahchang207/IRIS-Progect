"""
IRIS — Camera Calibration
Checkerboard intrinsic calibration + saves K and dist to models/camera_calibration.npz

Usage:
    python calibrate_camera.py
    Press SPACE to capture a frame, ESC when done (need ≥15 good captures).
"""

import cv2
import numpy as np
import yaml
import argparse
from pathlib import Path


def calibrate(cfg_path: str = "config.yaml"):
    with open(cfg_path) as f:
        cfg = yaml.safe_load(f)

    cam_cfg = cfg["camera"]
    out_file = Path(cfg["vision"]["calibration_file"])
    out_file.parent.mkdir(parents=True, exist_ok=True)

    # Checkerboard config — PLACEHOLDER: update to match your printed board
    BOARD_W   = 9    # inner corners per row    PLACEHOLDER
    BOARD_H   = 6    # inner corners per column PLACEHOLDER
    SQ_SIZE_M = 0.025  # square size in metres  PLACEHOLDER

    criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 30, 0.001)

    obj_p = np.zeros((BOARD_W * BOARD_H, 3), dtype=np.float32)
    obj_p[:, :2] = np.mgrid[0:BOARD_W, 0:BOARD_H].T.reshape(-1, 2) * SQ_SIZE_M

    obj_points = []   # 3D points in world space
    img_points = []   # 2D points in image plane

    cap = cv2.VideoCapture(cam_cfg["index"])
    cap.set(cv2.CAP_PROP_FRAME_WIDTH,  cam_cfg["width"])
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, cam_cfg["height"])

    print("Camera calibration")
    print(f"  Board: {BOARD_W}x{BOARD_H} inner corners, {SQ_SIZE_M*100:.1f}cm squares")
    print("  SPACE = capture frame | ESC = compute & save")
    print(f"  Target: 15+ captures from varied angles")

    captured = 0
    while True:
        ret, frame = cap.read()
        if not ret:
            print("Camera read failed")
            break

        gray   = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        found, corners = cv2.findChessboardCorners(gray, (BOARD_W, BOARD_H), None)

        display = frame.copy()
        if found:
            cv2.drawChessboardCorners(display, (BOARD_W, BOARD_H), corners, found)
            cv2.putText(display, "Board detected — SPACE to capture",
                        (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
        else:
            cv2.putText(display, "Board NOT detected",
                        (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)

        cv2.putText(display, f"Captures: {captured}",
                    (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 0), 2)
        cv2.imshow("IRIS Camera Calibration", display)

        key = cv2.waitKey(1) & 0xFF
        if key == 27:   # ESC
            break
        if key == 32 and found:   # SPACE
            corners_sub = cv2.cornerSubPix(gray, corners, (11, 11), (-1, -1), criteria)
            obj_points.append(obj_p)
            img_points.append(corners_sub)
            captured += 1
            print(f"  Captured {captured}")

    cap.release()
    cv2.destroyAllWindows()

    if captured < 10:
        print(f"Only {captured} captures — need at least 10. Aborting.")
        return

    print(f"\nComputing calibration from {captured} captures...")
    h, w = gray.shape
    ret, K, dist, rvecs, tvecs = cv2.calibrateCamera(
        obj_points, img_points, (w, h), None, None
    )

    # Reprojection error
    errors = []
    for obj, img, rv, tv in zip(obj_points, img_points, rvecs, tvecs):
        proj, _ = cv2.projectPoints(obj, rv, tv, K, dist)
        errors.append(cv2.norm(img, proj, cv2.NORM_L2) / len(proj))
    mean_err = np.mean(errors)

    print(f"  RMS reprojection error: {mean_err:.4f} px")
    if mean_err > 1.0:
        print("  WARNING: high reprojection error — recalibrate with more varied captures")

    np.savez(out_file, K=K, dist=dist)
    print(f"  Saved to {out_file}")
    print(f"\n  Focal length : fx={K[0,0]:.1f}  fy={K[1,1]:.1f}")
    print(f"  Principal pt : cx={K[0,2]:.1f}  cy={K[1,2]:.1f}")
    print(f"  Distortion   : {dist.ravel()}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default="config.yaml")
    args = ap.parse_args()
    calibrate(args.config)
