# IRIS Flutter UI — TODO
> See PLAN.md for full architecture. Work through phases in order.

---

## Phase F1 — Python Bridge Server (`host/bridge_server.py`)

- [ ] **F1.1** Add dependencies to `host/` — `fastapi`, `uvicorn`, `python-multipart`, `websockets`
  - Add `host/requirements.txt`
- [ ] **F1.2** Scaffold `host/bridge_server.py`
  - FastAPI app, uvicorn runner, CORS for localhost
  - Import `IRISSerial`, `IRISVision`, `IRISPipeline` from existing files
  - Startup/shutdown lifecycle (connect serial, open camera)
- [ ] **F1.3** WebSocket: `/ws/joints` (10 Hz)
  - Poll `serial.get_position()` + `serial.get_status()`
  - Emit `{"joints": [j1..j6], "status": "IDLE"}`
- [ ] **F1.4** WebSocket: `/ws/camera` (15 Hz)
  - Capture frame → `vision.detect()` → `vision.annotate_frame()`
  - JPEG encode at 70% quality → base64
  - Emit `{"frame_b64": "...", "detections": [{"x_m":..., "y_m":..., "conf":..., "bbox":[...]}]}`
- [ ] **F1.5** WebSocket: `/ws/log` (event-driven)
  - Custom `logging.Handler` that broadcasts to all connected clients
  - Payload: `{"level": "INFO", "msg": "..."}`
- [ ] **F1.6** REST endpoints
  - `POST /cmd/estop`
  - `POST /cmd/home` — body `{"joint": null | 1-6}`
  - `POST /cmd/movej` — body `{"angles": [j1..j6]}`
  - `POST /cmd/jog` — body `{"joint": 0-5, "delta_deg": float}`
  - `POST /cmd/pipeline/start`
  - `POST /cmd/pipeline/stop`
  - `POST /cmd/enable`
  - `POST /cmd/disable`
  - `GET /status`
  - `GET /config` — returns parsed `config.yaml` as JSON
  - `PUT /config` — partial update, writes back to `config.yaml`
- [ ] **F1.7** Test bridge standalone with `curl` + `websocat` before touching Flutter

---

## Phase F2 — Flutter Project Setup

- [ ] **F2.1** Create Flutter project with desktop targets
  ```bash
  flutter create --platforms=macos,windows iris_gui
  cd iris_gui
  flutter config --enable-macos-desktop
  flutter config --enable-windows-desktop
  ```
- [ ] **F2.2** Add all packages to `pubspec.yaml`
  - `flutter_riverpod`, `web_socket_channel`, `dio`, `fl_chart`
  - `flutter_svg`, `window_manager`, `freezed_annotation`
  - `json_annotation`, `logger`, `yaml`, `intl`
  - Dev: `build_runner`, `freezed`, `riverpod_generator`, `json_serializable`
- [ ] **F2.3** macOS entitlements — add `com.apple.security.network.client` to both entitlements files
- [ ] **F2.4** `main.dart` — window setup: min size 1200×800, title "IRIS Control", dark mode
- [ ] **F2.5** `theme/app_theme.dart` — Material3 dark, deep red accent (#C62828)
- [ ] **F2.6** Verify `flutter run -d macos` shows blank dark window

---

## Phase F3 — Models + Services

- [ ] **F3.1** `models/system_status.dart` — enum `SystemStatus { idle, moving, homing, estopped }`
- [ ] **F3.2** `models/joint_state.dart` — `JointState(List<double> angles, SystemStatus status)` (freezed)
- [ ] **F3.3** `models/detection.dart` — `Detection(double xM, yM, zM, conf, List<double> bboxPx)` (freezed)
- [ ] **F3.4** `models/log_entry.dart` — `LogEntry(DateTime time, String level, String msg)` (freezed)
- [ ] **F3.5** `services/bridge_client.dart`
  - `Dio` instance pointed at `localhost:8765`
  - `connectWebSocket(String path)` → `WebSocketChannel`
  - `post(String path, Map body)` helper
  - Connection error handling + timeout
- [ ] **F3.6** `services/joint_state_service.dart` — parse `/ws/joints` JSON → `JointState`
- [ ] **F3.7** `services/camera_service.dart` — parse `/ws/camera` JSON → base64 decode → `Uint8List` + `List<Detection>`
- [ ] **F3.8** `services/log_service.dart` — parse `/ws/log` JSON → `LogEntry`

---

## Phase F4 — Providers (State Management)

- [ ] **F4.1** `providers/bridge_provider.dart`
  - `BridgeNotifier extends StateNotifier<BridgeState>`
  - States: `disconnected | connecting | connected | error`
  - `connect()`: `GET /status` with exponential backoff (max 5s)
  - `launchBridge()`: `Process.run('python3', ['host/bridge_server.py'])`
  - Reconnect on WS disconnect (backoff: 1s, 2s, 4s, max 10s)
- [ ] **F4.2** `providers/joint_provider.dart`
  - `StreamProvider<JointState>` from joints WebSocket stream
  - Fallback: `AsyncValue.loading()` while connecting
- [ ] **F4.3** `providers/camera_provider.dart`
  - `StreamProvider<CameraFrame>` from camera WebSocket stream
- [ ] **F4.4** `providers/log_provider.dart`
  - `StateNotifierProvider<LogNotifier, List<LogEntry>>`
  - Circular buffer: max 10,000 entries
  - `filterLevel(String level)` derived provider
- [ ] **F4.5** `providers/pipeline_provider.dart`
  - `StateNotifierProvider<PipelineNotifier, PipelineState>`
  - Tracks: `running`, `cycleCount`, `detectionCount`, `lastDetection`

---

## Phase F5 — Widgets (Bottom-up)

- [ ] **F5.1** `widgets/estop_button.dart`
  - 72×72dp red filled circle, white stop icon
  - `Overlay` inserted at root — never covered
  - `Escape` key also triggers ESTOP
  - Pulses red glow animation when ESTOPPED state active
  - Calls `POST /cmd/estop` + latches local `estopped` flag
- [ ] **F5.2** `widgets/status_badge.dart` — colour-coded chip (green=IDLE, blue=MOVING, yellow=HOMING, red=ESTOP)
- [ ] **F5.3** `widgets/connection_status_chip.dart` — green dot + "Connected" | red + "Disconnected"
- [ ] **F5.4** `widgets/joint_gauge.dart`
  - `fl_chart` arc gauge (SemiCircle style), min/max from config joint limits
  - Displays joint number, current degree, motor type (NEMA23/17)
- [ ] **F5.5** `widgets/joint_panel.dart` — Row of 6× `JointGauge` with labels
- [ ] **F5.6** `widgets/joint_slider_card.dart`
  - `Slider` with joint limit min/max
  - Four jog buttons: -10°, -1°, +1°, +10°
  - Numeric text field (on submit → POST /cmd/movej)
  - Greys out when ESTOPPED or disconnected
- [ ] **F5.7** `widgets/detection_overlay.dart` — `CustomPainter` draws bounding boxes + confidence labels over camera image
- [ ] **F5.8** `widgets/camera_feed.dart` — `Image.memory(jpegBytes)` with `DetectionOverlay` stack
- [ ] **F5.9** `widgets/log_list_view.dart` — `ListView.builder` virtualised, auto-scroll on new entries, pause button

---

## Phase F6 — Screens

- [ ] **F6.1** `screens/main_shell.dart`
  - `NavigationRail` (left): Dashboard, Manual, Pipeline, Console, Settings icons
  - `Stack` with `EStopButton` always at `Positioned(bottom:24, right:24)`
  - `ConnectionStatusChip` in rail header
- [ ] **F6.2** `screens/dashboard_screen.dart`
  - Left: `CameraFeed` (constrained 640×480 max)
  - Right top: `JointPanel` (6 gauges)
  - Right bottom: Quick controls (Home All, Enable, Disable, Go Home buttons)
  - Bottom: 5-line log preview → taps navigate to Console
- [ ] **F6.3** `screens/manual_control_screen.dart`
  - Scrollable `Column` of 6× `JointSliderCard`
  - Footer: Home individual joint buttons + Home All
  - "Send to Target" button — sends all 6 sliders as one `MOVEA` command
- [ ] **F6.4** `screens/pipeline_screen.dart`
  - Large START / STOP buttons
  - Stats card: cycles, detections, last detection position
  - Config snapshot: conf_threshold, loop_hz, min_detections (read-only)
- [ ] **F6.5** `screens/console_screen.dart`
  - `LogListView` full-height
  - Level filter dropdown (ALL / INFO / DEBUG / WARN / ERROR)
  - Text search filter
  - Clear and Pause/Resume buttons
- [ ] **F6.6** `screens/settings_screen.dart`
  - `GET /config` → parse into typed form widgets
  - Sections: Serial, Camera, Vision, IK (DH params table), Arm, Pipeline
  - "Apply" button → `PUT /config`
  - Warning banner for fields that require restart

---

## Phase F7 — Bridge Launch + Integration

- [ ] **F7.1** `BridgeProvider.launchBridge()`
  - macOS: `Process.run('python3', ['host/bridge_server.py'])`
  - Windows: `Process.run('python', ['host/bridge_server.py'])` or `.exe`
  - Show launch progress dialog while polling `GET /status`
- [ ] **F7.2** Startup screen / splash
  - Show IRIS logo + "Connecting to bridge..." with spinner
  - "Launch Bridge" button if connection refused after 3s
  - Auto-proceed on successful connection
- [ ] **F7.3** End-to-end smoke test
  - Bridge starts → Flutter connects → joints WebSocket shows positions
  - Send MOVEA from Manual Control → arm moves → gauge updates
  - Camera feed displays with YOLO boxes
  - ESTOP button halts motion from any screen
- [ ] **F7.4** Error states
  - Bridge disconnects mid-session → auto-reconnect with banner
  - Camera unavailable → grey placeholder with "No camera" message
  - Serial disconnected → red banner, disable all motion widgets

---

## Phase F8 — Polish + Distribution

- [ ] **F8.1** Keyboard shortcuts
  - `Escape` → ESTOP
  - `Cmd/Ctrl+H` → Home All
  - `1-5` → navigate screens
- [ ] **F8.2** macOS app bundle: `flutter build macos --release`
- [ ] **F8.3** Windows executable: `flutter build windows --release`
- [ ] **F8.4** PyInstaller freeze of bridge server (optional, for standalone distribution)
  ```bash
  pyinstaller --onedir --name iris_bridge host/bridge_server.py
  ```
- [ ] **F8.5** Update GitHub Pages docs with Flutter UI section
- [ ] **F8.6** Commit + push to GitHub

---

## Open Questions

| # | Question | Blocks |
| --- | --- | --- |
| FQ1 | Should the bridge auto-start when Flutter launches, or require manual "Start Bridge" click? | F7.1 |
| FQ2 | Is a dark theme only, or should light mode be supported? | F2.5 |
| FQ3 | Should joint history (angle over time) charts be on Dashboard or a separate screen? | F6.2 |
| FQ4 | Should Settings allow live DH param editing (risky) or read-only for IK params? | F6.6 |
