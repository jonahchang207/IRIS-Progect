import 'package:flutter/material.dart';
import '../core/constants.dart';
import '../theme/app_theme.dart';

class JointSliderCard extends StatefulWidget {
  final int index;           // 0-5
  final double currentDeg;
  final double minDeg;
  final double maxDeg;
  final bool enabled;
  final void Function(double deg) onMove;
  final VoidCallback onHome;

  const JointSliderCard({
    super.key,
    required this.index,
    required this.currentDeg,
    required this.minDeg,
    required this.maxDeg,
    required this.enabled,
    required this.onMove,
    required this.onHome,
  });

  @override
  State<JointSliderCard> createState() => _JointSliderCardState();
}

class _JointSliderCardState extends State<JointSliderCard> {
  late double _draft;
  late final TextEditingController _ctrl;

  @override
  void initState() {
    super.initState();
    _draft = widget.currentDeg;
    _ctrl = TextEditingController(text: widget.currentDeg.toStringAsFixed(1));
  }

  @override
  void didUpdateWidget(JointSliderCard old) {
    super.didUpdateWidget(old);
    // Update draft only if not being dragged (focus check)
    if (!_ctrl.text.contains(RegExp(r'[a-zA-Z]'))) {
      _draft = widget.currentDeg;
    }
  }

  @override
  void dispose() {
    _ctrl.dispose();
    super.dispose();
  }

  void _jog(double delta) {
    if (!widget.enabled) return;
    final target = (_draft + delta).clamp(widget.minDeg, widget.maxDeg);
    widget.onMove(target);
  }

  void _sendFromText() {
    final val = double.tryParse(_ctrl.text);
    if (val != null) {
      final clamped = val.clamp(widget.minDeg, widget.maxDeg);
      widget.onMove(clamped);
    }
  }

  @override
  Widget build(BuildContext context) {
    final col = kJointColors[widget.index];
    final motor = kMotorTypes[widget.index];

    return Card(
      margin: const EdgeInsets.symmetric(vertical: 4, horizontal: 0),
      child: Padding(
        padding: const EdgeInsets.all(12),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // Header row
            Row(
              children: [
                Container(
                  width: 4, height: 20,
                  decoration: BoxDecoration(
                      color: col,
                      borderRadius: BorderRadius.circular(2)),
                ),
                const SizedBox(width: 8),
                Text(kJointNames[widget.index],
                    style: TextStyle(
                        color: col,
                        fontWeight: FontWeight.w700,
                        fontSize: 14)),
                const SizedBox(width: 6),
                Text(motor,
                    style: const TextStyle(
                        color: kColorTextSecond, fontSize: 11)),
                const Spacer(),
                // Numeric input
                SizedBox(
                  width: 72,
                  height: 28,
                  child: TextField(
                    controller: _ctrl,
                    enabled: widget.enabled,
                    style: const TextStyle(
                        fontSize: 12, color: kColorTextPrimary),
                    decoration: InputDecoration(
                      isDense: true,
                      contentPadding: const EdgeInsets.symmetric(
                          horizontal: 8, vertical: 6),
                      border: OutlineInputBorder(
                          borderRadius: BorderRadius.circular(6),
                          borderSide:
                              const BorderSide(color: kColorBorder)),
                      enabledBorder: OutlineInputBorder(
                          borderRadius: BorderRadius.circular(6),
                          borderSide:
                              const BorderSide(color: kColorBorder)),
                      suffix: const Text('°',
                          style: TextStyle(
                              color: kColorTextSecond, fontSize: 11)),
                    ),
                    onSubmitted: (_) => _sendFromText(),
                  ),
                ),
                const SizedBox(width: 8),
                // Home joint button
                Tooltip(
                  message: 'Home ${kJointNames[widget.index]}',
                  child: IconButton(
                    icon: const Icon(Icons.home, size: 18),
                    color: kColorTextSecond,
                    onPressed: widget.enabled ? widget.onHome : null,
                    padding: EdgeInsets.zero,
                    constraints: const BoxConstraints(
                        minWidth: 28, minHeight: 28),
                  ),
                ),
              ],
            ),
            const SizedBox(height: 6),
            // Slider
            SliderTheme(
              data: SliderTheme.of(context).copyWith(
                  activeTrackColor: col,
                  thumbColor: col,
                  overlayColor: col.withOpacity(0.15)),
              child: Slider(
                value: _draft.clamp(widget.minDeg, widget.maxDeg),
                min: widget.minDeg,
                max: widget.maxDeg,
                onChanged: widget.enabled
                    ? (v) => setState(() => _draft = v)
                    : null,
                onChangeEnd: widget.enabled ? widget.onMove : null,
              ),
            ),
            // Min/max labels + jog buttons
            Row(
              children: [
                Text('${widget.minDeg.toStringAsFixed(0)}°',
                    style: const TextStyle(
                        color: kColorTextSecond, fontSize: 10)),
                const Spacer(),
                for (final inc in kJogIncrements) ...[
                  _JogBtn(
                      label: '-${inc.toStringAsFixed(inc < 1 ? 1 : 0)}',
                      enabled: widget.enabled,
                      onTap: () => _jog(-inc)),
                  const SizedBox(width: 4),
                ],
                const SizedBox(width: 8),
                for (final inc in kJogIncrements.reversed) ...[
                  _JogBtn(
                      label: '+${inc.toStringAsFixed(inc < 1 ? 1 : 0)}',
                      enabled: widget.enabled,
                      onTap: () => _jog(inc)),
                  const SizedBox(width: 4),
                ],
                const Spacer(),
                Text('${widget.maxDeg.toStringAsFixed(0)}°',
                    style: const TextStyle(
                        color: kColorTextSecond, fontSize: 10)),
              ],
            ),
          ],
        ),
      ),
    );
  }
}

class _JogBtn extends StatelessWidget {
  final String label;
  final bool enabled;
  final VoidCallback onTap;

  const _JogBtn(
      {required this.label,
      required this.enabled,
      required this.onTap});

  @override
  Widget build(BuildContext context) {
    return SizedBox(
      width: 36,
      height: 24,
      child: OutlinedButton(
        onPressed: enabled ? onTap : null,
        style: OutlinedButton.styleFrom(
          padding: EdgeInsets.zero,
          side: const BorderSide(color: kColorBorder),
          shape: RoundedRectangleBorder(
              borderRadius: BorderRadius.circular(4)),
        ),
        child: Text(label,
            style: const TextStyle(
                fontSize: 9,
                color: kColorTextSecond,
                fontWeight: FontWeight.w600)),
      ),
    );
  }
}
