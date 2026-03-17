#include <Arduino.h>
#include "config.h"
#include "stepper.h"
#include "protocol.h"
#include "homing.h"

// ============================================================
//  IRIS Firmware — Teensy 4.1
//  Main loop: protocol processing + stepper step generation
// ============================================================

void setup() {
    protocol_init();
    axes_init();
    axes_enable_all();
    Serial.println("IRIS firmware ready");
}

void loop() {
    // Step generation — must run every iteration for smooth motion
    axes_run();

    // Serial command processing + state machine updates
    protocol_process();
}
