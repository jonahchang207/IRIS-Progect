import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../providers/bridge_provider.dart';
import '../widgets/arm_visualizer.dart';
import '../widgets/camera_feed.dart';
import '../widgets/status_badge.dart';
import '../theme/app_theme.dart';
import '../models/system_status.dart';

/// Dashboard — the only screen visible during operation.
/// Shows: live arm visualisation | camera feed + YOLO | stats | arm sequence.
class DashboardScreen extends ConsumerWidget {
  const DashboardScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final jointAsync  = ref.watch(jointStreamProvider);
    final cameraAsync = ref.watch(cameraStreamProvider);
    final client      = ref.watch(bridgeClientProvider);

    final joints = jointAsync.whenData((j) => j.angles).valueOrNull
        ?? List.filled(6, 0.0);
    final status = jointAsync.whenData((j) => j.status).valueOrNull
        ?? SystemStatus.idle;
    final initialized =
        jointAsync.whenData((j) => j.initialized).valueOrNull ?? false;
    final frame = cameraAsync.valueOrNull;

    return Padding(
      padding: const EdgeInsets.all(16),
      child: Column(
        children: [
          // ── Top bar ────────────────────────────────────────────────────────
          Row(
            children: [
              const Text('IRIS CONTROL',
                  style: TextStyle(
                      color: kColorTextPrimary,
                      fontSize: 16,
                      fontWeight: FontWeight.w700,
                      letterSpacing: 2)),
              const SizedBox(width: 16),
              StatusBadge(status: status),
              const Spacer(),
              if (!initialized)
                _ArmSequenceButton(client: client, ref: ref)
              else
                const _InitializedBadge(),
            ],
          ),
          const SizedBox(height: 16),
          // ── Main content: arm visualiser + camera feed ─────────────────────
          Expanded(
            child: Row(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                // Left: arm visualiser
                Expanded(
                  flex: 5,
                  child: Card(
                    child: Column(
                      children: [
                        _SectionHeader(
                            icon: Icons.precision_manufacturing,
                            title: 'Live Arm',
                            trailing: _JointAngleRow(joints: joints)),
                        Expanded(
                          child: ArmVisualizer(jointAnglesDeg: joints),
                        ),
                      ],
                    ),
                  ),
                ),
                const SizedBox(width: 12),
                // Right: camera feed + stats
                Expanded(
                  flex: 7,
                  child: Card(
                    child: Column(
                      children: [
                        _SectionHeader(
                            icon: Icons.camera,
                            title: 'Camera Feed',
                            trailing: _DetectionStats(frame: frame)),
                        Expanded(
                          child: Padding(
                            padding: const EdgeInsets.all(8),
                            child: CameraFeed(frame: frame),
                          ),
                        ),
                      ],
                    ),
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

// ── Sub-widgets ───────────────────────────────────────────────────────────────

class _SectionHeader extends StatelessWidget {
  final IconData icon;
  final String title;
  final Widget? trailing;

  const _SectionHeader(
      {required this.icon, required this.title, this.trailing});

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
      decoration: const BoxDecoration(
        border: Border(bottom: BorderSide(color: kColorBorder)),
      ),
      child: Row(
        children: [
          Icon(icon, size: 15, color: kColorTextSecond),
          const SizedBox(width: 6),
          Text(title,
              style: const TextStyle(
                  color: kColorTextSecond,
                  fontSize: 12,
                  fontWeight: FontWeight.w600,
                  letterSpacing: 0.5)),
          const Spacer(),
          if (trailing != null) trailing!,
        ],
      ),
    );
  }
}

class _JointAngleRow extends StatelessWidget {
  final List<double> joints;
  const _JointAngleRow({required this.joints});

  @override
  Widget build(BuildContext context) {
    return Row(
      children: List.generate(6, (i) {
        final col = kJointColors[i];
        return Padding(
          padding: const EdgeInsets.symmetric(horizontal: 4),
          child: Column(
            children: [
              Text('J${i + 1}',
                  style: TextStyle(
                      color: col, fontSize: 9, fontWeight: FontWeight.w700)),
              Text('${joints[i].toStringAsFixed(1)}°',
                  style:
                      const TextStyle(color: kColorTextPrimary, fontSize: 9)),
            ],
          ),
        );
      }),
    );
  }
}

class _DetectionStats extends StatelessWidget {
  final dynamic frame;   // CameraFrame?
  const _DetectionStats({this.frame});

  @override
  Widget build(BuildContext context) {
    final count = frame?.detections.length ?? 0;
    if (count == 0) {
      return const Text('No detections',
          style: TextStyle(color: kColorTextSecond, fontSize: 11));
    }
    final best = (frame!.detections as List)
        .reduce((a, b) => a.confidence > b.confidence ? a : b);
    return Text(
      '$count detected · best ${(best.confidence * 100).toStringAsFixed(0)}%',
      style: const TextStyle(color: kColorGreen, fontSize: 11),
    );
  }
}

class _ArmSequenceButton extends StatefulWidget {
  final dynamic client;
  final WidgetRef ref;
  const _ArmSequenceButton({required this.client, required this.ref});

  @override
  State<_ArmSequenceButton> createState() => _ArmSequenceButtonState();
}

class _ArmSequenceButtonState extends State<_ArmSequenceButton> {
  bool _running = false;

  Future<void> _run() async {
    setState(() => _running = true);
    final ok = await widget.client.runArmSequence();
    setState(() => _running = false);
    if (mounted) {
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(
        content: Text(ok
            ? 'Arm sequence complete — config locked'
            : 'Arm sequence failed — check console'),
        backgroundColor: ok ? kColorGreen : kColorAccent,
      ));
    }
  }

  @override
  Widget build(BuildContext context) {
    return ElevatedButton.icon(
      onPressed: _running ? null : _run,
      icon: _running
          ? const SizedBox(
              width: 14,
              height: 14,
              child: CircularProgressIndicator(
                  strokeWidth: 2, color: kColorTextPrimary))
          : const Icon(Icons.rocket_launch, size: 16),
      label:
          Text(_running ? 'Running sequence…' : 'Run Arm Sequence'),
      style: ElevatedButton.styleFrom(
        backgroundColor: kColorAccent.withOpacity(0.15),
        foregroundColor: kColorAccent,
        side: const BorderSide(color: kColorAccent),
      ),
    );
  }
}

class _InitializedBadge extends StatelessWidget {
  const _InitializedBadge();

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 5),
      decoration: BoxDecoration(
        color: kColorGreen.withOpacity(0.1),
        borderRadius: BorderRadius.circular(20),
        border: Border.all(color: kColorGreen.withOpacity(0.4)),
      ),
      child: const Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(Icons.lock, size: 12, color: kColorGreen),
          SizedBox(width: 5),
          Text('INITIALISED',
              style: TextStyle(
                  color: kColorGreen,
                  fontSize: 11,
                  fontWeight: FontWeight.w700,
                  letterSpacing: 0.8)),
        ],
      ),
    );
  }
}
