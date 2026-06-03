import inspect
import importlib
import gc
import FreeCAD as App
import FreeCADGui
import Part
from dataclasses import dataclass
import helper_funcs as hf
import last_insole
import last_profile

importlib.reload(hf)
importlib.reload(last_insole)
importlib.reload(last_profile)

print(f"+++++++++++++++Line({inspect.currentframe().f_lineno}) File:({__file__})+++++++++++++++++++")

#           name needs to change to 3d_xz from 2d xy?
def bspline_to_3dyz_from_2dxy(bc_2d:  Part.BSplineCurve ):
    # HC from top_bc/xs_0 plane intersection in global 3D
    poles_3d = [last_profile.sketch_profile.Placement.multVec(p)
                for p in bc_2d.getPoles()]
    bc_3d = Part.BSplineCurve()
    bc_3d.buildFromPolesMultsKnots(
        poles_3d,
        bc_2d.getMultiplicities(),
        bc_2d.getKnots(),
        False, bc_2d.Degree)
    return bc_3d
# --- Global direction vectors ---
gvec_uHB  = hf.xz_xy_place * (last_profile.profile_dwg.B  - last_profile.profile_dwg.H).normalize()
gvec_uHC5 = hf.xz_xy_place * (last_profile.profile_dwg.C5 - last_profile.profile_dwg.H).normalize()
g_H  = last_profile.sketch_profile.Placement.multVec(last_profile.profile_dwg.H)
g_J  = last_profile.sketch_profile.Placement.multVec(last_profile.profile_dwg.J)
g_C5 = last_profile.sketch_profile.Placement.multVec(last_profile.profile_dwg.C5)
g_H2 = last_profile.sketch_profile.Placement.multVec(last_profile.profile_dwg.H2)
g_H2_mod_heel = last_profile.sketch_profile.Placement.multVec(
    last_profile.profile_dwg.H2 + App.Vector(-5, 0, 0))
g_B1 = last_profile.sketch_profile.Placement.multVec(last_profile.profile_dwg.B1)
g_B2 = last_profile.sketch_profile.Placement.multVec(last_profile.profile_dwg.B2)
g_uHJ = last_profile.sketch_profile.Placement.Rotation.multVec(
    (last_profile.profile_dwg.J - last_profile.profile_dwg.H).normalize())
d_HJ  = (g_J - g_H).dot(g_uHJ)   # scalar distance H→J along H-J axis

Show_Plane = [False, #xs_0
               False,
               False,
               False, #xs_3
               False,
               False, #xs_5
               False,
               False,
               False, #xs_8
               True] #xs_toe_end

NURBS_DEGREE = 2    # 1=linear, 2=quadratic
CRISP_SOLE   = True  # True doubles H2 and H1 (insole edges) for sharp insole crease; H3 seam not doubled

# xs_0: first heel section
xs_0_tvec   = g_H + gvec_uHB * (last_insole.insole_lens.H1H2/4.0)
xs_0_normal = App.Vector(gvec_uHB)
xs_0_placement = App.Placement(xs_0_tvec, App.Rotation(hf.nX, xs_0_normal))
last_profile.build_xs_plane_pi("xs_0", xs_0_placement, Show_Plane[0])

# xs_1: second heel section
xs_1_tvec   = g_H + gvec_uHB * last_insole.insole_lens.AH
xs_1_normal = App.Vector(gvec_uHB)
xs_1_placement = App.Placement(xs_1_tvec, App.Rotation(hf.nX, xs_1_normal))
last_profile.build_xs_plane_pi("xs_1", xs_1_placement, Show_Plane[1])

# xs_2: crown, normal to Kb->E
xs_2_tvec  = last_profile.sketch_profile.Placement.multVec(last_profile.profile_dwg.Kb)
gvec_Kb_E  = hf.xz_xy_place * (last_profile.profile_dwg.E - last_profile.profile_dwg.Kb)
xs_2_normal = App.Vector(gvec_Kb_E.z, 0, -gvec_Kb_E.x).normalize()
gvec_uKbE   = gvec_Kb_E.normalize()
hf.p_vec(gvec_Kb_E,   "gvec_Kb_E")
hf.p_vec(xs_2_normal, "xs_2_normal")
xs_2_placement = App.Placement(xs_2_tvec, App.Rotation(hf.nX, xs_2_normal))
last_profile.build_xs_plane_pi("xs_2", xs_2_placement, Show_Plane[2])

# xs_3: instep, plane at K, the midpoint of J1-H1
lvec_I   = last_profile.profile_dwg.J1 + (last_profile.profile_dwg.H1 - last_profile.profile_dwg.J1)/2.0
g_lvec_I = last_profile.sketch_profile.Placement.multVec(lvec_I)
g_K      = last_profile.sketch_profile.Placement.multVec(last_profile.profile_dwg.K)
xs_3_tvec = App.Vector(g_K)
gvec_K_I = (g_lvec_I - g_K).normalize()
xs_3_normal    = App.Vector(gvec_K_I.z, 0, -gvec_K_I.x)
xs_3_placement = App.Placement(g_K, App.Rotation(hf.nX, xs_3_normal))
last_profile.build_xs_plane_pi("xs_3_Instep", xs_3_placement, Show_Plane[3])
hf.p_vec(g_lvec_I, "g_lvec_I")
hf.p_vec(g_K,      "g_K")

# xs_4: waist, midpoint between instep (xs_3) and joint (xs_5), same normal as instep
xs_4_tvec   = (g_K + g_J) * 0.5
xs_4_normal = App.Vector(xs_3_normal)
xs_4_placement = App.Placement(xs_4_tvec, App.Rotation(hf.nX, xs_4_normal))
last_profile.build_xs_plane_pi("xs_4_Waist", xs_4_placement, Show_Plane[4])

# xs_5: joint, at profile J, normal from J1-J direction
gvec_J1_J  = hf.xz_xy_place * (last_profile.profile_dwg.J1 - last_profile.profile_dwg.J).normalize()
xs_5_tvec = App.Vector(g_J)
xs_5_normal = App.Vector(gvec_J1_J.z, 0, -gvec_J1_J.x)
gvec_uJB1       = hf.xz_xy_place * (last_profile.profile_dwg.B1 - last_profile.profile_dwg.J).normalize()
gvec_uJB1_localY = App.Vector(-gvec_uJB1.z, 0, gvec_uJB1.x)
xs_5_placement = App.Placement(xs_5_tvec, App.Rotation(hf.nX, xs_5_normal))
last_profile.build_xs_plane_pi("xs_5_Joint", xs_5_placement, Show_Plane[5])

# jb1_len: spine distance J → profile X (end of foot length, before toe space/spring).
# Full toe width is sampled here; xs_6/xs_7/xs_8 divide this range in thirds.
# xs_toe_end caps at profile g_B1.
g_X     = last_profile.sketch_profile.Placement.multVec(last_profile.profile_dwg.X)
jb1_len = (g_X - g_J).dot(gvec_uJB1)
hf.p_vec(g_X,"g_X")

# xs_6: 1/3 along J->ball line
xs_6_tvec   = g_J + gvec_uJB1 * (jb1_len / 3.0)
xs_6_normal = App.Vector(gvec_uJB1)
xs_6_placement = App.Placement(xs_6_tvec, App.Rotation(hf.nX, xs_6_normal))
last_profile.build_xs_plane_pi("xs_6_ToeCap", xs_6_placement, Show_Plane[6])

# xs_7: 2/3 along J->ball line
xs_7_tvec   = g_J + gvec_uJB1 * (jb1_len * 2.0 / 3.0)
xs_7_normal = App.Vector(gvec_uJB1)
xs_7_placement = App.Placement(xs_7_tvec, App.Rotation(hf.nX, xs_7_normal))
last_profile.build_xs_plane_pi("xs_7_ToeBox", xs_7_placement, Show_Plane[7])

# xs_8: at insole ball line — full toe width before taper begins
xs_8_tvec   = g_J + gvec_uJB1 * jb1_len
xs_8_normal = App.Vector(gvec_uJB1)
xs_8_placement = App.Placement(xs_8_tvec, App.Rotation(hf.nX, xs_8_normal))
last_profile.build_xs_plane_pi("xs_8_ToeEnd", xs_8_placement, Show_Plane[8])

# xs_toe_end details here


# --- 3D BSplines (profile curves transformed to global XZ space) ---
bc_3d_edge_list = []

bc_3d_heel = bspline_to_3dyz_from_2dxy(last_profile.profile_dwg.heel_bc)
bc_3d_edge_list.append(bc_3d_heel)

bc_3d_bottom = bspline_to_3dyz_from_2dxy(last_profile.profile_dwg.bottom_bc)
bc_3d_edge_list.append(bc_3d_bottom)

bc_3d_front_top = bspline_to_3dyz_from_2dxy(last_profile.profile_dwg.front_top_bc)
bc_3d_edge_list.append(bc_3d_front_top.toShape())

bc_3d_front = bspline_to_3dyz_from_2dxy(last_profile.profile_dwg.front_bc)
bc_3d_edge_list.append(bc_3d_front.toShape())

bc_3d_medial_highwater = bspline_to_3dyz_from_2dxy(last_profile.profile_dwg.medial_highwate_bc)
bc_3d_edge_list.append(bc_3d_medial_highwater.toShape())

bc_3d_lateral_highwater = bspline_to_3dyz_from_2dxy(last_profile.profile_dwg.lateral_highwater_bc)
bc_3d_edge_list.append(bc_3d_lateral_highwater.toShape())

# Crown contour curves for C1/C2:
#   Height from C1_profile_bc / C2_profile_bc (profile sketch, each has own height)
#   Y-offset from C1_insole_medial / C2_insole_lateral (insole sketch, used only
#   for curve construction — CC1/CC2 width in compute_xs_scalars uses insole_bc_medial
#   * _crown_fraction directly so it stays inside T1/T2)
# Tune shoulder height in last_profile.draw_crown_profiles().
# Tune crown width fraction below.
_crown_fraction = 0.3
_c1_fbc       = last_profile.profile_dwg.C1_profile_bc
_c1_poles_3d  = [last_profile.sketch_profile.Placement.multVec(p)
                 for p in _c1_fbc.getPoles()]
_c2_fbc       = last_profile.profile_dwg.C2_profile_bc
_c2_poles_3d  = [last_profile.sketch_profile.Placement.multVec(p)
                 for p in _c2_fbc.getPoles()]

_xs8_x = xs_8_tvec.x
_mc_poles = []
for _p in _c1_poles_3d:
    _x_lookup = min(_p.x, _xs8_x)
    try:
        _y_med = hf.get_bspline_plane_intersection_new(
            last_insole.insole_dwg.C1_insole_medial,
            App.Vector(_x_lookup, 0, 0), hf.nX)[0].y
    except IndexError:
        _y_med = 0.0
    _mc_poles.append(_p + App.Vector(0, _y_med, 0))

_lc_poles = []
for _p in _c2_poles_3d:
    _x_lookup = min(_p.x, _xs8_x)
    try:
        _y_lat = hf.get_bspline_plane_intersection_new(
            last_insole.insole_dwg.C2_insole_lateral,
            App.Vector(_x_lookup, 0, 0), hf.nX)[0].y
    except IndexError:
        _y_lat = 0.0
    _lc_poles.append(_p + App.Vector(0, _y_lat, 0))

bc_3d_medial_crown = Part.BSplineCurve()
bc_3d_medial_crown.buildFromPolesMultsKnots(
    _mc_poles, _c1_fbc.getMultiplicities(), _c1_fbc.getKnots(), False, _c1_fbc.Degree)

bc_3d_lateral_crown = Part.BSplineCurve()
bc_3d_lateral_crown.buildFromPolesMultsKnots(
    _lc_poles, _c2_fbc.getMultiplicities(), _c2_fbc.getKnots(), False, _c2_fbc.Degree)

bc_3d_edge_list.append(bc_3d_medial_crown.toShape())
bc_3d_edge_list.append(bc_3d_lateral_crown.toShape())


# --- Dataclasses for section geometry ---
@dataclass
class xs_scalars_c:
    TT1: float
    HT1: float
    TT2: float
    HT2: float
    H3:  App.Vector
    H:   App.Vector
    HH1: float
    HH2: float
    H1:  App.Vector
    H2:  App.Vector
    CC1: float = 0.0
    CC2: float = 0.0
    HC1: float = 0.0   # C1 shoulder height in local frame (from C1_profile_bc)
    HC2: float = 0.0   # C2 shoulder height in local frame (from C2_profile_bc)


# Cross section control point naming follows George Koeleff's book
# Top to bottom, median on left , lateral on right follow
#     C1 C C2,  C on front_bc/top_bc; C1/C2 on bc_3d_medial/lateral_crown contours.
#     |     |,  All crown contours converge to g_B1 at the toe tip.
#     |     |.
#     T1 T T2,  T on heel outline, T1 and t2 on on medial_highwate_bc, and lateral_highwater_bc.
#     |      |, Insole last outline for width but use H1->J1 and H2->J2 in that area.
#     |      |   (Need to add last outline in insole drawing instead of using insole H1->J1 and H2->J2.)
#     H1 H H2
#        H3
#
# ---- If extra sampling needed (plan B): that maintains a sortable order ----
# Cross section names can be inserted before xs_0 as xs__5,
# and after say xs_5 as xs_55, implementing a decimal system.

@dataclass
class xs_ctrl_pts_c:
    H3: App.Vector = None
    H:  App.Vector = None
    H1: App.Vector = None
    H2: App.Vector = None
    T:  App.Vector = None
    T1: App.Vector = None
    T2: App.Vector = None
    C:  App.Vector = None
    C1: App.Vector = None
    C2: App.Vector = None

    def control_points(self, crisp_sole=False):
        # lateral -> bottom -> medial, consistent v-direction for NURBS.
        # H3 is the seam (appears at index 0 and last); not doubled in crisp.
        # crisp_sole doubles H2 (lateral edge) and H1 (medial edge) for sharp insole crease.
        if crisp_sole:
            return [self.H3, self.H2, self.H2, self.T2, self.C2,
                    self.C, self.C1, self.T1, self.H1, self.H1, self.H3]
        return [self.H3, self.H2, self.T2, self.C2,
                self.C, self.C1, self.T1, self.H1, self.H3]


def compute_xs_scalars(placement: App.Placement,
                       local_up:  App.Vector) -> xs_scalars_c:
    origin = placement.Base
    normal = App.Vector(placement.Matrix.A11,
                        placement.Matrix.A21,
                        placement.Matrix.A31)
    d      = origin.x
    C_x    = last_insole.insole_dwg.C.x

    H3    = App.Vector(hf.get_bspline_plane_intersection_new(bc_3d_bottom, origin, normal)[0])
    H     = H3 + local_up * 3.0
    HH1   = hf.get_bspline_plane_intersection_new(
                last_insole.insole_dwg.insole_bc_medial,
                App.Vector(d, 0, 0), hf.nX)[0].y
    HH2   = hf.get_bspline_plane_intersection_new(
                last_insole.insole_dwg.insole_bc_lateral,
                App.Vector(d, 0, 0), hf.nX)[0].y
    H1    = App.Vector(H.x, HH1, H.z)
    H2    = App.Vector(H.x, HH2, H.z)

    g_T1  = App.Vector(hf.get_bspline_plane_intersection_new(
                bc_3d_medial_highwater, origin, normal)[0])
    d_T1  = (g_T1 - g_H).dot(g_uHJ)
    if d_T1 >= d_HJ:
        d_T1 = d_HJ + (g_T1 - g_J).dot(gvec_uJB1)
    try:
        TT1 = hf.get_bspline_plane_intersection_new(
                  last_insole.insole_dwg.bc_medial_last_outline,
                  App.Vector(C_x + d_T1, 0, 0), hf.nX)[0].y
    except IndexError:
        TT1 = HH1   # last outline not defined here; insole width is closest proxy
    HT1   = (g_T1 - origin).dot(local_up)

    g_T2  = App.Vector(hf.get_bspline_plane_intersection_new(
                bc_3d_lateral_highwater, origin, normal)[0])
    d_T2  = (g_T2 - g_H).dot(g_uHJ)
    if d_T2 >= d_HJ:
        d_T2 = d_HJ + (g_T2 - g_J).dot(gvec_uJB1)
    try:
        TT2 = hf.get_bspline_plane_intersection_new(
                  last_insole.insole_dwg.bc_lateral_last_outline,
                  App.Vector(C_x + d_T2, 0, 0), hf.nX)[0].y
    except IndexError:
        TT2 = HH2   # last outline not defined here; insole width is closest proxy
    HT2   = (g_T2 - origin).dot(local_up)

    # CC1/CC2: width from explicit C1/C2 insole crown curves
    _x_clamp = min(d, _xs8_x)
    try:
        CC1 = hf.get_bspline_plane_intersection_new(
                  last_insole.insole_dwg.C1_insole_medial,
                  App.Vector(_x_clamp, 0, 0), hf.nX)[0].y
    except IndexError:
        CC1 = 0.0
    try:
        CC2 = abs(hf.get_bspline_plane_intersection_new(
                  last_insole.insole_dwg.C2_insole_lateral,
                  App.Vector(_x_clamp, 0, 0), hf.nX)[0].y)
    except IndexError:
        CC2 = 0.0

    # HC1/HC2: height from crown profile curve intersection
    try:
        _g_C1 = App.Vector(hf.get_bspline_plane_intersection_new(
                    bc_3d_medial_crown, origin, normal)[0])
        HC1 = (_g_C1 - origin).dot(local_up)
    except IndexError:
        HC1 = 0.0
    try:
        _g_C2 = App.Vector(hf.get_bspline_plane_intersection_new(
                    bc_3d_lateral_crown, origin, normal)[0])
        HC2 = (_g_C2 - origin).dot(local_up)
    except IndexError:
        HC2 = 0.0

    return xs_scalars_c(TT1=TT1, HT1=HT1, TT2=TT2, HT2=HT2,
                        H3=H3, H=H, HH1=HH1, HH2=HH2, H1=H1, H2=H2,
                        CC1=CC1, CC2=CC2, HC1=HC1, HC2=HC2)


# --- Compute scalars for each section ---
xs_0 = compute_xs_scalars(xs_0_placement, gvec_uHC5)
xs_1 = compute_xs_scalars(xs_1_placement, gvec_uHC5)
xs_2 = compute_xs_scalars(xs_2_placement, gvec_uKbE)
xs_3 = compute_xs_scalars(xs_3_placement, gvec_K_I)
xs_4 = compute_xs_scalars(xs_4_placement, gvec_K_I)
xs_5 = compute_xs_scalars(xs_5_placement, gvec_J1_J)
xs_6 = compute_xs_scalars(xs_6_placement, gvec_uJB1_localY)
xs_7 = compute_xs_scalars(xs_7_placement, gvec_uJB1_localY)
xs_8 = compute_xs_scalars(xs_8_placement, gvec_uJB1_localY)

_cap_spread = 0.1  # mm — small spread prevents NURBS row singularity at ends
_cap_lat    = App.Vector(0, _cap_spread, 0)

# heel cap row: v-order matches control_points(): H3, H2, T2, C2, C, C1, T1, H1, H3
# Heights come directly from heel_bc poles: [0]=C5(top), [1]=H2_mod(mid), [2]=H(sole)
# If heel_bc poles change in last_profile, this row updates automatically.
_hp = bc_3d_heel.getPoles()   # [0]=top(C5), [1]=mid(H2_mod), [2]=sole(H)
xs_heel_end_row = [
    App.Vector(_hp[2]),        # H3: heel sole center (seam)
    _hp[2] - _cap_lat,         # H2: heel sole lateral
    _hp[1] - _cap_lat,         # T2: mid-heel lateral
    _hp[0] - _cap_lat,         # C2: top-heel lateral
    App.Vector(_hp[0]),        # C:  top-heel center
    _hp[0] + _cap_lat,         # C1: top-heel medial
    _hp[1] + _cap_lat,         # T1: mid-heel medial
    _hp[2] + _cap_lat,         # H1: heel sole medial
    App.Vector(_hp[2]),        # H3: heel sole center (close seam)
]

def get_heel_end_row(crisp_sole=False):
    """Return heel cap row matching control_points() v-order; doubles H2/H1 (not H3) when crisp."""
    r = xs_heel_end_row
    if not crisp_sole:
        return r
    return [r[0], r[1], r[1], r[2], r[3], r[4], r[5], r[6], r[7], r[7], r[8]]

# toe cap: find furthest-forward xs plane where insole half-width >= _min_toe_half_width.
# Assumes insole medial width decreases monotonically from xs_8 toward B1.
_min_toe_half_width = 5.0   # mm each side — minimum for stable NURBS row
_d_jb1_total = (g_B1 - g_J).dot(gvec_uJB1)

def _insole_medial_y_at_spine_d(d: float) -> float:
    pt   = g_J + gvec_uJB1 * d
    hits = hf.get_bspline_plane_intersection_new(
        last_insole.insole_dwg.insole_bc_medial,
        App.Vector(pt.x, 0, 0), hf.nX)
    return hits[0].y if hits else 0.0

_d_lo, _d_hi = jb1_len, _d_jb1_total
for _ in range(30):
    _d_mid = (_d_lo + _d_hi) * 0.5
    if _insole_medial_y_at_spine_d(_d_mid) >= _min_toe_half_width:
        _d_lo = _d_mid
    else:
        _d_hi = _d_mid

xs_toe_end_tvec      = g_J + gvec_uJB1 * _d_lo
xs_toe_end_placement = App.Placement(xs_toe_end_tvec, App.Rotation(hf.nX, xs_8_normal))
last_profile.build_xs_plane_pi("xs_toe_end", xs_toe_end_placement, Show_Plane[9])
print(f"xs_toe_end at d={_d_lo:.2f} mm from J  (insole half-width ≈ {_insole_medial_y_at_spine_d(_d_lo):.2f} mm)")

_sc   = compute_xs_scalars(xs_toe_end_placement, gvec_uJB1_localY)
_g_C  = hf.get_bspline_plane_intersection_new(
            bc_3d_front, xs_toe_end_tvec, gvec_uJB1)[0]
_HC   = (_g_C - xs_toe_end_tvec).dot(gvec_uJB1_localY)
_H3_y = (_sc.H3 - xs_toe_end_tvec).dot(gvec_uJB1_localY)
_H_y  = _H3_y + 3.0
_t    = _sc.TT1 / (_sc.TT1 - _sc.TT2)
_T_y  = _sc.HT1 + _t * (_sc.HT2 - _sc.HT1)

# Taper C1/C2 width proportionally as insole narrows from xs_8 to toe end
_xs8_iw  = _insole_medial_y_at_spine_d(jb1_len)
_toe_iw  = _insole_medial_y_at_spine_d(_d_lo)
_taper_f = (_toe_iw / _xs8_iw) if _xs8_iw > 0 else 1.0
print(f"xs_toe_end taper: xs8_iw={_xs8_iw:.2f}  toe_iw={_toe_iw:.2f}  f={_taper_f:.3f}")

xs_toe_end = xs_ctrl_pts_c(
    H3=App.Vector(0,          _H_y,     0),   # match H1/H2 height — no insole dome at narrow toe end
    H =App.Vector(0,          _H_y,     0),
    H1=App.Vector( _sc.HH1,  _H_y,     0),
    H2=App.Vector( _sc.HH2,  _H_y,     0),
    T =App.Vector(0,          _T_y,     0),
    T1=App.Vector( _sc.TT1,  _sc.HT1,  0),
    T2=App.Vector( _sc.TT2,  _sc.HT2,  0),
    C =App.Vector(0,                      _HC,                0),
    C1=App.Vector( xs_8.CC1 * _taper_f,  min(_sc.HC1, _HC),  0),
    C2=App.Vector(-xs_8.CC2 * _taper_f,  min(_sc.HC2, _HC),  0))


def show_bsplineshapes(edge_list=[]):
    bc_compound_shape = Part.makeCompound(bc_3d_edge_list)
    obj_name = "BSplinesShape"
    if last_profile.doc.getObject(obj_name):
        last_profile.doc.removeObject(obj_name)
        gc.collect()
        print("Removed BSplines Shape")
    obj = last_profile.doc.addObject("Part::Feature", obj_name)
    obj.Shape = bc_compound_shape

show_bsplineshapes(bc_3d_edge_list)

view = FreeCADGui.ActiveDocument.ActiveView
view.viewFront()
view.fitAll()
last_profile.doc.recompute()

print("\nThe end\n")


def main():
    print("xs_base main")
if __name__ == "__main__":
    main()
