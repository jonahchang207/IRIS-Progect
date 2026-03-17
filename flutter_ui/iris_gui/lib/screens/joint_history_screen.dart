import 'package:fl_chart/fl_chart.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../core/constants.dart';
import '../providers/bridge_provider.dart';
import '../theme/app_theme.dart';

class JointHistoryScreen extends ConsumerStatefulWidget {
  const JointHistoryScreen({super.key});

  @override
  ConsumerState<JointHistoryScreen> createState() =>
      _JointHistoryScreenState();
}

class _JointHistoryScreenState
    extends ConsumerState<JointHistoryScreen> {
  // Ring buffer — last 600 samples (60s at 10 Hz)
  static const _maxSamples = 600;
  final List<List<double>> _history = List.generate(6, (_) => []);
  int _sampleCount = 0;
  final Set<int> _visible = {0, 1, 2, 3, 4, 5};

  @override
  void initState() {
    super.initState();
    // Listen to joint stream and buffer
    ref.listenManual(jointStreamProvider, (_, next) {
      next.whenData((js) {
        setState(() {
          for (int i = 0; i < 6; i++) {
            _history[i].add(js.angles[i]);
            if (_history[i].length > _maxSamples) {
              _history[i].removeAt(0);
            }
          }
          _sampleCount++;
        });
      });
    });
  }

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.all(16),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // Header
          Row(
            children: [
              const Text('JOINT HISTORY',
                  style: TextStyle(
                      color: kColorTextPrimary,
                      fontSize: 14,
                      fontWeight: FontWeight.w700,
                      letterSpacing: 1.5)),
              const Spacer(),
              // Joint toggles
              for (int i = 0; i < 6; i++)
                Padding(
                  padding: const EdgeInsets.only(left: 6),
                  child: FilterChip(
                    label: Text(kJointNames[i],
                        style: TextStyle(
                            color: _visible.contains(i)
                                ? kJointColors[i]
                                : kColorTextSecond,
                            fontSize: 11,
                            fontWeight: FontWeight.w600)),
                    selected: _visible.contains(i),
                    onSelected: (v) => setState(() {
                      v ? _visible.add(i) : _visible.remove(i);
                    }),
                    selectedColor:
                        kJointColors[i].withOpacity(0.15),
                    backgroundColor: kColorSurface,
                    side: BorderSide(
                        color: _visible.contains(i)
                            ? kJointColors[i]
                            : kColorBorder),
                    checkmarkColor: kJointColors[i],
                    showCheckmark: false,
                  ),
                ),
              const SizedBox(width: 8),
              TextButton(
                onPressed: () => setState(() {
                  for (final h in _history) h.clear();
                }),
                child: const Text('Clear',
                    style: TextStyle(
                        color: kColorTextSecond, fontSize: 11)),
              ),
            ],
          ),
          const SizedBox(height: 4),
          const Divider(),
          const SizedBox(height: 8),
          // Chart
          Expanded(child: _buildChart()),
          const SizedBox(height: 8),
          Text(
            'Showing last ${_history[0].length} samples at 10 Hz  (${(_history[0].length / 10.0).toStringAsFixed(0)}s)',
            style: const TextStyle(
                color: kColorTextSecond, fontSize: 10),
          ),
        ],
      ),
    );
  }

  Widget _buildChart() {
    if (_history[0].isEmpty) {
      return const Center(
        child: Text('No data yet — start the arm to see joint history.',
            style: TextStyle(color: kColorTextSecond)),
      );
    }

    final lines = <LineChartBarData>[];
    for (int i = 0; i < 6; i++) {
      if (!_visible.contains(i) || _history[i].isEmpty) continue;
      final spots = _history[i]
          .asMap()
          .entries
          .map((e) => FlSpot(e.key.toDouble(), e.value))
          .toList();
      lines.add(LineChartBarData(
        spots: spots,
        isCurved: true,
        curveSmoothness: 0.2,
        color: kJointColors[i],
        barWidth: 1.5,
        dotData: const FlDotData(show: false),
        belowBarData: BarAreaData(
            show: true,
            color: kJointColors[i].withOpacity(0.05)),
      ));
    }

    return LineChart(
      LineChartData(
        backgroundColor: kColorBackground,
        gridData: FlGridData(
          show: true,
          getDrawingHorizontalLine: (_) =>
              const FlLine(color: kColorBorder, strokeWidth: 1),
          getDrawingVerticalLine: (_) =>
              const FlLine(color: kColorBorder, strokeWidth: 1),
        ),
        borderData: FlBorderData(
            show: true,
            border: Border.all(color: kColorBorder)),
        titlesData: FlTitlesData(
          topTitles: const AxisTitles(
              sideTitles: SideTitles(showTitles: false)),
          rightTitles: const AxisTitles(
              sideTitles: SideTitles(showTitles: false)),
          leftTitles: AxisTitles(
            sideTitles: SideTitles(
              showTitles: true,
              reservedSize: 40,
              getTitlesWidget: (v, _) => Text('${v.toInt()}°',
                  style: const TextStyle(
                      color: kColorTextSecond, fontSize: 9)),
            ),
          ),
          bottomTitles: AxisTitles(
            sideTitles: SideTitles(
              showTitles: true,
              reservedSize: 24,
              getTitlesWidget: (v, _) {
                final secs = (v / 10).toStringAsFixed(0);
                return Text('${secs}s',
                    style: const TextStyle(
                        color: kColorTextSecond, fontSize: 9));
              },
            ),
          ),
        ),
        lineBarsData: lines,
        lineTouchData: LineTouchData(
          touchTooltipData: LineTouchTooltipData(
            getTooltipItems: (spots) => spots.map((s) {
              final i = lines.indexWhere(
                  (l) => l.color == s.bar.color);
              return LineTooltipItem(
                '${i >= 0 ? kJointNames[_visible.elementAt(i)] : ''}: ${s.y.toStringAsFixed(1)}°',
                TextStyle(
                    color: s.bar.color ?? Colors.white,
                    fontSize: 10),
              );
            }).toList(),
          ),
        ),
      ),
      duration: Duration.zero,
    );
  }
}
