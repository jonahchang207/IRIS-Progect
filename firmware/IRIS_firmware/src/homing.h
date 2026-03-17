#pragma once
#include <stdint.h>
#include <stdbool.h>

// ============================================================
//  Homing — limit switch sequence for each joint
//
//  Sequence per joint:
//    1. Fast move in HOME_DIR until limit switch triggers
//    2. Back off HOME_BACKOFF_DEG
//    3. Slow move in HOME_DIR until switch triggers again
//    4. setZero() — this is now the home position
//    5. Move to 0.0 deg (absolute home)
//
//  Homing order: J1 → J2 → J3 → J4 → J5 → J6
//  (outermost to innermost reduces mechanical stress)
// ============================================================

// Begin homing all joints sequentially (non-blocking state machine)
void homing_start_all();

// Begin homing a single joint (non-blocking)
void homing_start_joint(uint8_t joint);

// Must be called every loop while homing is active
void homing_run();

bool homing_is_active();
bool homing_succeeded();    // true after successful completion

// Returns true if the limit switch for joint j is currently triggered
bool limit_switch_triggered(uint8_t joint);
