"""
IRIS — Trajectory Planner
Trapezoidal velocity profile in joint space.
Ensures all joints arrive at the same time (synchronised interpolation).
"""

import numpy as np
from typing import List, Iterator


def _trap_profile(dist: float, v_max: float, a_max: float, dt: float):
    """
    Generate a 1-D trapezoidal velocity profile.
    Yields (position, velocity) at each time step.

    dist  : total distance (degrees)
    v_max : peak speed (deg/s)
    a_max : acceleration (deg/s²)
    dt    : time step (s)
    """
    sign  = np.sign(dist)
    dist  = abs(dist)

    # Time to reach v_max from rest
    t_accel = v_max / a_max
    d_accel = 0.5 * a_max * t_accel ** 2

    if 2 * d_accel > dist:
        # Triangular profile — not enough distance to reach v_max
        t_accel = np.sqrt(dist / a_max)
        v_peak  = a_max * t_accel
        t_const = 0.0
    else:
        v_peak  = v_max
        t_const = (dist - 2 * d_accel) / v_max

    t_total = 2 * t_accel + t_const

    pos = 0.0
    t   = 0.0
    while t <= t_total:
        if t < t_accel:
            v = a_max * t
        elif t < t_accel + t_const:
            v = v_peak
        else:
            v = v_peak - a_max * (t - t_accel - t_const)
        v = max(0.0, v)

        yield sign * pos, sign * v
        pos += v * dt
        t   += dt


def plan_joint_trajectory(
    start_deg:  List[float],
    target_deg: List[float],
    v_max_deg_s:  List[float],
    a_max_deg_s2: List[float],
    dt: float = 0.02,          # 50 Hz default
) -> List[List[float]]:
    """
    Plan a synchronised joint-space trajectory.

    All joints start and finish at the same time.
    The joint requiring the most time sets the duration;
    others are scaled proportionally.

    Args:
        start_deg     : start joint angles (6,)
        target_deg    : target joint angles (6,)
        v_max_deg_s   : max speeds per joint
        a_max_deg_s2  : max accelerations per joint
        dt            : time step in seconds

    Returns:
        List of waypoints, each a list of 6 joint angles.
    """
    n = len(start_deg)
    deltas = [target_deg[i] - start_deg[i] for i in range(n)]

    # Compute unconstrained duration for each joint
    def joint_duration(dist, v, a):
        dist = abs(dist)
        t_a  = v / a
        d_a  = 0.5 * a * t_a ** 2
        if 2 * d_a >= dist:
            return 2 * np.sqrt(dist / a)
        return 2 * t_a + (dist - 2 * d_a) / v

    durations = [joint_duration(deltas[i], v_max_deg_s[i], a_max_deg_s2[i])
                 for i in range(n)]
    T_sync = max(durations)

    if T_sync < dt:
        return [list(target_deg)]  # already at target

    # Re-compute v_max for each joint so it finishes in T_sync
    steps = int(np.ceil(T_sync / dt))
    waypoints = []

    # Build per-joint position profiles resampled to `steps` points
    joint_profiles = []
    for i in range(n):
        d   = deltas[i]
        # Scale v_max so this joint takes exactly T_sync
        # (reduce speed, not increase — keeps within motor limits)
        scaled_v = abs(d) / T_sync if T_sync > 0 else 0.0
        scaled_v = min(scaled_v * 2.0, v_max_deg_s[i])  # heuristic upper bound
        pts = list(_trap_profile(d, max(scaled_v, 1e-6), a_max_deg_s2[i], dt))
        pos_list = [p for p, _ in pts]
        # Resample to exactly `steps` points
        if len(pos_list) < steps:
            pos_list += [pos_list[-1]] * (steps - len(pos_list))
        joint_profiles.append(pos_list[:steps])

    for k in range(steps):
        wp = [start_deg[i] + joint_profiles[i][k] for i in range(n)]
        waypoints.append(wp)

    # Ensure final point is exactly the target
    waypoints.append(list(target_deg))
    return waypoints


# ---- quick self-test ----------------------------------------
if __name__ == "__main__":
    start  = [0.0] * 6
    target = [30.0, -45.0, 60.0, 0.0, 90.0, -30.0]
    v_max  = [60.0] * 6    # deg/s   PLACEHOLDER
    a_max  = [120.0] * 6   # deg/s²  PLACEHOLDER

    traj = plan_joint_trajectory(start, target, v_max, a_max, dt=0.02)
    print(f"Trajectory: {len(traj)} waypoints at 50 Hz")
    print(f"  First : {[round(x,2) for x in traj[0]]}")
    print(f"  Last  : {[round(x,2) for x in traj[-1]]}")
