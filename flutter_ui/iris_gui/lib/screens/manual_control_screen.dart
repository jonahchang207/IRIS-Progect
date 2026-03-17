import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../core/constants.dart';
import '../providers/bridge_provider.dart';
import '../widgets/joint_slider_card.dart';
import '../theme/app_theme.dart';
import '../models/system_status.dart';

class ManualControlScreen extends ConsumerStatefulWidget {
  const ManualControlScreen({super.key});

  @override
  ConsumerState<ManualControlScreen> createState() =>
      _ManualControlScreenState();
}

class _ManualControlScreenState extends ConsumerState<ManualControlScreen> {
  // Target angles (draft state for "Send All" button)
  List<double> _target = List.filled(6, 0.0);

  // Joint limits — PLACEHOLDER until loaded from config
  final List<double> _mins = [-170, -90, -135, -170, -90, -170];
  final List<double> _maxs = [ 170,  90,  135,  170,  90,  170];

  @override
  Widget build(BuildContext context) {
    final jointAsync = ref.watch(jointStreamProvider);
    final client     = ref.watch(bridgeClientProvider);

    final joints = jointAsync.whenData((j) => j.angles).valueOrNull
        ?? List.filled(6, 0.0);
    final status = jointAsync.whenData((j) => j.status).valueOrNull
        ?? SystemStatus.idle;
    final initialized =
        jointAsync.whenData((j) => j.initialized).valueOrNull ?? false;
    final enabled = initialized &&
        status != SystemStatus.estopped &&
        status != SystemStatus.homing;

    return Padding(
      padding: const EdgeInsets.all(16),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // Header
          Row(
            children: [
              const Text('MANUAL CONTROL',
                  style: TextStyle(
                      color: kColorTextPrimary,
                      fontSize: 14,
                      fontWeight: FontWeight.w700,
                      letterSpacing: 1.5)),
              const SizedBox(width: 12),
              if (!initialized)
                const Text('Run Arm Sequence first',
                    style:
                        TextStyle(color: kColorYellow, fontSize: 12)),
            ],
          ),
          const SizedBox(height: 4),
          const Divider(),
          // Joint cards
          Expanded(
            child: ListView.builder(
              itemCount: 6,
              itemBuilder: (_, i) => JointSliderCard(
                index: i,
                currentDeg: joints[i],
                minDeg: _mins[i],
                maxDeg: _maxs[i],
                enabled: enabled,
                onMove: (deg) {
                  setState(() => _target[i] = deg);
                  client.jog(i, deg - joints[i]);
                },
                onHome: () => client.home(joint: i + 1),
              ),
            ),
          ),
          // Footer actions
          const Divider(),
          Padding(
            padding: const EdgeInsets.symmetric(vertical: 8),
            child: Row(
              children: [
                ElevatedButton.icon(
                  onPressed: enabled ? () => client.home() : null,
                  icon: const Icon(Icons.home, size: 16),
                  label: const Text('Home All'),
                ),
                const SizedBox(width: 12),
                ElevatedButton.icon(
                  onPressed: enabled
                      ? () => client.moveJ(List.from(joints.map((_) => 0.0)))
                      : null,
                  icon: const Icon(Icons.adjust, size: 16),
                  label: const Text('Go to Zero'),
                ),
                const SizedBox(width: 12),
                OutlinedButton.icon(
                  onPressed: enabled
                      ? () => client.disable()
                      : null,
                  icon: const Icon(Icons.power_off, size: 16),
                  label: const Text('Disable Drivers'),
                  style: OutlinedButton.styleFrom(
                    foregroundColor: kColorYellow,
                    side:
                        const BorderSide(color: kColorYellow, width: 1),
                  ),
                ),
                const SizedBox(width: 12),
                OutlinedButton.icon(
                  onPressed: !enabled && initialized
                      ? () => client.enable()
                      : null,
                  icon: const Icon(Icons.power, size: 16),
                  label: const Text('Enable Drivers'),
                  style: OutlinedButton.styleFrom(
                    foregroundColor: kColorGreen,
                    side:
                        const BorderSide(color: kColorGreen, width: 1),
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
