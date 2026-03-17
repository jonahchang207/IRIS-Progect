---
title: Firmware
layout: default
nav_order: 4
---

# Firmware
{: .no_toc }

Teensy 4.1 firmware — stepper control, homing, and USB serial protocol.
{: .fs-6 .fw-300 }

<details open markdown="block">
  <summary>Table of contents</summary>
  {: .text-delta }
- TOC
{:toc}
</details>

---

## File Structure

```
firmware/IRIS_firmware/
├── platformio.ini        # Build config (Teensy 4.1, AccelStepper)
└── src/
    ├── main.cpp          # Setup + loop (5 lines)
    ├── config.h          # ALL hardware constants — edit this file
    ├── stepper.h/cpp     # StepperAxis class + global axes[] array
    ├── protocol.h/cpp    # Serial command parser + state machine
    └── homing.h/cpp      # Limit-switch homing state machine
```

---

## Building and Uploading

```bash
cd firmware/IRIS_firmware

# Build only
pio run

# Build and upload
pio run --target upload

# Serial monitor (115200 baud)
pio device monitor --baud 115200
```

---

## Configuration (`src/config.h`)

Every physical constant is in `config.h`. All lines marked `// PLACEHOLDER` must be set before first use.

### Microstepping and steps/rev

```cpp
// Set to match your DM542T dip switch SW1-4 setting
constexpr uint16_t STEPS_REV_NEMA23 = 1600;   // PLACEHOLDER
constexpr uint16_t STEPS_REV_NEMA17 = 1600;   // PLACEHOLDER
```

### Gear ratios

If your joints have belt or gear reduction, set the ratio (output turns / input turns):

```cpp
constexpr float RATIO_J1 = 1.0f;   // PLACEHOLDER — e.g. 5.0 for 5:1 gearbox
```

The firmware automatically converts `degrees → output steps` accounting for the ratio.

### Soft limits

```cpp
constexpr float LIMIT_MIN_J1 = -170.0f;
constexpr float LIMIT_MAX_J1 =  170.0f;
// ... etc.
```

Any `MOVEA` command that would exceed a soft limit is clamped and a `WARN` message is sent to the host.

### Homing direction

```cpp
constexpr int8_t HOME_DIR_J1 = -1;   // -1 = move negative to find switch
```

Set to `+1` or `-1` depending on which direction each joint needs to move to reach its limit switch.

---

## Serial Protocol

All commands and responses are ASCII strings terminated with `\n`.

### Commands (Host → Teensy)

| Command | Arguments | Description |
|---------|-----------|-------------|
| `MOVEA` | `j1 j2 j3 j4 j5 j6` | Absolute move. All 6 joint angles in degrees (float). |
| `HOME` | `[n]` | Home all joints sequentially, or joint `n` (1–6). |
| `POS` | — | Query current joint positions. |
| `STATUS` | — | Query system state. |
| `SPEED` | `s1 s2 s3 s4 s5 s6` | Set max speed per joint in steps/sec. |
| `ENABLE` | — | Enable all DM542T drivers. |
| `DISABLE` | — | Disable all drivers (motors free-wheeling). |
| `ESTOP` | — | Immediate stop, no deceleration. Enters ESTOPPED state. |

### Responses (Teensy → Host)

| Response | Meaning |
|----------|---------|
| `OK` | Command accepted, motion started (or action complete). |
| `DONE` | All axes have reached their target position. |
| `POS d1 d2 d3 d4 d5 d6` | Current joint angles in degrees (3 decimal places). |
| `STATUS IDLE` | No motion, not homing, no estop. |
| `STATUS MOVING` | One or more joints are moving. |
| `STATUS HOMING` | Homing sequence active. |
| `STATUS ESTOP` | Emergency stop active — send `ENABLE` to clear. |
| `WARN soft_limit J3 clamped to 135.000` | Joint was clamped to soft limit. |
| `ERR <reason>` | Command rejected — see reason string. |

### Example session

```
→ STATUS
← STATUS IDLE

→ MOVEA 30.0 -20.0 45.0 0.0 90.0 0.0
← OK
← DONE

→ POS
← POS 30.000 -20.000 45.000 0.000 90.000 0.000

→ MOVEA 200.0 0.0 0.0 0.0 0.0 0.0
← WARN soft_limit J1 clamped to 170.000
← OK
← DONE

→ ESTOP
← OK
```

---

## Homing Sequence

Homing runs joints in order J1 → J2 → J3 → J4 → J5 → J6.

For each joint, the three-phase sequence is:

```
Phase 1 — FAST_SEEK
  Move in HOME_DIR at HOME_FAST_SPEED (800 steps/sec default)
  until limit switch triggers (reads LOW).

Phase 2 — BACK_OFF
  Move away from switch by HOME_BACKOFF_DEG (3° default).

Phase 3 — SLOW_SEEK
  Move back toward switch at HOME_SLOW_SPEED (200 steps/sec).
  When switch triggers: setZero() — this position is now 0°.
```

The two-phase approach (fast seek + slow creep) gives repeatable homing accuracy typically within ±0.05° at 1/8 microstepping.

{: .note }
Homing order (J1 first, J6 last) minimises mechanical stress. The outermost joints settle first, reducing load on inner joints during their homing moves.

---

## State Machine

```
          ENABLE
   ┌──── ESTOPPED ◄───────────────────────────┐
   │                                           │ ESTOP
   ▼                                           │
 IDLE ──── MOVEA ────► MOVING ──── DONE ────► IDLE
   │                                           ▲
   └──── HOME  ────► HOMING ──── DONE ────────┘
```

From any state, `ESTOP` transitions immediately to `ESTOPPED`.
`ENABLE` from `ESTOPPED` returns to `IDLE`.

---

## AccelStepper Notes

- `axes_run()` is called every loop iteration — do not add blocking code to `loop()`
- Speed is in **steps/sec**, acceleration in **steps/sec²**
- The Teensy 4.1 at 600 MHz can sustain ~200 000 steps/sec across all 6 axes simultaneously in software step generation — well above any requirement for this arm
