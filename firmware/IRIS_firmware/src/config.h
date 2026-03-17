#pragma once
#include <stdint.h>

// ============================================================
//  IRIS Firmware — Hardware Configuration
//  All PLACEHOLDER values must be filled in once hardware
//  is physically measured / dip-switch settings confirmed.
// ============================================================

// --- Serial ---
constexpr uint32_t SERIAL_BAUD = 115200;

// --- Stepper driver (DM542T) ---
// EN pin is active LOW: LOW = drivers enabled, HIGH = free-wheeling
constexpr bool     EN_ACTIVE_LOW = true;

// --- Steps per revolution ---
// PLACEHOLDER: confirm DM542T dip-switch microstepping setting
// Common: 400 (1/2), 800 (1/4), 1600 (1/8), 3200 (1/16)
constexpr uint16_t STEPS_REV_NEMA23 = 1600;   // PLACEHOLDER
constexpr uint16_t STEPS_REV_NEMA17 = 1600;   // PLACEHOLDER

// --- Degrees per step ---
constexpr float DEG_PER_STEP_J1 = 360.0f / STEPS_REV_NEMA23;
constexpr float DEG_PER_STEP_J2 = 360.0f / STEPS_REV_NEMA23;
constexpr float DEG_PER_STEP_J3 = 360.0f / STEPS_REV_NEMA17;
constexpr float DEG_PER_STEP_J4 = 360.0f / STEPS_REV_NEMA17;
constexpr float DEG_PER_STEP_J5 = 360.0f / STEPS_REV_NEMA17;
constexpr float DEG_PER_STEP_J6 = 360.0f / STEPS_REV_NEMA17;

// --- Gear / belt reduction ratios (output/input) ---
// PLACEHOLDER: measure from CAD or physical arm
constexpr float RATIO_J1 = 1.0f;   // PLACEHOLDER
constexpr float RATIO_J2 = 1.0f;   // PLACEHOLDER
constexpr float RATIO_J3 = 1.0f;   // PLACEHOLDER
constexpr float RATIO_J4 = 1.0f;   // PLACEHOLDER
constexpr float RATIO_J5 = 1.0f;   // PLACEHOLDER
constexpr float RATIO_J6 = 1.0f;   // PLACEHOLDER

// Effective steps per output degree (accounts for gear ratio)
constexpr float STEPS_PER_DEG_J1 = (1.0f / DEG_PER_STEP_J1) * RATIO_J1;
constexpr float STEPS_PER_DEG_J2 = (1.0f / DEG_PER_STEP_J2) * RATIO_J2;
constexpr float STEPS_PER_DEG_J3 = (1.0f / DEG_PER_STEP_J3) * RATIO_J3;
constexpr float STEPS_PER_DEG_J4 = (1.0f / DEG_PER_STEP_J4) * RATIO_J4;
constexpr float STEPS_PER_DEG_J5 = (1.0f / DEG_PER_STEP_J5) * RATIO_J5;
constexpr float STEPS_PER_DEG_J6 = (1.0f / DEG_PER_STEP_J6) * RATIO_J6;

// --- Joint soft limits (degrees) ---
// PLACEHOLDER: set to real mechanical limits after testing
constexpr float LIMIT_MIN_J1 = -170.0f;  constexpr float LIMIT_MAX_J1 = 170.0f;
constexpr float LIMIT_MIN_J2 =  -90.0f;  constexpr float LIMIT_MAX_J2 =  90.0f;
constexpr float LIMIT_MIN_J3 = -135.0f;  constexpr float LIMIT_MAX_J3 = 135.0f;
constexpr float LIMIT_MIN_J4 = -170.0f;  constexpr float LIMIT_MAX_J4 = 170.0f;
constexpr float LIMIT_MIN_J5 =  -90.0f;  constexpr float LIMIT_MAX_J5 =  90.0f;
constexpr float LIMIT_MIN_J6 = -170.0f;  constexpr float LIMIT_MAX_J6 = 170.0f;

// --- Speed / acceleration ---
// PLACEHOLDER: tune per motor after bench testing
constexpr float MAX_SPEED_J1  = 2000.0f;   // steps/sec
constexpr float MAX_SPEED_J2  = 2000.0f;
constexpr float MAX_SPEED_J3  = 3000.0f;
constexpr float MAX_SPEED_J4  = 4000.0f;
constexpr float MAX_SPEED_J5  = 4000.0f;
constexpr float MAX_SPEED_J6  = 4000.0f;
constexpr float ACCEL_J1      = 800.0f;    // steps/sec²
constexpr float ACCEL_J2      = 800.0f;
constexpr float ACCEL_J3      = 1200.0f;
constexpr float ACCEL_J4      = 2000.0f;
constexpr float ACCEL_J5      = 2000.0f;
constexpr float ACCEL_J6      = 2000.0f;

// Homing creep speed (slow approach after fast find)
constexpr float HOME_FAST_SPEED = 800.0f;   // steps/sec
constexpr float HOME_SLOW_SPEED = 200.0f;   // steps/sec
constexpr float HOME_BACKOFF_DEG = 3.0f;    // degrees to back off after trigger

// --- Pin mapping (Teensy 4.1 + breakout board) ---
// PLACEHOLDER: set once breakout board wiring is confirmed

// STEP pins
constexpr uint8_t PIN_STEP_J1 = 0;   // PLACEHOLDER
constexpr uint8_t PIN_STEP_J2 = 3;   // PLACEHOLDER
constexpr uint8_t PIN_STEP_J3 = 6;   // PLACEHOLDER
constexpr uint8_t PIN_STEP_J4 = 9;   // PLACEHOLDER
constexpr uint8_t PIN_STEP_J5 = 12;  // PLACEHOLDER
constexpr uint8_t PIN_STEP_J6 = 15;  // PLACEHOLDER

// DIR pins
constexpr uint8_t PIN_DIR_J1 = 1;    // PLACEHOLDER
constexpr uint8_t PIN_DIR_J2 = 4;    // PLACEHOLDER
constexpr uint8_t PIN_DIR_J3 = 7;    // PLACEHOLDER
constexpr uint8_t PIN_DIR_J4 = 10;   // PLACEHOLDER
constexpr uint8_t PIN_DIR_J5 = 13;   // PLACEHOLDER
constexpr uint8_t PIN_DIR_J6 = 16;   // PLACEHOLDER

// EN pins (one shared or individual — PLACEHOLDER for individual)
constexpr uint8_t PIN_EN_J1 = 2;     // PLACEHOLDER
constexpr uint8_t PIN_EN_J2 = 5;     // PLACEHOLDER
constexpr uint8_t PIN_EN_J3 = 8;     // PLACEHOLDER
constexpr uint8_t PIN_EN_J4 = 11;    // PLACEHOLDER
constexpr uint8_t PIN_EN_J5 = 14;    // PLACEHOLDER
constexpr uint8_t PIN_EN_J6 = 17;    // PLACEHOLDER

// Limit switch pins (normally-open, pulled high, trigger = LOW)
constexpr uint8_t PIN_LIMIT_J1 = 24; // PLACEHOLDER
constexpr uint8_t PIN_LIMIT_J2 = 25; // PLACEHOLDER
constexpr uint8_t PIN_LIMIT_J3 = 26; // PLACEHOLDER
constexpr uint8_t PIN_LIMIT_J4 = 27; // PLACEHOLDER
constexpr uint8_t PIN_LIMIT_J5 = 28; // PLACEHOLDER
constexpr uint8_t PIN_LIMIT_J6 = 29; // PLACEHOLDER

// Homing direction: +1 or -1 (which way each joint moves to find its switch)
// PLACEHOLDER: set based on physical mounting of switches
constexpr int8_t HOME_DIR_J1 = -1;
constexpr int8_t HOME_DIR_J2 = -1;
constexpr int8_t HOME_DIR_J3 = -1;
constexpr int8_t HOME_DIR_J4 = -1;
constexpr int8_t HOME_DIR_J5 = -1;
constexpr int8_t HOME_DIR_J6 = -1;

// Number of joints
constexpr uint8_t NUM_JOINTS = 6;
