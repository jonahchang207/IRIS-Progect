import 'dart:async';
import 'dart:io';

import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../core/constants.dart';
import '../models/camera_frame.dart';
import '../models/joint_state.dart';
import '../models/log_entry.dart';
import '../services/bridge_client.dart';

// ── Singleton client ──────────────────────────────────────────────────────────
final bridgeClientProvider = Provider<BridgeClient>((ref) => BridgeClient());

// ── Connection state ──────────────────────────────────────────────────────────
enum BridgeState { disconnected, connecting, connected, error }

class BridgeNotifier extends StateNotifier<BridgeState> {
  BridgeNotifier(this._client) : super(BridgeState.disconnected);

  final BridgeClient _client;
  Process? _bridgeProcess;
  Timer? _reconnectTimer;

  Future<void> connect() async {
    state = BridgeState.connecting;
    // Poll for bridge with exponential backoff
    Duration delay = kBridgeReconnectBase;
    final deadline = DateTime.now().add(kBridgeConnectTimeout);
    while (DateTime.now().isBefore(deadline)) {
      if (await _client.ping()) {
        state = BridgeState.connected;
        return;
      }
      await Future.delayed(delay);
      delay = Duration(
          milliseconds:
              (delay.inMilliseconds * 1.5).round().clamp(0, kBridgeReconnectMax.inMilliseconds));
    }
    state = BridgeState.error;
  }

  Future<void> launchAndConnect() async {
    state = BridgeState.connecting;
    try {
      final pythonCmd = Platform.isWindows ? 'python' : 'python3';
      _bridgeProcess = await Process.start(
        pythonCmd,
        ['host/bridge_server.py'],
        workingDirectory: '../../',   // relative to iris_gui/
      );
    } catch (_) {
      // Process launch failed — bridge might already be running
    }
    await Future.delayed(const Duration(seconds: 2));
    await connect();
  }

  void scheduleReconnect() {
    _reconnectTimer?.cancel();
    _reconnectTimer = Timer(kBridgeReconnectBase, connect);
  }

  @override
  void dispose() {
    _reconnectTimer?.cancel();
    super.dispose();
  }
}

final bridgeProvider =
    StateNotifierProvider<BridgeNotifier, BridgeState>((ref) {
  return BridgeNotifier(ref.watch(bridgeClientProvider));
});

// ── Data streams ──────────────────────────────────────────────────────────────
final jointStreamProvider = StreamProvider<JointState>((ref) {
  final client = ref.watch(bridgeClientProvider);
  return client.jointStream().handleError((_) {
    ref.read(bridgeProvider.notifier).scheduleReconnect();
  });
});

final cameraStreamProvider = StreamProvider<CameraFrame>((ref) {
  final client = ref.watch(bridgeClientProvider);
  return client.cameraStream().handleError((_) {});
});

final logStreamProvider = StreamProvider<LogEntry>((ref) {
  final client = ref.watch(bridgeClientProvider);
  return client.logStream().handleError((_) {});
});

// ── Log buffer ────────────────────────────────────────────────────────────────
class LogNotifier extends StateNotifier<List<LogEntry>> {
  LogNotifier() : super([]);

  void add(LogEntry e) {
    final next = [...state, e];
    if (next.length > kLogBufferSize) {
      state = next.sublist(next.length - kLogBufferSize);
    } else {
      state = next;
    }
  }

  void clear() => state = [];
}

final logBufferProvider =
    StateNotifierProvider<LogNotifier, List<LogEntry>>((ref) {
  final notifier = LogNotifier();
  ref.listen(logStreamProvider, (_, next) {
    next.whenData(notifier.add);
  });
  return notifier;
});

// ── Pipeline state ────────────────────────────────────────────────────────────
class PipelineState {
  final bool running;
  final int cycles;
  final int detections;

  const PipelineState(
      {this.running = false, this.cycles = 0, this.detections = 0});

  PipelineState copyWith({bool? running, int? cycles, int? detections}) =>
      PipelineState(
        running: running ?? this.running,
        cycles: cycles ?? this.cycles,
        detections: detections ?? this.detections,
      );
}

class PipelineNotifier extends StateNotifier<PipelineState> {
  PipelineNotifier() : super(const PipelineState());

  void setRunning(bool v) => state = state.copyWith(running: v);
  void incrementCycle() => state = state.copyWith(cycles: state.cycles + 1);
  void incrementDetection() =>
      state = state.copyWith(detections: state.detections + 1);
  void reset() => state = const PipelineState();
}

final pipelineProvider =
    StateNotifierProvider<PipelineNotifier, PipelineState>(
        (_) => PipelineNotifier());
