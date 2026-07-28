import math
import inspect
import FreeCAD as App
import Part
import helper_funcs as hf
import last_insole
import last_profile
import importlib
#import shape_params as sp
import text_overlay
importlib.reload(hf)
V = App.Vector

print(f"Line({inspect.currentframe().f_lineno})\n" f"File:({__file__})")
sketch_io_name = "sketch_insole_overlay"
doc, sketch_io = hf.Doc_Sketch(last_insole.doc, sketch_io_name)
sketch_po_name = "sketch_profile_overlay"
doc, sketch_po = hf.Doc_Sketch(last_insole.doc, sketch_po_name)

# Pipeline: last_insole -> last_profile -> control_curves -> xs_base -> xs_0...xs_8 -> uv_0 -> girth_checks
#                                                ^               ^                                   |
#                                                |               |                                   |
#                                                +---------------+-----------------------------<-----+
# All BSpline (continuous) geometry is built here.
# last_insole and last_profile supply only discrete geometry: points, lengths,
# construction lines, and point-identifying circles.
#
# The last takes shape ebottom-up:
#   last insole -> profile top → profile bottom -> plast outline → ighwaters -> crowns
#
# Each xs-plane point is located by intersecting one insole curve and one profile curve:
#
#   insole curve   + profile curve  →  xs-plane point
#   (x-axis)         C_profile          C
#   H1_insole        H_profile          H1
#   H2_insole        H_profile          H2
#   T1_insole        T1_profile         T1
#   T2_insole        T2_profile         T2
#   C1_insole        C1_profile         C1
#   C2_insole        C2_profile         C2
#   Heel_profile     (xz plane)         H, H2, C5
#
# Profile curves  (XZ plane → 3D via sketch_profile.Placement):
#   H_profile, Heel_profile                — profile outline
#   T1_profile, T2_profile                 — T1/T2 height loci
#   C_profile                              — C crown/top front, heel-to-toe poles
#   C1_profile, C2_profile                 — crown shoulder height loci
#
# Insole curves  (global XY, Z=0):
#   H1_insole, H2_insole   — insole outline
#   T1_insole, T2_insole   — last outline (T1/T2 width loci)
#   C1_insole, C2_insole   — crown shoulder width loci
#
# HOW TO TUNE per section:  [Ad hoc tuning method untractable and kills curve continuity]
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
# Insole curves (XY)
H1_insole = None
H2_insole = None
T1_insole = None
T2_insole = None
C1_insole = None
C2_insole = None
# Profile curves (XZ)
H_profile    = None
T1_profile   = None
T2_profile   = None
C_profile    = None
C1_profile   = None
C2_profile   = None
Heel_profile = None

xs_heights = {
}  # keyed 0–8; {'g_T1','g_T2','HT1','HT2','HC','HC1','HC2'} per section

insole_vecs = None   # SimpleNamespace of insole drawing vectors; populated in build()
profile_vecs = None  # SimpleNamespace of profile vectors in world 3D; populated in build()
# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


# All local-coordinate profile curves must be transformed to xz plane,
#H_profile,T1_profile,T2_profile,C_profile,Heel_profile (5 total)
def _bc_to_3d(bc_2d):
    """Bake sketch_profile's Placement into a copy of bc_2d's poles (local XZ -> global 3D)."""
    bc = bc_2d.copy()
    bc.transform(last_profile.sketch_profile.Placement.toMatrix())
    return bc


# ???
def _intersect_height(bc_3d, origin, normal, local_up):
    """Intersect bc_3d with plane; return (height_along_local_up, g_pt) or (None, None)."""
    try:
        g_pt = App.Vector(
            hf.get_bspline_plane_intersection_new(bc_3d, origin, normal)[0])
        return (g_pt - origin).dot(local_up), g_pt
    except Exception:
        print("Error in _intersect_height in control_curves.py")
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
            y = hf.get_bspline_plane_intersection_new(insole_crown_bc,
                                                      App.Vector(x, 0, 0),
                                                      hf.nX)[0].y
        except Exception:
            print("Error: build_crown_3d in control_curves.py")
            y = 0.0
        poles.append(p + App.Vector(0, y, 0))
    bc_out = Part.BSplineCurve()
    bc_out.buildFromPolesMultsKnots(poles, profile_bc_2d.getMultiplicities(),
                                    profile_bc_2d.getKnots(), False,
                                    profile_bc_2d.Degree)
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
    pd = last_profile.profile_dwg
    skp = last_profile.sketch_profile
    il = last_insole.insole_lens

    gvec_uHB = hf.xz_xy_place * (pd.B - pd.H).normalize()
    gvec_uHC5 = hf.xz_xy_place * (pd.C5 - pd.H).normalize()
    g_H = skp.Placement.multVec(pd.H)
    g_J = skp.Placement.multVec(pd.J)
    g_K = skp.Placement.multVec(pd.K)
    g_Kb = skp.Placement.multVec(pd.Kb)

    gvec_Kb_E = hf.xz_xy_place * (pd.E - pd.Kb)
    gvec_uKbE = gvec_Kb_E.normalize()
    lvec_I = pd.J1 + (pd.H1 - pd.J1) / 2.0
    gvec_K_I = (skp.Placement.multVec(lvec_I) - g_K).normalize()
    gvec_J1_J = hf.xz_xy_place * (pd.J1 - pd.J).normalize()
    gvec_uJB1 = hf.xz_xy_place * (pd.B1 - pd.J).normalize()
    gvec_uJB1y = App.Vector(-gvec_uJB1.z, 0, gvec_uJB1.x)
    g_X  = skp.Placement.multVec(pd.X)
    g_B1 = skp.Placement.multVec(pd.B1)
    jb1_len       = (g_X  - g_J).dot(gvec_uJB1)
    _d_jb1_total  = (g_B1 - g_J).dot(gvec_uJB1)

    n_uHB = gvec_uHB
    n_KbE = App.Vector(gvec_Kb_E.z, 0, -gvec_Kb_E.x)
    n_KI = App.Vector(gvec_K_I.z, 0, -gvec_K_I.x)
    n_J1J = App.Vector(gvec_J1_J.z, 0, -gvec_J1_J.x)
    n_JB1 = gvec_uJB1

    return [
        ('xs_0', g_H + gvec_uHB * (il.H1H2 / 4.0), n_uHB, gvec_uHC5),
        ('xs_1', g_H + gvec_uHB * il.AH, n_uHB, gvec_uHC5),
        ('xs_2', App.Vector(g_Kb), n_KbE, gvec_uKbE),
        ('xs_3', App.Vector(g_K), n_KI, gvec_K_I),
        ('xs_4', (g_K + g_J) * 0.5, n_KI, gvec_K_I),
        ('xs_5', App.Vector(g_J), n_J1J, gvec_J1_J),
        ('xs_6', g_J + gvec_uJB1 * (jb1_len / 3.0), n_JB1, gvec_uJB1y),
        ('xs_7', g_J + gvec_uJB1 * (jb1_len * 2.0 / 3.0), n_JB1, gvec_uJB1y),
        ('xs_8', g_J + gvec_uJB1 * jb1_len, n_JB1, gvec_uJB1y),
        ('xs_9', g_J + gvec_uJB1 * (_d_jb1_total - 10.0), n_JB1, gvec_uJB1y),
    ]


# ---------------------------------------------------------------------------
# Build — all BSpline geometry 
# ---------------------------------------------------------------------------


def build():
    global t_outline_bc
    global T1_insole, T2_insole
    global T1_profile, T2_profile
    global H1_insole, H2_insole, H_profile, C_profile
    global C1_insole, C2_insole, C1_profile, C2_profile
    global Heel_profile
    global xs_heights
    global insole_vecs, profile_vecs


    pd = last_profile.profile_dwg
    idw = last_insole.insole_dwg
    #sp_p    = sp.shape_params
    ft_meas = last_insole.ft_measurements

    import types
    _pl = last_profile.sketch_profile.Placement
    _g_H   = _pl.multVec(pd.H)
    _g_J   = _pl.multVec(pd.J)
    _g_C5  = _pl.multVec(pd.C5)
    _g_H2  = _pl.multVec(pd.H2)
    _g_J_insole = App.Vector(_g_J.x, _g_J.y, 0)
    _uJA = (idw.A - _g_J_insole).normalize()
    _h2_reach = hf.scalar_proj_a_onto_b(_g_H2, _g_H, _g_J)
    insole_vecs = types.SimpleNamespace(
        A=idw.A, B=idw.B, C=idw.C, D=idw.D,
        H1=idw.H1, H2=idw.H2, J1=idw.J1, J2=idw.J2, K=idw.K,
        B1=idw.B1, B2=idw.B2,
    )
    profile_vecs = types.SimpleNamespace(
        H=_g_H, J=_g_J, C5=_g_C5, H2=_g_H2,
        uHC5=(_g_C5 - _g_H).normalize(),
        uJH=(_g_H - _g_J).normalize(),
        A0=_g_J_insole + _uJA * _h2_reach,
    )
    sections = _section_geometry()
    xs8_x = sections[-1][1].x

    # =========================================================================
    # class C_H — Koleff's primary enclosing profile curves in the XZ plane: 
    # C_profile ("top of last" curve), H_profile ("bottom of last" curve), Heel
    # =========================================================================
    class C_H:
        global C_profile, H_profile, Heel_profile
        # XZ: profile top curve (C Z-height locus). Poles heel-to-toe (C5 -> B1)
        class _C_profile:
            p_Instep = pd.J1 + (pd.H1 - pd.J1)*.5 + V(5,9,0)
            pole_list = [
                pd.C5,
                pd.C5E_intercept,
                pd.C5E_intercept,
                pd.E,
                pd.E,
                pd.H1,
                p_Instep,
                pd.J1 + App.Vector(0, -10, 0),
                pd.B2 + App.Vector(5, 5, 0),
                pd.B1
            ]

        C_profile = Part.BSplineCurve()
        C_profile.buildFromPoles(_C_profile.pole_list, False, 2, False)
        sketch_po.addGeometry(C_profile)
        if Draw_Sketch_C_profile := False:
            text_overlay.control_curve_text(_C_profile.pole_list,hf.nY,5.0,sketch_po)
            print("**********C_profile Control Points*********************")
            for k, p in enumerate(_C_profile.pole_list):
                sketch_po.addGeometry(Part.Circle(p, hf.nZ, 2.0))
                hf.p_vec(p, f"{k}")

        # H_profile XZ plane
        class _H_profile:
            pole_list = [pd.H, pd.K1, pd.K, pd.J + App.Vector(0, -10, 0), pd.B1]

        H_profile = Part.BSplineCurve()
        H_profile.buildFromPoles(_H_profile.pole_list, False, 2, True)
        sketch_po.addGeometry(H_profile)
        if Draw_Sketch_H_profile := False:
            text_overlay.control_curve_text(_H_profile.pole_list,hf.nY,5.0,sketch_po)
            print("**********H_profile Control Points*********************")
            for k, p in enumerate(_H_profile.pole_list):
                sketch_po.addGeometry(Part.Circle(p, hf.nZ, 2.0))
                hf.p_vec(p, f"{k}")

        # =========================================================================
        # Heel_profile — in XZ plane
        # =========================================================================

        # XZ: heel curve (spans C5 → H2 → H, closes the profile outline)
        class _Heel_profile:
            pole_list = [pd.C5, pd.H2 + App.Vector(-5, 0, 0), pd.H]

        Heel_profile = Part.BSplineCurve()
        Heel_profile.buildFromPoles(_Heel_profile.pole_list, False, 2, True)
        sketch_po.addGeometry(Heel_profile)
        if Draw_Sketch_Heel_profile := False:
            text_overlay.control_curve_text(_Heel_profile.pole_list,hf.nY,5.0,sketch_po)
            print("**********Heel_profile Control Points******************")
            for k, p in enumerate(_Heel_profile.pole_list):
                sketch_po.addGeometry(Part.Circle(p, hf.nZ, 2.0))
                hf.p_vec(p, f"{k}")

    # =========================================================================
    # H1/H2 — insole outline (XY) + H_profile profile bottom (XZ)
    # =========================================================================

    # XY: insole outline medial / lateral (H1/H2 Y-width loci)
    class H1_H2:
        global H1_insole, H2_insole
        class _H1_insole:
            V = App.Vector
            C = idw.C
            C2 = idw.C + V(5, 5 + 15, 0)
            H1 = idw.H1 + V(0,5,0)
            K2 = idw.K + V(0, -10, 0)
            J1 = idw.J1 + V(-5,5,0)
            B1 = idw.B1 + V(10, 5, 0)
            D = idw.D
            pole_list = [C, C2, H1, K2, J1, B1, D, D]

        H1_insole = Part.BSplineCurve()
        H1_insole.buildFromPoles(_H1_insole.pole_list, False, 2, False)
        sketch_io.addGeometry(H1_insole)
        if Draw_Sketch_H1_insole := True:
            text_overlay.control_curve_text(_H1_insole.pole_list,hf.nY,5.0,sketch_io)
            print("**********H1_insole Control Points*********************")
            for k, p in enumerate(_H1_insole.pole_list):
                sketch_io.addGeometry(Part.Circle(p, hf.nZ, 2.0))
                hf.p_vec(p, f"{k}")

        class _H2_insole:
            extra_K = (idw.J2 + idw.H2 + App.Vector(0, 20, 0)) * 0.5
            iC3 = idw.C + App.Vector(5, -5 - 15, 0)
            pole_list = [idw.D, idw.D, idw.B2, idw.J2, extra_K, idw.H2, iC3, idw.C]

        H2_insole = Part.BSplineCurve()
        H2_insole.buildFromPoles(_H2_insole.pole_list, False, 2, False)
        sketch_io.addGeometry(H2_insole)
        if Draw_Sketch_H2_insole := False:
            print("**********H2_insole Control Points*********************")
            for k, p in enumerate(_H2_insole.pole_list):
                sketch_io.addGeometry(Part.Circle(p, hf.nZ, 2.0))
                hf.p_vec(p, f"{k}")

    # =========================================================================
    # class highwater — T1/T2 insole + profile loci
    # =========================================================================
    class highwater:
        global T1_insole, T2_insole, T1_profile, T2_profile
        # =========================================================================
        # T1_insole + T1_profile -> T1   
        # =========================================================================
        class _T1_insole:
            iv = insole_vecs
            pv = profile_vecs
            A0       = pv.A0
            C_sq      = pv.A0 + App.Vector(0, iv.H1.y*.75,0) 
            H1_t     = iv.H1 + App.Vector(0, 3, 0)
            om_med_K = App.Vector(iv.K)
            om_med_K.y = 30
            B1_t     = iv.B1 + App.Vector(28, 8, 0)  # TODO: review large offset
            D_t      = iv.D  + App.Vector(2, 0, 0)
            J1       = iv.J1 + App.Vector(0,iv.H1.y*.05,0)
            pole_list   = [A0, C_sq, H1_t, om_med_K, J1, B1_t, D_t]

        T1_insole = Part.BSplineCurve()
        T1_insole.buildFromPoles(_T1_insole.pole_list, False, 2, False)
        sketch_io.addGeometry(T1_insole)

        if Draw_Sketch_Overlay_of_T1_Last_Outline := False:
            print("**********Last Outline Medial Control Points***********")
            for k, p in enumerate(_T1_insole.pole_list):
                sketch_io.addGeometry(Part.Circle(p, hf.nZ, 2.0))
                hf.p_vec(p, f"{k}")

        class _T1_profile:
            Pa = pd.K
            Pb = pd.J1 + (pd.H1 - pd.J1) * 2.0 / 3.0
            toe = pd.B1 + (pd.B2 - pd.B1) * 2.0 / 3.0
            pole_list = [
                pd.H2,
                pd.H2 + App.Vector(60, -10, 0),
                Pa + (Pb - Pa) * 0.85,  #sp_p.hw_med_pct_instep,
                pd.J + (pd.J1 - pd.J) * 0.55,  #sp_p.hw_med_pct_joint,
                toe
            ]

        T1_profile = Part.BSplineCurve()
        T1_profile.buildFromPoles(_T1_profile.pole_list, False, 2, False)
        sketch_po.addGeometry(T1_profile)

        if Draw_Sketch_Overlay_Highwater_Medial := False:
            print("**********T1_profile control points *******************")
            for k, p in enumerate(_T1_profile.pole_list):
                sketch_po.addGeometry(Part.Circle(p, hf.nZ, 2.0))
                hf.p_vec(p, f"{k}")

        class _T2_insole:
            iv = insole_vecs
            pv = profile_vecs
            A0    = pv.A0
            lC3   = pv.A0 + App.Vector(0, iv.H2.y*.7,0) #-5 - 17, 0)
            H2_t  = iv.H2 + App.Vector(0, -2, 0)
            B2_t  = iv.B2 + App.Vector(9, -7, 0)
            D_t   = iv.D  + App.Vector(2, 0, 0)
            lat_K = (iv.J2 + iv.H2 + App.Vector(0, 10, 0)) * 0.5
            J2    = iv.J2
            pinky = iv.B2 + (iv.J2 - iv.B2) * 0.5 + App.Vector(0, -8, 0)
            pole_list   = [D_t, B2_t, pinky, J2, lat_K, H2_t, lC3, A0]

        T2_insole = Part.BSplineCurve()
        T2_insole.buildFromPoles(_T2_insole.pole_list, False, 2, False)
        sketch_io.addGeometry(T2_insole)

        if Draw_Sketch_Overlay_Lateral_Last_Outline := False:
            print("**********Lateral Last Outline Control Points**********")
            for k, p in enumerate(_T2_insole.pole_list):
                sketch_io.addGeometry(Part.Circle(p, hf.nZ, 2.0))
                hf.p_vec(p, f"{k}")

        class _T2_profile:
            Pa = pd.K
            Pb = pd.J1 + (pd.H1 - pd.J1) * 2.0 / 3.0
            toe = pd.B1 + (pd.B2 - pd.B1) * 2.0 / 3.0
            pole_list = [
                pd.H2,
                pd.H2 + App.Vector(60, -10, 0),
                Pa + (Pb - Pa) * 0.25,  #sp_p.hw_lat_pct_instep,
                pd.J + (pd.J1 - pd.J) * 0.60,  #sp_p.hw_lat_pct_joint,
                toe
            ]

        T2_profile = Part.BSplineCurve()
        T2_profile.buildFromPoles( _T2_profile.pole_list, False, 2, False)
        sketch_po.addGeometry(T2_profile)

        if Draw_Sketch_Overlay_Lateral_Highwater := False:
            text_overlay.control_curve_text(_T2_profile.pole_list,hf.nY,5.0,sketch_po)
            print("**********Lateral Highwater Control Points*************")
            for k, p in enumerate(_T2_profile.pole_list):
                sketch_po.addGeometry(Part.Circle(p, hf.nZ, 2.0))
                hf.p_vec(p, f"{k}")

    global t_outline_bc
    # full combined insole outline (xs_0/xs_1/xs_3 look up Y-width here)
    _t1_poles = T1_insole.getPoles()
    _t2_poles = T2_insole.getPoles()
    t_outline_bc_poles = _t1_poles + [_t2_poles[0]] + _t2_poles
    t_outline_bc = Part.BSplineCurve()
    t_outline_bc.buildFromPoles(t_outline_bc_poles, False, 2, False)
    last_insole.outline_bc = t_outline_bc

    # =========================================================================
    # C1_profie, C2_profile — crown shoulders (XY + XZ)
    # =========================================================================

    class crown:
        global C1_insole, C2_insole, C1_profile, C2_profile

        class _C1_insole:
            iC2 = idw.C + App.Vector(5, 5 + 15, 0)
            cosd = math.cos(37.0 * math.pi / 180.0)
            _ic_x = ft_meas.heel * 0.9 / 2 * cosd - 10
            pole_list = [
                App.Vector(idw.C.x, 0, 0),
                App.Vector(iC2.x, 12.5, 0),
                App.Vector(idw.H1.x, 12.5, 0),
                App.Vector(_ic_x, 4.5, 0),
                App.Vector(idw.J1.x - 20, idw.J1.y * 0.70, 0),  #_crown_med_cf, 0),
                App.Vector(idw.J1.x + 10, idw.J1.y * 0.70, 0),  #_crown_med_cf, 0),
                App.Vector(idw.B1.x+15, idw.B1.y * 0.9, 0),  #_crown_med_cf, 0),
                App.Vector(idw.D.x, 0, 0)
            ]

        C1_insole = Part.BSplineCurve()
        C1_insole.buildFromPoles(_C1_insole.pole_list, False, 2, False)
        sketch_io.addGeometry(C1_insole)
        if Draw_Sketch_Overlay_C1_insole := False:
            text_overlay.control_curve_text(_C1_insole.pole_list,hf.nZ,5.0,sketch_io)
            print("**********C1_insole Control Points*********************")
            for k, p in enumerate(_C1_insole.pole_list):
                sketch_io.addGeometry(Part.Circle(p, hf.nZ, 2.0))
                hf.p_vec(p, f"{k}")

        class _C2_insole:
            iC3 = idw.C + App.Vector(5, -5 - 15, 0)
            cosd = math.cos(37.0 * math.pi / 180.0)
            _ic_x = ft_meas.heel * 0.9 / 2 * cosd - 10
            pole_list = [
                App.Vector(idw.D.x, 0, 0),
                App.Vector(idw.B2.x, idw.B2.y * 0.5, 0),  #_crown_lat_cf, 0),
                App.Vector(idw.J2.x + 10, idw.J2.y * 0.5, 0),  #_crown_lat_cf, 0),
                App.Vector(idw.J2.x - 10, idw.J2.y * 0.5, 0),  #_crown_lat_cf, 0),
                App.Vector(_ic_x, -4.5, 0),
                App.Vector(idw.H2.x, -12.5, 0),
                App.Vector(iC3.x, -12.5, 0),
                App.Vector(idw.C.x, 0, 0),
            ]

        C2_insole = Part.BSplineCurve()
        C2_insole.buildFromPoles(_C2_insole.pole_list, False, 2, False)
        sketch_io.addGeometry(C2_insole)
        if Draw_Sketch_C2_insole := False:
            print("**********C2_insole Control Points*********************")
            for k, p in enumerate(_C2_insole.pole_list):
                sketch_io.addGeometry(Part.Circle(p, hf.nZ, 2.0))
                hf.p_vec(p, f"{k}")

        class _C1_profile:
            _Pa = pd.K
            _Pb = pd.J1 + (pd.H1 - pd.J1) * 2.0 / 3.0
            _toe = pd.B1 + (pd.B2 - pd.B1) * 0.9  #_toe_crown_fraction
            pole_list = [
                pd.C5,
                pd.C5E_intercept,
                pd.C5E_intercept,
                pd.E,
                pd.E,
                _Pa + (_Pb - _Pa) * 0.92,  #_crown_med_pct_instep,
                pd.J + (pd.J1 - pd.J) * 0.84,  #_crown_med_pct_joint,
                _toe,
            ]

        C1_profile = Part.BSplineCurve()
        C1_profile.buildFromPoles(_C1_profile.pole_list, False, 2, False)
        sketch_po.addGeometry(C1_profile)
        if Draw_Sketch_C1_profile := False:
            text_overlay.control_curve_text(_C1_profile.pole_list,hf.nY,5,sketch_po)
            print("**********C_profile Control Points*********************")
            for k, p in enumerate(_C1_profile.pole_list):
                sketch_po.addGeometry(Part.Circle(p, hf.nZ, 2.0))
                hf.p_vec(p, f"{k}")

        class _C2_profile:
            _Pa = pd.K
            _Pb = pd.J1 + (pd.H1 - pd.J1) * 2.0 / 3.0
            _toe = pd.B1 + (pd.B2 - pd.B1) * 0.9  #_toe_crown_fraction
            pole_list = [
                pd.C5,
                pd.C5E_intercept,
                pd.C5E_intercept,
                pd.E,
                pd.E,
                _Pa + (_Pb - _Pa) * 0.70,  #_crown_lat_pct_instep,
                pd.J + (pd.J1 - pd.J) * 0.72,  #_crown_lat_pct_joint,
                _toe
            ]

        C2_profile = Part.BSplineCurve()
        C2_profile.buildFromPoles(_C2_profile.pole_list, False, 2, False)
        sketch_po.addGeometry(C2_profile)
        if Draw_Sketch_C2_profile := False:
            text_overlay.control_curve_text(_C2_profile.pole_list,hf.nY,5,sketch_po)
            print("**********C2_profile Control Points********************")
            for k, p in enumerate(_C2_profile.pole_list):
                sketch_po.addGeometry(Part.Circle(p, hf.nZ, 2.0))
                hf.p_vec(p, f"{k}")

    # =========================================================================
    # Display 3D compounds
    # =========================================================================
    if False:
        _show_compound([
            _bc_to_3d(Heel_profile).toShape(),
            _bc_to_3d(H_profile).toShape(),
            _bc_to_3d(C_profile).toShape(),
            _bc_to_3d(T1_profile).toShape(),
            _bc_to_3d(T2_profile).toShape(),
            _bc_to_3d(C1_profile).toShape(),
            _bc_to_3d(C2_profile).toShape(),
        ], "ProfileCurves3D")

        _show_compound([
            H1_insole.toShape(),
            H2_insole.toShape(),
            C1_insole.toShape(),
            C2_insole.toShape(),
            T1_insole.toShape(),
            T2_insole.toShape(),
        ], "InsoleCurves3D")

    # =========================================================================
    # Sample loci, apply overrides, build interpolating BSplines
    # =========================================================================
    # Temporary restore (see project_surface_fit_direction memory) — this will be
    # replaced by a post-uv_0 least-squares pole-delta fit; don't build further on it.
    bc_hw_med = _bc_to_3d(T1_profile)
    bc_hw_lat = _bc_to_3d(T2_profile)
    bc_cr_cen_3d = _bc_to_3d(C_profile)
    bc_cr_med_3d = _build_crown_3d(C1_profile, C1_insole, xs8_x)
    bc_cr_lat_3d = _build_crown_3d(C2_profile, C2_insole, xs8_x)

    T1_pts, T2_pts, C_pts, C1_pts, C2_pts = [], [], [], [], []

    if False:
        print("\n=== Control loci heights mm (above H, local_up) ===")
        print(
            f"  {'Section':<8}  {'HT1':>7}  {'HT2':>7}  {'HC':>7}  {'HC1':>7}  {'HC2':>7}"
        )

    xs_heights = {}
    for i, (name, origin, normal, local_up) in enumerate(sections):
        ovr = _OVERRIDES.get(name, {})

        HT1_0, g_T1 = _intersect_height(bc_hw_med, origin, normal, local_up)
        HT2_0, g_T2 = _intersect_height(bc_hw_lat, origin, normal, local_up)
        HC_0, g_C_ = _intersect_height(bc_cr_cen_3d, origin, normal, local_up)
        HC1_0, g_C1 = _intersect_height(bc_cr_med_3d, origin, normal, local_up)
        HC2_0, g_C2 = _intersect_height(bc_cr_lat_3d, origin, normal, local_up)

        def _resolve(val, default):
            if val is None: return default or 0.0
            return val

        HT1 = _resolve(ovr.get('HT1', HT1_0), HT1_0)
        HT2 = _resolve(ovr.get('HT2', HT2_0), HT2_0)
        HC = _resolve(ovr.get('HC', HC_0), HC_0)
        HC1 = min(_resolve(ovr.get('HC1', HC1_0), HC1_0), HC)
        HC2 = min(_resolve(ovr.get('HC2', HC2_0), HC2_0), HC)

        xs_heights[i] = {
            'g_T1': g_T1,
            'g_T2': g_T2,
            'HT1': HT1,
            'HT2': HT2,
            'HC': HC,
            'HC1': HC1,
            'HC2': HC2,
        }

        flag = '*' if name in _OVERRIDES else ' '
        if False:
            print(
                f" {flag}{name:<7}  {HT1:>7.2f}  {HT2:>7.2f}  {HC:>7.2f}  {HC1:>7.2f}  {HC2:>7.2f}"
            )

        T1_pts.append(
            _adjust_height(g_T1, origin, local_up, HT1) if g_T1 else origin)
        T2_pts.append(
            _adjust_height(g_T2, origin, local_up, HT2) if g_T2 else origin)
        C_pts.append(
            _adjust_height(g_C_, origin, local_up, HC) if g_C_ else origin)
        C1_pts.append(
            _adjust_height(g_C1, origin, local_up, HC1) if g_C1 else origin)
        C2_pts.append(
            _adjust_height(g_C2, origin, local_up, HC2) if g_C2 else origin)

    print("  * = override active\n")

    T1_locus = Part.BSplineCurve()
    T1_locus.interpolate(T1_pts)
    T2_locus = Part.BSplineCurve()
    T2_locus.interpolate(T2_pts)
    C_locus = Part.BSplineCurve()
    C_locus.interpolate(C_pts)
    C1_locus = Part.BSplineCurve()
    C1_locus.interpolate(C1_pts)
    C2_locus = Part.BSplineCurve()
    C2_locus.interpolate(C2_pts)

    if False:
        _show_compound(
            [
                T1_locus.toShape(),
                T2_locus.toShape(),
                C_locus.toShape(),
                #C1_locus.toShape(), C2_locus.toShape(),
            ],
            "ControlCurveLoci")



build()  # run on every import/reload so curves always appear

sketch_po.Placement = last_profile.sketch_profile.Placement
doc.recompute()


def main():
    build()
    print("control_curves main")


if __name__ == "__main__":
    main()





"""
deadcode
    # Tuning knobs — edit these directly; shape_params values are not used here.
    _crown_med_pct_joint   = 0.84   # C1 height at joint:   fraction of J→J1
    _crown_med_pct_instep  = 0.92   # C1 height at instep:  fraction of K→midpoint
    _crown_lat_pct_joint   = 0.72   # C2 height at joint:   fraction of J→J1
    _crown_lat_pct_instep  = 0.70   # C2 height at instep:  fraction of K→midpoint
    _crown_med_cf          = 0.70   # C1 Y-width: fraction of medial insole half-width
    _crown_lat_cf          = 0.50   # C2 Y-width: fraction of lateral insole half-width
    _top_crown_fraction    = 0.90       # C1/C2 top anchor: fraction of B1→B2 (raise toward 1.0 for more top crown)

def _build_crown_3d(profile_bc_2d, insole_crown_bc, xs8_x):
    #Profile crown BSpline + insole crown Y offset (same construction as xs_base).
    bc_3d = _bc_to_3d(profile_bc_2d)
    poles = []
    for p in bc_3d.getPoles():
        x = min(p.x, xs8_x)
        try:
            y = hf.get_bspline_plane_intersection_new(insole_crown_bc,
                                                      App.Vector(x, 0, 0),
                                                      hf.nX)[0].y
        except Exception:
            print("Error: build_crown_3d in control_curves.py")
            y = 0.0
        poles.append(p + App.Vector(0, y, 0))
    bc_out = Part.BSplineCurve()
    bc_out.buildFromPolesMultsKnots(poles, profile_bc_2d.getMultiplicities(),
                                    profile_bc_2d.getKnots(), False,
                                    profile_bc_2d.Degree)
    return bc_out

    # =========================================================================
    # Back-assign to profile_dwg / insole_dwg for xs_*.py compatibility
    # =========================================================================
    #pd.Heel_profile              = Heel_profile
    #pd.H_profile            = H_profile
    #pd.toe_profile         = toe_profile
    #pd.T1_profile  = T1_profile
    #pd.T2_profile = T2_profile
    #pd.C1_profile        = C1_profile
    #pd.C2_profile        = C2_profile
    #idw.H1_insole        = H1_insole
    #idw.H2_insole       = H2_insole
    #idw.C1_insole        = C1_insole
    #idw.C2_insole       = C2_insole
    #idw.T1_insole  = T1_insole
    #idw.T2_insole = T2_insole
"""


"""
"""



