---
title: Inverse Kinematics
layout: default
nav_order: 6
math: mathjax
---

# Inverse Kinematics
{: .no_toc }

Modified DH forward kinematics, analytical 6DOF IK solver, and synchronised trajectory planner.
{: .fs-6 .fw-300 }

<details open markdown="block">
  <summary>Table of contents</summary>
  {: .text-delta }
- TOC
{:toc}
</details>

---

## DH Parameter Convention

IRIS uses the **Modified DH (Craig) convention**. The transform from frame `i-1` to frame `i` is:

```
T_i = Rot_x(α_{i-1}) · Trans_x(a_{i-1}) · Rot_z(θ_i) · Trans_z(d_i)
```

Each row in the DH table is `[a, α (deg), d, θ_offset (deg)]`:

| Joint | a (m) | α (°) | d (m) | θ_offset (°) | Notes |
|-------|--------|--------|--------|--------------|-------|
| J1 | 0 | 90 | d1 | 0 | Base height |
| J2 | a2 | 0 | 0 | 0 | Upper arm length |
| J3 | a3 | 0 | 0 | 0 | Forearm length |
| J4 | 0 | 90 | 0 | 0 | Wrist roll |
| J5 | 0 | −90 | 0 | 0 | Wrist pitch |
| J6 | 0 | 0 | d6 | 0 | Tool offset |

{: .placeholder }
`d1`, `a2`, `a3`, `d6` are `PLACEHOLDER` values in `host/config.yaml` under `ik.dh_params`. Measure from your CAD model.

---

## Forward Kinematics

`ik/forward_kinematics.py` computes the end-effector pose as a 4×4 homogeneous transform:

```python
from forward_kinematics import forward_kinematics

T = forward_kinematics([0, 0, 0, 0, 0, 0], DH_PARAMS)
# T[:3, 3] = position (metres)
# T[:3, :3] = rotation matrix
```

Utility functions:
- `extract_position(T)` → `[x, y, z]`
- `extract_rotation(T)` → 3×3 rotation matrix
- `all_frame_transforms(q, dh)` → list of 7 transforms (base through EE) — useful for visualisation

---

## Inverse Kinematics — Spherical Wrist Decomposition

The analytical IK exploits the spherical wrist structure (joints 4, 5, 6 axes all intersect at one point) to decouple position from orientation.

### Step 1 — Wrist Centre

Compute the wrist centre position from the target EE pose:

```
p_wc = p_ee − d₆ · R_target[:, 2]
```

### Step 2 — Position Subproblem (J1, J2, J3)

Joint 1 — base rotation:
```
q₁ = atan2(p_wc_y, p_wc_x)
```

Planar distance and height:
```
r = √(p_wc_x² + p_wc_y²)
s = p_wc_z − d₁
```

Law of cosines for J3:
```
cos(q₃) = (r² + s² − a₂² − a₃²) / (2·a₂·a₃)
q₃ = atan2(±√(1 − cos²q₃), cos_q₃)      ← two solutions: elbow-up / elbow-down
```

Joint 2:
```
q₂ = atan2(s, r) − atan2(a₃·sin(q₃), a₂ + a₃·cos(q₃))
```

### Step 3 — Orientation Subproblem (J4, J5, J6)

Compute residual wrist rotation:
```
R₃₆ = R₀₃ᵀ · R_target
```

Extract ZYZ Euler angles:
```
q₅ = atan2(√(R₃₆[0,2]² + R₃₆[1,2]²), R₃₆[2,2])
q₄ = atan2(R₃₆[1,2]/sin(q₅), R₃₆[0,2]/sin(q₅))
q₆ = atan2(R₃₆[2,1]/sin(q₅), −R₃₆[2,0]/sin(q₅))
```

Gimbal lock (|sin(q₅)| ≈ 0) is handled by setting q₄=0 and solving for the combined q₄+q₆.

### Solution Selection

The solver generates up to 4 candidates (2 elbow configs × 2 wrist configs). Candidates that violate joint limits are discarded. The remaining solutions are ranked by **minimum joint-space distance** from the current configuration — this ensures smooth, predictable motion.

---

## Verifying the Solver

```bash
python ik/inverse_kinematics.py
```

The self-test picks a known joint configuration, runs FK to get a target pose, solves IK, and checks the position error:

```
Input angles  : [30.0, -20.0, 45.0, 10.0, -30.0, 15.0]
IK solution   : [30.0, -20.0, 45.0, 10.0, -30.0, 15.0]
Position error: 0.0000 mm  (PASS)
```

{: .warning }
If the error is > 0.5 mm with the placeholder DH params, something is wrong with the parameters. Always run this test after updating `config.yaml`.

---

## Trajectory Planner

`ik/trajectory.py` generates a synchronised trapezoidal velocity profile in joint space:

- All joints **start and finish at the same time**, regardless of travel distance
- Each joint follows an acceleration → constant velocity → deceleration profile
- The joint requiring the most time sets the synchronisation duration; all other joints scale their speed proportionally

```python
from trajectory import plan_joint_trajectory

waypoints = plan_joint_trajectory(
    start_deg  = [0, 0, 0, 0, 0, 0],
    target_deg = [30, -45, 60, 0, 90, -30],
    v_max_deg_s   = [60] * 6,    # PLACEHOLDER — tune per joint
    a_max_deg_s2  = [120] * 6,   # PLACEHOLDER
    dt = 0.02,                   # 50 Hz
)
# waypoints: list of [j1..j6] angle lists at 50 Hz
```

{: .note }
The trajectory planner is available for future use (e.g. smoother multi-step sequences). The current `host/main.py` sends direct `MOVEA` commands and lets the AccelStepper firmware handle acceleration internally. The planner becomes important if you add via-point planning or collision avoidance.
