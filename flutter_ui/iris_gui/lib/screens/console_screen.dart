import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../providers/bridge_provider.dart';
import '../widgets/log_list_view.dart';
import '../theme/app_theme.dart';

class ConsoleScreen extends ConsumerStatefulWidget {
  const ConsoleScreen({super.key});

  @override
  ConsumerState<ConsoleScreen> createState() => _ConsoleScreenState();
}

class _ConsoleScreenState extends ConsumerState<ConsoleScreen> {
  String _level = 'ALL';
  String _search = '';
  final _searchCtrl = TextEditingController();

  static const _levels = ['ALL', 'DEBUG', 'INFO', 'WARNING', 'ERROR'];

  @override
  void dispose() {
    _searchCtrl.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final entries = ref.watch(logBufferProvider);

    return Column(
      children: [
        // Toolbar
        Container(
          padding:
              const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
          decoration: const BoxDecoration(
            color: kColorSurface,
            border:
                Border(bottom: BorderSide(color: kColorBorder)),
          ),
          child: Row(
            children: [
              const Text('CONSOLE',
                  style: TextStyle(
                      color: kColorTextSecond,
                      fontSize: 11,
                      fontWeight: FontWeight.w700,
                      letterSpacing: 1)),
              const SizedBox(width: 16),
              // Level filter
              DropdownButton<String>(
                value: _level,
                dropdownColor: kColorSurface,
                style: const TextStyle(
                    color: kColorTextPrimary, fontSize: 12),
                underline: const SizedBox(),
                items: _levels
                    .map((l) => DropdownMenuItem(value: l, child: Text(l)))
                    .toList(),
                onChanged: (v) =>
                    setState(() => _level = v ?? 'ALL'),
              ),
              const SizedBox(width: 12),
              // Search
              SizedBox(
                width: 200,
                height: 32,
                child: TextField(
                  controller: _searchCtrl,
                  style: const TextStyle(
                      fontSize: 12, color: kColorTextPrimary),
                  decoration: InputDecoration(
                    hintText: 'Search…',
                    hintStyle: const TextStyle(
                        color: kColorTextSecond, fontSize: 12),
                    isDense: true,
                    contentPadding: const EdgeInsets.symmetric(
                        horizontal: 10, vertical: 6),
                    border: OutlineInputBorder(
                        borderRadius: BorderRadius.circular(6),
                        borderSide:
                            const BorderSide(color: kColorBorder)),
                    enabledBorder: OutlineInputBorder(
                        borderRadius: BorderRadius.circular(6),
                        borderSide:
                            const BorderSide(color: kColorBorder)),
                    prefixIcon: const Icon(Icons.search,
                        size: 14, color: kColorTextSecond),
                  ),
                  onChanged: (v) => setState(() => _search = v),
                ),
              ),
              const Spacer(),
              Text('${entries.length} entries',
                  style: const TextStyle(
                      color: kColorTextSecond, fontSize: 11)),
              const SizedBox(width: 12),
              TextButton(
                onPressed: () =>
                    ref.read(logBufferProvider.notifier).clear(),
                child: const Text('Clear',
                    style: TextStyle(
                        color: kColorTextSecond, fontSize: 11)),
              ),
            ],
          ),
        ),
        // Log view
        Expanded(
          child: Container(
            color: kColorBackground,
            child: LogListView(
              entries: entries,
              levelFilter: _level,
              textFilter: _search,
            ),
          ),
        ),
      ],
    );
  }
}
