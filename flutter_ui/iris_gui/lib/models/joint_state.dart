import 'system_status.dart';

class JointState {
  final List<double> angles;       // degrees, 6 elements
  final SystemStatus status;
  final bool initialized;

  const JointState({
    required this.angles,
    required this.status,
    required this.initialized,
  });

  factory JointState.zero() => JointState(
        angles: List.filled(6, 0.0),
        status: SystemStatus.idle,
        initialized: false,
      );

  factory JointState.fromJson(Map<String, dynamic> j) => JointState(
        angles: (j['joints'] as List).map((e) => (e as num).toDouble()).toList(),
        status: SystemStatus.fromString(j['status'] as String? ?? 'IDLE'),
        initialized: j['initialized'] as bool? ?? false,
      );
}
