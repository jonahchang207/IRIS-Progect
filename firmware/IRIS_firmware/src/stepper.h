#pragma once
#include <AccelStepper.h>
#include "config.h"

// ============================================================
//  StepperAxis — wraps one DM542T + AccelStepper instance
//  Adds degree-based API, soft limits, and enable control.
// ============================================================

class StepperAxis {
public:
    StepperAxis(uint8_t stepPin, uint8_t dirPin, uint8_t enPin,
                float stepsPerDeg, float maxSpeed, float accel,
                float minDeg, float maxDeg);

    void begin();
    void enable();
    void disable();

    // Target in degrees (absolute, from home = 0)
    bool moveToDeg(float deg);

    // Target in raw steps (absolute)
    void moveToSteps(long steps);

    // Must be called every loop iteration — runs the step ISR emulation
    void run();

    bool isRunning() const;
    void stop();            // decelerate to stop
    void estop();           // immediate stop, no decel

    float currentDeg()  const;
    long  currentSteps() const;

    // Called by homing module
    void setZero();
    void setCurrentDeg(float deg);

    AccelStepper& motor() { return _motor; }

private:
    AccelStepper _motor;
    uint8_t      _enPin;
    float        _stepsPerDeg;
    float        _minDeg;
    float        _maxDeg;

    bool clampDeg(float& deg) const;   // returns false if out of range
};

// ============================================================
//  Global axis array — indexed 0-5 = J1-J6
// ============================================================
extern StepperAxis axes[NUM_JOINTS];

void axes_init();
void axes_run();          // call every loop — runs all axes
void axes_enable_all();
void axes_disable_all();
void axes_estop_all();
bool axes_any_running();
