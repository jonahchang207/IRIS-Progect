"""
IRIS — Inverse Kinematics (Analytical, closed-form)

Strategy: spherical wrist decomposition
  1. Position subproblem (J1-J3): geometric solution for wrist centre
  2. Orientation subproblem (J4-J6): ZYZ Euler extraction from residual R

Assumptions (standard 6R anthropomorphic arm with spherical wrist):
  - Joint 4, 5, 6 axes all intersect at the wrist centre
  - DH layout matches forward_kinematics.py
"""

import numpy as np
from typing import Optional, Tuple, List
from forward_kinematics import forward_kinematics, dh_transform


_EPS = 1e-9


# ============================================================
#  Rotation utilities
# ============================================================

def rot_x(a: float) -> np.ndarray:
    c, s = np.cos(a), np.sin(a)
    return np.array([[1,0,0],[0,c,-s],[0,s,c]])

def rot_z(a: float) -> np.ndarray:
    c, s = np.cos(a), np.sin(a)
    return np.array([[c,-s,0],[s,c,0],[0,0,1]])


def _R_0_3(q: List[float], dh: List[List[float]]) -> np.ndarray:
    """Rotation matrix from base to joint 3 frame."""
    T = np.eye(4)
    for i in range(3):
        a, alpha_deg, d, toff = dh[i]
        T = T @ dh_transform(a, np.deg2rad(alpha_deg), d,
                              np.deg2rad(q[i] + toff))
    return T[:3, :3]


# ============================================================
#  Position subproblem — solve J1, J2, J3
# ============================================================

def _solve_position(p_wc: np.ndarray, dh: List[List[float]]) -> List[Tuple[float, float, float]]:
    """
    Solve J1, J2, J3 for a given wrist-centre position p_wc (metres).
    Returns up to 2 solutions (elbow-up / elbow-down).
    Each solution is a tuple (q1, q2, q3) in degrees.
    """
    # Unpack DH
    d1 = dh[0][2]   # base height
    a2 = dh[1][0]   # upper arm
    a3 = dh[2][0]   # forearm

    px, py, pz = p_wc

    # --- Joint 1 ---
    q1 = np.arctan2(py, px)

    # Horizontal reach in the arm plane
    r = np.hypot(px, py)
    s = pz - d1   # height above shoulder pivot

    # Distance from shoulder to wrist centre
    D = np.hypot(r, s)

    # Law of cosines for J3
    cos_q3 = (D**2 - a2**2 - a3**2) / (2.0 * a2 * a3)
    cos_q3 = np.clip(cos_q3, -1.0, 1.0)

    solutions = []
    for sign in (+1, -1):   # elbow-up / elbow-down
        sin_q3 = sign * np.sqrt(max(0.0, 1.0 - cos_q3**2))
        q3 = np.arctan2(sin_q3, cos_q3)

        # Joint 2
        q2 = np.arctan2(s, r) - np.arctan2(a3 * sin_q3, a2 + a3 * cos_q3)

        solutions.append((np.degrees(q1), np.degrees(q2), np.degrees(q3)))

    return solutions


# ============================================================
#  Orientation subproblem — solve J4, J5, J6 (ZYZ wrist)
# ============================================================

def _solve_orientation(R_0_3: np.ndarray, R_target: np.ndarray) -> List[Tuple[float, float, float]]:
    """
    Given R_0_3 and the target end-effector rotation R_target,
    compute R_3_6 and extract ZYZ Euler angles → q4, q5, q6.
    Returns up to 2 solutions (q5 positive / negative).
    """
    R_3_6 = R_0_3.T @ R_target

    # ZYZ Euler extraction
    # R = Rz(q4) * Ry(q5) * Rz(q6)
    # R[2,2] = cos(q5)
    r = R_3_6

    cos_q5 = np.clip(r[2, 2], -1.0, 1.0)
    solutions = []

    for sign in (+1, -1):
        sin_q5 = sign * np.sqrt(max(0.0, 1.0 - cos_q5**2))
        q5 = np.arctan2(sin_q5, cos_q5)

        if abs(sin_q5) > _EPS:
            q4 = np.arctan2( r[1, 2] / sin_q5,  r[0, 2] / sin_q5)
            q6 = np.arctan2( r[2, 1] / sin_q5, -r[2, 0] / sin_q5)
        else:
            # Gimbal lock: q5 ≈ 0 or ±π, set q4 = 0, solve q6
            q4 = 0.0
            if cos_q5 > 0:
                q6 = np.arctan2(-r[1, 0], r[0, 0])
            else:
                q6 = np.arctan2( r[1, 0], -r[0, 0])

        solutions.append((np.degrees(q4), np.degrees(q5), np.degrees(q6)))

    return solutions


# ============================================================
#  Joint limit check
# ============================================================

def _within_limits(q: List[float], limits: List[List[float]]) -> bool:
    for angle, (lo, hi) in zip(q, limits):
        if not (lo <= angle <= hi):
            return False
    return True


# ============================================================
#  Public API
# ============================================================

def inverse_kinematics(
    target_T: np.ndarray,
    dh_params: List[List[float]],
    joint_limits: List[List[float]],
    prefer_config: Optional[List[float]] = None,
) -> Optional[List[float]]:
    """
    Compute joint angles for a target end-effector pose.

    Args:
        target_T      : 4x4 homogeneous transform (base → EE)
        dh_params     : 6-row DH table [[a, alpha_deg, d, theta_offset_deg], ...]
        joint_limits  : [[min, max], ...] in degrees for each joint
        prefer_config : current joint angles (deg) — used to select closest solution

    Returns:
        List of 6 joint angles in degrees, or None if no valid solution found.
    """
    R_target = target_T[:3, :3]
    p_ee     = target_T[:3,  3]

    # Tool-frame Z axis (wrist approach direction)
    d6 = dh_params[5][2]   # EE offset
    z_ee = R_target[:, 2]
    p_wc = p_ee - d6 * z_ee   # wrist centre position

    pos_solutions = _solve_position(p_wc, dh_params)

    all_solutions = []
    for (q1, q2, q3) in pos_solutions:
        R03 = _R_0_3([q1, q2, q3], dh_params)
        ori_solutions = _solve_orientation(R03, R_target)
        for (q4, q5, q6) in ori_solutions:
            candidate = [q1, q2, q3, q4, q5, q6]
            if _within_limits(candidate, joint_limits):
                all_solutions.append(candidate)

    if not all_solutions:
        return None

    # Pick solution closest to current config (minimise joint-space distance)
    if prefer_config is not None:
        ref = np.array(prefer_config)
        all_solutions.sort(
            key=lambda s: float(np.sum((np.array(s) - ref) ** 2))
        )

    return all_solutions[0]


def verify_ik(
    joint_angles_deg: List[float],
    target_T: np.ndarray,
    dh_params: List[List[float]],
    pos_tol_mm: float = 0.5,
) -> Tuple[bool, float]:
    """
    Verify IK result by running FK and comparing.

    Returns:
        (ok, position_error_mm)
    """
    T_fk = forward_kinematics(joint_angles_deg, dh_params)
    err  = np.linalg.norm(T_fk[:3, 3] - target_T[:3, 3]) * 1000.0
    return err <= pos_tol_mm, err


# ---- quick self-test ----------------------------------------
if __name__ == "__main__":
    from forward_kinematics import forward_kinematics

    # PLACEHOLDER DH params
    DH = [
        [0.000,  90.0, 0.100, 0.0],
        [0.250,   0.0, 0.000, 0.0],
        [0.220,   0.0, 0.000, 0.0],
        [0.000,  90.0, 0.000, 0.0],
        [0.000, -90.0, 0.000, 0.0],
        [0.000,   0.0, 0.080, 0.0],
    ]

    LIMITS = [[-170,170],[-90,90],[-135,135],[-170,170],[-90,90],[-170,170]]

    # Test round-trip FK → IK
    test_angles = [30.0, -20.0, 45.0, 10.0, -30.0, 15.0]
    T_target    = forward_kinematics(test_angles, DH)
    result      = inverse_kinematics(T_target, DH, LIMITS, prefer_config=test_angles)

    if result:
        ok, err = verify_ik(result, T_target, DH)
        print(f"Input angles  : {[round(a,3) for a in test_angles]}")
        print(f"IK solution   : {[round(a,3) for a in result]}")
        print(f"Position error: {err:.4f} mm  ({'PASS' if ok else 'FAIL'})")
    else:
        print("IK: no solution found (check DH params and limits)")
