import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../providers/bridge_provider.dart';
import '../widgets/estop_button.dart';
import '../theme/app_theme.dart';
import '../models/system_status.dart';
import '../widgets/status_badge.dart';
import 'dashboard_screen.dart';
import 'manual_control_screen.dart';
import 'pipeline_screen.dart';
import 'console_screen.dart';
import 'settings_screen.dart';
import 'joint_history_screen.dart';

class MainShell extends ConsumerStatefulWidget {
  const MainShell({super.key});

  @override
  ConsumerState<MainShell> createState() => _MainShellState();
}

class _MainShellState extends ConsumerState<MainShell> {
  int _selectedIndex = 0;

  static const _screens = [
    DashboardScreen(),
    ManualControlScreen(),
    PipelineScreen(),
    JointHistoryScreen(),
    ConsoleScreen(),
    SettingsScreen(),
  ];

  static const _navItems = [
    NavigationRailDestination(
        icon: Icon(Icons.dashboard_outlined),
        selectedIcon: Icon(Icons.dashboard),
        label: Text('Dashboard')),
    NavigationRailDestination(
        icon: Icon(Icons.tune_outlined),
        selectedIcon: Icon(Icons.tune),
        label: Text('Manual')),
    NavigationRailDestination(
        icon: Icon(Icons.play_circle_outline),
        selectedIcon: Icon(Icons.play_circle),
        label: Text('Pipeline')),
    NavigationRailDestination(
        icon: Icon(Icons.show_chart_outlined),
        selectedIcon: Icon(Icons.show_chart),
        label: Text('History')),
    NavigationRailDestination(
        icon: Icon(Icons.terminal_outlined),
        selectedIcon: Icon(Icons.terminal),
        label: Text('Console')),
    NavigationRailDestination(
        icon: Icon(Icons.settings_outlined),
        selectedIcon: Icon(Icons.settings),
        label: Text('Settings')),
  ];

  @override
  Widget build(BuildContext context) {
    final bridgeState = ref.watch(bridgeProvider);
    final jointAsync  = ref.watch(jointStreamProvider);
    final status = jointAsync.whenData((j) => j.status).valueOrNull
        ?? SystemStatus.idle;
    final initialized = jointAsync.whenData((j) => j.initialized).valueOrNull
        ?? false;

    return Scaffold(
      backgroundColor: kColorBackground,
      body: Stack(
        children: [
          Row(
            children: [
              // ── Navigation rail ────────────────────────────────────────────
              Container(
                decoration: const BoxDecoration(
                  color: kColorSurface,
                  border: Border(right: BorderSide(color: kColorBorder)),
                ),
                child: NavigationRail(
                  backgroundColor: kColorSurface,
                  selectedIndex: _selectedIndex,
                  onDestinationSelected: (i) =>
                      setState(() => _selectedIndex = i),
                  extended: false,
                  minWidth: 64,
                  destinations: _navItems,
                  selectedIconTheme:
                      const IconThemeData(color: kColorAccent),
                  unselectedIconTheme:
                      const IconThemeData(color: kColorTextSecond),
                  leading: Padding(
                    padding: const EdgeInsets.symmetric(vertical: 16),
                    child: Column(
                      children: [
                        // IRIS logo placeholder
                        Container(
                          width: 36,
                          height: 36,
                          decoration: BoxDecoration(
                            color: kColorAccent.withOpacity(0.15),
                            borderRadius: BorderRadius.circular(8),
                            border: Border.all(
                                color: kColorAccent.withOpacity(0.4)),
                          ),
                          child: const Center(
                            child: Text('I',
                                style: TextStyle(
                                    color: kColorAccent,
                                    fontSize: 18,
                                    fontWeight: FontWeight.w800)),
                          ),
                        ),
                        const SizedBox(height: 12),
                        // Connection dot
                        _ConnectionDot(state: bridgeState),
                      ],
                    ),
                  ),
                  trailing: Padding(
                    padding: const EdgeInsets.only(bottom: 16),
                    child: Column(
                      children: [
                        StatusBadge(status: status),
                        if (initialized) ...[
                          const SizedBox(height: 6),
                          const Tooltip(
                            message: 'Config locked after arm sequence',
                            child: Icon(Icons.lock,
                                size: 14, color: kColorTextSecond),
                          ),
                        ],
                      ],
                    ),
                  ),
                ),
              ),
              // ── Main content ───────────────────────────────────────────────
              Expanded(child: _screens[_selectedIndex]),
            ],
          ),
          // ── Always-on-top E-STOP ────────────────────────────────────────
          const Positioned(
            bottom: 24,
            right: 24,
            child: EStopButton(),
          ),
        ],
      ),
    );
  }
}

class _ConnectionDot extends StatelessWidget {
  final BridgeState state;
  const _ConnectionDot({required this.state});

  @override
  Widget build(BuildContext context) {
    final (color, tooltip) = switch (state) {
      BridgeState.connected    => (kColorGreen,  'Bridge connected'),
      BridgeState.connecting   => (kColorYellow, 'Connecting…'),
      BridgeState.error        => (kColorAccent, 'Bridge error'),
      BridgeState.disconnected => (kColorBorder, 'Disconnected'),
    };
    return Tooltip(
      message: tooltip,
      child: Container(
        width: 8,
        height: 8,
        decoration: BoxDecoration(shape: BoxShape.circle, color: color),
      ),
    );
  }
}
