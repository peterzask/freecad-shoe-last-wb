import math
import inspect
import FreeCAD as App
import Part
import helper_funcs as hf
import last_insole
import last_profile
import shape_params as sp

print(f"+++++++++++++++Line({inspect.currentframe().f_lineno}) File:({__file__})+++++++++++++++++++")

# Pipeline: last_insole -> last_profile -> control_curves -> xs_base -> xs_0...xs_8 -> uv_0
#
# All BSpline (continuous) geometry is built here, organized by table row.
# last_insole and last_profile supply only discrete geometry: points, lengths,
# construction lines, and circles.
#
# The last takes shape bottom-up:
#   insole last outline → profile bottom/top → highwaters and crowns
#
# After build(), curves are back-assigned to profile_dwg / insole_dwg so that
# xs_*.py files need no changes.
#
"""

                                                                              Control Curve (CC)
           Input Curve       +      Input Curve            =       Output Control Curve*[1]
+----------------------------+-----------------------------+--------------------------+
|       xy plane curves     ,| xz plane curves,            |   control loci curve     |
+----------------------------+-----------------------------+--------------------------+
|       insole medial       ,| profile bottom           ,  |    H1 CC loci            |
|       insole lateral      ,| profile bottom           ,  |    H2 CC loci            |
|       last outline medial ,| profile highwater medial ,  |    T1 CC loci            |
|       last outline lateral,| profile highwater lateral,  |    T2 CC loci            |
|       xz-plane            ,| profile top-curve        ,  |    C  CC loci            |
|       xy plane C1         ,| profile curve C1         ,  |    C1 CC loci            |
|       xy plane C2         ,| profile curve C2         ,  |    C2 CC loci            |
|       heel curve          ,| xz-plane                 ,  |    Pts H,H2,C5 loci      |
+----------------------------+-----------------------------+--------------------------+
# used:   :!column -t -s, --output-separator ", "    , and DrawIt
*[1] I haven't look up proper names yet


I suggest the word loci be used only for curve combinations on output curves
"""
# Profile curves  (XZ plane -> 3D via sketch_profile.Placement):
#   (bc - 'B'spline'C'urve)
#   bottom_bc, heel_bc, front_bc, front_top_bc, top_bc  — profile outline
#   medial_highwater_bc, lateral_highwater_bc            — T1/T2 height loci
#   C1_profile_bc, C2_profile_bc                        — crown shoulder height loci
#
# Insole curves  (already global XY, Z=0):
#   insole_bc_medial, insole_bc_lateral        — insole outline (rows 4 & 5)
#   C1_insole_medial, C2_insole_lateral        — crown shoulder Y-width loci
#   bc_medial_last_outline, bc_lateral_last_outline  — T1/T2 Y-width loci
#
# Composite 3D loci  (profile height + insole Y combined, overridable per-section):
#   medial_hw_locus, lateral_hw_locus          — T1/T2 full 3D
#   medial_crown_locus, lateral_crown_locus    — C1/C2 full 3D
#
# Non-coplanarity note: profile (tilted at atan(AH/CJ) ≈ 11°) and insole (flat)
# diverge from J; a cos-correction of CJ/sqrt(CJ²+profile_AH²) ≈ 0.979 could
# be applied per distance from J. Deferred — not worse than existing code today. (Use to account for with projections.)
#
# HOW TO TUNE per section:
#   Uncomment and edit _OVERRIDES entries below.
#   Heights are mm above H along the section's local_up direction.
#   Fields: HT1 = medial highwater, HT2 = lateral highwater,
#           HC1 = medial crown shoulder, HC2 = lateral crown shoulder

_OVERRIDES = {}
# Saved override values (re-enable as needed):
# 'xs_5': dict(HC1=63.0, HC2=55.0,   # joint: raise crown; was 54.98 / 47.26
#              HT1=54.0, HT2=41.0),   # raise shoulder; was 47.77 / 35.73
# xs_4: local_up (gvec_K_I) nearly horizontal → height barely affects shape; use _SECTION_GIRTH_SCALE in uv_0 instead

# --- Module-level curve handles (set by build(), used by xs_base and xs_*.py) ---
# Rows 1 & 2: T1/T2 — last outline (XY) + highwater (XZ)
bc_medial_last_outline  = None
bc_lateral_last_outline = None
medial_highwater_bc     = None
lateral_highwater_bc    = None
# Row 3: C — profile top (XZ)
top_bc                  = None
# Rows 4 & 5: H1/H2 — insole outline (XY) + profile bottom (XZ)
insole_bc_medial        = None
insole_bc_lateral       = None
bottom_bc               = None
front_bc                = None
front_top_bc            = None
# Rows 6 & 7: C1/C2 — crown shoulder (XY + XZ)
C1_insole_medial        = None
C2_insole_lateral       = None
C1_profile_bc           = None
C2_profile_bc           = None
# Row 8: Heel (XZ)
heel_bc                 = None
# Composite 3D loci
medial_hw_locus         = None
lateral_hw_locus        = None
medial_crown_locus      = None
lateral_crown_locus     = None


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
    pd  = last_profile.profile_dwg
    skp = last_profile.sketch_profile
    il  = last_insole.insole_lens

    gvec_uHB  = hf.xz_xy_place * (pd.B  - pd.H).normalize()
    gvec_uHC5 = hf.xz_xy_place * (pd.C5 - pd.H).normalize()
    g_H  = skp.Placement.multVec(pd.H)
    g_J  = skp.Placement.multVec(pd.J)
    g_K  = skp.Placement.multVec(pd.K)
    g_Kb = skp.Placement.multVec(pd.Kb)

    gvec_Kb_E  = hf.xz_xy_place * (pd.E  - pd.Kb)
    gvec_uKbE  = gvec_Kb_E.normalize()
    lvec_I     = pd.J1 + (pd.H1 - pd.J1) / 2.0
    gvec_K_I   = (skp.Placement.multVec(lvec_I) - g_K).normalize()
    gvec_J1_J  = hf.xz_xy_place * (pd.J1 - pd.J).normalize()
    gvec_uJB1  = hf.xz_xy_place * (pd.B1 - pd.J).normalize()
    gvec_uJB1y = App.Vector(-gvec_uJB1.z, 0, gvec_uJB1.x)
    g_X        = skp.Placement.multVec(pd.X)
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
# Build — all BSpline geometry organized by table row
# ---------------------------------------------------------------------------

def build():
    global bc_medial_last_outline, bc_lateral_last_outline
    global medial_highwater_bc, lateral_highwater_bc
    global top_bc
    global insole_bc_medial, insole_bc_lateral, bottom_bc, front_bc, front_top_bc
    global C1_insole_medial, C2_insole_lateral, C1_profile_bc, C2_profile_bc
    global heel_bc
    global medial_hw_locus, lateral_hw_locus, medial_crown_locus, lateral_crown_locus

    pd      = last_profile.profile_dwg
    idw     = last_insole.insole_dwg
    sp_p    = sp.shape_params
    ft_meas = last_insole.ft_measurements

    sections = _section_geometry()
    xs8_x   = sections[-1][1].x

    # =========================================================================
    # Rows 1 & 2: T1/T2 — last outline (XY) + highwater profile (XZ)
    # =========================================================================

    # XY: last outline medial / lateral (T1/T2 Y-width loci)
    C0    = idw.A #idw.C  + App.Vector(-5, 0, 0)
    lC2   = idw.C  + App.Vector(0,  5 + 17, 0)
    lC3   = idw.C  + App.Vector(0, -5 - 17, 0)
    H1_t  = idw.H1 + App.Vector(0,  2, 0)
    H2_t  = idw.H2 + App.Vector(0, -2, 0)
    B1_t  = idw.B1 + App.Vector(1,  1, 0)
    B2_t  = idw.B2 + App.Vector(1, -1, 0)
    D_t   = idw.D  + App.Vector(2,  0, 0)
    med_K = App.Vector(idw.K); med_K.y *= 1.0#1.8
    lat_K = (idw.J2 + idw.H2 + App.Vector(0, 10, 0)) * 0.5; lat_K.y *= 0.95
    pinky = idw.B2 + (idw.J2 - idw.B2) * 0.5 + App.Vector(0, -8, 0)


    #sandbox A start exporting points for ploting
    _pt_list_medial =[C0, lC2, H1_t, med_K, idw.J1, B1_t, D_t]
    _name_list_medial =["C0", "lC2", "H1_t", "med_K", "idw.J1", "B1_t", "D_t"]
    k=0
    print("******************************************************************************")
    for p in _pt_list_medial:
        hf.p_vec(p,f"{_name_list_medial[k]}")
        k+=1
    #sandbox A stop

    bc_medial_last_outline = Part.BSplineCurve()
    bc_medial_last_outline.buildFromPoles(
        [C0, lC2, H1_t, med_K, idw.J1, B1_t, D_t], False, 2, False)

    bc_lateral_last_outline = Part.BSplineCurve()
    bc_lateral_last_outline.buildFromPoles(
        [D_t, B2_t, pinky, idw.J2, lat_K, H2_t, lC3, C0], False, 2, False)

    # XZ: highwater medial / lateral (T1/T2 Z-height loci)
    Pa  = pd.K
    Pb  = pd.J1 + (pd.H1 - pd.J1) * 2.0 / 3.0
    toe = pd.B1 + (pd.B2 - pd.B1) * 2.0 / 3.0

    medial_highwater_bc = Part.BSplineCurve()
    medial_highwater_bc.buildFromPoles([
        pd.H2,
        pd.H2 + App.Vector(60, -10, 0),
        Pa + (Pb - Pa) * sp_p.hw_med_pct_instep,
        pd.J + (pd.J1 - pd.J) * sp_p.hw_med_pct_joint,
        toe,
    ], False, 3, False)

    lateral_highwater_bc = Part.BSplineCurve()
    lateral_highwater_bc.buildFromPoles([
        pd.H2,
        pd.H2 + App.Vector(60, -10, 0),
        Pa + (Pb - Pa) * sp_p.hw_lat_pct_instep,
        pd.J + (pd.J1 - pd.J) * sp_p.hw_lat_pct_joint,
        toe,
    ], False, 3, False)

    # =========================================================================
    # Row 3: C — profile top (XZ)
    # =========================================================================

    # XZ: profile top curve (C Z-height locus, heel-to-crown)
    top_bc = Part.BSplineCurve()
    top_bc.buildFromPoles([pd.E, pd.C5E_intercept, pd.C5], False, 2, False)

    # =========================================================================
    # Rows 4 & 5: H1/H2 — insole outline (XY) + profile bottom (XZ)
    # =========================================================================

    # XY: insole outline medial / lateral (H1/H2 Y-width loci)
    extra_K = (idw.J2 + idw.H2 + App.Vector(0, 20, 0)) * 0.5
    K2      = idw.K + App.Vector(0, -5, 0)
    iC2     = idw.C + App.Vector(5,  5 + 15, 0)
    iC3     = idw.C + App.Vector(5, -5 - 15, 0)

    insole_bc_medial = Part.BSplineCurve()
    insole_bc_medial.buildFromPoles(
        [idw.C, iC2, idw.H1, K2, idw.J1, idw.B1, idw.D], False, 2, False)

    insole_bc_lateral = Part.BSplineCurve()
    insole_bc_lateral.buildFromPoles(
        [idw.D, idw.B2, idw.J2, extra_K, idw.H2, iC3, idw.C], False, 2, False)

    # full combined insole outline (xs_0/xs_1/xs_3 look up Y-width here)
    _outline_bc = Part.BSplineCurve()
    _outline_bc.buildFromPoles(
        [idw.C, iC2, idw.H1, K2, idw.J1, idw.B1, idw.D,
         idw.B2, idw.J2, extra_K, idw.H2, iC3, idw.C], False, 2, False)
    last_insole.outline_bc = _outline_bc

    # XZ: profile bottom + front (H1/H2 Z-height and HC intersection source)
    bottom_bc = Part.BSplineCurve()
    bottom_bc.buildFromPoles(
        [pd.H, pd.K1, pd.K, pd.J + App.Vector(0, -10, 0), pd.B1],
        False, 2, True)

    front_bc = Part.BSplineCurve()
    front_bc.buildFromPoles(
        [pd.B1, pd.B2 + App.Vector(5, 5, 0), pd.J1, pd.H1, pd.E],
        False, 2, False)

    front_top_bc = Part.BSplineCurve()
    front_top_bc.buildFromPoles(
        [pd.B1, pd.B2 + App.Vector(5, 5, 0),
         pd.J1 + App.Vector(0, -10, 0), pd.H1, pd.E,
         pd.E, pd.C5E_intercept, pd.C5E_intercept, pd.C5],
        False, 2, False)

    # =========================================================================
    # Rows 6 & 7: C1/C2 — crown shoulder (XY + XZ)
    # =========================================================================

    # XY: crown shoulder insole medial / lateral (C1/C2 Y-width loci)
    cosd  = math.cos(37.0 * math.pi / 180.0)
    _ic_x = ft_meas.heel * 0.9 / 2 * cosd - 10

    _cf = sp_p.insole_crown_med_cf
    C1_insole_medial = Part.BSplineCurve()
    C1_insole_medial.buildFromPoles([
        App.Vector(idw.C.x,        0,               0),
        App.Vector(iC2.x,          12.5,            0),
        App.Vector(idw.H1.x,       12.5,            0),
        App.Vector(_ic_x,          12.5,            0),
        App.Vector(idw.J1.x - 20,  idw.J1.y * _cf, 0),
        App.Vector(idw.J1.x + 10,  idw.J1.y * _cf, 0),
        App.Vector(idw.B1.x,       idw.B1.y * _cf, 0),
        App.Vector(idw.D.x,        0,               0),
    ], False, 2, False)

    _cf = sp_p.insole_crown_lat_cf
    C2_insole_lateral = Part.BSplineCurve()
    C2_insole_lateral.buildFromPoles([
        App.Vector(idw.D.x,        0,               0),
        App.Vector(idw.B2.x,       idw.B2.y * _cf, 0),
        App.Vector(idw.J2.x + 10,  idw.J2.y * _cf, 0),
        App.Vector(idw.J2.x - 10,  idw.J2.y * _cf, 0),
        App.Vector(_ic_x,          -12.5,           0),
        App.Vector(idw.H2.x,       -12.5,           0),
        App.Vector(iC3.x,          -12.5,           0),
        App.Vector(idw.C.x,        0,               0),
    ], False, 2, False)

    # XZ: crown shoulder profile medial / lateral (C1/C2 Z-height loci)
    _Pa  = pd.K
    _Pb  = pd.J1 + (pd.H1 - pd.J1) * 2.0 / 3.0
    _toe = pd.B1 + (pd.B2 - pd.B1) * 2.0 / 3.0

    C1_profile_bc = Part.BSplineCurve()
    C1_profile_bc.buildFromPoles([
        _toe,
        pd.J + (pd.J1 - pd.J) * sp_p.crown_med_pct_joint,
        _Pa  + (_Pb  - _Pa)   * sp_p.crown_med_pct_instep,
        pd.E, pd.E, pd.C5,
    ], False, 2, False)

    C2_profile_bc = Part.BSplineCurve()
    C2_profile_bc.buildFromPoles([
        _toe,
        pd.J + (pd.J1 - pd.J) * sp_p.crown_lat_pct_joint,
        _Pa  + (_Pb  - _Pa)   * sp_p.crown_lat_pct_instep,
        pd.E, pd.E, pd.C5,
    ], False, 2, False)

    # =========================================================================
    # Row 8: Heel — heel profile (XZ)
    # =========================================================================

    # XZ: heel curve (spans C5 → H2 → H, closes the profile outline)
    heel_bc = Part.BSplineCurve()
    heel_bc.buildFromPoles(
        [pd.C5, pd.H2 + App.Vector(-5, 0, 0), pd.H], False, 2, True)

    # =========================================================================
    # Back-assign to profile_dwg / insole_dwg for xs_*.py compatibility
    # =========================================================================
    pd.heel_bc              = heel_bc
    pd.bottom_bc            = bottom_bc
    pd.front_bc             = front_bc
    pd.front_top_bc         = front_top_bc
    pd.top_bc               = top_bc
    pd.medial_highwater_bc  = medial_highwater_bc
    pd.lateral_highwater_bc = lateral_highwater_bc
    pd.C1_profile_bc        = C1_profile_bc
    pd.C2_profile_bc        = C2_profile_bc
    idw.insole_bc_medial        = insole_bc_medial
    idw.insole_bc_lateral       = insole_bc_lateral
    idw.C1_insole_medial        = C1_insole_medial
    idw.C2_insole_lateral       = C2_insole_lateral
    idw.bc_medial_last_outline  = bc_medial_last_outline
    idw.bc_lateral_last_outline = bc_lateral_last_outline

    # =========================================================================
    # Display 3D compounds
    # =========================================================================
    _show_compound([
        _bc_to_3d(heel_bc).toShape(),
        _bc_to_3d(bottom_bc).toShape(),
        _bc_to_3d(front_bc).toShape(),
        _bc_to_3d(top_bc).toShape(),
        _bc_to_3d(medial_highwater_bc).toShape(),
        _bc_to_3d(lateral_highwater_bc).toShape(),
        _bc_to_3d(C1_profile_bc).toShape(),
        _bc_to_3d(C2_profile_bc).toShape(),
    ], "ProfileCurves3D")

    _show_compound([
        insole_bc_medial.toShape(),
        insole_bc_lateral.toShape(),
        C1_insole_medial.toShape(),
        C2_insole_lateral.toShape(),
        bc_medial_last_outline.toShape(),
        bc_lateral_last_outline.toShape(),
    ], "InsoleCurves3D")

    # =========================================================================
    # Sample loci, apply overrides, build interpolating BSplines
    # =========================================================================
    bc_hw_med    = _bc_to_3d(medial_highwater_bc)
    bc_hw_lat    = _bc_to_3d(lateral_highwater_bc)
    bc_cr_med_3d = _build_crown_3d(C1_profile_bc, C1_insole_medial,  xs8_x)
    bc_cr_lat_3d = _build_crown_3d(C2_profile_bc, C2_insole_lateral, xs8_x)

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

    medial_hw_locus     = Part.BSplineCurve(); medial_hw_locus.interpolate(T1_pts)
    lateral_hw_locus    = Part.BSplineCurve(); lateral_hw_locus.interpolate(T2_pts)
    medial_crown_locus  = Part.BSplineCurve(); medial_crown_locus.interpolate(C1_pts)
    lateral_crown_locus = Part.BSplineCurve(); lateral_crown_locus.interpolate(C2_pts)

    _show_compound([
        medial_hw_locus.toShape(), lateral_hw_locus.toShape(),
        medial_crown_locus.toShape(), lateral_crown_locus.toShape(),
    ], "ControlCurveLoci")


def main():
    build()
    print("control_curves main")
if __name__ == "__main__":
    main()
