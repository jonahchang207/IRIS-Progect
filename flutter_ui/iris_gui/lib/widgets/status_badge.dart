import 'package:flutter/material.dart';
import '../models/system_status.dart';
import '../theme/app_theme.dart';

class StatusBadge extends StatelessWidget {
  final SystemStatus status;
  const StatusBadge({super.key, required this.status});

  @override
  Widget build(BuildContext context) {
    final (color, icon) = switch (status) {
      SystemStatus.idle     => (kColorGreen,  Icons.check_circle_outline),
      SystemStatus.moving   => (kColorBlue,   Icons.sync),
      SystemStatus.homing   => (kColorYellow, Icons.home_outlined),
      SystemStatus.estopped => (kColorAccent, Icons.stop_circle_outlined),
    };
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
      decoration: BoxDecoration(
        color: color.withOpacity(0.12),
        borderRadius: BorderRadius.circular(20),
        border: Border.all(color: color.withOpacity(0.5)),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(icon, size: 13, color: color),
          const SizedBox(width: 5),
          Text(status.label,
              style: TextStyle(
                  color: color,
                  fontSize: 11,
                  fontWeight: FontWeight.w700,
                  letterSpacing: 0.8)),
        ],
      ),
    );
  }
}
