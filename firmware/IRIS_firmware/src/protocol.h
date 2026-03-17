#pragma once
#include <Arduino.h>

// ============================================================
//  Serial Command Protocol
//
//  Host → Teensy (commands, newline terminated):
//    MOVEA <j1> <j2> <j3> <j4> <j5> <j6>   absolute move in degrees
//    HOME [j]                                 home all joints, or single joint
//    POS                                      query current joint positions
//    STATUS                                   query running/idle/homing/estop state
//    SPEED <j1..j6>                           set max speed (steps/sec) per joint
//    ENABLE                                   enable all drivers
//    DISABLE                                  disable all drivers (free-wheeling)
//    ESTOP                                    immediate stop all axes
//
//  Teensy → Host (responses):
//    OK                                       command accepted, motion started
//    DONE                                     all axes reached target
//    POS <j1> <j2> <j3> <j4> <j5> <j6>      current degrees, 3 decimal places
//    STATUS IDLE | MOVING | HOMING | ESTOP
//    WARN soft_limit j<n> clamped to <val>    joint clamped to soft limit
//    ERR <reason>                             command rejected
// ============================================================

enum class SystemState : uint8_t {
    IDLE    = 0,
    MOVING  = 1,
    HOMING  = 2,
    ESTOPPED = 3,
};

void protocol_init();
void protocol_process();    // call every loop — reads serial, dispatches commands
void protocol_send_done();
void protocol_send_pos();
void protocol_send_status(SystemState s);

extern SystemState g_state;
