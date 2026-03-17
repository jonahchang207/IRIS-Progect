// IRIS — Bridge connection constants

const String kBridgeHost = 'localhost';
const int kBridgePort = 8765;
const String kBridgeBase = 'http://$kBridgeHost:$kBridgePort';
const String kWsBase = 'ws://$kBridgeHost:$kBridgePort';

const String kWsJoints = '$kWsBase/ws/joints';
const String kWsCamera = '$kWsBase/ws/camera';
const String kWsLog    = '$kWsBase/ws/log';

// How long to wait for bridge before showing manual launch button
const Duration kBridgeConnectTimeout = Duration(seconds: 5);
const Duration kBridgeReconnectBase  = Duration(seconds: 1);
const Duration kBridgeReconnectMax   = Duration(seconds: 10);

// Number of log entries to keep in memory
const int kLogBufferSize = 10000;

// Jog increments (degrees)
const List<double> kJogIncrements = [0.5, 1.0, 5.0, 10.0];

// Joint display names
const List<String> kJointNames = ['J1', 'J2', 'J3', 'J4', 'J5', 'J6'];
const List<String> kMotorTypes = [
  'NEMA 23', 'NEMA 23', 'NEMA 17', 'NEMA 17', 'NEMA 17', 'NEMA 17'
];
