import 'dart:io';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:window_manager/window_manager.dart';

import 'providers/bridge_provider.dart';
import 'screens/main_shell.dart';
import 'theme/app_theme.dart';
import 'core/constants.dart';

void main() async {
  WidgetsFlutterBinding.ensureInitialized();
  await windowManager.ensureInitialized();

  await windowManager.waitUntilReadyToShow(
    const WindowOptions(
      title: 'IRIS Control',
      minimumSize: Size(1200, 800),
      size: Size(1440, 900),
      center: true,
      backgroundColor: kColorBackground,
      titleBarStyle: TitleBarStyle.normal,
    ),
    () async {
      await windowManager.show();
      await windowManager.focus();
    },
  );

  runApp(const ProviderScope(child: IRISApp()));
}

class IRISApp extends ConsumerWidget {
  const IRISApp({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    return MaterialApp(
      title: 'IRIS Control',
      theme: buildAppTheme(),
      debugShowCheckedModeBanner: false,
      home: const _StartupGate(),
    );
  }
}

class _StartupGate extends ConsumerStatefulWidget {
  const _StartupGate();

  @override
  ConsumerState<_StartupGate> createState() => _StartupGateState();
}

class _StartupGateState extends ConsumerState<_StartupGate> {
  bool _launching = false;

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) => _autoLaunch());
  }

  Future<void> _autoLaunch() async {
    setState(() => _launching = true);
    await ref.read(bridgeProvider.notifier).launchAndConnect();
    setState(() => _launching = false);
  }

  @override
  Widget build(BuildContext context) {
    final state = ref.watch(bridgeProvider);

    if (state == BridgeState.connected) {
      return const MainShell();
    }

    return Scaffold(
      backgroundColor: kColorBackground,
      body: Center(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Container(
              width: 80, height: 80,
              decoration: BoxDecoration(
                color: kColorAccent.withOpacity(0.12),
                borderRadius: BorderRadius.circular(20),
                border: Border.all(color: kColorAccent.withOpacity(0.5), width: 2),
              ),
              child: const Center(
                child: Text('IRIS',
                    style: TextStyle(color: kColorAccent, fontSize: 18,
                        fontWeight: FontWeight.w800, letterSpacing: 2)),
              ),
            ),
            const SizedBox(height: 32),
            Text(
              switch (state) {
                BridgeState.connecting   => 'Connecting to bridge server\u2026',
                BridgeState.error        => 'Could not reach bridge server',
                BridgeState.disconnected => 'Bridge not running',
                BridgeState.connected    => '',
              },
              style: const TextStyle(color: kColorTextSecond, fontSize: 14),
            ),
            const SizedBox(height: 20),
            if (state == BridgeState.connecting || _launching)
              const SizedBox(width: 24, height: 24,
                child: CircularProgressIndicator(strokeWidth: 2, color: kColorAccent))
            else ...[
              ElevatedButton.icon(
                onPressed: _autoLaunch,
                icon: const Icon(Icons.refresh, size: 16),
                label: const Text('Launch Bridge & Connect'),
                style: ElevatedButton.styleFrom(
                  backgroundColor: kColorAccent.withOpacity(0.15),
                  foregroundColor: kColorAccent,
                  side: const BorderSide(color: kColorAccent),
                ),
              ),
              const SizedBox(height: 12),
              const Text(
                'Run  python3 host/bridge_server.py  manually if auto-launch fails',
                style: TextStyle(color: kColorTextSecond, fontSize: 11),
              ),
              const SizedBox(height: 4),
              Text('Bridge URL: $kBridgeBase',
                  style: const TextStyle(color: kColorTextSecond,
                      fontSize: 10, fontFamily: 'monospace')),
            ],
          ],
        ),
      ),
    );
  }
}
