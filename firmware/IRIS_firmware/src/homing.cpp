#include "homing.h"
#include "stepper.h"
#include "config.h"
#include <Arduino.h>

// ============================================================
//  Limit switch pin table (indexed 0-5 = J1-J6)
// ============================================================
static const uint8_t LIMIT_PINS[NUM_JOINTS] = {
    PIN_LIMIT_J1, PIN_LIMIT_J2, PIN_LIMIT_J3,
    PIN_LIMIT_J4, PIN_LIMIT_J5, PIN_LIMIT_J6,
};

static const int8_t HOME_DIRS[NUM_JOINTS] = {
    HOME_DIR_J1, HOME_DIR_J2, HOME_DIR_J3,
    HOME_DIR_J4, HOME_DIR_J5, HOME_DIR_J6,
};

// ============================================================
//  Homing state machine
// ============================================================

enum class HomingPhase : uint8_t {
    IDLE       = 0,
    FAST_SEEK  = 1,   // move fast toward switch
    BACK_OFF   = 2,   // retreat after fast trigger
    SLOW_SEEK  = 3,   // creep back toward switch
    SET_ZERO   = 4,   // record position as zero
    DONE       = 5,
    FAILED     = 6,
};

static HomingPhase  s_phase          = HomingPhase::IDLE;
static uint8_t      s_current_joint  = 0;
static uint8_t      s_target_joint   = 0;   // 255 = all
static bool         s_home_all       = false;
static bool         s_succeeded      = false;

// Large step count for open-ended move toward switch (will be stopped on trigger)
static constexpr long SEEK_STEPS = 100000L;

// ---- helpers -----------------------------------------------

static inline float backoff_steps(uint8_t j) {
    // steps to back off in direction opposite to homing
    float spd = (j < 2) ? STEPS_PER_DEG_J1 : STEPS_PER_DEG_J3;  // J1/J2 vs J3-J6
    return HOME_BACKOFF_DEG * spd;
}

static void start_fast_seek(uint8_t j) {
    axes[j].enable();
    axes[j].motor().setMaxSpeed(HOME_FAST_SPEED);
    axes[j].motor().setAcceleration(HOME_FAST_SPEED * 2.0f);
    long target = axes[j].currentSteps() + HOME_DIRS[j] * SEEK_STEPS;
    axes[j].motor().moveTo(target);
    s_phase = HomingPhase::FAST_SEEK;
}

static void start_back_off(uint8_t j) {
    float bo = backoff_steps(j);
    long target = axes[j].currentSteps() + (-HOME_DIRS[j]) * (long)bo;
    axes[j].motor().setMaxSpeed(HOME_FAST_SPEED);
    axes[j].motor().moveTo(target);
    s_phase = HomingPhase::BACK_OFF;
}

static void start_slow_seek(uint8_t j) {
    axes[j].motor().setMaxSpeed(HOME_SLOW_SPEED);
    axes[j].motor().setAcceleration(HOME_SLOW_SPEED * 4.0f);
    long target = axes[j].currentSteps() + HOME_DIRS[j] * SEEK_STEPS;
    axes[j].motor().moveTo(target);
    s_phase = HomingPhase::SLOW_SEEK;
}

static void advance_to_next_joint() {
    if (!s_home_all || s_current_joint >= NUM_JOINTS - 1) {
        s_phase     = HomingPhase::DONE;
        s_succeeded = true;
        return;
    }
    s_current_joint++;
    start_fast_seek(s_current_joint);
}

// ============================================================
//  Public API
// ============================================================

bool limit_switch_triggered(uint8_t j) {
    return digitalRead(LIMIT_PINS[j]) == LOW;   // active-low (NO switch, pulled high)
}

void homing_start_all() {
    for (uint8_t i = 0; i < NUM_JOINTS; i++)
        pinMode(LIMIT_PINS[i], INPUT_PULLUP);

    s_home_all      = true;
    s_succeeded     = false;
    s_current_joint = 0;
    start_fast_seek(0);
}

void homing_start_joint(uint8_t j) {
    if (j >= NUM_JOINTS) return;
    pinMode(LIMIT_PINS[j], INPUT_PULLUP);
    s_home_all      = false;
    s_succeeded     = false;
    s_current_joint = j;
    start_fast_seek(j);
}

void homing_run() {
    if (s_phase == HomingPhase::IDLE ||
        s_phase == HomingPhase::DONE ||
        s_phase == HomingPhase::FAILED) return;

    uint8_t j = s_current_joint;
    axes[j].run();

    switch (s_phase) {
        case HomingPhase::FAST_SEEK:
            if (limit_switch_triggered(j)) {
                axes[j].estop();
                start_back_off(j);
            } else if (!axes[j].isRunning()) {
                // Reached SEEK_STEPS without triggering — should not happen
                s_phase = HomingPhase::FAILED;
                Serial.println("ERR homing_timeout J" + String(j + 1));
            }
            break;

        case HomingPhase::BACK_OFF:
            if (!axes[j].isRunning()) {
                start_slow_seek(j);
            }
            break;

        case HomingPhase::SLOW_SEEK:
            if (limit_switch_triggered(j)) {
                axes[j].estop();
                s_phase = HomingPhase::SET_ZERO;
            } else if (!axes[j].isRunning()) {
                s_phase = HomingPhase::FAILED;
                Serial.println("ERR homing_timeout_slow J" + String(j + 1));
            }
            break;

        case HomingPhase::SET_ZERO:
            axes[j].setZero();
            axes[j].motor().setMaxSpeed(
                j < 2 ? MAX_SPEED_J1 : MAX_SPEED_J3);   // restore operating speed
            axes[j].motor().setAcceleration(
                j < 2 ? ACCEL_J1 : ACCEL_J3);
            Serial.println("OK homed J" + String(j + 1));
            advance_to_next_joint();
            break;

        default:
            break;
    }
}

bool homing_is_active() {
    return s_phase != HomingPhase::IDLE &&
           s_phase != HomingPhase::DONE &&
           s_phase != HomingPhase::FAILED;
}

bool homing_succeeded() {
    return s_succeeded;
}
