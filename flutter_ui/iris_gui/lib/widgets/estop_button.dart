import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../providers/bridge_provider.dart';
import '../theme/app_theme.dart';

/// Always-visible E-STOP overlay. Inserted at root level in main_shell.dart.
/// Also triggers on Escape key.
class EStopButton extends ConsumerStatefulWidget {
  const EStopButton({super.key});

  @override
  ConsumerState<EStopButton> createState() => _EStopButtonState();
}

class _EStopButtonState extends ConsumerState<EStopButton>
    with SingleTickerProviderStateMixin {
  late final AnimationController _pulse;
  bool _latched = false;

  @override
  void initState() {
    super.initState();
    _pulse = AnimationController(
        vsync: this, duration: const Duration(milliseconds: 700))
      ..repeat(reverse: true);
    _pulse.stop();
  }

  @override
  void dispose() {
    _pulse.dispose();
    super.dispose();
  }

  void _trigger() {
    ref.read(bridgeClientProvider).estop();
    setState(() => _latched = true);
    _pulse.repeat(reverse: true);
  }

  void _clear() {
    ref.read(bridgeClientProvider).enable();
    setState(() => _latched = false);
    _pulse.stop();
    _pulse.reset();
  }

  @override
  Widget build(BuildContext context) {
    return KeyboardListener(
      focusNode: FocusNode()..requestFocus(),
      autofocus: true,
      onKeyEvent: (e) {
        if (e is KeyDownEvent &&
            e.logicalKey == LogicalKeyboardKey.escape &&
            !_latched) {
          _trigger();
        }
      },
      child: AnimatedBuilder(
        animation: _pulse,
        builder: (context, child) {
          final glowRadius = _latched ? 8.0 + _pulse.value * 16.0 : 0.0;
          return GestureDetector(
            onTap: _latched ? _clear : _trigger,
            child: Container(
              width: 80,
              height: 80,
              decoration: BoxDecoration(
                shape: BoxShape.circle,
                color: _latched ? kColorAccent : kColorAccentDim,
                boxShadow: _latched
                    ? [
                        BoxShadow(
                          color: kColorAccent.withOpacity(0.6),
                          blurRadius: glowRadius,
                          spreadRadius: glowRadius * 0.3,
                        )
                      ]
                    : [],
                border: Border.all(
                  color: kColorAccent,
                  width: _latched ? 2.5 : 1.5,
                ),
              ),
              child: Column(
                mainAxisAlignment: MainAxisAlignment.center,
                children: [
                  Icon(Icons.stop,
                      size: 32,
                      color: _latched ? Colors.white : kColorAccent),
                  const SizedBox(height: 2),
                  Text(
                    _latched ? 'CLEAR' : 'STOP',
                    style: const TextStyle(
                        fontSize: 9,
                        fontWeight: FontWeight.w800,
                        letterSpacing: 1.2,
                        color: Colors.white),
                  ),
                ],
              ),
            ),
          );
        },
      ),
    );
  }
}
