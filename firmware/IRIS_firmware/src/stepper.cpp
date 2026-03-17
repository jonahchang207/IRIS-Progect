#include "stepper.h"
#include <Arduino.h>
#include <math.h>

// ============================================================
//  StepperAxis implementation
// ============================================================

StepperAxis::StepperAxis(uint8_t stepPin, uint8_t dirPin, uint8_t enPin,
                         float stepsPerDeg, float maxSpeed, float accel,
                         float minDeg, float maxDeg)
    : _motor(AccelStepper::DRIVER, stepPin, dirPin),
      _enPin(enPin),
      _stepsPerDeg(stepsPerDeg),
      _minDeg(minDeg),
      _maxDeg(maxDeg)
{
    _motor.setMaxSpeed(maxSpeed);
    _motor.setAcceleration(accel);
}

void StepperAxis::begin() {
    pinMode(_enPin, OUTPUT);
    disable();  // safe default — enable only when needed
    _motor.setCurrentPosition(0);
}

void StepperAxis::enable() {
    digitalWrite(_enPin, EN_ACTIVE_LOW ? LOW : HIGH);
}

void StepperAxis::disable() {
    digitalWrite(_enPin, EN_ACTIVE_LOW ? HIGH : LOW);
}

bool StepperAxis::moveToDeg(float deg) {
    if (!clampDeg(deg)) return false;
    long target = lroundf(deg * _stepsPerDeg);
    _motor.moveTo(target);
    return true;
}

void StepperAxis::moveToSteps(long steps) {
    _motor.moveTo(steps);
}

void StepperAxis::run() {
    _motor.run();
}

bool StepperAxis::isRunning() const {
    return _motor.distanceToGo() != 0;
}

void StepperAxis::stop() {
    _motor.stop();
}

void StepperAxis::estop() {
    _motor.setCurrentPosition(_motor.currentPosition());  // zero distance to go
    _motor.stop();
}

float StepperAxis::currentDeg() const {
    return static_cast<float>(_motor.currentPosition()) / _stepsPerDeg;
}

long StepperAxis::currentSteps() const {
    return _motor.currentPosition();
}

void StepperAxis::setZero() {
    _motor.setCurrentPosition(0);
}

void StepperAxis::setCurrentDeg(float deg) {
    _motor.setCurrentPosition(lroundf(deg * _stepsPerDeg));
}

bool StepperAxis::clampDeg(float& deg) const {
    if (deg < _minDeg || deg > _maxDeg) {
        deg = constrain(deg, _minDeg, _maxDeg);
        return false;  // caller warned — we still move to clamped value
    }
    return true;
}

// ============================================================
//  Global axis array
// ============================================================

StepperAxis axes[NUM_JOINTS] = {
    StepperAxis(PIN_STEP_J1, PIN_DIR_J1, PIN_EN_J1, STEPS_PER_DEG_J1, MAX_SPEED_J1, ACCEL_J1, LIMIT_MIN_J1, LIMIT_MAX_J1),
    StepperAxis(PIN_STEP_J2, PIN_DIR_J2, PIN_EN_J2, STEPS_PER_DEG_J2, MAX_SPEED_J2, ACCEL_J2, LIMIT_MIN_J2, LIMIT_MAX_J2),
    StepperAxis(PIN_STEP_J3, PIN_DIR_J3, PIN_EN_J3, STEPS_PER_DEG_J3, MAX_SPEED_J3, ACCEL_J3, LIMIT_MIN_J3, LIMIT_MAX_J3),
    StepperAxis(PIN_STEP_J4, PIN_DIR_J4, PIN_EN_J4, STEPS_PER_DEG_J4, MAX_SPEED_J4, ACCEL_J4, LIMIT_MIN_J4, LIMIT_MAX_J4),
    StepperAxis(PIN_STEP_J5, PIN_DIR_J5, PIN_EN_J5, STEPS_PER_DEG_J5, MAX_SPEED_J5, ACCEL_J5, LIMIT_MIN_J5, LIMIT_MAX_J5),
    StepperAxis(PIN_STEP_J6, PIN_DIR_J6, PIN_EN_J6, STEPS_PER_DEG_J6, MAX_SPEED_J6, ACCEL_J6, LIMIT_MIN_J6, LIMIT_MAX_J6),
};

void axes_init() {
    for (auto& ax : axes) ax.begin();
}

void axes_run() {
    for (auto& ax : axes) ax.run();
}

void axes_enable_all() {
    for (auto& ax : axes) ax.enable();
}

void axes_disable_all() {
    for (auto& ax : axes) ax.disable();
}

void axes_estop_all() {
    for (auto& ax : axes) ax.estop();
}

bool axes_any_running() {
    for (const auto& ax : axes)
        if (ax.isRunning()) return true;
    return false;
}
