enum SystemStatus {
  idle,
  moving,
  homing,
  estopped;

  static SystemStatus fromString(String s) => switch (s.toUpperCase()) {
        'MOVING'  => moving,
        'HOMING'  => homing,
        'ESTOP'   => estopped,
        _         => idle,
      };

  String get label => switch (this) {
        idle      => 'IDLE',
        moving    => 'MOVING',
        homing    => 'HOMING',
        estopped  => 'E-STOP',
      };
}
