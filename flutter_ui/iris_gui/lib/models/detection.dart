import 'dart:ui';

class Detection {
  final double xM, yM, zM;
  final double confidence;
  final List<double> bboxPx;   // [x1, y1, x2, y2] in original image pixels

  const Detection({
    required this.xM,
    required this.yM,
    required this.zM,
    required this.confidence,
    required this.bboxPx,
  });

  factory Detection.fromJson(Map<String, dynamic> j) => Detection(
        xM: (j['x_m'] as num).toDouble(),
        yM: (j['y_m'] as num).toDouble(),
        zM: (j['z_m'] as num).toDouble(),
        confidence: (j['conf'] as num).toDouble(),
        bboxPx: (j['bbox'] as List).map((e) => (e as num).toDouble()).toList(),
      );

  Rect scaledRect(double scaleX, double scaleY) => Rect.fromLTRB(
        bboxPx[0] * scaleX, bboxPx[1] * scaleY,
        bboxPx[2] * scaleX, bboxPx[3] * scaleY,
      );
}
