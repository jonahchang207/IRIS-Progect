import 'package:flutter/material.dart';

import '../models/camera_frame.dart';
import '../theme/app_theme.dart';

class CameraFeed extends StatelessWidget {
  final CameraFrame? frame;
  final bool showDetections;

  const CameraFeed({super.key, this.frame, this.showDetections = true});

  @override
  Widget build(BuildContext context) {
    if (frame == null || frame!.jpegBytes.isEmpty) {
      return _placeholder();
    }

    return Stack(
      fit: StackFit.expand,
      children: [
        ClipRRect(
          borderRadius: BorderRadius.circular(8),
          child: Image.memory(
            frame!.jpegBytes,
            fit: BoxFit.contain,
            gaplessPlayback: true,
          ),
        ),
        if (showDetections && frame!.detections.isNotEmpty)
          _DetectionOverlay(frame: frame!),
        // Detection count badge
        Positioned(
          top: 8,
          right: 8,
          child: Container(
            padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
            decoration: BoxDecoration(
              color: Colors.black.withOpacity(0.65),
              borderRadius: BorderRadius.circular(12),
              border: Border.all(color: kColorAccent.withOpacity(0.6)),
            ),
            child: Text(
              '${frame!.detections.length} screw${frame!.detections.length == 1 ? '' : 's'}',
              style: const TextStyle(
                  color: kColorTextPrimary,
                  fontSize: 11,
                  fontWeight: FontWeight.w600),
            ),
          ),
        ),
      ],
    );
  }

  Widget _placeholder() {
    return Container(
      decoration: BoxDecoration(
        color: kColorSurface,
        borderRadius: BorderRadius.circular(8),
        border: Border.all(color: kColorBorder),
      ),
      child: const Center(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(Icons.videocam_off, size: 40, color: kColorBorder),
            SizedBox(height: 8),
            Text('No camera signal',
                style: TextStyle(color: kColorTextSecond, fontSize: 13)),
          ],
        ),
      ),
    );
  }
}

class _DetectionOverlay extends StatelessWidget {
  final CameraFrame frame;
  const _DetectionOverlay({required this.frame});

  @override
  Widget build(BuildContext context) {
    return LayoutBuilder(builder: (_, constraints) {
      return CustomPaint(
        size: Size(constraints.maxWidth, constraints.maxHeight),
        painter: _BoxPainter(frame: frame),
      );
    });
  }
}

class _BoxPainter extends CustomPainter {
  final CameraFrame frame;
  _BoxPainter({required this.frame});

  static const _imgW = 1280.0;
  static const _imgH = 720.0;

  @override
  void paint(Canvas canvas, Size size) {
    final sx = size.width / _imgW;
    final sy = size.height / _imgH;

    for (final d in frame.detections) {
      final rect = d.scaledRect(sx, sy);
      // Box
      canvas.drawRect(
          rect,
          Paint()
            ..color = kColorGreen
            ..style = PaintingStyle.stroke
            ..strokeWidth = 1.8);
      // Label background
      final label = 'screw ${(d.confidence * 100).toStringAsFixed(0)}%';
      final tp = TextPainter(
        text: TextSpan(
            text: label,
            style: const TextStyle(
                color: Colors.white,
                fontSize: 10,
                fontWeight: FontWeight.w600)),
        textDirection: TextDirection.ltr,
      )..layout();
      final bgRect =
          Rect.fromLTWH(rect.left, rect.top - 18, tp.width + 6, 16);
      canvas.drawRect(
          bgRect,
          Paint()
            ..color = kColorGreen.withOpacity(0.8)
            ..style = PaintingStyle.fill);
      tp.paint(canvas, Offset(rect.left + 3, rect.top - 17));
    }
  }

  @override
  bool shouldRepaint(_BoxPainter old) =>
      old.frame.timestamp != frame.timestamp;
}
