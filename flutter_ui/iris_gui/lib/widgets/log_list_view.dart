import 'package:flutter/material.dart';
import '../models/log_entry.dart';
import '../theme/app_theme.dart';

class LogListView extends StatefulWidget {
  final List<LogEntry> entries;
  final String levelFilter;   // 'ALL', 'INFO', 'WARN', 'ERROR', 'DEBUG'
  final String textFilter;

  const LogListView({
    super.key,
    required this.entries,
    this.levelFilter = 'ALL',
    this.textFilter = '',
  });

  @override
  State<LogListView> createState() => _LogListViewState();
}

class _LogListViewState extends State<LogListView> {
  final ScrollController _scroll = ScrollController();
  bool _paused = false;

  @override
  void didUpdateWidget(LogListView old) {
    super.didUpdateWidget(old);
    if (!_paused && _scroll.hasClients) {
      WidgetsBinding.instance.addPostFrameCallback((_) {
        if (_scroll.hasClients) {
          _scroll.jumpTo(_scroll.position.maxScrollExtent);
        }
      });
    }
  }

  @override
  void dispose() {
    _scroll.dispose();
    super.dispose();
  }

  Color _levelColor(String level) => switch (level) {
        'ERROR'   => kColorAccent,
        'WARNING' => kColorYellow,
        'WARN'    => kColorYellow,
        'DEBUG'   => kColorTextSecond,
        _         => kColorTextPrimary,
      };

  List<LogEntry> get _filtered {
    return widget.entries.where((e) {
      if (widget.levelFilter != 'ALL' && e.level != widget.levelFilter) {
        return false;
      }
      if (widget.textFilter.isNotEmpty &&
          !e.msg.toLowerCase().contains(widget.textFilter.toLowerCase())) {
        return false;
      }
      return true;
    }).toList();
  }

  @override
  Widget build(BuildContext context) {
    final filtered = _filtered;
    return Column(
      children: [
        // Pause indicator
        if (_paused)
          GestureDetector(
            onTap: () => setState(() => _paused = false),
            child: Container(
              width: double.infinity,
              color: kColorYellow.withOpacity(0.1),
              padding: const EdgeInsets.symmetric(vertical: 4),
              child: const Text(
                '⏸  Log paused — tap to resume',
                textAlign: TextAlign.center,
                style: TextStyle(color: kColorYellow, fontSize: 11),
              ),
            ),
          ),
        Expanded(
          child: NotificationListener<ScrollNotification>(
            onNotification: (n) {
              if (n is UserScrollNotification) {
                final atBottom = _scroll.position.pixels >=
                    _scroll.position.maxScrollExtent - 20;
                if (!atBottom && !_paused) {
                  setState(() => _paused = true);
                } else if (atBottom && _paused) {
                  setState(() => _paused = false);
                }
              }
              return false;
            },
            child: ListView.builder(
              controller: _scroll,
              itemCount: filtered.length,
              itemExtent: 20,
              itemBuilder: (_, i) {
                final e = filtered[i];
                final ts = '${e.time.hour.toString().padLeft(2, '0')}:'
                    '${e.time.minute.toString().padLeft(2, '0')}:'
                    '${e.time.second.toString().padLeft(2, '0')}.'
                    '${(e.time.millisecond ~/ 10).toString().padLeft(2, '0')}';
                return Padding(
                  padding:
                      const EdgeInsets.symmetric(horizontal: 12, vertical: 1),
                  child: Row(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(ts,
                          style: const TextStyle(
                              fontFamily: 'monospace',
                              fontSize: 10,
                              color: kColorTextSecond)),
                      const SizedBox(width: 8),
                      SizedBox(
                        width: 44,
                        child: Text(e.level,
                            style: TextStyle(
                                fontFamily: 'monospace',
                                fontSize: 10,
                                color: _levelColor(e.level),
                                fontWeight: FontWeight.w700)),
                      ),
                      Expanded(
                        child: Text(e.msg,
                            style: const TextStyle(
                                fontFamily: 'monospace',
                                fontSize: 10,
                                color: kColorTextPrimary),
                            overflow: TextOverflow.ellipsis),
                      ),
                    ],
                  ),
                );
              },
            ),
          ),
        ),
      ],
    );
  }
}
