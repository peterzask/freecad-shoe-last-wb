import inspect
import FreeCAD as App
import Part
import helper_funcs as hf
import last_insole
import last_profile

print(f"+++++++++++++++Line({inspect.currentframe().f_lineno}) File:({__file__})+++++++++++++++++++")

# Pipeline: last_profile -> control_curves -> xs_base -> xs_0...xs_8 -> uv_0
#
# Collects all longitudinal control curves from last_insole and last_profile,
# displays them as named 3D compounds, and builds composite 3D loci that
# xs_base uses for per-section height intersections.
#
# Profile curves  (XZ plane -> 3D via sketch_profile.Placement):
#   bottom_bc, heel_bc, front_bc, top_bc  — profile outline
#   medial_highwater_bc, lateral_highwater_bc  — T1/T2 height loci
#   C1_profile_bc, C2_profile_bc              — crown shoulder height loci
#
# Insole curves  (already global XY, Z=0):
#   insole_bc_medial, insole_bc_lateral        — foot/last outline
#   C1_insole_medial, C2_insole_lateral        — crown shoulder Y-width loci
#   bc_medial_last_outline, bc_lateral_last_outline  — T1/T2 Y-width loci
#
# Composite 3D loci  (profile height + insole Y combined, overridable per-section):
#   medial_hw_locus, lateral_hw_locus          — T1/T2 full 3D
#   medial_crown_locus, lateral_crown_locus    — C1/C2 full 3D
#
# Non-coplanarity note: profile (tilted at atan(AH/CJ) ≈ 11°) and insole (flat)
# diverge from J; a cos-correction of CJ/sqrt(CJ²+profile_AH²) ≈ 0.979 could
# be applied per distance from J. Deferred — not worse than existing code today.
#
# HOW TO TUNE per section:
#   Uncomment and edit _OVERRIDES entries below.
#   Heights are mm above H along the section's local_up direction.
#   Fields: HT1 = medial highwater, HT2 = lateral highwater,
#           HC1 = medial crown shoulder, HC2 = lateral crown shoulder

_OVERRIDES = {
    # 'xs_3': dict(HC1=40.0, HC2=32.0),
    # 'xs_4': dict(HC1=38.0, HC2=28.0),  # waist: reduce crown shoulder for girth
    # 'xs_5': dict(HT1=47.0, HC1=50.0),
}

# --- Module-level loci (set by build(), used by xs_base) ---
medial_hw_locus     = None  # Part.BSplineCurve
lateral_hw_locus    = None
medial_crown_locus  = None
lateral_crown_locus = None


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _bc_to_3d(bc_2d):
    """Convert profile sketch BSpline (local XY) to global 3D via sketch placement."""
    poles = [last_profile.sketch_profile.Placement.multVec(p)
             for p in bc_2d.getPoles()]
    bc = Part.BSplineCurve()
    bc.buildFromPolesMultsKnots(poles, bc_2d.getMultiplicities(),
                                bc_2d.getKnots(), False, bc_2d.Degree)
    return bc


def _intersect_height(bc_3d, origin, normal, local_up):
    """Intersect bc_3d with plane; return (height_along_local_up, g_pt) or (None, None)."""
    try:
        g_pt = App.Vector(
            hf.get_bspline_plane_intersection_new(bc_3d, origin, normal)[0])
        return (g_pt - origin).dot(local_up), g_pt
    except Exception:
        return None, None


def _adjust_height(g_pt, origin, local_up, new_height):
    """Move g_pt to new_height along local_up; lateral Y component is preserved."""
    old_h = (g_pt - origin).dot(local_up)
    return g_pt + local_up * (new_height - old_h)


def _build_crown_3d(profile_bc_2d, insole_crown_bc, xs8_x):
    """Profile crown BSpline + insole crown Y offset (same construction as xs_base)."""
    bc_3d = _bc_to_3d(profile_bc_2d)
    poles = []
    for p in bc_3d.getPoles():
        x = min(p.x, xs8_x)
        try:
            y = hf.get_bspline_plane_intersection_new(
                insole_crown_bc, App.Vector(x, 0, 0), hf.nX)[0].y
        except Exception:
            y = 0.0
        poles.append(p + App.Vector(0, y, 0))
    bc_out = Part.BSplineCurve()
    bc_out.buildFromPolesMultsKnots(poles, profile_bc_2d.getMultiplicities(),
                                    profile_bc_2d.getKnots(), False, profile_bc_2d.Degree)
    return bc_out


def _show_compound(shapes, name):
    if not shapes:
        return
    doc = App.ActiveDocument
    obj = doc.getObject(name) or doc.addObject("Part::Feature", name)
    obj.Shape = Part.makeCompound(shapes)


# ---------------------------------------------------------------------------
# Section geometry (independent of xs_base)
# ---------------------------------------------------------------------------

def _section_geometry():
    """(name, origin, normal, local_up) for xs_0..xs_8 from last_profile."""
    pd = last_profile.profile_dwg
    sp = last_profile.sketch_profile
    il = last_insole.insole_lens

    gvec_uHB  = hf.xz_xy_place * (pd.B  - pd.H).normalize()
    gvec_uHC5 = hf.xz_xy_place * (pd.C5 - pd.H).normalize()
    g_H  = sp.Placement.multVec(pd.H)
    g_J  = sp.Placement.multVec(pd.J)
    g_K  = sp.Placement.multVec(pd.K)
    g_Kb = sp.Placement.multVec(pd.Kb)

    gvec_Kb_E  = hf.xz_xy_place * (pd.E  - pd.Kb)
    gvec_uKbE  = gvec_Kb_E.normalize()
    lvec_I     = pd.J1 + (pd.H1 - pd.J1) / 2.0
    gvec_K_I   = (sp.Placement.multVec(lvec_I) - g_K).normalize()
    gvec_J1_J  = hf.xz_xy_place * (pd.J1 - pd.J).normalize()
    gvec_uJB1  = hf.xz_xy_place * (pd.B1 - pd.J).normalize()
    gvec_uJB1y = App.Vector(-gvec_uJB1.z, 0, gvec_uJB1.x)
    g_X        = sp.Placement.multVec(pd.X)
    jb1_len    = (g_X - g_J).dot(gvec_uJB1)

    n_uHB = gvec_uHB
    n_KbE = App.Vector(gvec_Kb_E.z, 0, -gvec_Kb_E.x)
    n_KI  = App.Vector(gvec_K_I.z,  0, -gvec_K_I.x)
    n_J1J = App.Vector(gvec_J1_J.z, 0, -gvec_J1_J.x)
    n_JB1 = gvec_uJB1

    return [
        ('xs_0', g_H + gvec_uHB * (il.H1H2 / 4.0),         n_uHB,  gvec_uHC5),
        ('xs_1', g_H + gvec_uHB * il.AH,                    n_uHB,  gvec_uHC5),
        ('xs_2', App.Vector(g_Kb),                           n_KbE,  gvec_uKbE),
        ('xs_3', App.Vector(g_K),                            n_KI,   gvec_K_I),
        ('xs_4', (g_K + g_J) * 0.5,                         n_KI,   gvec_K_I),
        ('xs_5', App.Vector(g_J),                            n_J1J,  gvec_J1_J),
        ('xs_6', g_J + gvec_uJB1 * (jb1_len / 3.0),        n_JB1,  gvec_uJB1y),
        ('xs_7', g_J + gvec_uJB1 * (jb1_len * 2.0 / 3.0),  n_JB1,  gvec_uJB1y),
        ('xs_8', g_J + gvec_uJB1 * jb1_len,                 n_JB1,  gvec_uJB1y),
    ]


# ---------------------------------------------------------------------------
# Build
# ---------------------------------------------------------------------------

def build():
    global medial_hw_locus, lateral_hw_locus
    global medial_crown_locus, lateral_crown_locus

    pd  = last_profile.profile_dwg
    idw = last_insole.insole_dwg

    sections = _section_geometry()
    xs8_x = sections[-1][1].x  # clamp for insole crown lookup

    # --- Profile curves -> 3D ---
    bc_bottom    = _bc_to_3d(pd.bottom_bc)
    bc_heel      = _bc_to_3d(pd.heel_bc)
    bc_front     = _bc_to_3d(pd.front_bc)
    bc_top       = _bc_to_3d(pd.top_bc)
    bc_hw_med    = _bc_to_3d(pd.medial_highwater_bc)
    bc_hw_lat    = _bc_to_3d(pd.lateral_highwater_bc)
    bc_cr_med_p  = _bc_to_3d(pd.C1_profile_bc)   # profile-only (no insole Y)
    bc_cr_lat_p  = _bc_to_3d(pd.C2_profile_bc)

    profile_shapes = [
        bc_bottom.toShape(), bc_heel.toShape(), bc_front.toShape(), bc_top.toShape(),
        bc_hw_med.toShape(), bc_hw_lat.toShape(),
        bc_cr_med_p.toShape(), bc_cr_lat_p.toShape(),
    ]
    _show_compound(profile_shapes, "ProfileCurves3D")

    # --- Crown 3D loci base (profile height + insole Y offset) ---
    bc_cr_med_3d = _build_crown_3d(pd.C1_profile_bc, idw.C1_insole_medial,  xs8_x)
    bc_cr_lat_3d = _build_crown_3d(pd.C2_profile_bc, idw.C2_insole_lateral, xs8_x)

    # --- Insole curves (already global XY, Z=0) ---
    insole_shapes = [
        idw.insole_bc_medial.toShape(),
        idw.insole_bc_lateral.toShape(),
        idw.C1_insole_medial.toShape(),
        idw.C2_insole_lateral.toShape(),
        idw.bc_medial_last_outline.toShape(),
        idw.bc_lateral_last_outline.toShape(),
    ]
    _show_compound(insole_shapes, "InsoleCurves3D")

    # --- Sample loci at each section, apply overrides, build interpolating BSplines ---
    T1_pts, T2_pts, C1_pts, C2_pts = [], [], [], []

    print("\n=== Control loci heights mm (above H, local_up) ===")
    print(f"  {'Section':<8}  {'HT1':>7}  {'HT2':>7}  {'HC1':>7}  {'HC2':>7}")

    for name, origin, normal, local_up in sections:
        ovr = _OVERRIDES.get(name, {})

        HT1_0, g_T1 = _intersect_height(bc_hw_med,    origin, normal, local_up)
        HT2_0, g_T2 = _intersect_height(bc_hw_lat,    origin, normal, local_up)
        HC1_0, g_C1 = _intersect_height(bc_cr_med_3d, origin, normal, local_up)
        HC2_0, g_C2 = _intersect_height(bc_cr_lat_3d, origin, normal, local_up)

        def _resolve(val, default):
            if val is None: return default or 0.0
            return val

        HT1 = _resolve(ovr.get('HT1', HT1_0), HT1_0)
        HT2 = _resolve(ovr.get('HT2', HT2_0), HT2_0)
        HC1 = _resolve(ovr.get('HC1', HC1_0), HC1_0)
        HC2 = _resolve(ovr.get('HC2', HC2_0), HC2_0)

        flag = '*' if name in _OVERRIDES else ' '
        print(f" {flag}{name:<7}  {HT1:>7.2f}  {HT2:>7.2f}  {HC1:>7.2f}  {HC2:>7.2f}")

        T1_pts.append(_adjust_height(g_T1, origin, local_up, HT1) if g_T1 else origin)
        T2_pts.append(_adjust_height(g_T2, origin, local_up, HT2) if g_T2 else origin)
        C1_pts.append(_adjust_height(g_C1, origin, local_up, HC1) if g_C1 else origin)
        C2_pts.append(_adjust_height(g_C2, origin, local_up, HC2) if g_C2 else origin)

    print("  * = override active\n")

    medial_hw_locus    = Part.BSplineCurve(); medial_hw_locus.interpolate(T1_pts)
    lateral_hw_locus   = Part.BSplineCurve(); lateral_hw_locus.interpolate(T2_pts)
    medial_crown_locus = Part.BSplineCurve(); medial_crown_locus.interpolate(C1_pts)
    lateral_crown_locus = Part.BSplineCurve(); lateral_crown_locus.interpolate(C2_pts)

    _show_compound([
        medial_hw_locus.toShape(), lateral_hw_locus.toShape(),
        medial_crown_locus.toShape(), lateral_crown_locus.toShape(),
    ], "ControlCurveLoci")


build()


def main():
    print("control_curves main")
if __name__ == "__main__":
    main()
