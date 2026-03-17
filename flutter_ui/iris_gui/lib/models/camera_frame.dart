import 'dart:typed_data';
import 'detection.dart';

class CameraFrame {
  final Uint8List jpegBytes;
  final List<Detection> detections;
  final DateTime timestamp;

  const CameraFrame({
    required this.jpegBytes,
    required this.detections,
    required this.timestamp,
  });
}
