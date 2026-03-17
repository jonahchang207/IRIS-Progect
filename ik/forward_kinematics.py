"""
IRIS — Forward Kinematics
DH convention: Modified DH (Craig)
T_i = Rot_x(alpha_{i-1}) * Trans_x(a_{i-1}) * Rot_z(theta_i) * Trans_z(d_i)
"""

import numpy as np
from typing import List


def dh_transform(a: float, alpha: float, d: float, theta: float) -> np.ndarray:
    """
    Single Modified DH homogeneous transform matrix (4x4).

    Args:
        a     : link length (m)
        alpha : link twist (rad)
        d     : link offset (m)
        theta : joint angle (rad)
    """
    ct, st = np.cos(theta), np.sin(theta)
    ca, sa = np.cos(alpha), np.sin(alpha)

    return np.array([
        [ct,       -st,       0,      a      ],
        [st * ca,   ct * ca, -sa,    -sa * d  ],
        [st * sa,   ct * sa,  ca,     ca * d  ],
        [0,         0,        0,      1       ],
    ])


def forward_kinematics(
    joint_angles_deg: List[float],
    dh_params: List[List[float]],
) -> np.ndarray:
    """
    Compute end-effector pose from joint angles.

    Args:
        joint_angles_deg : list of 6 joint angles in degrees
        dh_params        : list of 6 rows, each [a, alpha_deg, d, theta_offset_deg]

    Returns:
        T_0_6 : 4x4 homogeneous transform from base to end-effector
    """
    assert len(joint_angles_deg) == 6, "Requires exactly 6 joint angles"
    assert len(dh_params)        == 6, "Requires exactly 6 DH rows"

    T = np.eye(4)
    for i in range(6):
        a, alpha_deg, d, theta_off_deg = dh_params[i]
        alpha = np.deg2rad(alpha_deg)
        theta = np.deg2rad(joint_angles_deg[i] + theta_off_deg)
        T = T @ dh_transform(a, alpha, d, theta)

    return T


def extract_position(T: np.ndarray) -> np.ndarray:
    """Return [x, y, z] from homogeneous transform (metres)."""
    return T[:3, 3]


def extract_rotation(T: np.ndarray) -> np.ndarray:
    """Return 3x3 rotation matrix from homogeneous transform."""
    return T[:3, :3]


def all_frame_transforms(
    joint_angles_deg: List[float],
    dh_params: List[List[float]],
) -> List[np.ndarray]:
    """
    Return list of 7 cumulative transforms: [T_0_0, T_0_1, ..., T_0_6].
    Useful for visualisation and debugging.
    """
    transforms = [np.eye(4)]
    T = np.eye(4)
    for i in range(6):
        a, alpha_deg, d, theta_off_deg = dh_params[i]
        alpha = np.deg2rad(alpha_deg)
        theta = np.deg2rad(joint_angles_deg[i] + theta_off_deg)
        T = T @ dh_transform(a, alpha, d, theta)
        transforms.append(T.copy())
    return transforms


# ---- quick self-test -----------------------------------------------
if __name__ == "__main__":
    # PLACEHOLDER DH params — replace with real values from config.yaml
    DH = [
        [0.000,  90.0, 0.100, 0.0],
        [0.250,   0.0, 0.000, 0.0],
        [0.220,   0.0, 0.000, 0.0],
        [0.000,  90.0, 0.000, 0.0],
        [0.000, -90.0, 0.000, 0.0],
        [0.000,   0.0, 0.080, 0.0],
    ]

    angles_home = [0.0, 0.0, 0.0, 0.0, 0.0, 0.0]
    T = forward_kinematics(angles_home, DH)
    print("Home pose:")
    print(f"  Position : {extract_position(T) * 1000} mm")
    np.set_printoptions(precision=4, suppress=True)
    print(f"  Transform:\n{T}")
