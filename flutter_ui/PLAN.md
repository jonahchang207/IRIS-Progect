# IRIS Flutter UI — Architecture Plan

## Architecture Decision: Python WebSocket Bridge (not direct serial)

Flutter connects to a **local FastAPI server** (`host/bridge_server.py`) over WebSocket + HTTP.
Python owns serial, YOLO, camera, and IK. Flutter is purely a display/input layer.

**Why not direct serial from Flutter:**
- IK solver (NumPy), YOLO inference (PyTorch), and camera capture (OpenCV) cannot run in Dart
- `serial_comm.py` is already thread-safe production code — rewriting it in Dart gains nothing
- Python's pyserial handles macOS/Windows port detection automatically; `flutter_libserialport` has known Teensy VID:PID edge cases

---

## System Architecture

```
Teensy 4.1 (USB Serial 115200)
    │
    ▼
host/bridge_server.py  —  FastAPI + uvicorn  (localhost:8765)
    │  wraps existing: IRISSerial, IRISVision, IRISPipeline — zero modification
    │
    ├─── WS /ws/joints   (10 Hz)  → {"joints":[j1..j6], "status":"IDLE"}
    ├─── WS /ws/camera   (15 Hz)  → {"frame_b64":"...", "detections":[...]}
    ├─── WS /ws/log      (event)  → {"level":"INFO", "msg":"..."}
    │
    ├─── POST /cmd/estop
    ├─── POST /cmd/home          {"joint": null | 1-6}
    ├─── POST /cmd/movej         {"angles": [j1..j6]}
    ├─── POST /cmd/jog           {"joint": 0-5, "delta_deg": ±n}
    ├─── POST /cmd/pipeline/start
    ├─── POST /cmd/pipeline/stop
    ├─── POST /cmd/enable
    ├─── POST /cmd/disable
    ├─── GET  /status
    ├─── GET  /config            → parsed config.yaml
    └─── PUT  /config            → update runtime config values
    │
    ▼
iris_gui/  (Flutter desktop — macOS + Windows)
    services/ → providers/ (Riverpod) → screens/ → widgets/
```

---

## Flutter App Structure

```
iris_gui/
├── pubspec.yaml
├── lib/
│   ├── main.dart
│   ├── core/
│   │   ├── constants.dart           # localhost:8765, WS endpoints
│   │   └── extensions.dart
│   ├── services/
│   │   ├── bridge_client.dart       # Dio + web_socket_channel
│   │   ├── joint_state_service.dart # /ws/joints parser
│   │   ├── camera_service.dart      # /ws/camera parser → Uint8List + detections
│   │   └── log_service.dart         # /ws/log parser
│   ├── models/
│   │   ├── joint_state.dart         # JointState(List<double> angles, SystemStatus)
│   │   ├── detection.dart           # Detection(x, y, z, conf, bbox)
│   │   ├── system_status.dart       # enum: idle, moving, homing, estopped
│   │   └── log_entry.dart           # LogEntry(time, level, msg)
│   ├── providers/
│   │   ├── bridge_provider.dart     # connection state + reconnect logic
│   │   ├── joint_provider.dart      # StreamProvider<JointState>
│   │   ├── camera_provider.dart     # StreamProvider<CameraFrame>
│   │   ├── log_provider.dart        # circular buffer, 10k entries
│   │   └── pipeline_provider.dart   # pipeline running state + stats
│   ├── screens/
│   │   ├── main_shell.dart          # NavigationRail + persistent E-STOP overlay
│   │   ├── dashboard_screen.dart    # camera + joint gauges + quick controls
│   │   ├── manual_control_screen.dart # sliders + jog buttons per joint
│   │   ├── pipeline_screen.dart     # auto pipeline start/stop + stats
│   │   ├── console_screen.dart      # virtual-scroll log with filter
│   │   └── settings_screen.dart    # config.yaml viewer/editor
│   ├── widgets/
│   │   ├── estop_button.dart        # ALWAYS-visible overlay, 72×72 red
│   │   ├── camera_feed.dart         # Image.memory() JPEG + overlay
│   │   ├── detection_overlay.dart   # CustomPainter for bounding boxes
│   │   ├── joint_gauge.dart         # Arc gauge for one joint
│   │   ├── joint_panel.dart         # 6× JointGauge row
│   │   ├── joint_slider_card.dart   # slider + ±1° ±10° jog + numeric input
│   │   ├── connection_status_chip.dart
│   │   ├── status_badge.dart        # IDLE/MOVING/HOMING/ESTOP colour chip
│   │   └── log_list_view.dart       # virtualised log scroll
│   └── theme/
│       ├── app_theme.dart           # Material3 dark, IRIS accent colour
│       └── text_styles.dart
├── macos/Runner/
│   ├── DebugProfile.entitlements    # com.apple.security.network.client = true
│   └── Release.entitlements
└── windows/runner/main.cpp
```

---

## Key Packages

```yaml
flutter_riverpod: ^2.5.1      # state management
web_socket_channel: ^3.0.1    # WS streams
dio: ^5.4.3                   # HTTP REST
fl_chart: ^0.68.0             # joint arc gauges + history
flutter_svg: ^2.0.10+1        # E-STOP icon
window_manager: ^0.3.9        # min window size 1200×800
freezed_annotation: ^2.4.1   # immutable models
```

---

## Screen Layout

### Dashboard (default)
```
┌──────────────────────────────────────────────────────────────────┐
│  [IRIS]  [● Connected]  [STATUS: IDLE]              [● E-STOP]  │
├──────────────────────────┬───────────────────────────────────────┤
│                          │  J1  J2  J3  J4  J5  J6              │
│  Camera Feed             │  ○   ○   ○   ○   ○   ○  (arc gauges) │
│  640×480 + YOLO boxes    │  0°  0° 90°  0° 90°  0°              │
│                          ├───────────────────────────────────────┤
│                          │  [Home All]  [Enable]  [Go Home]      │
└──────────────────────────┴───────────────────────────────────────┤
│  Serial log preview (last 5 lines)                     [→ More] │
└──────────────────────────────────────────────────────────────────┘
```

### Manual Control
```
┌──────────────────────────────────────────────────────────────────┐
│  J1 NEMA23  [◄◄-10] [◄-1] ─────●──────── [+1►] [+10►►]  30.0° │
│  J2 NEMA23  [◄◄-10] [◄-1] ──●─────────── [+1►] [+10►►] -20.0° │
│  J3 NEMA17  ...                                                   │
│  J4 NEMA17  ...                                                   │
│  J5 NEMA17  ...                                                   │
│  J6 NEMA17  ...                                                   │
├──────────────────────────────────────────────────────────────────┤
│  [Home J1][Home J2][Home J3][Home J4][Home J5][Home J6]         │
│  [Home All]              [Send to Target]                         │
└──────────────────────────────────────────────────────────────────┘
```

### Pipeline
```
  Pipeline Status: IDLE ●
  [▶ START AUTO PIPELINE]   [■ STOP]
  Cycles complete: 3   Detections this run: 14
  Last pick: (0.182, 0.093) m   conf: 0.87
```

### Console
```
  [ALL▼] [Search:________] [Clear] [‖ Pause]
  18:15:03 [INFO]  IRIS firmware ready
  18:15:03 [DEBUG] >> STATUS
  18:15:03 [DEBUG] << STATUS IDLE
  ... (virtualised, 10k line buffer)
```

### Settings
  Reads `GET /config` → renders config.yaml as a live-editable form.
  `PUT /config` to apply changes without restarting.

---

## Platform Notes

### macOS
- Add to both entitlements files: `com.apple.security.network.client = true`
- Flutter does NOT access serial or camera — no USB/camera entitlements needed
- Launch bridge via `Process.run('python3', ['host/bridge_server.py'])`

### Windows
- No sandbox — network just works
- Launch bridge via `Process.run('python', ['host/bridge_server.py'])` or `bridge_server.exe` (PyInstaller)
- Teensy 4.1 needs CDC serial driver installed once (via Teensyduino installer)

### Both
Bridge startup handshake in `BridgeProvider`:
```
startup → GET /status (5s timeout, exponential backoff)
  if refused → show "Launch Bridge" button
  if 200 OK  → connect 3× WebSockets → enable all UI
```

---

## E-STOP Safety Design
- Overlay widget inserted at root navigator — never covered by any screen
- POST /cmd/estop fires on tap with 0 debounce
- Local "estopped" flag disables all motion controls until ENABLE pressed
- Red ring animation pulses on ESTOP active state
- Keyboard shortcut: `Escape` key also triggers ESTOP
