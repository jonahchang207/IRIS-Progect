import 'package:flutter/material.dart';

// ── Colour palette ────────────────────────────────────────────────────────────
const kColorBackground   = Color(0xFF0D0D0F);
const kColorSurface      = Color(0xFF1A1A1F);
const kColorSurfaceHigh  = Color(0xFF252530);
const kColorBorder       = Color(0xFF2E2E3A);
const kColorAccent       = Color(0xFFE53935);   // IRIS red
const kColorAccentDim    = Color(0xFF7B1A1A);
const kColorGreen        = Color(0xFF4CAF50);
const kColorYellow       = Color(0xFFFFB300);
const kColorBlue         = Color(0xFF2196F3);
const kColorTextPrimary  = Color(0xFFE8E8F0);
const kColorTextSecond   = Color(0xFF8888A0);
const kColorTextMono     = Color(0xFF9BCEAA);

// ── Joint colours ─────────────────────────────────────────────────────────────
const kJointColors = [
  Color(0xFF5C6BC0),   // J1 indigo
  Color(0xFF26A69A),   // J2 teal
  Color(0xFF66BB6A),   // J3 green
  Color(0xFFFFCA28),   // J4 amber
  Color(0xFFEF5350),   // J5 red
  Color(0xFFAB47BC),   // J6 purple
];

// ── Theme ─────────────────────────────────────────────────────────────────────
ThemeData buildAppTheme() {
  return ThemeData(
    useMaterial3: true,
    brightness: Brightness.dark,
    scaffoldBackgroundColor: kColorBackground,
    colorScheme: const ColorScheme.dark(
      primary: kColorAccent,
      onPrimary: Colors.white,
      surface: kColorSurface,
      onSurface: kColorTextPrimary,
      outline: kColorBorder,
    ),
    cardTheme: const CardThemeData(
      color: kColorSurface,
      elevation: 0,
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.all(Radius.circular(12)),
        side: BorderSide(color: kColorBorder, width: 1),
      ),
    ),
    dividerTheme: const DividerThemeData(color: kColorBorder, thickness: 1),
    textTheme: const TextTheme(
      bodyMedium: TextStyle(color: kColorTextPrimary),
      bodySmall:  TextStyle(color: kColorTextSecond),
      labelSmall: TextStyle(
          fontFamily: 'monospace', color: kColorTextMono, fontSize: 11),
    ),
    iconTheme: const IconThemeData(color: kColorTextSecond),
    elevatedButtonTheme: ElevatedButtonThemeData(
      style: ElevatedButton.styleFrom(
        backgroundColor: kColorSurfaceHigh,
        foregroundColor: kColorTextPrimary,
        side: const BorderSide(color: kColorBorder),
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
        padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
      ),
    ),
    sliderTheme: const SliderThemeData(
      activeTrackColor: kColorAccent,
      thumbColor: kColorAccent,
      inactiveTrackColor: kColorBorder,
      overlayColor: Color(0x22E53935),
    ),
  );
}
