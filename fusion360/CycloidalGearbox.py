"""
IRIS Project — Parametric Cycloidal Gearbox Generator
Autodesk Fusion 360 Script

Generates three fully-parametric solid components:
  1. Cycloidal Disc   — the lobed gear with correct profile
  2. Ring Housing     — outer housing with pin pockets
  3. Output Flange    — output shaft with pin holes

Usage:
  Fusion 360 → Scripts & Add-Ins (Shift+S) → Add → select this file → Run

Theory:
  A cycloidal drive with N ring pins and N-1 disc lobes achieves
  a gear reduction of (N-1):1 — i.e. input shaft turns (N-1) times
  for one full output revolution. High reduction in minimal space,
  near-zero backlash, very high shock resistance.

Profile math (parametric, parameter φ ∈ [0, 2π)):
  K   = R / (e · N)
  α(φ) = atan2(sin((N-1)φ),  K − cos((N-1)φ))
  x(φ) = R·cos(φ) − rp·cos(φ+α) − e·cos(N·φ)
  y(φ) = R·sin(φ) − rp·sin(φ+α) − e·sin(N·φ)   (Fusion +Y = up)

  Where:
    N   = ring pin count
    R   = ring pin pitch circle radius (mm)
    rp  = ring pin radius (mm)
    e   = eccentricity (mm)
"""

import adsk.core
import adsk.fusion
import traceback
import math

# ── globals (keep handlers alive) ─────────────────────────────────────────────
_handlers = []
_app: adsk.core.Application = None
_ui:  adsk.core.UserInterface = None

CMD_ID   = 'IRIS_CycloidalGearboxGenerator'
CMD_NAME = 'Cycloidal Gearbox Generator'
CMD_DESC = 'Parametric cycloidal gearbox — disc, ring housing, output flange'


# ══════════════════════════════════════════════════════════════════════════════
#  MATH
# ══════════════════════════════════════════════════════════════════════════════

def cycloidal_profile(N: int, R: float, rp: float, e: float,
                      samples: int = 400) -> list:
    """
    Cycloidal disc profile in mm.

    N       : ring pin count
    R       : ring pin pitch-circle radius (mm)
    rp      : ring pin radius (mm)
    e       : eccentricity (mm)
    samples : number of profile vertices

    Returns list of (x_mm, y_mm) tuples.
    """
    pts = []
    K = R / (e * N)

    for i in range(samples):
        phi = 2.0 * math.pi * i / samples

        s = math.sin((N - 1) * phi)
        c = math.cos((N - 1) * phi)
        alpha = math.atan2(s, K - c)

        x =  R * math.cos(phi) - rp * math.cos(phi + alpha) - e * math.cos(N * phi)
        y =  R * math.sin(phi) - rp * math.sin(phi + alpha) - e * math.sin(N * phi)
        pts.append((x, y))

    return pts


def validate_profile(pts: list, shaft_r: float, rp: float) -> tuple:
    """
    Returns (ok: bool, message: str).
    Checks:
      - No point inside shaft hole
      - Profile is not self-intersecting (basic bounding check)
    """
    min_r = min(math.hypot(x, y) for x, y in pts)
    max_r = max(math.hypot(x, y) for x, y in pts)

    if min_r < shaft_r + rp:
        return False, (
            f'Shaft radius ({shaft_r:.1f} mm) too large — '
            f'conflicts with cycloidal profile (min profile radius = {min_r:.1f} mm).\n'
            f'Reduce shaft_radius or eccentricity.'
        )
    if max_r <= min_r + 0.5:
        return False, 'Profile has near-zero amplitude — check eccentricity and pin radius.'

    return True, 'OK'


def output_pin_circle_safe(N: int, R: float, rp: float, e: float,
                           out_pins: int, out_hole_r: float) -> bool:
    """
    Check that output pin holes don't overlap each other.
    out_hole_r = actual cut radius (pin_r + clearance).
    """
    # The output pin circle radius is typically ~(R - rp - e)*0.5
    # Minimum arc between adjacent holes
    out_c = (R - rp - e) * 0.5
    arc = 2.0 * math.pi * out_c / out_pins
    return arc >= 2.0 * out_hole_r + 1.0   # 1 mm wall between holes


# ══════════════════════════════════════════════════════════════════════════════
#  FUSION 360 GEOMETRY HELPERS
# ══════════════════════════════════════════════════════════════════════════════

def cm(v: float) -> float:
    """mm → Fusion internal units (cm)."""
    return v / 10.0


def pt(x_mm: float, y_mm: float, z_mm: float = 0.0) -> adsk.core.Point3D:
    return adsk.core.Point3D.create(cm(x_mm), cm(y_mm), cm(z_mm))


def val(v_cm: float) -> adsk.core.ValueInput:
    return adsk.core.ValueInput.createByReal(v_cm)


def spline_from_pts(sketch: adsk.fusion.Sketch,
                    pts_mm: list) -> adsk.fusion.SketchFittedSpline:
    """Create a closed fitted spline from mm points."""
    col = adsk.core.ObjectCollection.create()
    for x, y in pts_mm:
        col.add(pt(x, y))
    spline = sketch.sketchCurves.sketchFittedSplines.add(col)
    spline.isClosed = True
    return spline


def largest_profile(sketch: adsk.fusion.Sketch) -> adsk.fusion.Profile:
    """Return the profile with the largest area in a sketch."""
    best, best_area = None, -1.0
    for i in range(sketch.profiles.count):
        prof = sketch.profiles.item(i)
        area = prof.areaProperties().area
        if area > best_area:
            best_area = area
            best = prof
    return best


def extrude(comp: adsk.fusion.Component,
            profile: adsk.fusion.Profile,
            height_mm: float,
            op=adsk.fusion.FeatureOperations.NewBodyFeatureOperation
            ) -> adsk.fusion.ExtrudeFeature:
    inp = comp.features.extrudeFeatures.createInput(profile, op)
    inp.setDistanceExtent(False, val(cm(height_mm)))
    return comp.features.extrudeFeatures.add(inp)


def cut_thru(comp: adsk.fusion.Component,
             plane,
             cx_mm: float,
             cy_mm: float,
             r_mm: float,
             depth_mm: float) -> adsk.fusion.ExtrudeFeature:
    """Cut a circular through-hole on `plane` at (cx, cy) with radius r."""
    sk = comp.sketches.add(plane)
    sk.sketchCurves.sketchCircles.addByCenterRadius(
        pt(cx_mm, cy_mm), cm(r_mm))
    prof = sk.profiles.item(0)
    inp = comp.features.extrudeFeatures.createInput(
        prof, adsk.fusion.FeatureOperations.CutFeatureOperation)
    inp.setDistanceExtent(False, val(cm(depth_mm)))
    return comp.features.extrudeFeatures.add(inp)


def circular_pattern(comp: adsk.fusion.Component,
                     feature: adsk.fusion.Feature,
                     axis,
                     count: int) -> adsk.fusion.CircularPatternFeature:
    feats = adsk.core.ObjectCollection.create()
    feats.add(feature)
    inp = comp.features.circularPatternFeatures.createInput(feats, axis)
    inp.quantity = val(count)
    inp.totalAngle = val(2.0 * math.pi)
    inp.isSymmetric = False
    return comp.features.circularPatternFeatures.add(inp)


# ══════════════════════════════════════════════════════════════════════════════
#  COMPONENT GENERATORS
# ══════════════════════════════════════════════════════════════════════════════

def _new_comp(root: adsk.fusion.Component,
              name: str) -> adsk.fusion.Component:
    occ = root.occurrences.addNewComponent(adsk.core.Matrix3D.create())
    occ.component.name = name
    return occ.component


def build_cycloidal_disc(root: adsk.fusion.Component, p: dict):
    """
    Cycloidal disc:
      - Closed cycloidal spline profile extruded to disc_thickness
      - Shaft hole through centre
      - Output pin holes (enlarged for movement clearance) on out_circle_radius
    """
    comp = _new_comp(root, 'Cycloidal_Disc')
    plane = comp.xYConstructionPlane

    N       = p['ring_pins']
    R       = p['ring_radius']
    rp_ring = p['pin_radius']
    e       = p['eccentricity']
    thick   = p['disc_thickness']
    shaft_r = p['shaft_radius']
    out_n   = p['out_pins']
    out_pr  = p['out_pin_radius']
    out_cr  = p['out_circle_radius']
    samp    = p['profile_samples']

    # ── profile ──────────────────────────────────────────────────────────────
    pts = cycloidal_profile(N, R, rp_ring, e, samp)

    sk_profile = comp.sketches.add(plane)
    sk_profile.name = 'Cycloidal_Profile'
    spline_from_pts(sk_profile, pts)

    disc_prof = largest_profile(sk_profile)
    extrude(comp, disc_prof, thick)

    # ── shaft hole ────────────────────────────────────────────────────────────
    cut_thru(comp, plane, 0, 0, shaft_r, thick * 2)

    # ── output pin holes (enlarged: pin_r + eccentricity + 0.1 clearance) ────
    # The holes must be larger than the pin by the eccentricity so the disc can
    # orbit without the pins dragging.
    hole_r = out_pr + e + 0.1
    sk_holes = comp.sketches.add(plane)
    sk_holes.name = 'Output_Pin_Holes'
    sk_holes.sketchCurves.sketchCircles.addByCenterRadius(
        pt(out_cr, 0), cm(hole_r))

    first_hole_prof = sk_holes.profiles.item(0)
    inp = comp.features.extrudeFeatures.createInput(
        first_hole_prof,
        adsk.fusion.FeatureOperations.CutFeatureOperation)
    inp.setDistanceExtent(False, val(cm(thick * 2)))
    first_hole = comp.features.extrudeFeatures.add(inp)

    if out_n > 1:
        circular_pattern(comp, first_hole, comp.zConstructionAxis, out_n)

    return comp


def build_ring_housing(root: adsk.fusion.Component, p: dict):
    """
    Ring housing:
      - Solid outer cylinder (R + pin_r + wall_thickness)
      - Inner bore (R − pin_r − 0.5 clearance)
      - N evenly-spaced pin holes at radius R (diameter = pin_r * 2)
    """
    comp = _new_comp(root, 'Ring_Housing')
    plane = comp.xYConstructionPlane

    N      = p['ring_pins']
    R      = p['ring_radius']
    rp     = p['pin_radius']
    thick  = p['disc_thickness']
    wall   = p['housing_wall']

    outer_r = R + rp + wall
    bore_r  = R - rp - 0.5           # 0.5 mm clearance inside pins
    housing_h = thick + 4.0           # 2 mm proud each side

    # ── outer cylinder ────────────────────────────────────────────────────────
    sk_outer = comp.sketches.add(plane)
    sk_outer.name = 'Outer_Cylinder'
    sk_outer.sketchCurves.sketchCircles.addByCenterRadius(
        pt(0, 0), cm(outer_r))
    extrude(comp, sk_outer.profiles.item(0), housing_h)

    # ── bore (cut inner cylinder) ─────────────────────────────────────────────
    cut_thru(comp, plane, 0, 0, bore_r, housing_h * 2)

    # ── pin holes ─────────────────────────────────────────────────────────────
    # Pin holes are slightly oversized (+0.05 mm) for press-fit pins
    pin_hole_r = rp + 0.05
    sk_pin = comp.sketches.add(plane)
    sk_pin.name = 'Pin_Holes'
    sk_pin.sketchCurves.sketchCircles.addByCenterRadius(
        pt(R, 0), cm(pin_hole_r))

    first_pin_prof = sk_pin.profiles.item(0)
    inp = comp.features.extrudeFeatures.createInput(
        first_pin_prof,
        adsk.fusion.FeatureOperations.CutFeatureOperation)
    inp.setDistanceExtent(False, val(cm(housing_h * 2)))
    first_pin = comp.features.extrudeFeatures.add(inp)

    if N > 1:
        circular_pattern(comp, first_pin, comp.zConstructionAxis, N)

    return comp


def build_output_flange(root: adsk.fusion.Component, p: dict):
    """
    Output flange:
      - Solid disc (radius = out_circle_radius + pin_radius + wall)
      - Shaft hole through centre
      - N output pins as solid bosses (raised cylinders) or bolt holes
    """
    comp = _new_comp(root, 'Output_Flange')
    plane = comp.xYConstructionPlane

    shaft_r = p['shaft_radius']
    out_n   = p['out_pins']
    out_pr  = p['out_pin_radius']
    out_cr  = p['out_circle_radius']
    wall    = p['housing_wall']
    thick   = p['disc_thickness']

    flange_r = out_cr + out_pr + wall
    flange_h  = thick * 0.6

    # ── flange disc ───────────────────────────────────────────────────────────
    sk = comp.sketches.add(plane)
    sk.name = 'Flange_Profile'
    sk.sketchCurves.sketchCircles.addByCenterRadius(pt(0, 0), cm(flange_r))
    extrude(comp, sk.profiles.item(0), flange_h)

    # ── shaft hole ────────────────────────────────────────────────────────────
    cut_thru(comp, plane, 0, 0, shaft_r, flange_h * 2)

    # ── output pin bosses (extruded cylinders) ────────────────────────────────
    # Pins project upward from flange face; they pass through disc output holes
    pin_boss_h = thick + 2.0   # boss height = disc thickness + 2 mm

    # Offset plane to top face of flange
    off_planes = comp.constructionPlanes
    off_input = off_planes.createInput()
    off_input.setByOffset(plane, val(cm(flange_h)))
    top_plane = off_planes.add(off_input)

    sk_boss = comp.sketches.add(top_plane)
    sk_boss.name = 'Output_Pin_Bosses'
    sk_boss.sketchCurves.sketchCircles.addByCenterRadius(
        pt(out_cr, 0), cm(out_pr))

    first_boss_prof = sk_boss.profiles.item(0)
    inp = comp.features.extrudeFeatures.createInput(
        first_boss_prof,
        adsk.fusion.FeatureOperations.JoinFeatureOperation)
    inp.setDistanceExtent(False, val(cm(pin_boss_h)))
    first_boss = comp.features.extrudeFeatures.add(inp)

    if out_n > 1:
        circular_pattern(comp, first_boss, comp.zConstructionAxis, out_n)

    return comp


def build_gearbox(p: dict):
    """Build all components with given parameters."""
    app  = adsk.core.Application.get()
    des  = adsk.fusion.Design.cast(app.activeProduct)
    root = des.rootComponent

    des.designType = adsk.fusion.DesignTypes.ParametricDesignType

    # Validate profile first
    pts = cycloidal_profile(p['ring_pins'], p['ring_radius'],
                            p['pin_radius'], p['eccentricity'], 200)
    ok, msg = validate_profile(pts, p['shaft_radius'], p['pin_radius'])
    if not ok:
        app.userInterface.messageBox(f'⚠ Invalid parameters:\n\n{msg}', CMD_NAME)
        return False

    build_cycloidal_disc(root, p)
    build_ring_housing(root, p)
    build_output_flange(root, p)

    app.userInterface.messageBox(
        f'✓  Cycloidal Gearbox Generated\n\n'
        f'  Ring pins (N)   : {p["ring_pins"]}\n'
        f'  Disc lobes      : {p["ring_pins"] - 1}\n'
        f'  Reduction ratio : {p["ring_pins"] - 1} : 1\n'
        f'  Output pins     : {p["out_pins"]}\n\n'
        f'Components created:\n'
        f'  • Cycloidal_Disc\n'
        f'  • Ring_Housing\n'
        f'  • Output_Flange\n\n'
        f'Tip: position Ring_Housing at Z=0,\n'
        f'     Cycloidal_Disc at Z=2 (inside housing),\n'
        f'     Output_Flange above disc.',
        CMD_NAME
    )
    return True


# ══════════════════════════════════════════════════════════════════════════════
#  FUSION 360 COMMAND DIALOG
# ══════════════════════════════════════════════════════════════════════════════

class CycloidalCommandCreatedHandler(adsk.core.CommandCreatedEventHandler):
    def notify(self, args):
        try:
            cmd    = adsk.core.CommandCreatedEventArgs.cast(args).command
            inputs = cmd.commandInputs

            # ── Ring gear ─────────────────────────────────────────────────────
            grp_ring = inputs.addGroupCommandInput('grp_ring', 'Ring Gear')
            grp_ring.children.addValueInput(
                'ring_pins_f', 'Pin count (N)',
                '', adsk.core.ValueInput.createByReal(12))
            grp_ring.children.addValueInput(
                'ring_radius', 'Pin pitch-circle radius',
                'mm', adsk.core.ValueInput.createByString('40 mm'))
            grp_ring.children.addValueInput(
                'pin_radius', 'Pin radius',
                'mm', adsk.core.ValueInput.createByString('3 mm'))

            # ── Disc ──────────────────────────────────────────────────────────
            grp_disc = inputs.addGroupCommandInput('grp_disc', 'Cycloidal Disc')
            grp_disc.children.addValueInput(
                'eccentricity', 'Eccentricity (e)',
                'mm', adsk.core.ValueInput.createByString('1.5 mm'))
            grp_disc.children.addValueInput(
                'disc_thickness', 'Disc thickness',
                'mm', adsk.core.ValueInput.createByString('8 mm'))
            grp_disc.children.addValueInput(
                'shaft_radius', 'Input shaft radius',
                'mm', adsk.core.ValueInput.createByString('5 mm'))
            grp_disc.children.addValueInput(
                'profile_samples_f', 'Profile samples (100–600)',
                '', adsk.core.ValueInput.createByReal(300))

            # ── Output ────────────────────────────────────────────────────────
            grp_out = inputs.addGroupCommandInput('grp_out', 'Output Stage')
            grp_out.children.addValueInput(
                'out_pins_f', 'Output pin count',
                '', adsk.core.ValueInput.createByReal(6))
            grp_out.children.addValueInput(
                'out_pin_radius', 'Output pin radius',
                'mm', adsk.core.ValueInput.createByString('3.5 mm'))
            grp_out.children.addValueInput(
                'out_circle_radius', 'Output pin circle radius',
                'mm', adsk.core.ValueInput.createByString('18 mm'))

            # ── Housing ───────────────────────────────────────────────────────
            grp_hous = inputs.addGroupCommandInput('grp_hous', 'Housing')
            grp_hous.children.addValueInput(
                'housing_wall', 'Wall thickness',
                'mm', adsk.core.ValueInput.createByString('4 mm'))

            # ── Info display ──────────────────────────────────────────────────
            inputs.addTextBoxCommandInput(
                'info', 'Gear ratio',
                'Reduction = (N−1) : 1\n'
                'Default (N=12) → 11 : 1\n\n'
                'Tip: keep e < R/(N·2) for a valid profile.\n'
                'Max e ≈ R/N − rp/2',
                4, True)

            # ── Handlers ─────────────────────────────────────────────────────
            on_exec = CycloidalCommandExecuteHandler()
            cmd.execute.add(on_exec)
            _handlers.append(on_exec)

            on_change = CycloidalCommandInputChangedHandler()
            cmd.inputChanged.add(on_change)
            _handlers.append(on_change)

            on_validate = CycloidalCommandValidateInputsHandler()
            cmd.validateInputs.add(on_validate)
            _handlers.append(on_validate)

        except Exception:
            _ui.messageBox(f'Command setup failed:\n{traceback.format_exc()}')


class CycloidalCommandInputChangedHandler(adsk.core.InputChangedEventHandler):
    """Live-updates the gear ratio info box as parameters change."""
    def notify(self, args):
        try:
            inputs = adsk.core.InputChangedEventArgs.cast(args).inputs
            n_input = inputs.itemById('ring_pins_f')
            info    = inputs.itemById('info')
            if n_input and info:
                N = max(3, int(round(n_input.value)))
                info.text = (
                    f'Disc lobes    : {N - 1}\n'
                    f'Reduction     : {N - 1} : 1\n'
                    f'Output pins   : set below (must divide evenly)\n'
                    f'Max e (approx): R/N − rp/2'
                )
        except Exception:
            pass


class CycloidalCommandValidateInputsHandler(adsk.core.ValidateInputsEventHandler):
    """Disables OK button if parameters are clearly invalid."""
    def notify(self, args):
        try:
            event  = adsk.core.ValidateInputsEventArgs.cast(args)
            inputs = event.inputs

            N  = max(3, int(round(inputs.itemById('ring_pins_f').value)))
            R  = inputs.itemById('ring_radius').value * 10   # cm→mm
            rp = inputs.itemById('pin_radius').value * 10
            e  = inputs.itemById('eccentricity').value * 10

            max_e = R / N - rp / 2.0
            event.areInputsValid = (
                N >= 3 and
                R > 0 and
                rp > 0 and
                0 < e < max_e and
                inputs.itemById('shaft_radius').value > 0 and
                inputs.itemById('disc_thickness').value > 0
            )
        except Exception:
            pass


class CycloidalCommandExecuteHandler(adsk.core.CommandExecuteEventHandler):
    def notify(self, args):
        try:
            inputs = adsk.core.CommandExecuteEventArgs.cast(args).command.commandInputs

            def get_mm(id_):
                return inputs.itemById(id_).value * 10.0   # cm → mm

            def get_int(id_):
                return max(1, int(round(inputs.itemById(id_).value)))

            params = {
                'ring_pins':        get_int('ring_pins_f'),
                'ring_radius':      get_mm('ring_radius'),
                'pin_radius':       get_mm('pin_radius'),
                'eccentricity':     get_mm('eccentricity'),
                'disc_thickness':   get_mm('disc_thickness'),
                'shaft_radius':     get_mm('shaft_radius'),
                'profile_samples':  get_int('profile_samples_f'),
                'out_pins':         get_int('out_pins_f'),
                'out_pin_radius':   get_mm('out_pin_radius'),
                'out_circle_radius':get_mm('out_circle_radius'),
                'housing_wall':     get_mm('housing_wall'),
            }

            build_gearbox(params)

        except Exception:
            _ui.messageBox(f'Generate failed:\n{traceback.format_exc()}')


# ══════════════════════════════════════════════════════════════════════════════
#  ENTRY POINTS
# ══════════════════════════════════════════════════════════════════════════════

def run(context):
    global _app, _ui
    try:
        _app = adsk.core.Application.get()
        _ui  = _app.userInterface

        # Clean up old definition if re-running without restart
        existing = _ui.commandDefinitions.itemById(CMD_ID)
        if existing:
            existing.deleteMe()

        cmd_def = _ui.commandDefinitions.addButtonDefinition(
            CMD_ID, CMD_NAME, CMD_DESC)

        on_created = CycloidalCommandCreatedHandler()
        cmd_def.commandCreated.add(on_created)
        _handlers.append(on_created)

        cmd_def.execute()

        # Keep script alive until dialog closes
        adsk.autoTerminate(False)

    except Exception:
        if _ui:
            _ui.messageBox(f'Run failed:\n{traceback.format_exc()}')


def stop(context):
    try:
        existing = _ui.commandDefinitions.itemById(CMD_ID) if _ui else None
        if existing:
            existing.deleteMe()
    except Exception:
        pass
