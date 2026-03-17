class LogEntry {
  final DateTime time;
  final String level;
  final String msg;

  const LogEntry({required this.time, required this.level, required this.msg});

  factory LogEntry.fromJson(Map<String, dynamic> j) => LogEntry(
        time: DateTime.now(),
        level: j['level'] as String? ?? 'INFO',
        msg: j['msg'] as String? ?? '',
      );

  factory LogEntry.local(String level, String msg) =>
      LogEntry(time: DateTime.now(), level: level, msg: msg);
}
