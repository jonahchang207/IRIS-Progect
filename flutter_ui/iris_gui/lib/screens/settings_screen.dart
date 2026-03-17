import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../providers/bridge_provider.dart';
import '../theme/app_theme.dart';

/// Settings screen — read-only after arm sequence is complete.
/// Shows config.yaml values. Only editable before initialisation.
class SettingsScreen extends ConsumerStatefulWidget {
  const SettingsScreen({super.key});

  @override
  ConsumerState<SettingsScreen> createState() => _SettingsScreenState();
}

class _SettingsScreenState extends ConsumerState<SettingsScreen> {
  Map<String, dynamic>? _config;
  bool _locked = false;
  bool _loading = true;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    final client = ref.read(bridgeClientProvider);
    final data = await client.getConfig();
    if (mounted && data != null) {
      setState(() {
        _config = data['config'] as Map<String, dynamic>?;
        _locked = data['locked'] as bool? ?? false;
        _loading = false;
      });
    } else if (mounted) {
      setState(() => _loading = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    if (_loading) {
      return const Center(
          child: CircularProgressIndicator(color: kColorAccent));
    }
    if (_config == null) {
      return const Center(
          child: Text('Could not load config',
              style: TextStyle(color: kColorTextSecond)));
    }

    return Column(
      children: [
        // Header
        Container(
          padding:
              const EdgeInsets.symmetric(horizontal: 16, vertical: 10),
          decoration: const BoxDecoration(
            color: kColorSurface,
            border:
                Border(bottom: BorderSide(color: kColorBorder)),
          ),
          child: Row(
            children: [
              const Text('SETTINGS',
                  style: TextStyle(
                      color: kColorTextPrimary,
                      fontSize: 14,
                      fontWeight: FontWeight.w700,
                      letterSpacing: 1.5)),
              const SizedBox(width: 12),
              if (_locked) ...[
                const Icon(Icons.lock, size: 14, color: kColorYellow),
                const SizedBox(width: 5),
                const Text('Config locked after arm sequence',
                    style: TextStyle(
                        color: kColorYellow, fontSize: 11)),
              ],
              const Spacer(),
              if (!_locked)
                TextButton.icon(
                  icon: const Icon(Icons.refresh, size: 14),
                  label: const Text('Reload'),
                  onPressed: () {
                    setState(() => _loading = true);
                    _load();
                  },
                ),
            ],
          ),
        ),
        if (_locked)
          Container(
            width: double.infinity,
            color: kColorYellow.withOpacity(0.05),
            padding: const EdgeInsets.all(10),
            child: const Text(
              '⚠  Parameters are locked. ESTOP the arm and reset the arm sequence to make changes.',
              style: TextStyle(color: kColorYellow, fontSize: 11),
              textAlign: TextAlign.center,
            ),
          ),
        // Config tree
        Expanded(
          child: ListView(
            padding: const EdgeInsets.all(16),
            children: _buildConfigTree(_config!, 0),
          ),
        ),
      ],
    );
  }

  List<Widget> _buildConfigTree(Map<String, dynamic> map, int depth) {
    final widgets = <Widget>[];
    for (final entry in map.entries) {
      if (entry.value is Map) {
        // Section header
        widgets.add(Padding(
          padding: EdgeInsets.only(
              left: depth * 16.0, top: depth == 0 ? 12 : 4, bottom: 4),
          child: Text(entry.key.toUpperCase(),
              style: TextStyle(
                  color: depth == 0
                      ? kColorTextPrimary
                      : kColorTextSecond,
                  fontSize: depth == 0 ? 12 : 11,
                  fontWeight: FontWeight.w700,
                  letterSpacing: 0.8)),
        ));
        if (depth == 0) widgets.add(const Divider(height: 4));
        widgets.addAll(_buildConfigTree(
            entry.value as Map<String, dynamic>, depth + 1));
      } else {
        // Leaf value
        widgets.add(Padding(
          padding: EdgeInsets.only(
              left: (depth * 16.0) + 8, top: 2, bottom: 2),
          child: Row(
            children: [
              SizedBox(
                width: 180,
                child: Text(entry.key,
                    style: const TextStyle(
                        color: kColorTextSecond,
                        fontSize: 11,
                        fontFamily: 'monospace')),
              ),
              Expanded(
                child: _locked
                    ? Text(
                        entry.value.toString(),
                        style: const TextStyle(
                            color: kColorTextPrimary,
                            fontSize: 11,
                            fontFamily: 'monospace'),
                      )
                    : _EditableValue(
                        value: entry.value,
                        onChanged: (_) {},  // full PUT /config on save
                      ),
              ),
            ],
          ),
        ));
      }
    }
    return widgets;
  }
}

class _EditableValue extends StatelessWidget {
  final dynamic value;
  final ValueChanged<dynamic> onChanged;
  const _EditableValue({required this.value, required this.onChanged});

  @override
  Widget build(BuildContext context) {
    return Text(
      value.toString(),
      style: const TextStyle(
          color: kColorAccent,
          fontSize: 11,
          fontFamily: 'monospace'),
    );
  }
}
