import 'dart:convert';
import 'dart:typed_data';

import 'package:dio/dio.dart';
import 'package:web_socket_channel/web_socket_channel.dart';

import '../core/constants.dart';
import '../models/camera_frame.dart';
import '../models/detection.dart';
import '../models/joint_state.dart';
import '../models/log_entry.dart';

class BridgeClient {
  final Dio _dio = Dio(BaseOptions(
    baseUrl: kBridgeBase,
    connectTimeout: const Duration(seconds: 3),
    receiveTimeout: const Duration(seconds: 5),
  ));

  // ── connectivity ─────────────────────────────────────────────────────────

  Future<bool> ping() async {
    try {
      final r = await _dio.get('/status');
      return r.statusCode == 200;
    } catch (_) {
      return false;
    }
  }

  // ── WebSocket streams ─────────────────────────────────────────────────────

  Stream<JointState> jointStream() {
    final ch = WebSocketChannel.connect(Uri.parse(kWsJoints));
    return ch.stream.map((raw) {
      final j = jsonDecode(raw as String) as Map<String, dynamic>;
      return JointState.fromJson(j);
    });
  }

  Stream<CameraFrame> cameraStream() {
    final ch = WebSocketChannel.connect(Uri.parse(kWsCamera));
    return ch.stream.map((raw) {
      final j = jsonDecode(raw as String) as Map<String, dynamic>;
      final b64 = j['frame_b64'] as String? ?? '';
      final bytes = b64.isEmpty
          ? Uint8List(0)
          : base64Decode(b64);
      final dets = (j['detections'] as List? ?? [])
          .map((e) => Detection.fromJson(e as Map<String, dynamic>))
          .toList();
      return CameraFrame(
          jpegBytes: bytes, detections: dets, timestamp: DateTime.now());
    });
  }

  Stream<LogEntry> logStream() {
    final ch = WebSocketChannel.connect(Uri.parse(kWsLog));
    return ch.stream.map((raw) {
      final j = jsonDecode(raw as String) as Map<String, dynamic>;
      return LogEntry.fromJson(j);
    });
  }

  // ── commands ──────────────────────────────────────────────────────────────

  Future<void> estop() async {
    try { await _dio.post('/cmd/estop'); } catch (_) {}
  }

  Future<bool> enable() => _post('/cmd/enable');
  Future<bool> disable() => _post('/cmd/disable');

  Future<bool> home({int? joint}) =>
      _post('/cmd/home', data: {'joint': joint});

  Future<bool> moveJ(List<double> angles) =>
      _post('/cmd/movej', data: {'angles': angles});

  Future<bool> jog(int joint, double deltaDeg) =>
      _post('/cmd/jog', data: {'joint': joint, 'delta_deg': deltaDeg});

  Future<bool> pipelineStart() => _post('/cmd/pipeline/start');
  Future<bool> pipelineStop()  => _post('/cmd/pipeline/stop');

  Future<bool> runArmSequence() => _post('/cmd/arm_sequence');

  Future<Map<String, dynamic>?> getStatus() async {
    try {
      final r = await _dio.get('/status');
      return r.data as Map<String, dynamic>;
    } catch (_) { return null; }
  }

  Future<Map<String, dynamic>?> getConfig() async {
    try {
      final r = await _dio.get('/config');
      return r.data as Map<String, dynamic>;
    } catch (_) { return null; }
  }

  Future<List<List<double>>?> getFkTransforms() async {
    try {
      final r = await _dio.get('/fk');
      final raw = (r.data['transforms'] as List);
      return raw
          .map((t) => (t as List).map((e) => (e as num).toDouble()).toList())
          .toList();
    } catch (_) { return null; }
  }

  // ── helpers ───────────────────────────────────────────────────────────────

  Future<bool> _post(String path, {Map<String, dynamic>? data}) async {
    try {
      final r = await _dio.post(path, data: data);
      return r.statusCode != null && r.statusCode! < 300;
    } catch (_) { return false; }
  }
}
