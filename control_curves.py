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
# construction lines, and point-identifying circles.
#
# The last takes shape bottom-up:
#   insole outline -> last outline → profile bottom/top → highwaters and crowns
#
# After build(), curves are back-assigned to profile_dwg / insole_dwg so that
# xs_*.py files need no changes.
#
"""

                                                                              Control Curve (CC)
           Input Curve       +      Input Curve            =    3d Output Control Curve*[1]                
+----------------------------+-----------------------------+--------------------------+   -
|       xy plane curves     ,| xz plane curves,            |   Control Curve          |
+----------------------------+-----------------------------+--------------------------+
|1      last outline medial ,| profile highwater medial ,  |    T1  control curve     |
|2      last outline lateral,| profile highwater lateral,  |    T2  control curve     |
|3      insole medial       ,| profile bottom           ,  |    H1  control curve     |
|4      insole lateral      ,| profile bottom           ,  |    H2  control curve     |
|5      xz-plane            ,| profile top-curve        ,  |    C   control curve     |
|6      xy plane C1         ,| profile curve C1         ,  |    C1  control curve     |
|7      xy plane C2         ,| profile curve C2         ,  |    C2  control curve     |
|8      heel curve          ,| xz-plane                 ,  |    Pts H,H2,C5           |
+----------------------------+-----------------------------+--------------------------+
# used:   :!column -t -s, --output-separator ", "    , and DrawIt
*[1] These are proposed names for exisitng curve names.


"""
# Profile curves  (XZ plane -> 3D via sketch_profile.Placement):
#   (define bc - 'B'spline'C'urve)
#   bottom_bc, heel_bc, front_top_bc, top_bc  — profile outline
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
# Rows 1 & 2: H1/H2 — insole outline (XY) + profile bottom (XZ)
insole_bc_medial        = None
insole_bc_lateral       = None
bottom_bc               = None
# Rows 3 & 4: T1/T2 — last outline (XY) + highwater (XZ)
bc_medial_last_outline  = None
bc_lateral_last_outline = None
medial_highwater_bc     = None
lateral_highwater_bc    = None
# Row 5: C — profile top (XZ)
front_top_bc            = None # and x-z plane
bc_C_locus              = None  # 2D profile: C crown locus heel→toe (C5→E→J1→B2)
center_crown_locus      = None  # 3D interpolating locus for HC per section

# Rows 6 & 7: C1/C2 — crown shoulder (XY + XZ)
C1_insole_medial        = None
C2_insole_lateral       = None
C1_profile_bc           = None
C2_profile_bc           = None
# Row 8: Heel (XZ)
heel_bc                 = None # with x-z plane
# Composite 3D loci
medial_hw_locus         = None
lateral_hw_locus        = None
medial_crown_locus      = None
lateral_crown_locus     = None
# missing loci: front_top_locus , bottom_locus, heel_bc_locus

top_bc                  = None   # Redundant because of front_top_bc

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

# All local-coordinate profile curves must be transformed to xz plane, 
#bottom_bc,medial_highwater_bc,lateral_highwater_bc,front_top_bc,heel_bc (5 total)
def _bc_to_3d(bc_2d):
    """Convert profile sketch BSpline (local XY) to global 3D via sketch placement's Rotation only."""
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


# All section intersections should be in xs_base
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
    global top_bc                                                         #top_bc should be extinct, replaced by front_top_bc 
    global insole_bc_medial, insole_bc_lateral, bottom_bc, front_top_bc, bc_C_locus
    global C1_insole_medial, C2_insole_lateral, C1_profile_bc, C2_profile_bc
    global heel_bc
    global medial_hw_locus, lateral_hw_locus, center_crown_locus, medial_crown_locus, lateral_crown_locus

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
    A0    = idw.A #idw.C  + App.Vector(-5, 0, 0)
    #lC2   = idw.C  + App.Vector(0,  5 + 17, 0)
    #lC3   = idw.C  + App.Vector(0, -5 - 17, 0)
    lC2   = idw.A  + App.Vector(0,  5 + 17, 0)
    lC3   = idw.A  + App.Vector(0, -5 - 17, 0)
    H1_t  = idw.H1 + App.Vector(0,  2, 0)
    H2_t  = idw.H2 + App.Vector(0, -2, 0)
    B1_t  = idw.B1 + App.Vector(1,  1, 0)
    B2_t  = idw.B2 + App.Vector(1, -1, 0)
    D_t   = idw.D  + App.Vector(2,  0, 0)
    om_med_K = App.Vector(idw.K); om_med_K.y =30 #*= 2.0#1.8
    lat_K = (idw.J2 + idw.H2 + App.Vector(0, 10, 0)) * 0.5; lat_K.y *= 0.95
    pinky = idw.B2 + (idw.J2 - idw.B2) * 0.5 + App.Vector(0, -8, 0)


    bc_medial_last_outline = Part.BSplineCurve()
    bc_medial_last_outline.buildFromPoles(
        [A0, lC2, H1_t, om_med_K, idw.J1, B1_t, D_t], False, 2, False)

    #sandbox 1A start
    #Row 1 input curve. Draw an overlay of poles used for the last outline medial side
    #These bspline curve poles are edited by changing there positions above
    if Draw_Sketch_Overlay_of_Medial_Last_Outline:=False:
        sketch_name = "sketch_insole_overlay"
        doc,sketch_io = hf.Doc_Sketch(last_insole.doc,sketch_name)
        _pt_list=[A0, lC2, H1_t, om_med_K, idw.J1, B1_t, D_t]
        for p in _pt_list:
            sketch_io.addGeometry(Part.Circle(p,hf.nZ,2.0))
        _name_list=["A0", "lC2", "H1_t", "med_K", "idw.J1", "B1_t", "D_t"]
        k=0
        print("**********Last Outline Medial Control Points**********************************")
        for p in _pt_list:
            hf.p_vec(p,f"{_name_list[k]}")
            k+=1
    #sandbox 1A stop


    # XZ: highwater medial / lateral (T1/T2 Z-height loci)
    Pa  = pd.K
    Pb  = pd.J1 + (pd.H1 - pd.J1) * 2.0 / 3.0
    toe = pd.B1 + (pd.B2 - pd.B1) * 2.0 / 3.0



    medial_highwater_bc = Part.BSplineCurve()
    medial_highwater_pole_list =[
        pd.H2,
        pd.H2 + App.Vector(60, -10, 0),
        Pa + (Pb - Pa) * sp_p.hw_med_pct_instep,
        pd.J + (pd.J1 - pd.J) * sp_p.hw_med_pct_joint,
        toe]
    medial_highwater_bc.buildFromPoles(medial_highwater_pole_list, False, 3, False)
    #sandbox 1B start
    #Row 1 Input curve 
    if Draw_Sketch_Overlay_Highwater_Medial:=False:
        sketch_name = "sketch_profile_overlay"
        doc,sketch_po = hf.Doc_Sketch(last_insole.doc,sketch_name)
        _pt_list = medial_highwater_pole_list
        for p in _pt_list:
            sketch_po.addGeometry(Part.Circle(p,hf.nZ,2.0))
        _name_list = ["pd.H2"," pd.H2 + App.Vector(60, -10, 0)", "Pa + (Pb - Pa) * sp_p.hw_med_pct_instep",
        "pd.J + (pd.J1 - pd.J) * sp_p.hw_med_pct_joint","toe"]
        k=0
        print("**********Medial Highwater Control Points*************************************")
        for p in _pt_list:
            hf.p_vec(p,f"{_name_list[k]}")
            k+=1
        sketch_po.addGeometry(medial_highwater_bc)
        sketch_po.Placement = last_profile.sketch_profile.Placement
    #sandbox 1B stop




    bc_lateral_last_outline = Part.BSplineCurve()
    bc_lateral_last_outline.buildFromPoles(
        [D_t, B2_t, pinky, idw.J2, lat_K, H2_t, lC3, A0], False, 2, False)

    #sandbox 2A start
    #Row 2 Input curve 
    if Draw_Sketch_Overlay_Lateral_Last_Outline:=False:
        sketch_name = "sketch_insole_overlay"
        doc,sketch_io = hf.Doc_Sketch(last_insole.doc,sketch_name)
        _pt_list =  [D_t, B2_t, pinky, idw.J2, lat_K, H2_t, lC3, A0]
        for p in _pt_list:
            sketch_io.addGeometry(Part.Circle(p,hf.nZ,2.0))
        _name_list = ["D_t", "B2_t", "pinky", "idw.J2", "lat_K", "H2_t", "lC3", "A0"]
        k=0
        print("**********Lateral Last Outline Control Points*************************************")
        for p in _pt_list:
            hf.p_vec(p,f"{_name_list[k]}")
            k+=1
        sketch_io.addGeometry(bc_lateral_last_outline)
    #sandbox 2A stop

    lateral_highwater_bc = Part.BSplineCurve()
    lateral_highwater_bc.buildFromPoles([
        pd.H2,
        pd.H2 + App.Vector(60, -10, 0),
        Pa + (Pb - Pa) * sp_p.hw_lat_pct_instep,
        pd.J + (pd.J1 - pd.J) * sp_p.hw_lat_pct_joint,
        toe,
    ], False, 3, False)
    #sandbox 2B start
    #Row 2 Input curve
    if Draw_Sketch_Overlay_Lateral_Highwater:=False:
        sketch_name = "sketch_profile_overlay"
        doc,sketch_po = hf.Doc_Sketch(last_insole.doc,sketch_name)
        _pt_list = [pd.H2, pd.H2 + App.Vector(60, -10, 0), Pa + (Pb - Pa) * sp_p.hw_lat_pct_instep,
        pd.J + (pd.J1 - pd.J) * sp_p.hw_lat_pct_joint, toe]
        for p in _pt_list:
            sketch_po.addGeometry(Part.Circle(p,hf.nZ,2.0))
        _name_list =  ["pd.H2", "pd.H2 + App.Vector(60, -10, 0)", "Pa + (Pb - Pa) * sp_p.hw_lat_pct_instep",
        "pd.J + (pd.J1 - pd.J) * sp_p.hw_lat_pct_joint", "toe"]
        k=0
        print("**********Lateral Highwater Control Points*************************************")
        for p in _pt_list:
            hf.p_vec(p,f"{_name_list[k]}")
            k+=1
        sketch_po.addGeometry(lateral_highwater_bc)
        sketch_po.Placement = last_profile.sketch_profile.Placement
    #sandbox 2B stop

    # =========================================================================
    # Row 5: C — profile top (XZ)
    # =========================================================================

    # XZ: profile top curve (C Z-height locus, heel-to-crown)
    top_bc = Part.BSplineCurve()
    top_bc.buildFromPoles([pd.E, pd.C5E_intercept, pd.C5], False, 2, False)

    # XZ: C crown locus — heel to toe, double pole at E for table-top crispness
    bc_C_locus = Part.BSplineCurve()
    bc_C_locus.buildFromPoles(
        [pd.C5, pd.C5E_intercept, pd.E, pd.E, pd.J1, pd.J1, pd.B2],
        False, 2, False)
    #sandbox 5A start
    #Row 5 Input curve. C crown locus poles in profile (XZ) plane.
    if Draw_Sketch_bc_C_locus:=False:
        sketch_name = "sketch_profile_overlay"
        doc, sketch_po = hf.Doc_Sketch(last_insole.doc, sketch_name)
        _pt_list = bc_C_locus.getPoles()
        for p in _pt_list:
            sketch_po.addGeometry(Part.Circle(p, hf.nZ, 2.0))
        _name_list = ["pd.C5", "pd.C5E_intercept", "pd.E", "pd.E", "pd.J1", "pd.J1", "pd.B2"]
        k = 0
        print("**********bc_C_locus Control Points*************************************")
        for p in _pt_list:
            hf.p_vec(p, f"{_name_list[k]}")
            k += 1
        sketch_po.addGeometry(bc_C_locus)
        sketch_po.Placement = last_profile.sketch_profile.Placement
    #sandbox 5A stop

    # =========================================================================
    # Rows 3 & 4: H1/H2 — insole outline (XY) + profile bottom (XZ)
    # =========================================================================

    # XY: insole outline medial / lateral (H1/H2 Y-width loci)
    extra_K = (idw.J2 + idw.H2 + App.Vector(0, 20, 0)) * 0.5
    K2      = idw.K + App.Vector(0, -5, 0)
    iC2     = idw.C + App.Vector(5,  5 + 15, 0)
    iC3     = idw.C + App.Vector(5, -5 - 15, 0)

    insole_bc_medial = Part.BSplineCurve()
    insole_bc_medial.buildFromPoles(
        [idw.C, iC2, idw.H1, K2, idw.J1, idw.B1, idw.D], False, 2, False)
    #sandbox 3B start
    #Row 3 Input curve. Insole medial outline poles (XY).
    if Draw_Sketch_insole_bc_medial:=False:
        sketch_name = "sketch_insole_overlay"
        doc, sketch_io = hf.Doc_Sketch(last_insole.doc, sketch_name)
        _pt_list = [idw.C, iC2, idw.H1, K2, idw.J1, idw.B1, idw.D]
        for p in _pt_list:
            sketch_io.addGeometry(Part.Circle(p, hf.nZ, 2.0))
        _name_list = ["idw.C", "iC2", "idw.H1", "K2", "idw.J1", "idw.B1", "idw.D"]
        k = 0
        print("**********insole_bc_medial Control Points*************************************")
        for p in _pt_list:
            hf.p_vec(p, f"{_name_list[k]}")
            k += 1
        sketch_io.addGeometry(insole_bc_medial)
    #sandbox 3B stop

    insole_bc_lateral = Part.BSplineCurve()
    insole_bc_lateral.buildFromPoles(
        [idw.D, idw.B2, idw.J2, extra_K, idw.H2, iC3, idw.C], False, 2, False)
    #sandbox 4A start
    #Row 4 Input curve. Insole lateral outline poles (XY).
    if Draw_Sketch_insole_bc_lateral:=False:
        sketch_name = "sketch_insole_overlay"
        doc, sketch_io = hf.Doc_Sketch(last_insole.doc, sketch_name)
        _pt_list = [idw.D, idw.B2, idw.J2, extra_K, idw.H2, iC3, idw.C]
        for p in _pt_list:
            sketch_io.addGeometry(Part.Circle(p, hf.nZ, 2.0))
        _name_list = ["idw.D", "idw.B2", "idw.J2", "extra_K", "idw.H2", "iC3", "idw.C"]
        k = 0
        print("**********insole_bc_lateral Control Points*************************************")
        for p in _pt_list:
            hf.p_vec(p, f"{_name_list[k]}")
            k += 1
        sketch_io.addGeometry(insole_bc_lateral)
    #sandbox 4A stop

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
    #sandbox 3A start
    #Row 3/4 Input curve. Profile bottom curve poles (XZ).
    if Draw_Sketch_bottom_bc:=False:
        sketch_name = "sketch_profile_overlay"
        doc, sketch_po = hf.Doc_Sketch(last_insole.doc, sketch_name)
        _pt_list = [pd.H, pd.K1, pd.K, pd.J + App.Vector(0, -10, 0), pd.B1]
        for p in _pt_list:
            sketch_po.addGeometry(Part.Circle(p, hf.nZ, 2.0))
        _name_list = ["pd.H", "pd.K1", "pd.K", "pd.J+(0,-10,0)", "pd.B1"]
        k = 0
        print("**********bottom_bc Control Points*************************************")
        for p in _pt_list:
            hf.p_vec(p, f"{_name_list[k]}")
            k += 1
        sketch_po.addGeometry(bottom_bc)
        sketch_po.Placement = last_profile.sketch_profile.Placement
    #sandbox 3A stop

    front_top_bc = Part.BSplineCurve()
    front_top_bc.buildFromPoles(
        [pd.B1, pd.B2 + App.Vector(-5, 0, 0),
         pd.J1, pd.H1, pd.E,
         pd.E, pd.C5E_intercept, pd.C5E_intercept, pd.C5],
        False, 2, False)
    #sandbox 5B start
    #Row 5 Input curve. Profile front+top curve poles (XZ).
    if Draw_Sketch_front_top_bc:=False:
        sketch_name = "sketch_profile_overlay"
        doc, sketch_po = hf.Doc_Sketch(last_insole.doc, sketch_name)
        _pt_list = [pd.B1, pd.B2 + App.Vector(-5, 0, 0), pd.J1, pd.H1, pd.E,
                    pd.E, pd.C5E_intercept, pd.C5E_intercept, pd.C5]
        for p in _pt_list:
            sketch_po.addGeometry(Part.Circle(p, hf.nZ, 2.0))
        _name_list = ["pd.B1", "pd.B2+(-5,0,0)", "pd.J1", "pd.H1", "pd.E",
                      "pd.E", "pd.C5E_intercept", "pd.C5E_intercept", "pd.C5"]
        k = 0
        print("**********front_top_bc Control Points*************************************")
        for p in _pt_list:
            hf.p_vec(p, f"{_name_list[k]}")
            k += 1
        sketch_po.addGeometry(front_top_bc)
        sketch_po.Placement = last_profile.sketch_profile.Placement
    #sandbox 5B stop

    # =========================================================================
    # Rows 6 & 7: C1/C2 — crown shoulder (XY + XZ)
    # =========================================================================

    # Tuning knobs — edit these directly; shape_params values are not used here.
    _crown_med_pct_joint   = 0.84   # C1 height at joint:   fraction of J→J1
    _crown_med_pct_instep  = 0.92   # C1 height at instep:  fraction of K→midpoint
    _crown_lat_pct_joint   = 0.72   # C2 height at joint:   fraction of J→J1
    _crown_lat_pct_instep  = 0.70   # C2 height at instep:  fraction of K→midpoint
    _crown_med_cf          = 0.70   # C1 Y-width: fraction of medial insole half-width
    _crown_lat_cf          = 0.50   # C2 Y-width: fraction of lateral insole half-width
    _toe_crown_fraction    = 0.90       # C1/C2 toe anchor: fraction of B1→B2 (raise toward 1.0 for more toe crown)

    # XY: crown shoulder insole medial / lateral (C1/C2 Y-width loci)
    cosd  = math.cos(37.0 * math.pi / 180.0)
    _ic_x = ft_meas.heel * 0.9 / 2 * cosd - 10

    C1_insole_medial = Part.BSplineCurve()
    C1_insole_medial_poles = [    App.Vector(idw.C.x,        0,                         0),
        App.Vector(iC2.x,          12.5,                      0),
        App.Vector(idw.H1.x,       12.5,                      0),
        App.Vector(_ic_x,          12.5,                      0),
        App.Vector(idw.J1.x - 20,  idw.J1.y * _crown_med_cf, 0),
        App.Vector(idw.J1.x + 10,  idw.J1.y * _crown_med_cf, 0),
        App.Vector(idw.B1.x,       idw.B1.y * _crown_med_cf, 0),
        App.Vector(idw.D.x,        0,                         0)]
    C1_insole_medial.buildFromPoles(C1_insole_medial_poles , False, 2, False)
    #sandbox 6A start
    #Row 2 Input curve 
    if Draw_Sketch_Overlay_insole_medial:=True:
        sketch_name = "sketch_insole_overlay"
        doc,sketch_io = hf.Doc_Sketch(last_insole.doc,sketch_name)
        _pt_list = C1_insole_medial_poles 
        for p in _pt_list:
            sketch_io.addGeometry(Part.Circle(p,hf.nZ,2.0))
        _name_list = C1_insole_medial_poles = ["App.Vector(idw.C.x,0,0)\n",
        "App.Vector(iC2.x,          12.5,0)",
        "App.Vector(idw.H1.x,       12.5,0)",
        "App.Vector(_ic_x,          12.5,0)",
        "App.Vector(idw.J1.x - 20,  idw.J1.y * _crown_med_cf, 0)",
        "App.Vector(idw.J1.x + 10,  idw.J1.y * _crown_med_cf, 0)",
        "App.Vector(idw.B1.x,       idw.B1.y * _crown_med_cf, 0)",
        "App.Vector(idw.D.x,        0,0)"]

        k=0
        print("**********Lateral Last Outline Control Points*************************************")
        for p in _pt_list:
            hf.p_vec(p,f"{_name_list[k]}")
            k+=1
        sketch_io.addGeometry(bc_lateral_last_outline)
    #sandbox 6A stop

    C2_insole_lateral = Part.BSplineCurve()
    C2_insole_lateral.buildFromPoles([
        App.Vector(idw.D.x,        0,                         0),
        App.Vector(idw.B2.x,       idw.B2.y * _crown_lat_cf, 0),
        App.Vector(idw.J2.x + 10,  idw.J2.y * _crown_lat_cf, 0),
        App.Vector(idw.J2.x - 10,  idw.J2.y * _crown_lat_cf, 0),
        App.Vector(_ic_x,          -12.5,                     0),
        App.Vector(idw.H2.x,       -12.5,                     0),
        App.Vector(iC3.x,          -12.5,                     0),
        App.Vector(idw.C.x,        0,                         0),
    ], False, 2, False)
    #sandbox 7A start
    #Row 7 Input curve. C2 insole lateral crown poles (XY).
    if Draw_Sketch_C2_insole_lateral:=False:
        sketch_name = "sketch_insole_overlay"
        doc, sketch_io = hf.Doc_Sketch(last_insole.doc, sketch_name)
        _pt_list = C2_insole_lateral.getPoles()
        for p in _pt_list:
            sketch_io.addGeometry(Part.Circle(p, hf.nZ, 2.0))
        _name_list = ["D.x/0", "B2.x/lat*cf", "J2.x+10/lat*cf", "J2.x-10/lat*cf",
                      "_ic_x/-12.5", "H2.x/-12.5", "iC3.x/-12.5", "C.x/0"]
        k = 0
        print("**********C2_insole_lateral Control Points*************************************")
        for p in _pt_list:
            hf.p_vec(p, f"{_name_list[k]}")
            k += 1
        sketch_io.addGeometry(C2_insole_lateral)
    #sandbox 7A stop

    # XZ: crown shoulder profile medial / lateral (C1/C2 Z-height loci)
    _Pa  = pd.K
    _Pb  = pd.J1 + (pd.H1 - pd.J1) * 2.0 / 3.0
    _toe = pd.B1 + (pd.B2 - pd.B1) * _toe_crown_fraction

    C1_profile_bc = Part.BSplineCurve()
    C1_profile_bc.buildFromPoles([
        _toe,
        pd.J + (pd.J1 - pd.J) * _crown_med_pct_joint,
        _Pa  + (_Pb  - _Pa)   * _crown_med_pct_instep,
        pd.E, pd.E, pd.C5,
    ], False, 2, False)
    #sandbox 6B start
    #Row 6 Input curve. C1 medial crown shoulder height profile poles (XZ).
    if Draw_Sketch_C1_profile_bc:=False:
        sketch_name = "sketch_profile_overlay"
        doc, sketch_po = hf.Doc_Sketch(last_insole.doc, sketch_name)
        _pt_list = C1_profile_bc.getPoles()
        for p in _pt_list:
            sketch_po.addGeometry(Part.Circle(p, hf.nZ, 2.0))
        _name_list = ["_toe", "J+med_pct_joint", "_Pa+med_pct_instep", "pd.E", "pd.E", "pd.C5"]
        k = 0
        print("**********C1_profile_bc Control Points*************************************")
        for p in _pt_list:
            hf.p_vec(p, f"{_name_list[k]}")
            k += 1
        sketch_po.addGeometry(C1_profile_bc)
        sketch_po.Placement = last_profile.sketch_profile.Placement
    #sandbox 6B stop

    C2_profile_bc = Part.BSplineCurve()
    C2_profile_bc.buildFromPoles([
        _toe,
        pd.J + (pd.J1 - pd.J) * _crown_lat_pct_joint,
        _Pa  + (_Pb  - _Pa)   * _crown_lat_pct_instep,
        pd.E, pd.E, pd.C5,
    ], False, 2, False)
    #sandbox 7B start
    #Row 7 Input curve. C2 lateral crown shoulder height profile poles (XZ).
    if Draw_Sketch_C2_profile_bc:=False:
        sketch_name = "sketch_profile_overlay"
        doc, sketch_po = hf.Doc_Sketch(last_insole.doc, sketch_name)
        _pt_list = C2_profile_bc.getPoles()
        for p in _pt_list:
            sketch_po.addGeometry(Part.Circle(p, hf.nZ, 2.0))
        _name_list = ["_toe", "J+lat_pct_joint", "_Pa+lat_pct_instep", "pd.E", "pd.E", "pd.C5"]
        k = 0
        print("**********C2_profile_bc Control Points*************************************")
        for p in _pt_list:
            hf.p_vec(p, f"{_name_list[k]}")
            k += 1
        sketch_po.addGeometry(C2_profile_bc)
        sketch_po.Placement = last_profile.sketch_profile.Placement
    #sandbox 7B stop

    # =========================================================================
    # Row 8: Heel — heel profile (XZ)
    # =========================================================================

    # XZ: heel curve (spans C5 → H2 → H, closes the profile outline)
    heel_bc = Part.BSplineCurve()
    heel_bc.buildFromPoles(
        [pd.C5, pd.H2 + App.Vector(-5, 0, 0), pd.H], False, 2, True)
    #sandbox 8A start
    #Row 8 Input curve. Heel profile poles (XZ).
    if Draw_Sketch_heel_bc:=False:
        sketch_name = "sketch_profile_overlay"
        doc, sketch_po = hf.Doc_Sketch(last_insole.doc, sketch_name)
        _pt_list = heel_bc.getPoles()
        for p in _pt_list:
            sketch_po.addGeometry(Part.Circle(p, hf.nZ, 2.0))
        _name_list = ["pd.C5", "H2+(-5,0,0)", "pd.H"]
        k = 0
        print("**********heel_bc Control Points*************************************")
        for p in _pt_list:
            hf.p_vec(p, f"{_name_list[k]}")
            k += 1
        sketch_po.addGeometry(heel_bc)
        sketch_po.Placement = last_profile.sketch_profile.Placement
    #sandbox 8A stop

    # =========================================================================
    # Back-assign to profile_dwg / insole_dwg for xs_*.py compatibility
    # =========================================================================
    pd.heel_bc              = heel_bc
    pd.bottom_bc            = bottom_bc
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
        _bc_to_3d(front_top_bc).toShape(),
        _bc_to_3d(bc_C_locus).toShape(),
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
    bc_cr_cen_3d = _bc_to_3d(bc_C_locus)
    bc_cr_med_3d = _build_crown_3d(C1_profile_bc, C1_insole_medial,  xs8_x)
    bc_cr_lat_3d = _build_crown_3d(C2_profile_bc, C2_insole_lateral, xs8_x)

    T1_pts, T2_pts, C_pts, C1_pts, C2_pts = [], [], [], [], []

    print("\n=== Control loci heights mm (above H, local_up) ===")
    print(f"  {'Section':<8}  {'HT1':>7}  {'HT2':>7}  {'HC':>7}  {'HC1':>7}  {'HC2':>7}")

    for name, origin, normal, local_up in sections:
        ovr = _OVERRIDES.get(name, {})

        HT1_0, g_T1 = _intersect_height(bc_hw_med,    origin, normal, local_up)
        HT2_0, g_T2 = _intersect_height(bc_hw_lat,    origin, normal, local_up)
        HC_0,  g_C_ = _intersect_height(bc_cr_cen_3d, origin, normal, local_up)
        HC1_0, g_C1 = _intersect_height(bc_cr_med_3d, origin, normal, local_up)
        HC2_0, g_C2 = _intersect_height(bc_cr_lat_3d, origin, normal, local_up)

        def _resolve(val, default):
            if val is None: return default or 0.0
            return val

        HT1 = _resolve(ovr.get('HT1', HT1_0), HT1_0)
        HT2 = _resolve(ovr.get('HT2', HT2_0), HT2_0)
        HC  = _resolve(ovr.get('HC',  HC_0),  HC_0)
        HC1 = min(_resolve(ovr.get('HC1', HC1_0), HC1_0), HC)
        HC2 = min(_resolve(ovr.get('HC2', HC2_0), HC2_0), HC)

        flag = '*' if name in _OVERRIDES else ' '
        print(f" {flag}{name:<7}  {HT1:>7.2f}  {HT2:>7.2f}  {HC:>7.2f}  {HC1:>7.2f}  {HC2:>7.2f}")

        T1_pts.append(_adjust_height(g_T1, origin, local_up, HT1) if g_T1 else origin)
        T2_pts.append(_adjust_height(g_T2, origin, local_up, HT2) if g_T2 else origin)
        C_pts.append( _adjust_height(g_C_, origin, local_up, HC)  if g_C_ else origin)
        C1_pts.append(_adjust_height(g_C1, origin, local_up, HC1) if g_C1 else origin)
        C2_pts.append(_adjust_height(g_C2, origin, local_up, HC2) if g_C2 else origin)

    print("  * = override active\n")

    medial_hw_locus     = Part.BSplineCurve(); medial_hw_locus.interpolate(T1_pts)     # nyet
    lateral_hw_locus    = Part.BSplineCurve(); lateral_hw_locus.interpolate(T2_pts)
    center_crown_locus  = Part.BSplineCurve(); center_crown_locus.interpolate(C_pts)
    medial_crown_locus  = Part.BSplineCurve(); medial_crown_locus.interpolate(C1_pts)
    lateral_crown_locus = Part.BSplineCurve(); lateral_crown_locus.interpolate(C2_pts)

    _show_compound([
        medial_hw_locus.toShape(), lateral_hw_locus.toShape(),
        center_crown_locus.toShape(),
        medial_crown_locus.toShape(), lateral_crown_locus.toShape(),
    ], "ControlCurveLoci")


def main(): 
    build()
    print("control_curves main")
if __name__ == "__main__":
    main()
