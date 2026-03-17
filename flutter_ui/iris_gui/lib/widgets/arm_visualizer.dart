import 'dart:math' as math;
import 'package:flutter/material.dart';
import '../theme/app_theme.dart';

/// 2D side-view visualisation of the IRIS 6DOF arm.
/// Draws joint circles and links using current joint angles + DH link lengths.
/// Link lengths are PLACEHOLDER values until real DH params are configured.
class ArmVisualizer extends StatelessWidget {
  final List<double> jointAnglesDeg;   // 6 elements

  /// DH link lengths [d1, a2, a3, d6] in metres — read from config.
  /// Defaults are placeholder values.
  final double d1;   // base height (J1 offset)
  final double a2;   // upper arm
  final double a3;   // forearm
  final double d6;   // tool offset

  const ArmVisualizer({
    super.key,
    required this.jointAnglesDeg,
    this.d1 = 0.10,   // PLACEHOLDER
    this.a2 = 0.25,   // PLACEHOLDER
    this.a3 = 0.22,   // PLACEHOLDER
    this.d6 = 0.08,   // PLACEHOLDER
  });

  @override
  Widget build(BuildContext context) {
    return LayoutBuilder(builder: (_, constraints) {
      return CustomPaint(
        size: Size(constraints.maxWidth, constraints.maxHeight),
        painter: _ArmPainter(
          angles: jointAnglesDeg,
          d1: d1, a2: a2, a3: a3, d6: d6,
        ),
      );
    });
  }
}

class _ArmPainter extends CustomPainter {
  final List<double> angles;
  final double d1, a2, a3, d6;

  _ArmPainter({required this.angles, required this.d1, required this.a2,
      required this.a3, required this.d6});

  @override
  void paint(Canvas canvas, Size size) {
    final cx = size.width * 0.5;
    final cy = size.height * 0.85;

    // Scale factor: fit arm in canvas
    final totalReach = d1 + a2 + a3 + d6;
    final scale = (size.height * 0.8) / totalReach;

    // Joint angles in radians
    final q2 = _deg2rad(angles.length > 1 ? angles[1] : 0.0);
    final q3 = _deg2rad(angles.length > 2 ? angles[2] : 0.0);
    final q5 = _deg2rad(angles.length > 4 ? angles[4] : 0.0);

    // Draw grid lines
    final gridPaint = Paint()
      ..color = kColorBorder
      ..strokeWidth = 1;
    for (int i = 0; i < 5; i++) {
      final y = cy - i * size.height * 0.2;
      canvas.drawLine(Offset(0, y), Offset(size.width, y), gridPaint);
    }
    // Centre vertical
    canvas.drawLine(Offset(cx, 0), Offset(cx, size.height), gridPaint);

    // Base point
    final base = Offset(cx, cy);

    // Shoulder (after d1 vertical offset)
    final shoulder = Offset(cx, cy - d1 * scale);

    // Elbow (after a2 at angle q2 from vertical)
    final elbowAngle = math.pi / 2 - q2;  // from horizontal
    final elbow = Offset(
      shoulder.dx + a2 * scale * math.cos(elbowAngle),
      shoulder.dy - a2 * scale * math.sin(elbowAngle),
    );

    // Wrist (after a3 at angle q2+q3 from vertical)
    final wristAngle = math.pi / 2 - (q2 + q3);
    final wrist = Offset(
      elbow.dx + a3 * scale * math.cos(wristAngle),
      elbow.dy - a3 * scale * math.sin(wristAngle),
    );

    // EE (after d6 at wrist pitch q5)
    final eeAngle = wristAngle - q5;
    final ee = Offset(
      wrist.dx + d6 * scale * math.cos(eeAngle),
      wrist.dy - d6 * scale * math.sin(eeAngle),
    );

    // Link paint
    final linkPaint = Paint()
      ..strokeWidth = 5
      ..strokeCap = StrokeCap.round
      ..style = PaintingStyle.stroke;

    // Base pedestal
    _drawLink(canvas, base, shoulder, kColorBorder, 8, linkPaint);

    // Upper arm (J2)
    _drawLink(canvas, shoulder, elbow, kJointColors[1], 5, linkPaint);

    // Forearm (J3)
    _drawLink(canvas, elbow, wrist, kJointColors[2], 4, linkPaint);

    // Tool (J5)
    _drawLink(canvas, wrist, ee, kJointColors[4], 3, linkPaint);

    // Joint circles
    _drawJoint(canvas, base,     kColorTextSecond, 10, 'BASE');
    _drawJoint(canvas, shoulder, kJointColors[0],  8,  'J1/J2');
    _drawJoint(canvas, elbow,    kJointColors[2],  7,  'J3');
    _drawJoint(canvas, wrist,    kJointColors[3],  6,  'J4/J5');
    _drawJoint(canvas, ee,       kJointColors[5],  5,  'EE');

    // J1 top-down inset (base rotation)
    _drawJ1Inset(canvas, size, angles.isNotEmpty ? angles[0] : 0.0);

    // Angle labels
    final tp = TextPainter(textDirection: TextDirection.ltr);
    _drawAngleLabel(canvas, tp, shoulder, angles.length > 1 ? angles[1] : 0, kJointColors[1]);
    _drawAngleLabel(canvas, tp, elbow,    angles.length > 2 ? angles[2] : 0, kJointColors[2]);
  }

  void _drawLink(Canvas c, Offset a, Offset b, Color col, double w, Paint p) {
    p.color = col;
    p.strokeWidth = w;
    c.drawLine(a, b, p);
  }

  void _drawJoint(Canvas c, Offset pos, Color col, double r, String label) {
    c.drawCircle(pos, r, Paint()..color = kColorBackground);
    c.drawCircle(pos, r, Paint()
      ..color = col
      ..style = PaintingStyle.stroke
      ..strokeWidth = 2.5);

    final tp = TextPainter(
      text: TextSpan(
          text: label,
          style: TextStyle(
              color: col.withOpacity(0.8),
              fontSize: 9,
              fontWeight: FontWeight.w600)),
      textDirection: TextDirection.ltr,
    )..layout();
    tp.paint(c, Offset(pos.dx + r + 3, pos.dy - tp.height / 2));
  }

  void _drawAngleLabel(
      Canvas c, TextPainter tp, Offset pos, double deg, Color col) {
    tp.text = TextSpan(
        text: '${deg.toStringAsFixed(1)}°',
        style: TextStyle(color: col, fontSize: 10));
    tp.textDirection = TextDirection.ltr;
    tp.layout();
    tp.paint(c, Offset(pos.dx - 20, pos.dy + 10));
  }

  void _drawJ1Inset(Canvas canvas, Size size, double j1Deg) {
    const r = 28.0;
    final centre = Offset(size.width - r - 12, r + 12);

    // Circle
    canvas.drawCircle(
        centre, r, Paint()..color = kColorSurface);
    canvas.drawCircle(
        centre, r,
        Paint()
          ..color = kColorBorder
          ..style = PaintingStyle.stroke
          ..strokeWidth = 1);

    // Arrow showing J1 rotation
    final angle = _deg2rad(j1Deg) - math.pi / 2;
    final arrowEnd = Offset(
        centre.dx + (r - 6) * math.cos(angle),
        centre.dy + (r - 6) * math.sin(angle));
    canvas.drawLine(centre, arrowEnd,
        Paint()
          ..color = kJointColors[0]
          ..strokeWidth = 2
          ..strokeCap = StrokeCap.round);

    // Label
    final tp = TextPainter(
      text: TextSpan(
          text: 'J1\n${j1Deg.toStringAsFixed(0)}°',
          style: const TextStyle(
              color: kColorTextSecond, fontSize: 8, height: 1.2)),
      textDirection: TextDirection.ltr,
      textAlign: TextAlign.center,
    )..layout();
    tp.paint(
        canvas, Offset(centre.dx - tp.width / 2, centre.dy - tp.height / 2));
  }

  double _deg2rad(double d) => d * math.pi / 180.0;

  @override
  bool shouldRepaint(_ArmPainter old) =>
      old.angles.toString() != angles.toString();
}
