import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../providers/bridge_provider.dart';
import '../theme/app_theme.dart';
import '../models/system_status.dart';

class PipelineScreen extends ConsumerWidget {
  const PipelineScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final client     = ref.watch(bridgeClientProvider);
    final pipeline   = ref.watch(pipelineProvider);
    final jointAsync = ref.watch(jointStreamProvider);
    final initialized =
        jointAsync.whenData((j) => j.initialized).valueOrNull ?? false;
    final status = jointAsync.whenData((j) => j.status).valueOrNull
        ?? SystemStatus.idle;

    return Padding(
      padding: const EdgeInsets.all(24),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Text('AUTO PIPELINE',
              style: TextStyle(
                  color: kColorTextPrimary,
                  fontSize: 14,
                  fontWeight: FontWeight.w700,
                  letterSpacing: 1.5)),
          const SizedBox(height: 4),
          const Divider(),
          const SizedBox(height: 24),
          // Big start/stop buttons
          Row(
            children: [
              _PipelineBtn(
                label: 'START PIPELINE',
                icon: Icons.play_arrow,
                color: kColorGreen,
                enabled: initialized && !pipeline.running &&
                    status != SystemStatus.estopped,
                onTap: () {
                  ref.read(pipelineProvider.notifier).setRunning(true);
                  client.pipelineStart();
                },
              ),
              const SizedBox(width: 16),
              _PipelineBtn(
                label: 'STOP PIPELINE',
                icon: Icons.stop,
                color: kColorAccent,
                enabled: pipeline.running,
                onTap: () {
                  ref.read(pipelineProvider.notifier).setRunning(false);
                  client.pipelineStop();
                },
              ),
            ],
          ),
          const SizedBox(height: 32),
          // Stats
          Wrap(
            spacing: 16,
            runSpacing: 12,
            children: [
              _StatCard(
                  label: 'Status',
                  value: pipeline.running ? 'RUNNING' : 'IDLE',
                  color: pipeline.running ? kColorGreen : kColorTextSecond),
              _StatCard(
                  label: 'Cycles Complete',
                  value: '${pipeline.cycles}',
                  color: kColorBlue),
              _StatCard(
                  label: 'Detections This Run',
                  value: '${pipeline.detections}',
                  color: kColorYellow),
            ],
          ),
          if (!initialized) ...[
            const SizedBox(height: 24),
            Container(
              padding: const EdgeInsets.all(12),
              decoration: BoxDecoration(
                color: kColorYellow.withOpacity(0.08),
                borderRadius: BorderRadius.circular(8),
                border: Border.all(color: kColorYellow.withOpacity(0.4)),
              ),
              child: const Row(
                children: [
                  Icon(Icons.warning_amber, color: kColorYellow, size: 18),
                  SizedBox(width: 8),
                  Text(
                    'Complete the Arm Sequence on the Dashboard before running the pipeline.',
                    style: TextStyle(color: kColorYellow, fontSize: 12),
                  ),
                ],
              ),
            ),
          ],
        ],
      ),
    );
  }
}

class _PipelineBtn extends StatelessWidget {
  final String label;
  final IconData icon;
  final Color color;
  final bool enabled;
  final VoidCallback onTap;

  const _PipelineBtn({
    required this.label,
    required this.icon,
    required this.color,
    required this.enabled,
    required this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    return SizedBox(
      width: 200,
      height: 64,
      child: ElevatedButton.icon(
        onPressed: enabled ? onTap : null,
        icon: Icon(icon, size: 22),
        label: Text(label,
            style: const TextStyle(
                fontWeight: FontWeight.w700, letterSpacing: 1)),
        style: ElevatedButton.styleFrom(
          backgroundColor:
              enabled ? color.withOpacity(0.15) : kColorSurface,
          foregroundColor: enabled ? color : kColorTextSecond,
          side: BorderSide(
              color: enabled ? color : kColorBorder, width: 1.5),
        ),
      ),
    );
  }
}

class _StatCard extends StatelessWidget {
  final String label;
  final String value;
  final Color color;

  const _StatCard(
      {required this.label, required this.value, required this.color});

  @override
  Widget build(BuildContext context) {
    return Container(
      width: 160,
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
      decoration: BoxDecoration(
        color: kColorSurface,
        borderRadius: BorderRadius.circular(10),
        border: Border.all(color: kColorBorder),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(label,
              style: const TextStyle(
                  color: kColorTextSecond, fontSize: 10)),
          const SizedBox(height: 4),
          Text(value,
              style: TextStyle(
                  color: color,
                  fontSize: 22,
                  fontWeight: FontWeight.w700)),
        ],
      ),
    );
  }
}
