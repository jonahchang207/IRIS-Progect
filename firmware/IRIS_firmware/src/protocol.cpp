#include "protocol.h"
#include "stepper.h"
#include "homing.h"
#include "config.h"
#include <Arduino.h>

SystemState g_state = SystemState::IDLE;

static constexpr uint8_t BUF_SIZE = 128;
static char     s_buf[BUF_SIZE];
static uint8_t  s_pos = 0;

// ---- helpers -----------------------------------------------

static void send(const char* msg) {
    Serial.println(msg);
}

static void sendf(const char* fmt, ...) {
    char tmp[128];
    va_list ap;
    va_start(ap, fmt);
    vsnprintf(tmp, sizeof(tmp), fmt, ap);
    va_end(ap);
    Serial.println(tmp);
}

// ---- command handlers --------------------------------------

static void cmd_movea(char* args) {
    if (g_state == SystemState::ESTOPPED) { send("ERR estop_active"); return; }
    if (g_state == SystemState::HOMING)   { send("ERR homing_active"); return; }

    float deg[NUM_JOINTS];
    int   parsed = sscanf(args, "%f %f %f %f %f %f",
                          &deg[0], &deg[1], &deg[2],
                          &deg[3], &deg[4], &deg[5]);
    if (parsed != NUM_JOINTS) {
        send("ERR movea_requires_6_values");
        return;
    }

    bool clamped = false;
    for (uint8_t i = 0; i < NUM_JOINTS; i++) {
        bool ok = axes[i].moveToDeg(deg[i]);
        if (!ok) {
            sendf("WARN soft_limit J%d clamped to %.3f", i + 1, axes[i].currentDeg());
            clamped = true;
        }
    }
    g_state = SystemState::MOVING;
    send("OK");
}

static void cmd_home(char* args) {
    if (g_state == SystemState::ESTOPPED) { send("ERR estop_active"); return; }

    if (args == nullptr || args[0] == '\0') {
        homing_start_all();
    } else {
        int j = atoi(args);
        if (j < 1 || j > NUM_JOINTS) { send("ERR invalid_joint"); return; }
        homing_start_joint((uint8_t)(j - 1));
    }
    g_state = SystemState::HOMING;
    send("OK");
}

static void cmd_pos() {
    protocol_send_pos();
}

static void cmd_status() {
    protocol_send_status(g_state);
}

static void cmd_speed(char* args) {
    float spd[NUM_JOINTS];
    int parsed = sscanf(args, "%f %f %f %f %f %f",
                        &spd[0], &spd[1], &spd[2],
                        &spd[3], &spd[4], &spd[5]);
    if (parsed != NUM_JOINTS) { send("ERR speed_requires_6_values"); return; }
    for (uint8_t i = 0; i < NUM_JOINTS; i++)
        axes[i].motor().setMaxSpeed(spd[i]);
    send("OK");
}

static void cmd_enable() {
    axes_enable_all();
    send("OK");
}

static void cmd_disable() {
    if (g_state == SystemState::MOVING) { send("ERR motion_active"); return; }
    axes_disable_all();
    send("OK");
}

static void cmd_estop() {
    axes_estop_all();
    g_state = SystemState::ESTOPPED;
    send("OK");
}

// ---- dispatch ----------------------------------------------

static void dispatch(char* line) {
    // Split verb from args
    char* sp = strchr(line, ' ');
    char* args = nullptr;
    if (sp) {
        *sp  = '\0';
        args = sp + 1;
    }

    if      (strcmp(line, "MOVEA")   == 0) cmd_movea(args ? args : (char*)"");
    else if (strcmp(line, "HOME")    == 0) cmd_home(args);
    else if (strcmp(line, "POS")     == 0) cmd_pos();
    else if (strcmp(line, "STATUS")  == 0) cmd_status();
    else if (strcmp(line, "SPEED")   == 0) cmd_speed(args ? args : (char*)"");
    else if (strcmp(line, "ENABLE")  == 0) cmd_enable();
    else if (strcmp(line, "DISABLE") == 0) cmd_disable();
    else if (strcmp(line, "ESTOP")   == 0) cmd_estop();
    else sendf("ERR unknown_cmd_%s", line);
}

// ============================================================
//  Public API
// ============================================================

void protocol_init() {
    Serial.begin(SERIAL_BAUD);
    while (!Serial && millis() < 2000) {}  // wait up to 2s for USB serial
}

void protocol_process() {
    // --- read serial into line buffer ---
    while (Serial.available()) {
        char c = (char)Serial.read();
        if (c == '\r') continue;  // ignore CR in CRLF
        if (c == '\n') {
            s_buf[s_pos] = '\0';
            if (s_pos > 0) dispatch(s_buf);
            s_pos = 0;
        } else if (s_pos < BUF_SIZE - 1) {
            s_buf[s_pos++] = c;
        }
    }

    // --- state transitions ---
    if (g_state == SystemState::HOMING) {
        homing_run();
        if (!homing_is_active()) {
            g_state = homing_succeeded() ? SystemState::IDLE : SystemState::IDLE;
            if (homing_succeeded()) send("DONE");
            else                    send("ERR homing_failed");
        }
    }

    if (g_state == SystemState::MOVING) {
        if (!axes_any_running()) {
            g_state = SystemState::IDLE;
            protocol_send_done();
        }
    }
}

void protocol_send_done() {
    send("DONE");
}

void protocol_send_pos() {
    sendf("POS %.3f %.3f %.3f %.3f %.3f %.3f",
          axes[0].currentDeg(), axes[1].currentDeg(), axes[2].currentDeg(),
          axes[3].currentDeg(), axes[4].currentDeg(), axes[5].currentDeg());
}

void protocol_send_status(SystemState s) {
    switch (s) {
        case SystemState::IDLE:     send("STATUS IDLE");    break;
        case SystemState::MOVING:   send("STATUS MOVING");  break;
        case SystemState::HOMING:   send("STATUS HOMING");  break;
        case SystemState::ESTOPPED: send("STATUS ESTOP");   break;
    }
}
