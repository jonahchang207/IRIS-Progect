---
title: Hardware
layout: default
nav_order: 3
---

# Hardware
{: .no_toc }

<details open markdown="block">
  <summary>Table of contents</summary>
  {: .text-delta }
- TOC
{:toc}
</details>

---

## Bill of Materials

| Qty | Component | Notes |
|-----|-----------|-------|
| 1 | Teensy 4.1 | 600 MHz ARM Cortex-M7 |
| 1 | Breakout board | Mates with Teensy 4.1 |
| 6 | DM542T Stepper Driver | 1.0–4.2 A, 20–50 VDC |
| 2 | NEMA 23 Stepper Motor | Joints 1 and 2 |
| 4 | NEMA 17 Stepper Motor | Joints 3–6 |
| 6 | Limit switch (NO) | Homing — normally-open, panel mount |
| 1 | USB-B to USB-A cable | Host PC ↔ Teensy |
| 1 | 24–48 V DC power supply | Motor power rail |
| 1 | 5 V DC supply | Logic power (or USB-powered) |

---

## DM542T Driver Configuration

Each DM542T has two dip-switch banks: **SW1–4** (microstepping) and **SW5–8** (current).

### Current Setting (SW5–8)

Set peak current to match your motor's rated current. Example for a 3 A NEMA 23:

| SW5 | SW6 | SW7 | SW8 | Peak Current |
|-----|-----|-----|-----|-------------|
| ON  | ON  | OFF | OFF | 3.00 A |
| ON  | OFF | ON  | OFF | 2.84 A |

Consult the DM542T datasheet for the full table.

### Microstepping (SW1–4)

{: .placeholder }
Set all 6 drivers to the **same** microstepping value, then update `STEPS_REV_NEMA23` and `STEPS_REV_NEMA17` in `src/config.h` to match.

| SW1 | SW2 | SW3 | SW4 | Steps/Rev (200 base) |
|-----|-----|-----|-----|---------------------|
| ON  | ON  | ON  | ON  | 400 (½ step) |
| OFF | ON  | ON  | ON  | 800 (¼ step) |
| ON  | OFF | ON  | ON  | 1600 (⅛ step) ← recommended |
| OFF | OFF | ON  | ON  | 3200 (1/16 step) |

**Recommended: 1600 steps/rev** — good resolution without excessive step frequency.

---

## Wiring: Teensy 4.1 → DM542T

Each driver needs three signals from the Teensy:

| Teensy Pin | DM542T Terminal | Description |
|------------|-----------------|-------------|
| `PIN_STEP_Jn` | `PUL+` | Step pulse (3.3 V logic OK with 1 kΩ series resistor) |
| GND | `PUL-` | Step ground |
| `PIN_DIR_Jn` | `DIR+` | Direction |
| GND | `DIR-` | Direction ground |
| `PIN_EN_Jn` | `ENA+` | Enable (LOW = enabled) |
| GND | `ENA-` | Enable ground |

{: .warning }
The DM542T `PUL+` input expects 5 V logic but will work with 3.3 V if you use a 1 kΩ pull-up resistor to 5 V on the PUL+ line. Alternatively use the Teensy 4.1's 5 V-tolerant pins on the breakout board.

---

## Wiring: Limit Switches

Each joint has one normally-open (NO) limit switch wired as active-low:

```
Teensy 3.3V ──── 10kΩ ──┬──── PIN_LIMIT_Jn (INPUT_PULLUP)
                          │
                        [SW NO]
                          │
                         GND
```

The firmware configures each limit pin as `INPUT_PULLUP`. When the switch is open, the pin reads HIGH. When triggered, it reads LOW.

{: .note }
`INPUT_PULLUP` uses the Teensy's internal ~47 kΩ pull-up. An external 10 kΩ pull-up is optional but improves noise immunity in an electrically noisy stepper environment.

---

## Pin Assignment Placeholder Table

Open `firmware/IRIS_firmware/src/config.h` and set these to match your breakout board:

```cpp
// STEP pins
PIN_STEP_J1 = ??;   PIN_STEP_J2 = ??;   PIN_STEP_J3 = ??;
PIN_STEP_J4 = ??;   PIN_STEP_J5 = ??;   PIN_STEP_J6 = ??;

// DIR pins
PIN_DIR_J1  = ??;   PIN_DIR_J2  = ??;   PIN_DIR_J3  = ??;
PIN_DIR_J4  = ??;   PIN_DIR_J5  = ??;   PIN_DIR_J6  = ??;

// EN pins (LOW = enabled)
PIN_EN_J1   = ??;   PIN_EN_J2   = ??;   PIN_EN_J3   = ??;
PIN_EN_J4   = ??;   PIN_EN_J5   = ??;   PIN_EN_J6   = ??;

// Limit switch pins
PIN_LIMIT_J1 = ??;  PIN_LIMIT_J2 = ??;  PIN_LIMIT_J3 = ??;
PIN_LIMIT_J4 = ??;  PIN_LIMIT_J5 = ??;  PIN_LIMIT_J6 = ??;
```

---

## Power Supply

- **Motor rail:** 24–48 VDC, sized for total stepper current draw.
  - 2× NEMA 23 @ ~3 A + 4× NEMA 17 @ ~1.5 A = ~12 A peak (derated: ~8 A continuous supply minimum)
- **Logic rail:** Teensy 4.1 is powered via USB from the host PC (500 mA max). No separate logic supply needed if USB-powered.
- **Safety:** Use a fuse on the motor rail. Never connect/disconnect stepper motor wires while the driver is powered.
