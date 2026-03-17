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

# ── globals (keep handlers alive so GC doesn't destroy them) ──────────────────
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


def validate_params(p: dict) -> tuple:
    """Returns (ok: bool, message: str)."""
    N  = p['ring_pins']
    R  = p['ring_radius']
    rp = p['pin_radius']
    e  = p['eccentricity']

    if N < 3:
        return False, 'Pin count N must be ≥ 3.'
    if R <= 0 or rp <= 0 or e <= 0:
        return False, 'Ring radius, pin radius, and eccentricity must all be > 0.'

    max_e = R / N - rp / 2.0
    if e >= max_e:
        return False, (
            f'Eccentricity e={e:.2f} mm exceeds maximum {max_e:.2f} mm\n'
            f'(max e = R/N − rp/2 = {R:.1f}/{N} − {rp:.1f}/2)\n\n'
            f'Try reducing e or pin radius, or increasing ring radius.'
        )

    pts = cycloidal_profile(N, R, rp, e, 200)
    min_r = min(math.hypot(x, y) for x, y in pts)
    shaft_r = p['shaft_radius']
    if shaft_r >= min_r:
        return False, (
            f'Shaft radius ({shaft_r:.1f} mm) conflicts with cycloidal profile\n'
            f'(min profile radius = {min_r:.1f} mm).\n'
            f'Reduce shaft_radius or eccentricity.'
        )

    return True, 'OK'


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


def cut_circle(comp: adsk.fusion.Component,
               plane,
               cx_mm: float,
               cy_mm: float,
               r_mm: float,
               depth_mm: float) -> adsk.fusion.ExtrudeFeature:
    """Cut a circular hole on `plane` at (cx, cy) with radius r."""
    sk = comp.sketches.add(plane)
    sk.sketchCurves.sketchCircles.addByCenterRadius(pt(cx_mm, cy_mm), cm(r_mm))
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
    inp.quantity = adsk.core.ValueInput.createByReal(count)
    inp.totalAngle = adsk.core.ValueInput.createByReal(2.0 * math.pi)
    inp.isSymmetric = False
    return comp.features.circularPatternFeatures.add(inp)


# ══════════════════════════════════════════════════════════════════════════════
#  COMPONENT GENERATORS
# ══════════════════════════════════════════════════════════════════════════════

def _new_comp(root: adsk.fusion.Component, name: str) -> adsk.fusion.Component:
    occ = root.occurrences.addNewComponent(adsk.core.Matrix3D.create())
    occ.component.name = name
    return occ.component


def build_cycloidal_disc(root: adsk.fusion.Component, p: dict):
    """
    Cycloidal disc:
      - Closed cycloidal spline extruded to disc_thickness
      - Shaft hole through centre
      - Output pin holes (enlarged for orbital movement) on out_circle_radius
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

    # ── cycloidal profile ─────────────────────────────────────────────────────
    pts = cycloidal_profile(N, R, rp_ring, e, samp)
    sk_profile = comp.sketches.add(plane)
    sk_profile.name = 'Cycloidal_Profile'
    spline_from_pts(sk_profile, pts)
    extrude(comp, largest_profile(sk_profile), thick)

    # ── shaft hole ────────────────────────────────────────────────────────────
    cut_circle(comp, plane, 0, 0, shaft_r, thick * 2)

    # ── output pin holes (enlarged by eccentricity so disc can orbit) ─────────
    hole_r = out_pr + e + 0.1   # +0.1 mm clearance
    sk_holes = comp.sketches.add(plane)
    sk_holes.name = 'Output_Pin_Holes'
    sk_holes.sketchCurves.sketchCircles.addByCenterRadius(pt(out_cr, 0), cm(hole_r))

    inp = comp.features.extrudeFeatures.createInput(
        sk_holes.profiles.item(0),
        adsk.fusion.FeatureOperations.CutFeatureOperation)
    inp.setDistanceExtent(False, val(cm(thick * 2)))
    first_hole = comp.features.extrudeFeatures.add(inp)

    if out_n > 1:
        circular_pattern(comp, first_hole, comp.zConstructionAxis, out_n)

    return comp


def build_ring_housing(root: adsk.fusion.Component, p: dict):
    """
    Ring housing:
      - Solid outer cylinder
      - Inner bore (clears cycloidal disc)
      - N evenly-spaced pin holes at radius R
    """
    comp = _new_comp(root, 'Ring_Housing')
    plane = comp.xYConstructionPlane

    N     = p['ring_pins']
    R     = p['ring_radius']
    rp    = p['pin_radius']
    thick = p['disc_thickness']
    wall  = p['housing_wall']

    outer_r  = R + rp + wall
    bore_r   = R - rp - 0.5     # 0.5 mm clearance inside pin circle
    housing_h = thick + 4.0      # 2 mm proud each side

    # ── outer cylinder ────────────────────────────────────────────────────────
    sk_outer = comp.sketches.add(plane)
    sk_outer.name = 'Housing_Outer'
    sk_outer.sketchCurves.sketchCircles.addByCenterRadius(pt(0, 0), cm(outer_r))
    extrude(comp, sk_outer.profiles.item(0), housing_h)

    # ── inner bore ────────────────────────────────────────────────────────────
    cut_circle(comp, plane, 0, 0, bore_r, housing_h * 2)

    # ── ring pin holes (+0.05 mm for press-fit) ───────────────────────────────
    pin_hole_r = rp + 0.05
    sk_pin = comp.sketches.add(plane)
    sk_pin.name = 'Ring_Pin_Holes'
    sk_pin.sketchCurves.sketchCircles.addByCenterRadius(pt(R, 0), cm(pin_hole_r))

    inp = comp.features.extrudeFeatures.createInput(
        sk_pin.profiles.item(0),
        adsk.fusion.FeatureOperations.CutFeatureOperation)
    inp.setDistanceExtent(False, val(cm(housing_h * 2)))
    first_pin = comp.features.extrudeFeatures.add(inp)

    if N > 1:
        circular_pattern(comp, first_pin, comp.zConstructionAxis, N)

    return comp


def build_output_flange(root: adsk.fusion.Component, p: dict):
    """
    Output flange:
      - Solid disc
      - Shaft hole through centre
      - Output pin bosses (raised cylinders that pass through disc holes)
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
    flange_h = thick * 0.6

    # ── flange disc ───────────────────────────────────────────────────────────
    sk = comp.sketches.add(plane)
    sk.name = 'Flange_Profile'
    sk.sketchCurves.sketchCircles.addByCenterRadius(pt(0, 0), cm(flange_r))
    extrude(comp, sk.profiles.item(0), flange_h)

    # ── shaft hole ────────────────────────────────────────────────────────────
    cut_circle(comp, plane, 0, 0, shaft_r, flange_h * 2)

    # ── output pin bosses on top face ─────────────────────────────────────────
    pin_boss_h = thick + 2.0

    off_planes = comp.constructionPlanes
    off_input  = off_planes.createInput()
    off_input.setByOffset(plane, val(cm(flange_h)))
    top_plane  = off_planes.add(off_input)

    sk_boss = comp.sketches.add(top_plane)
    sk_boss.name = 'Output_Pin_Bosses'
    sk_boss.sketchCurves.sketchCircles.addByCenterRadius(pt(out_cr, 0), cm(out_pr))

    inp = comp.features.extrudeFeatures.createInput(
        sk_boss.profiles.item(0),
        adsk.fusion.FeatureOperations.JoinFeatureOperation)
    inp.setDistanceExtent(False, val(cm(pin_boss_h)))
    first_boss = comp.features.extrudeFeatures.add(inp)

    if out_n > 1:
        circular_pattern(comp, first_boss, comp.zConstructionAxis, out_n)

    return comp


def build_gearbox(p: dict):
    """Build all three components with the given parameters dict."""
    app  = adsk.core.Application.get()
    des  = adsk.fusion.Design.cast(app.activeProduct)
    root = des.rootComponent
    des.designType = adsk.fusion.DesignTypes.ParametricDesignType

    ok, msg = validate_params(p)
    if not ok:
        app.userInterface.messageBox(f'Invalid parameters:\n\n{msg}', CMD_NAME)
        return False

    build_cycloidal_disc(root, p)
    build_ring_housing(root, p)
    build_output_flange(root, p)

    app.userInterface.messageBox(
        f'Cycloidal Gearbox Generated\n\n'
        f'  Ring pins (N)   : {p["ring_pins"]}\n'
        f'  Disc lobes      : {p["ring_pins"] - 1}\n'
        f'  Reduction ratio : {p["ring_pins"] - 1} : 1\n'
        f'  Output pins     : {p["out_pins"]}\n\n'
        f'Components created:\n'
        f'  Cycloidal_Disc\n'
        f'  Ring_Housing\n'
        f'  Output_Flange\n\n'
        f'Assembly tip:\n'
        f'  Ring_Housing at Z=0\n'
        f'  Cycloidal_Disc offset by eccentricity ({p["eccentricity"]:.1f} mm) inside housing\n'
        f'  Output_Flange above disc',
        CMD_NAME
    )
    return True


# ══════════════════════════════════════════════════════════════════════════════
#  COMMAND DIALOG HANDLERS
# ══════════════════════════════════════════════════════════════════════════════

class CycloidalCommandDestroyHandler(adsk.core.CommandEventHandler):
    """Called when the dialog is closed — lets the script terminate cleanly."""
    def notify(self, args):
        adsk.terminate()


class CycloidalCommandCreatedHandler(adsk.core.CommandCreatedEventHandler):
    def notify(self, args):
        try:
            cmd    = adsk.core.CommandCreatedEventArgs.cast(args).command
            inputs = cmd.commandInputs

            # ── Ring gear ─────────────────────────────────────────────────────
            grp_ring = inputs.addGroupCommandInput('grp_ring', 'Ring Gear')
            ri = grp_ring.children
            ri.addValueInput('ring_pins_f',  'Pin count (N)',
                             '', adsk.core.ValueInput.createByReal(12))
            ri.addValueInput('ring_radius',  'Pin pitch-circle radius',
                             'mm', adsk.core.ValueInput.createByString('40 mm'))
            ri.addValueInput('pin_radius',   'Ring pin radius',
                             'mm', adsk.core.ValueInput.createByString('3 mm'))

            # ── Cycloidal disc ────────────────────────────────────────────────
            grp_disc = inputs.addGroupCommandInput('grp_disc', 'Cycloidal Disc')
            di = grp_disc.children
            di.addValueInput('eccentricity',     'Eccentricity (e)',
                             'mm', adsk.core.ValueInput.createByString('1.5 mm'))
            di.addValueInput('disc_thickness',   'Disc thickness',
                             'mm', adsk.core.ValueInput.createByString('8 mm'))
            di.addValueInput('shaft_radius',     'Input shaft radius',
                             'mm', adsk.core.ValueInput.createByString('5 mm'))
            di.addValueInput('profile_samples_f','Profile samples',
                             '', adsk.core.ValueInput.createByReal(300))

            # ── Output stage ──────────────────────────────────────────────────
            grp_out = inputs.addGroupCommandInput('grp_out', 'Output Stage')
            oi = grp_out.children
            oi.addValueInput('out_pins_f',       'Output pin count',
                             '', adsk.core.ValueInput.createByReal(6))
            oi.addValueInput('out_pin_radius',   'Output pin radius',
                             'mm', adsk.core.ValueInput.createByString('3.5 mm'))
            oi.addValueInput('out_circle_radius','Output pin circle radius',
                             'mm', adsk.core.ValueInput.createByString('18 mm'))

            # ── Housing ───────────────────────────────────────────────────────
            grp_hous = inputs.addGroupCommandInput('grp_hous', 'Housing')
            grp_hous.children.addValueInput(
                'housing_wall', 'Wall thickness',
                'mm', adsk.core.ValueInput.createByString('4 mm'))

            # ── Info / gear ratio display ─────────────────────────────────────
            inputs.addTextBoxCommandInput(
                'info', 'Info',
                '<b>Default (N=12):</b> Reduction = 11 : 1\n'
                'Disc lobes = N − 1 = 11\n\n'
                'Rule: e &lt; R/N − rp/2\n'
                'Default max e ≈ 40/12 − 3/2 = 1.83 mm',
                5, True)

            # ── Register remaining handlers ───────────────────────────────────
            on_change = CycloidalInputChangedHandler()
            cmd.inputChanged.add(on_change)
            _handlers.append(on_change)

            on_validate = CycloidalValidateHandler()
            cmd.validateInputs.add(on_validate)
            _handlers.append(on_validate)

            on_exec = CycloidalExecuteHandler()
            cmd.execute.add(on_exec)
            _handlers.append(on_exec)

            on_destroy = CycloidalCommandDestroyHandler()
            cmd.destroy.add(on_destroy)
            _handlers.append(on_destroy)

        except Exception:
            _ui.messageBox(f'Dialog setup error:\n{traceback.format_exc()}', CMD_NAME)


class CycloidalInputChangedHandler(adsk.core.InputChangedEventHandler):
    """Live-update gear ratio info box when N changes."""
    def notify(self, args):
        try:
            event  = adsk.core.InputChangedEventArgs.cast(args)
            inputs = event.inputs

            n_inp = inputs.itemById('ring_pins_f')
            r_inp = inputs.itemById('ring_radius')
            rp_inp = inputs.itemById('pin_radius')
            e_inp  = inputs.itemById('eccentricity')
            info   = inputs.itemById('info')

            if not (n_inp and r_inp and rp_inp and e_inp and info):
                return

            N  = max(3, int(round(n_inp.value)))
            R  = r_inp.value  * 10.0   # cm → mm
            rp = rp_inp.value * 10.0
            e  = e_inp.value  * 10.0
            max_e = R / N - rp / 2.0

            info.text = (
                f'<b>Disc lobes:</b> {N - 1}<br>'
                f'<b>Reduction:</b> {N - 1} : 1<br><br>'
                f'<b>Max eccentricity:</b> {max_e:.2f} mm<br>'
                f'<b>Current e:</b> {e:.2f} mm '
                + ('<font color="red">(TOO LARGE)</font>' if e >= max_e else '<font color="green">(OK)</font>')
            )
        except Exception:
            pass


class CycloidalValidateHandler(adsk.core.ValidateInputsEventHandler):
    """Disable OK if parameters are invalid."""
    def notify(self, args):
        try:
            event  = adsk.core.ValidateInputsEventArgs.cast(args)
            inputs = event.inputs

            N  = max(3, int(round(inputs.itemById('ring_pins_f').value)))
            R  = inputs.itemById('ring_radius').value  * 10.0
            rp = inputs.itemById('pin_radius').value   * 10.0
            e  = inputs.itemById('eccentricity').value * 10.0
            sr = inputs.itemById('shaft_radius').value
            dt = inputs.itemById('disc_thickness').value

            max_e = R / N - rp / 2.0
            event.areInputsValid = (
                N >= 3 and R > 0 and rp > 0 and
                0 < e < max_e and sr > 0 and dt > 0
            )
        except Exception:
            pass


class CycloidalExecuteHandler(adsk.core.CommandExecuteEventHandler):
    def notify(self, args):
        try:
            inputs = adsk.core.CommandExecuteEventArgs.cast(args).command.commandInputs

            def mm(id_):
                return inputs.itemById(id_).value * 10.0   # cm → mm

            def to_int(id_):
                return max(1, int(round(inputs.itemById(id_).value)))

            params = {
                'ring_pins':         to_int('ring_pins_f'),
                'ring_radius':       mm('ring_radius'),
                'pin_radius':        mm('pin_radius'),
                'eccentricity':      mm('eccentricity'),
                'disc_thickness':    mm('disc_thickness'),
                'shaft_radius':      mm('shaft_radius'),
                'profile_samples':   to_int('profile_samples_f'),
                'out_pins':          to_int('out_pins_f'),
                'out_pin_radius':    mm('out_pin_radius'),
                'out_circle_radius': mm('out_circle_radius'),
                'housing_wall':      mm('housing_wall'),
            }
            build_gearbox(params)

        except Exception:
            _ui.messageBox(f'Generate failed:\n{traceback.format_exc()}', CMD_NAME)


# ══════════════════════════════════════════════════════════════════════════════
#  ENTRY POINTS
# ══════════════════════════════════════════════════════════════════════════════

def run(context):
    global _app, _ui
    try:
        _app = adsk.core.Application.get()
        _ui  = _app.userInterface

        # Remove stale definition from a previous run
        existing = _ui.commandDefinitions.itemById(CMD_ID)
        if existing:
            existing.deleteMe()

        # Create the button command definition
        cmd_def = _ui.commandDefinitions.addButtonDefinition(
            CMD_ID, CMD_NAME, CMD_DESC)

        # Attach created handler (BEFORE execute so it's ready when event fires)
        on_created = CycloidalCommandCreatedHandler()
        cmd_def.commandCreated.add(on_created)
        _handlers.append(on_created)

        # Prevent script from auto-terminating BEFORE calling execute()
        adsk.autoTerminate(False)

        # Trigger the command — fires commandCreated → shows dialog
        cmd_def.execute()

    except Exception:
        if _ui:
            _ui.messageBox(f'Startup error:\n{traceback.format_exc()}', CMD_NAME)


def stop(context):
    global _handlers
    try:
        existing = _ui.commandDefinitions.itemById(CMD_ID) if _ui else None
        if existing:
            existing.deleteMe()
        _handlers.clear()
    except Exception:
        pass
