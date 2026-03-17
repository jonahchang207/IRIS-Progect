"""
IRIS Project — Cycloidal Gearbox Generator  (Fusion 360 Add-In)
================================================================
Adds a persistent toolbar button to the Solid ▸ Create panel.
Clicking it opens a parameter dialog; clicking OK builds three
components and then assembles them with motion joints so the
gearbox can be animated in Fusion 360's Motion Study.

Assembly result
---------------
  Ring_Housing  — grounded (fixed frame)
  Cycloidal_Disc — revolute joint around its eccentric Z axis
                   (orbital + spin visualisation)
  Output_Flange  — revolute joint around the central Z axis
                   (the output shaft rotation)

Profile maths (parameter φ ∈ [0, 2π))
--------------------------------------
  K    = R / (e · N)
  α(φ) = atan2( sin((N-1)φ),  K − cos((N-1)φ) )
  x(φ) = R·cos φ − rp·cos(φ+α) − e·cos(N·φ)
  y(φ) = R·sin φ − rp·sin(φ+α) − e·sin(N·φ)

  N  = ring pin count        R  = pin pitch-circle radius (mm)
  rp = ring pin radius (mm)  e  = eccentricity (mm)
"""

import adsk.core
import adsk.fusion
import os
import struct
import traceback
import zlib
import math

# ── globals ────────────────────────────────────────────────────────────────────
_handlers: list = []
_app: adsk.core.Application = None
_ui:  adsk.core.UserInterface = None

CMD_ID       = 'IRIS_CycloidalGearboxGen'
CMD_NAME     = 'Cycloidal Gearbox Generator'
CMD_DESC     = 'Build a parametric cycloidal gearbox with assembled motion joints'
WORKSPACE_ID = 'FusionSolidEnvironment'
PANEL_ID     = 'SolidCreatePanel'


# ══════════════════════════════════════════════════════════════════════════════
#  ICON GENERATION  (no external libs — pure stdlib PNG)
# ══════════════════════════════════════════════════════════════════════════════

def _make_png(size: int, r: int, g: int, b: int) -> bytes:
    """Create a minimal solid-colour RGB PNG (stdlib only)."""
    row = bytes([0]) + bytes([r, g, b] * size)   # filter-none + pixels
    raw = row * size
    compressed = zlib.compress(raw, 9)

    def chunk(tag: bytes, data: bytes) -> bytes:
        body = tag + data
        return struct.pack('>I', len(data)) + body + struct.pack('>I', zlib.crc32(body) & 0xFFFFFFFF)

    ihdr = struct.pack('>IIBBBBB', size, size, 8, 2, 0, 0, 0)
    return (b'\x89PNG\r\n\x1a\n'
            + chunk(b'IHDR', ihdr)
            + chunk(b'IDAT', compressed)
            + chunk(b'IEND', b''))


def _ensure_icons(addin_dir: str):
    """Write icon PNGs into resources/ if they don't already exist."""
    res = os.path.join(addin_dir, 'resources')
    os.makedirs(res, exist_ok=True)
    specs = {
        '16x16.png':       (16, 229,  57,  53),   # IRIS red  (light bg)
        '16x16-dark.png':  (16, 239,  83,  80),   # lighter   (dark bg)
        '32x32.png':       (32, 229,  57,  53),
        '32x32-dark.png':  (32, 239,  83,  80),
        '64x64.png':       (64, 229,  57,  53),
    }
    for fname, (sz, r, g, bv) in specs.items():
        path = os.path.join(res, fname)
        if not os.path.exists(path):
            with open(path, 'wb') as f:
                f.write(_make_png(sz, r, g, bv))


# ══════════════════════════════════════════════════════════════════════════════
#  MATHS
# ══════════════════════════════════════════════════════════════════════════════

def cycloidal_profile(N: int, R: float, rp: float, e: float,
                      samples: int = 400) -> list:
    """
    Returns list of (x, y) mm tuples for the cycloidal disc profile.
    N       – ring pin count
    R       – ring pin pitch-circle radius (mm)
    rp      – ring pin radius (mm)
    e       – eccentricity (mm)
    samples – number of vertices
    """
    pts = []
    K = R / (e * N)
    for i in range(samples):
        phi = 2.0 * math.pi * i / samples
        alpha = math.atan2(math.sin((N - 1) * phi), K - math.cos((N - 1) * phi))
        x = R * math.cos(phi) - rp * math.cos(phi + alpha) - e * math.cos(N * phi)
        y = R * math.sin(phi) - rp * math.sin(phi + alpha) - e * math.sin(N * phi)
        pts.append((x, y))
    return pts


def validate_params(p: dict) -> tuple:
    """Returns (ok: bool, message: str)."""
    N, R, rp, e = p['ring_pins'], p['ring_radius'], p['pin_radius'], p['eccentricity']

    if N < 3:
        return False, 'Pin count N must be ≥ 3.'
    if R <= 0 or rp <= 0 or e <= 0:
        return False, 'Ring radius, pin radius and eccentricity must all be > 0.'

    max_e = R / N - rp / 2.0
    if max_e <= 0:
        return False, f'Pin radius ({rp} mm) is too large for N={N}, R={R} mm.\nTry a smaller pin or larger ring.'
    if e >= max_e:
        return False, (
            f'Eccentricity e = {e:.2f} mm exceeds maximum {max_e:.2f} mm\n'
            f'(max e = R/N − rp/2 = {R:.1f}/{N} − {rp:.1f}/2)\n\n'
            f'Reduce e, reduce pin radius, or increase ring radius.'
        )

    pts = cycloidal_profile(N, R, rp, e, 200)
    min_r = min(math.hypot(x, y) for x, y in pts)
    shaft_r = p['shaft_radius']
    if shaft_r >= min_r:
        return False, (
            f'Shaft radius ({shaft_r:.1f} mm) conflicts with the cycloidal profile\n'
            f'(min profile radius ≈ {min_r:.1f} mm).\n'
            f'Reduce shaft_radius or eccentricity.'
        )
    return True, 'OK'


# ══════════════════════════════════════════════════════════════════════════════
#  FUSION 360 GEOMETRY HELPERS
# ══════════════════════════════════════════════════════════════════════════════

def _cm(v: float) -> float:
    """mm → Fusion internal units (cm)."""
    return v / 10.0


def _pt(x_mm: float, y_mm: float, z_mm: float = 0.0) -> adsk.core.Point3D:
    return adsk.core.Point3D.create(_cm(x_mm), _cm(y_mm), _cm(z_mm))


def _vi(v_cm: float) -> adsk.core.ValueInput:
    return adsk.core.ValueInput.createByReal(v_cm)


def _spline(sketch: adsk.fusion.Sketch, pts_mm: list) -> adsk.fusion.SketchFittedSpline:
    """Closed fitted spline from (x_mm, y_mm) list."""
    col = adsk.core.ObjectCollection.create()
    for x, y in pts_mm:
        col.add(_pt(x, y))
    sp = sketch.sketchCurves.sketchFittedSplines.add(col)
    sp.isClosed = True
    return sp


def _largest_profile(sketch: adsk.fusion.Sketch) -> adsk.fusion.Profile:
    best, best_area = None, -1.0
    for i in range(sketch.profiles.count):
        prof = sketch.profiles.item(i)
        area = prof.areaProperties().area
        if area > best_area:
            best_area = area
            best = prof
    return best


def _extrude(comp: adsk.fusion.Component,
             profile: adsk.fusion.Profile,
             height_mm: float,
             op=adsk.fusion.FeatureOperations.NewBodyFeatureOperation
             ) -> adsk.fusion.ExtrudeFeature:
    inp = comp.features.extrudeFeatures.createInput(profile, op)
    inp.setDistanceExtent(False, _vi(_cm(height_mm)))
    return comp.features.extrudeFeatures.add(inp)


def _cut_circle(comp: adsk.fusion.Component,
                plane,
                cx_mm: float, cy_mm: float,
                r_mm: float, depth_mm: float) -> adsk.fusion.ExtrudeFeature:
    sk = comp.sketches.add(plane)
    sk.sketchCurves.sketchCircles.addByCenterRadius(_pt(cx_mm, cy_mm), _cm(r_mm))
    inp = comp.features.extrudeFeatures.createInput(
        sk.profiles.item(0),
        adsk.fusion.FeatureOperations.CutFeatureOperation)
    inp.setDistanceExtent(False, _vi(_cm(depth_mm)))
    return comp.features.extrudeFeatures.add(inp)


def _circ_pattern(comp: adsk.fusion.Component,
                  feature: adsk.fusion.Feature,
                  axis, count: int) -> adsk.fusion.CircularPatternFeature:
    feats = adsk.core.ObjectCollection.create()
    feats.add(feature)
    inp = comp.features.circularPatternFeatures.createInput(feats, axis)
    inp.quantity = adsk.core.ValueInput.createByReal(count)
    inp.totalAngle = adsk.core.ValueInput.createByReal(2.0 * math.pi)
    inp.isSymmetric = False
    return comp.features.circularPatternFeatures.add(inp)


def _new_comp(root: adsk.fusion.Component, name: str):
    """Add an empty child component; returns (occurrence, component) tuple."""
    occ  = root.occurrences.addNewComponent(adsk.core.Matrix3D.create())
    comp = occ.component
    comp.name = name
    return occ, comp


# ══════════════════════════════════════════════════════════════════════════════
#  COMPONENT BUILDERS
# ══════════════════════════════════════════════════════════════════════════════

def build_ring_housing(root: adsk.fusion.Component, p: dict):
    """
    Solid outer cylinder + inner bore + N ring pin holes.
    Returns the occurrence so the assembler can position/joint it.
    """
    occ, comp = _new_comp(root, 'Ring_Housing')
    plane = comp.xYConstructionPlane

    N     = p['ring_pins']
    R     = p['ring_radius']
    rp    = p['pin_radius']
    thick = p['disc_thickness']
    wall  = p['housing_wall']

    outer_r  = R + rp + wall
    bore_r   = R - rp - 0.5          # 0.5 mm clearance inside pin circle
    housing_h = thick + 4.0           # 2 mm cap each side of disc

    # outer cylinder
    sk = comp.sketches.add(plane)
    sk.name = 'Housing_Outer'
    sk.sketchCurves.sketchCircles.addByCenterRadius(_pt(0, 0), _cm(outer_r))
    _extrude(comp, sk.profiles.item(0), housing_h)

    # inner bore
    _cut_circle(comp, plane, 0, 0, bore_r, housing_h * 2)

    # ring pin holes (press-fit: +0.05 mm)
    sk_p = comp.sketches.add(plane)
    sk_p.name = 'Ring_Pin_Holes'
    sk_p.sketchCurves.sketchCircles.addByCenterRadius(_pt(R, 0), _cm(rp + 0.05))
    inp = comp.features.extrudeFeatures.createInput(
        sk_p.profiles.item(0),
        adsk.fusion.FeatureOperations.CutFeatureOperation)
    inp.setDistanceExtent(False, _vi(_cm(housing_h * 2)))
    first_pin = comp.features.extrudeFeatures.add(inp)
    if N > 1:
        _circ_pattern(comp, first_pin, comp.zConstructionAxis, N)

    return occ


def build_cycloidal_disc(root: adsk.fusion.Component, p: dict):
    """
    Cycloidal-profile disc + shaft hole + enlarged output pin holes.
    Returns the occurrence.
    """
    occ, comp = _new_comp(root, 'Cycloidal_Disc')
    plane = comp.xYConstructionPlane

    N       = p['ring_pins']
    R       = p['ring_radius']
    rp      = p['pin_radius']
    e       = p['eccentricity']
    thick   = p['disc_thickness']
    shaft_r = p['shaft_radius']
    out_n   = p['out_pins']
    out_pr  = p['out_pin_radius']
    out_cr  = p['out_circle_radius']
    samp    = p['profile_samples']

    # cycloidal profile spline → extrude
    pts = cycloidal_profile(N, R, rp, e, samp)
    sk_prof = comp.sketches.add(plane)
    sk_prof.name = 'Cycloidal_Profile'
    _spline(sk_prof, pts)
    _extrude(comp, _largest_profile(sk_prof), thick)

    # central shaft hole
    _cut_circle(comp, plane, 0, 0, shaft_r, thick * 2)

    # output pin holes — enlarged by eccentricity so disc can orbit
    hole_r = out_pr + e + 0.1
    sk_h = comp.sketches.add(plane)
    sk_h.name = 'Output_Pin_Holes'
    sk_h.sketchCurves.sketchCircles.addByCenterRadius(_pt(out_cr, 0), _cm(hole_r))
    inp = comp.features.extrudeFeatures.createInput(
        sk_h.profiles.item(0),
        adsk.fusion.FeatureOperations.CutFeatureOperation)
    inp.setDistanceExtent(False, _vi(_cm(thick * 2)))
    first_hole = comp.features.extrudeFeatures.add(inp)
    if out_n > 1:
        _circ_pattern(comp, first_hole, comp.zConstructionAxis, out_n)

    return occ


def build_output_flange(root: adsk.fusion.Component, p: dict):
    """
    Flange disc + shaft hole + output pin bosses that project upward
    through the cycloidal disc's enlarged holes.
    Returns the occurrence.
    """
    occ, comp = _new_comp(root, 'Output_Flange')
    plane = comp.xYConstructionPlane

    shaft_r = p['shaft_radius']
    out_n   = p['out_pins']
    out_pr  = p['out_pin_radius']
    out_cr  = p['out_circle_radius']
    wall    = p['housing_wall']
    thick   = p['disc_thickness']

    flange_r = out_cr + out_pr + wall
    flange_h = thick * 0.6
    boss_h   = thick + 2.0    # bosses pass fully through disc + 1 mm proud each side

    # flange body
    sk = comp.sketches.add(plane)
    sk.name = 'Flange_Profile'
    sk.sketchCurves.sketchCircles.addByCenterRadius(_pt(0, 0), _cm(flange_r))
    _extrude(comp, sk.profiles.item(0), flange_h)

    # central shaft hole
    _cut_circle(comp, plane, 0, 0, shaft_r, flange_h * 2)

    # pin bosses on top face of flange (project upward)
    off_planes = comp.constructionPlanes
    off_inp    = off_planes.createInput()
    off_inp.setByOffset(plane, _vi(_cm(flange_h)))
    top_plane  = off_planes.add(off_inp)

    sk_b = comp.sketches.add(top_plane)
    sk_b.name = 'Output_Pin_Bosses'
    sk_b.sketchCurves.sketchCircles.addByCenterRadius(_pt(out_cr, 0), _cm(out_pr))
    inp = comp.features.extrudeFeatures.createInput(
        sk_b.profiles.item(0),
        adsk.fusion.FeatureOperations.JoinFeatureOperation)
    inp.setDistanceExtent(False, _vi(_cm(boss_h)))
    first_boss = comp.features.extrudeFeatures.add(inp)
    if out_n > 1:
        _circ_pattern(comp, first_boss, comp.zConstructionAxis, out_n)

    return occ


# ══════════════════════════════════════════════════════════════════════════════
#  ASSEMBLY  — position + ground + as-built revolute joints
# ══════════════════════════════════════════════════════════════════════════════

def assemble_gearbox(root: adsk.fusion.Component, p: dict,
                     occ_housing, occ_disc, occ_flange):
    """
    Positions the three occurrences relative to each other and creates
    as-built revolute joints so the assembly can be animated.

    Layout (Z up):
      Ring_Housing   Z = 0 … housing_h          (grounded)
      Cycloidal_Disc Z = 2 … 2+thick, X = +e    (revolute around disc centre)
      Output_Flange  Z = -flange_h … 0, bosses → through disc  (revolute at Z axis)
    """
    thick     = p['disc_thickness']
    e         = p['eccentricity']
    housing_h = thick + 4.0          # same formula as build_ring_housing
    flange_h  = thick * 0.6          # same as build_output_flange

    # ── 1. Ring housing stays at origin ──────────────────────────────────────
    #    (addNewComponent already places it there — nothing to transform)
    occ_housing.isGrounded = True

    # ── 2. Cycloidal disc: inside housing, offset by eccentricity ────────────
    #    Z = 2 mm from housing bottom so it's centred with 2 mm cap each side
    disc_m = adsk.core.Matrix3D.create()
    disc_m.translation = adsk.core.Vector3D.create(
        _cm(e), 0.0, _cm(2.0))
    occ_disc.transform = disc_m

    # ── 3. Output flange: sits below the disc with bosses projecting up ───────
    #    flange top face aligns with disc bottom face (Z = 2 mm)
    #    so flange origin = Z = 2 - flange_h
    flange_z = 2.0 - flange_h        # may be slightly negative — that's fine
    flange_m = adsk.core.Matrix3D.create()
    flange_m.translation = adsk.core.Vector3D.create(
        0.0, 0.0, _cm(flange_z))
    occ_flange.transform = flange_m

    # ── 4. As-built revolute joint: Output_Flange ↔ Ring_Housing (Z axis) ────
    ab = root.asBuiltJoints
    inp_flange = ab.createInput(occ_flange, occ_housing, None)
    inp_flange.setAsRevoluteJointMotion(
        adsk.fusion.JointDirections.ZAxisJointDirection)
    j_out = ab.add(inp_flange)
    j_out.name = 'Output_Revolute'

    # ── 5. As-built revolute joint: Cycloidal_Disc ↔ Ring_Housing ────────────
    #    The disc revolves around its own (offset) Z axis, representing
    #    the orbital + spin motion.
    inp_disc = ab.createInput(occ_disc, occ_housing, None)
    inp_disc.setAsRevoluteJointMotion(
        adsk.fusion.JointDirections.ZAxisJointDirection)
    j_disc = ab.add(inp_disc)
    j_disc.name = 'Disc_Eccentric_Revolute'

    return j_out, j_disc


# ══════════════════════════════════════════════════════════════════════════════
#  MAIN BUILD ORCHESTRATOR
# ══════════════════════════════════════════════════════════════════════════════

def build_gearbox(p: dict) -> bool:
    app  = adsk.core.Application.get()
    des  = adsk.fusion.Design.cast(app.activeProduct)
    root = des.rootComponent
    des.designType = adsk.fusion.DesignTypes.ParametricDesignType

    # Validate
    ok, msg = validate_params(p)
    if not ok:
        _ui.messageBox(f'Invalid parameters:\n\n{msg}', CMD_NAME)
        return False

    # Build in order: housing first (it is the assembly ground)
    occ_housing = build_ring_housing(root, p)
    occ_disc    = build_cycloidal_disc(root, p)
    occ_flange  = build_output_flange(root, p)

    # Assemble
    assemble_gearbox(root, p, occ_housing, occ_disc, occ_flange)

    _ui.messageBox(
        f'Cycloidal Gearbox — Generated & Assembled\n\n'
        f'  Ring pins N      : {p["ring_pins"]}\n'
        f'  Disc lobes       : {p["ring_pins"] - 1}\n'
        f'  Reduction ratio  : {p["ring_pins"] - 1} : 1\n'
        f'  Output pins      : {p["out_pins"]}\n\n'
        f'Components\n'
        f'  Ring_Housing   — grounded\n'
        f'  Cycloidal_Disc — as-built revolute (eccentric axis)\n'
        f'  Output_Flange  — as-built revolute (central Z axis)\n\n'
        f'To animate:\n'
        f'  Design ▸ Motion Study (or Animation workspace)\n'
        f'  Drive "Output_Revolute" to see output rotation.\n'
        f'  Drive "Disc_Eccentric_Revolute" to see orbital motion.',
        CMD_NAME
    )
    return True


# ══════════════════════════════════════════════════════════════════════════════
#  COMMAND DIALOG HANDLERS
# ══════════════════════════════════════════════════════════════════════════════

class _DestroyHandler(adsk.core.CommandEventHandler):
    """No-op destroy handler — add-in stays loaded after dialog closes."""
    def notify(self, args):
        pass


class _CreatedHandler(adsk.core.CommandCreatedEventHandler):
    def notify(self, args):
        try:
            cmd    = adsk.core.CommandCreatedEventArgs.cast(args).command
            inputs = cmd.commandInputs

            # ── Ring Gear ─────────────────────────────────────────────────────
            g = inputs.addGroupCommandInput('grp_ring', 'Ring Gear')
            c = g.children
            c.addValueInput('ring_pins_f',  'Pin count (N)',
                            '', adsk.core.ValueInput.createByReal(12))
            c.addValueInput('ring_radius',  'Pin pitch-circle radius',
                            'mm', adsk.core.ValueInput.createByString('40 mm'))
            c.addValueInput('pin_radius',   'Ring pin radius',
                            'mm', adsk.core.ValueInput.createByString('3 mm'))

            # ── Cycloidal Disc ────────────────────────────────────────────────
            g = inputs.addGroupCommandInput('grp_disc', 'Cycloidal Disc')
            c = g.children
            c.addValueInput('eccentricity',      'Eccentricity  e',
                            'mm', adsk.core.ValueInput.createByString('1.5 mm'))
            c.addValueInput('disc_thickness',    'Disc thickness',
                            'mm', adsk.core.ValueInput.createByString('8 mm'))
            c.addValueInput('shaft_radius',      'Input shaft radius',
                            'mm', adsk.core.ValueInput.createByString('5 mm'))
            c.addValueInput('profile_samples_f', 'Profile samples  (100–600)',
                            '', adsk.core.ValueInput.createByReal(300))

            # ── Output Stage ──────────────────────────────────────────────────
            g = inputs.addGroupCommandInput('grp_out', 'Output Stage')
            c = g.children
            c.addValueInput('out_pins_f',        'Output pin count',
                            '', adsk.core.ValueInput.createByReal(6))
            c.addValueInput('out_pin_radius',    'Output pin radius',
                            'mm', adsk.core.ValueInput.createByString('3.5 mm'))
            c.addValueInput('out_circle_radius', 'Output pin circle radius',
                            'mm', adsk.core.ValueInput.createByString('18 mm'))

            # ── Housing ───────────────────────────────────────────────────────
            g = inputs.addGroupCommandInput('grp_hous', 'Housing')
            g.children.addValueInput('housing_wall', 'Wall thickness',
                                     'mm', adsk.core.ValueInput.createByString('4 mm'))

            # ── Info ──────────────────────────────────────────────────────────
            inputs.addTextBoxCommandInput(
                'info', 'Info',
                '<b>Default (N=12):</b>  Reduction = 11 : 1<br>'
                'Disc lobes = N − 1 = 11<br><br>'
                'Rule: &nbsp;e &lt; R/N − rp/2<br>'
                'Default max e ≈ 40/12 − 3/2 = 1.83 mm',
                5, True)

            # ── sub-handlers ──────────────────────────────────────────────────
            for h_cls, event in (
                (_InputChangedHandler, cmd.inputChanged),
                (_ValidateHandler,     cmd.validateInputs),
                (_ExecuteHandler,      cmd.execute),
                (_DestroyHandler,      cmd.destroy),
            ):
                h = h_cls()
                event.add(h)
                _handlers.append(h)

        except Exception:
            _ui.messageBox(f'Dialog setup error:\n{traceback.format_exc()}', CMD_NAME)


class _InputChangedHandler(adsk.core.InputChangedEventHandler):
    """Live-update the info box as N / R / rp / e change."""
    def notify(self, args):
        try:
            inputs = adsk.core.InputChangedEventArgs.cast(args).inputs
            n_i  = inputs.itemById('ring_pins_f')
            r_i  = inputs.itemById('ring_radius')
            rp_i = inputs.itemById('pin_radius')
            e_i  = inputs.itemById('eccentricity')
            info = inputs.itemById('info')
            if not all([n_i, r_i, rp_i, e_i, info]):
                return

            N    = max(3, int(round(n_i.value)))
            R    = r_i.value  * 10.0   # cm → mm
            rp   = rp_i.value * 10.0
            e    = e_i.value  * 10.0
            max_e = R / N - rp / 2.0 if (R / N - rp / 2.0) > 0 else 0.0

            ok_str = ('<font color="#00e676">(OK)</font>'
                      if 0 < e < max_e
                      else '<font color="#ef5350">(TOO LARGE)</font>')
            info.text = (
                f'<b>Disc lobes:</b> {N - 1}<br>'
                f'<b>Reduction:</b> {N - 1} : 1<br><br>'
                f'<b>Max e:</b> {max_e:.2f} mm<br>'
                f'<b>Current e:</b> {e:.2f} mm &nbsp;{ok_str}'
            )
        except Exception:
            pass


class _ValidateHandler(adsk.core.ValidateInputsEventHandler):
    """Disable OK button when parameters are obviously invalid."""
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
                max_e > 0 and 0 < e < max_e and
                sr > 0 and dt > 0
            )
        except Exception:
            pass


class _ExecuteHandler(adsk.core.CommandExecuteEventHandler):
    def notify(self, args):
        try:
            inputs = adsk.core.CommandExecuteEventArgs.cast(args).command.commandInputs

            def mm(id_):
                return inputs.itemById(id_).value * 10.0   # cm → mm

            def to_int(id_):
                return max(1, int(round(inputs.itemById(id_).value)))

            build_gearbox({
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
            })
        except Exception:
            _ui.messageBox(f'Build failed:\n{traceback.format_exc()}', CMD_NAME)


# ══════════════════════════════════════════════════════════════════════════════
#  ADD-IN ENTRY POINTS
# ══════════════════════════════════════════════════════════════════════════════

def run(context):
    """Called once when the add-in is loaded. Adds button to toolbar."""
    global _app, _ui
    try:
        _app = adsk.core.Application.get()
        _ui  = _app.userInterface

        # Generate icons if missing
        addin_dir = os.path.dirname(os.path.realpath(__file__))
        _ensure_icons(addin_dir)

        # Remove stale command definition from a previous session
        existing = _ui.commandDefinitions.itemById(CMD_ID)
        if existing:
            existing.deleteMe()

        # Build resource path for icons
        res_path = os.path.join(addin_dir, 'resources')

        # Create command definition
        cmd_def = _ui.commandDefinitions.addButtonDefinition(
            CMD_ID, CMD_NAME, CMD_DESC, res_path)

        # Attach created handler
        on_created = _CreatedHandler()
        cmd_def.commandCreated.add(on_created)
        _handlers.append(on_created)

        # Add button to Solid ▸ Create panel
        workspace = _ui.workspaces.itemById(WORKSPACE_ID)
        panel     = workspace.toolbarPanels.itemById(PANEL_ID)
        btn       = panel.controls.addCommand(cmd_def)
        btn.isPromotedByDefault = False

    except Exception:
        if _ui:
            _ui.messageBox(f'Add-in startup error:\n{traceback.format_exc()}', CMD_NAME)


def stop(context):
    """Called when the add-in is unloaded. Removes button and cleans up."""
    global _handlers
    try:
        if _ui:
            # Remove toolbar button
            workspace = _ui.workspaces.itemById(WORKSPACE_ID)
            if workspace:
                panel = workspace.toolbarPanels.itemById(PANEL_ID)
                if panel:
                    ctrl = panel.controls.itemById(CMD_ID)
                    if ctrl:
                        ctrl.deleteMe()

            # Remove command definition
            cmd_def = _ui.commandDefinitions.itemById(CMD_ID)
            if cmd_def:
                cmd_def.deleteMe()

        _handlers.clear()
    except Exception:
        pass
