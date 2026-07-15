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
#import shape_params as sp
import control_curves

importlib.reload(hf)
importlib.reload(last_insole)
importlib.reload(last_profile)

print(
    f"+++++++++++++++Line({inspect.currentframe().f_lineno}) File:({__file__})+++++++++++++++++++"
)


def bspline_to_3dyz_from_2dxy(bc_2d: Part.BSplineCurve):
    poles_3d = [
        last_profile.sketch_profile.Placement.multVec(p)
        for p in bc_2d.getPoles()
    ]
    bc_3d = Part.BSplineCurve()
    bc_3d.buildFromPolesMultsKnots(poles_3d, bc_2d.getMultiplicities(),
                                   bc_2d.getKnots(), False, bc_2d.Degree)
    return bc_3d


# User-editable: set True to show a section plane in the 3D view
Show_Plane = [
    False,  # xs_0
    False,
    False,
    False,  # xs_3
    False,
    False,  # xs_5
    False,
    False,
    False,  # xs_8
    False,  # xs_9
    False,  # xs_toe_end
]

# Derived from shape_params — kept as module names so uv_0.py / xs_N.py don't need changing
"""
NURBS_DEGREE  = sp.shape_params.nurbs_degree
CRISP_SOLE    = sp.shape_params.crisp_sole
C_SCALE       = sp.shape_params.c_scale
T_SCALE       = sp.shape_params.t_scale
"""

# --- Module-level handles set by build() ---
gvec_uHB = gvec_uHC5 = None
g_H = g_J = g_C5 = g_H2 = g_H2_mod_heel = g_B1 = g_B2 = None
g_uHJ = d_HJ = None
gvec_Kb_E = gvec_uKbE = gvec_K_I = gvec_J1_J = None
gvec_uJB1 = gvec_uJB1_localY = None
jb1_len = g_X = _xs8_x = None
xs_0_tvec = xs_1_tvec = xs_2_tvec = xs_3_tvec = xs_4_tvec = None
xs_5_tvec = xs_6_tvec = xs_7_tvec = xs_8_tvec = xs_9_tvec = xs_toe_end_tvec = None
xs_0_normal = xs_1_normal = xs_2_normal = xs_3_normal = xs_4_normal = None
xs_0_placement = xs_1_placement = xs_2_placement = xs_3_placement = None
xs_4_placement = xs_5_placement = xs_6_placement = xs_7_placement = None
xs_8_placement = xs_9_placement = xs_toe_end_placement = None
xs_heel_near_placement = None
bc_3d_heel = bc_3d_bottom = bc_3d_front_top = None
bc_3d_edge_list = []
xs_0 = xs_1 = xs_2 = xs_3 = xs_4 = xs_5 = xs_6 = xs_7 = xs_8 = xs_9 = None
xs_heel_near = None
xs_heel_end_row = None
xs_heel_near_row = None
xs_toe_end_row = None        # 10 pts, crisp (doubled H1) — used by uv_0
xs_toe_end_row_plain = None  # 9 pts, non-crisp — used by make_wireframe

# --- Dataclasses ---


@dataclass
class xs_scalars_c:
    TT1: float
    HT1: float
    TT2: float
    HT2: float
    H3: App.Vector
    H: App.Vector
    HH1: float
    HH2: float
    H1: App.Vector
    H2: App.Vector
    CC1: float = 0.0
    CC2: float = 0.0
    HC: float = 0.0
    HC1: float = 0.0
    HC2: float = 0.0


# Cross-section control point naming follows George Koleff's book.
# Ring order (lateral→sole→medial, consistent v-direction for NURBS):
#     C1 C C2   — C on toe_profile; C1/C2 on crown contour curves
#     T1 T T2   — T1/T2 on medial/lateral highwater curves
#     H1 H H2
#        H3     — sole low point touches ground at J


@dataclass
class xs_ctrl_pts_c:
    H3: App.Vector = None
    H: App.Vector = None
    H1: App.Vector = None
    H2: App.Vector = None
    T: App.Vector = None
    T1: App.Vector = None
    T2: App.Vector = None
    C: App.Vector = None
    C1: App.Vector = None
    C2: App.Vector = None

    def control_points(self, crisp_sole=False):
        # H2 is the seam (index 0 and last): lateral insole edge, C0 crease on sole side.
        # crisp_sole doubles H1 (medial edge): locks H1→T1 tangent so instep side
        # stays low to ground before rising — better medial billow.
        if crisp_sole:
            return [
                self.H2, self.H3, self.H1, self.H1, self.T1, self.C1, self.C,
                self.C2, self.T2, self.H2
            ]
        return [
            self.H2, self.H3, self.H1, self.T1, self.C1, self.C, self.C2,
            self.T2, self.H2
        ]


# --- Functions that use module globals (defined before build so they're accessible) ---
counter = 0


def compute_xs_scalars(placement: App.Placement,
                       local_up: App.Vector,
                       xs_idx: int = None) -> xs_scalars_c:
    global counter
    print(f"counters count{counter}")
    counter += 1
    origin = placement.Base
    normal = App.Vector(placement.Matrix.A11, placement.Matrix.A21,
                        placement.Matrix.A31)
    #[
    # Verifying geometric calculations:
    # Control curve intersectons with cross section planes give locations
    # for H1, H, H3, H2, T2, C2, C, C1, T1. Three surfaces intersect to give a point.
    # H1 is the intersection of the insole curve surface extruded upwards and intersecting
    # with the cross section plane and the bottom curve of the last.
    # T1 is the intersection of the medial highwater curve extruded in y-directions,
    # last outline curve extruded in z-axis direction and the cross section plane.
    # Profile control curves give z-locations and x-locatons, this point projected
    # to the insole
    # Insole control curves give y-locations
    #
    print(f"compute xs scalers, xs_idx[{xs_idx}]")
    hf.p_vec(normal, "normal")
    #]
    d = origin.x
    C_x = last_insole.insole_dwg.C.x

    H3 = App.Vector(
        hf.get_bspline_plane_intersection_new(bc_3d_bottom, origin, normal)[0])
    H = H3 + local_up * 3.0
    HH1 = hf.get_bspline_plane_intersection_new(
        control_curves.H1_insole, App.Vector(d, 0, 0),
        hf.nX)[0].y  #[ H.x , not d] note: differences are ~ 1mm
    #[ nX is approximation
    print(f" xs_indx({xs_idx}) d({d}) H.x({H.x})")
    HH2 = hf.get_bspline_plane_intersection_new(
        control_curves.H2_insole, App.Vector(d, 0, 0),
        hf.nX)[0].y  #[ H.x, not d] note these are small differences
    #[ nX is approximation, clearly wrong at xs 0 and 8
    H1 = App.Vector(H.x, HH1, H.z)
    H2 = App.Vector(H.x, HH2, H.z)

    _h = control_curves.xs_heights[xs_idx if xs_idx is not None else 8]
    HT1 = _h['HT1'] or 0.0
    HT2 = _h['HT2'] or 0.0

    _x_clamp = min(d, _xs8_x)
    try:
        TT1 = hf.get_bspline_plane_intersection_new(
            control_curves.T1_insole,
            App.Vector(_x_clamp, 0, 0), hf.nX)[0].y
    except IndexError:
        print(f"Error: TT1 fallback to HH1={HH1:.2f} at x={_x_clamp:.2f}")
        TT1 = HH1
    try:
        TT2 = hf.get_bspline_plane_intersection_new(
            control_curves.T2_insole,
            App.Vector(_x_clamp, 0, 0), hf.nX)[0].y
    except IndexError:
        print(f"Error: TT2 fallback to HH2={HH2:.2f} at x={_x_clamp:.2f}")
        TT2 = HH2

    hf.p_vec(App.Vector(TT1, HT1, 0), "TT1 HT1")
    hf.p_vec(App.Vector(TT2, HT2, 0), "TT2 HT2")
    try:
        CC1 = hf.get_bspline_plane_intersection_new(
            control_curves.C1_insole, App.Vector(_x_clamp, 0, 0),
            hf.nX)[0].y
    except IndexError:
        CC1 = 0.0
        print("error5")
    try:
        CC2 = abs(
            hf.get_bspline_plane_intersection_new(
                control_curves.C2_insole, App.Vector(_x_clamp, 0, 0),
                hf.nX)[0].y)
    except IndexError:
        CC2 = 0.0
        print("error6")

    HC = _h['HC']
    HC1 = _h['HC1']
    HC2 = _h['HC2']

    return xs_scalars_c(TT1=TT1,
                        HT1=HT1,
                        TT2=TT2,
                        HT2=HT2,
                        H3=H3,
                        H=H,
                        HH1=HH1,
                        HH2=HH2,
                        H1=H1,
                        H2=H2,
                        CC1=CC1,
                        CC2=CC2,
                        HC=HC,
                        HC1=HC1,
                        HC2=HC2)


def get_heel_end_row(crisp_sole=False):
    """Return heel cap row matching control_points() v-order; doubles H1 (index 2) when crisp."""
    r = xs_heel_end_row
    if not crisp_sole:
        return r
    return [r[0], r[1], r[2], r[2], r[3], r[4], r[5], r[6], r[7], r[8]]


def get_xs_heel_near_row(crisp_sole=False):
    """Return heel-near row sampled from bc_3d_heel at t=0.25/0.50/0.75; bows to heel curve."""
    r = xs_heel_near_row
    if not crisp_sole:
        return r
    return [r[0], r[1], r[2], r[2], r[3], r[4], r[5], r[6], r[7], r[8]]


def _insole_medial_y_at_spine_d(d: float) -> float:
    pt = g_J + gvec_uJB1 * d
    hits = hf.get_bspline_plane_intersection_new(
        control_curves.H1_insole, App.Vector(pt.x, 0, 0), hf.nX)
    return hits[0].y if hits else 0.0


def insolePoint_from_profilePoint(ptV: App.Vector) -> App.Vector:
    """Map a global 3D profile point (J-to-H region) to its insole plane location along J→A."""
    g_JH  = g_H - g_J
    g_uJH = App.Vector(g_JH).normalize()
    g_uJA = (last_insole.insole_dwg.A - g_J).normalize()
    d = (ptV - g_J).dot(g_uJH)
    return g_uJA * d + g_J


# --- Build ---
# add, C1 C2 curves in last_insole, and from last_profileC1_insole
def build():
    global gvec_uHB, gvec_uHC5
    global g_H, g_J, g_C5, g_H2, g_H2_mod_heel, g_B1, g_B2, g_uHJ, d_HJ, g_K
    global gvec_Kb_E, gvec_uKbE, gvec_K_I, gvec_J1_J
    global gvec_uJB1, gvec_uJB1_localY
    global jb1_len, g_X, _xs8_x
    global xs_0_tvec, xs_1_tvec, xs_2_tvec, xs_3_tvec, xs_4_tvec
    global xs_5_tvec, xs_6_tvec, xs_7_tvec, xs_8_tvec, xs_9_tvec, xs_toe_end_tvec
    global xs_0_normal, xs_1_normal, xs_2_normal, xs_3_normal, xs_4_normal
    global xs_5_normal, xs_6_normal, xs_6_normal, xs_7_normal, xs_8_normal
    global xs_0_placement, xs_1_placement, xs_2_placement, xs_3_placement
    global xs_4_placement, xs_5_placement, xs_6_placement, xs_7_placement
    global xs_8_placement, xs_9_placement, xs_toe_end_placement
    global xs_heel_near_placement
    global bc_3d_heel, bc_3d_bottom, bc_3d_front_top, bc_3d_edge_list
    global xs_0, xs_1, xs_2, xs_3, xs_4, xs_5, xs_6, xs_7, xs_8, xs_9
    global xs_heel_near
    global xs_heel_end_row, xs_heel_near_row, xs_toe_end_row, xs_toe_end_row_plain
    global NURBS_DEGREE, CRISP_SOLE, C_SCALE, T_SCALE

    #importlib.reload(sp)
    importlib.reload(control_curves)
    """
    NURBS_DEGREE = sp.shape_params.nurbs_degree
    CRISP_SOLE   = sp.shape_params.crisp_sole
    C_SCALE      = sp.shape_params.c_scale
    T_SCALE      = sp.shape_params.t_scale
    """

    # Build control loci now that last_profile has been freshly reloaded above.
    control_curves.build()

    # --- Global direction vectors ---
    gvec_uHB = hf.xz_xy_place * (last_profile.profile_dwg.B -
                                 last_profile.profile_dwg.H).normalize()
    gvec_uHC5 = hf.xz_xy_place * (last_profile.profile_dwg.C5 -
                                  last_profile.profile_dwg.H).normalize()
    g_H = last_profile.sketch_profile.Placement.multVec(
        last_profile.profile_dwg.H)
    g_J = last_profile.sketch_profile.Placement.multVec(
        last_profile.profile_dwg.J)
    g_C5 = last_profile.sketch_profile.Placement.multVec(
        last_profile.profile_dwg.C5)
    g_H2 = last_profile.sketch_profile.Placement.multVec(
        last_profile.profile_dwg.H2)
    g_H2_mod_heel = last_profile.sketch_profile.Placement.multVec(
        last_profile.profile_dwg.H2 + App.Vector(-5, 0, 0))
    g_B1 = last_profile.sketch_profile.Placement.multVec(
        last_profile.profile_dwg.B1)
    g_B2 = last_profile.sketch_profile.Placement.multVec(
        last_profile.profile_dwg.B2)
    g_uHJ = last_profile.sketch_profile.Placement.Rotation.multVec(
        (last_profile.profile_dwg.J - last_profile.profile_dwg.H).normalize())
    d_HJ = (g_J - g_H).dot(g_uHJ)

    # --- Cross-section placements ---
    xs_heel_near_tvec = g_H + gvec_uHB * (last_insole.insole_lens.H1H2 / 8.0)
    xs_heel_near_placement = App.Placement(xs_heel_near_tvec,
                                           App.Rotation(hf.nX, App.Vector(gvec_uHB)))

    xs_0_tvec = g_H + gvec_uHB * (last_insole.insole_lens.H1H2 / 4.0)
    xs_0_normal = App.Vector(gvec_uHB)
    xs_0_placement = App.Placement(xs_0_tvec, App.Rotation(hf.nX, xs_0_normal))
    last_profile.build_xs_plane_pi("xs_0", xs_0_placement, Show_Plane[0])

    xs_1_tvec = g_H + gvec_uHB * last_insole.insole_lens.AH
    xs_1_normal = App.Vector(gvec_uHB)
    xs_1_placement = App.Placement(xs_1_tvec, App.Rotation(hf.nX, xs_1_normal))
    last_profile.build_xs_plane_pi("xs_1", xs_1_placement, Show_Plane[1])

    xs_2_tvec = last_profile.sketch_profile.Placement.multVec(
        last_profile.profile_dwg.Kb)
    gvec_Kb_E = hf.xz_xy_place * (last_profile.profile_dwg.E -
                                  last_profile.profile_dwg.Kb)
    xs_2_normal = App.Vector(gvec_Kb_E.z, 0, -gvec_Kb_E.x).normalize()
    gvec_uKbE = gvec_Kb_E.normalize()
    hf.p_vec(gvec_Kb_E, "gvec_Kb_E")
    hf.p_vec(xs_2_normal, "xs_2_normal")
    xs_2_placement = App.Placement(xs_2_tvec, App.Rotation(hf.nX, xs_2_normal))
    last_profile.build_xs_plane_pi("xs_2", xs_2_placement, Show_Plane[2])

    lvec_I = last_profile.profile_dwg.J1 + (last_profile.profile_dwg.H1 -
                                            last_profile.profile_dwg.J1) / 2.0
    g_lvec_I = last_profile.sketch_profile.Placement.multVec(lvec_I)
    g_K = last_profile.sketch_profile.Placement.multVec(
        last_profile.profile_dwg.K)
    xs_3_tvec = App.Vector(g_K)
    gvec_K_I = (g_lvec_I - g_K).normalize()
    xs_3_normal = App.Vector(gvec_K_I.z, 0, -gvec_K_I.x)
    xs_3_placement = App.Placement(g_K, App.Rotation(hf.nX, xs_3_normal))
    last_profile.build_xs_plane_pi("xs_3_Instep", xs_3_placement,
                                   Show_Plane[3])
    hf.p_vec(g_lvec_I, "g_lvec_I")
    hf.p_vec(g_K, "g_K")

    xs_4_tvec = (g_K + g_J) * 0.5
    xs_4_normal = App.Vector(xs_3_normal)
    xs_4_placement = App.Placement(xs_4_tvec, App.Rotation(hf.nX, xs_4_normal))
    last_profile.build_xs_plane_pi("xs_4_Waist", xs_4_placement, Show_Plane[4])

    gvec_J1_J = hf.xz_xy_place * (last_profile.profile_dwg.J1 -
                                  last_profile.profile_dwg.J).normalize()
    xs_5_tvec = App.Vector(g_J)
    xs_5_normal = App.Vector(gvec_J1_J.z, 0, -gvec_J1_J.x)
    gvec_uJB1 = hf.xz_xy_place * (last_profile.profile_dwg.B1 -
                                  last_profile.profile_dwg.J).normalize()
    gvec_uJB1_localY = App.Vector(-gvec_uJB1.z, 0, gvec_uJB1.x)
    xs_5_placement = App.Placement(xs_5_tvec, App.Rotation(hf.nX, xs_5_normal))
    last_profile.build_xs_plane_pi("xs_5_Joint", xs_5_placement, Show_Plane[5])

    g_X = last_profile.sketch_profile.Placement.multVec(
        last_profile.profile_dwg.X)
    jb1_len = (g_X - g_J).dot(gvec_uJB1)
    hf.p_vec(g_X, "g_X")
    _d_jb1_total = (g_B1 - g_J).dot(gvec_uJB1)

    xs_6_tvec = g_J + gvec_uJB1 * (jb1_len / 3.0)
    xs_6_normal = App.Vector(gvec_uJB1)
    xs_6_placement = App.Placement(xs_6_tvec, App.Rotation(hf.nX, xs_6_normal))
    last_profile.build_xs_plane_pi("xs_6_ToeCap", xs_6_placement,
                                   Show_Plane[6])

    xs_7_tvec = g_J + gvec_uJB1 * (jb1_len * 2.0 / 3.0)
    xs_7_normal = App.Vector(gvec_uJB1)
    xs_7_placement = App.Placement(xs_7_tvec, App.Rotation(hf.nX, xs_7_normal))
    last_profile.build_xs_plane_pi("xs_7_ToeBox", xs_7_placement,
                                   Show_Plane[7])

    xs_8_tvec = g_J + gvec_uJB1 * jb1_len
    xs_8_normal = App.Vector(gvec_uJB1)
    xs_8_placement = App.Placement(xs_8_tvec, App.Rotation(hf.nX, xs_8_normal))
    last_profile.build_xs_plane_pi("xs_8_ToeEnd", xs_8_placement,
                                   Show_Plane[8])

    xs_9_tvec = g_J + gvec_uJB1 * (_d_jb1_total - 10.0)
    xs_9_normal = App.Vector(gvec_uJB1)
    xs_9_placement = App.Placement(xs_9_tvec, App.Rotation(hf.nX, xs_9_normal))
    last_profile.build_xs_plane_pi("xs_9_ToeEnd2", xs_9_placement,
                                   Show_Plane[9])
    _xs8_x = xs_9_tvec.x

    # --- 3D BSplines ---
    bc_3d_edge_list = []

    bc_3d_heel = bspline_to_3dyz_from_2dxy(control_curves.heel_profile)
    bc_3d_edge_list.append(bc_3d_heel)

    bc_3d_bottom = bspline_to_3dyz_from_2dxy(control_curves.H_profile)
    bc_3d_edge_list.append(bc_3d_bottom)

    bc_3d_front_top = bspline_to_3dyz_from_2dxy(control_curves.toe_profile)
    bc_3d_edge_list.append(bc_3d_front_top.toShape())

    # --- Scalar samples for each section (xs_heights[i] from control_curves) ---
    xs_heel_near = compute_xs_scalars(xs_heel_near_placement, gvec_uHC5, xs_idx=0)
    xs_0 = compute_xs_scalars(xs_0_placement, gvec_uHC5, xs_idx=0)
    xs_1 = compute_xs_scalars(xs_1_placement, gvec_uHC5, xs_idx=1)
    xs_2 = compute_xs_scalars(xs_2_placement, gvec_uKbE, xs_idx=2)
    xs_3 = compute_xs_scalars(xs_3_placement, gvec_K_I, xs_idx=3)
    xs_4 = compute_xs_scalars(xs_4_placement, gvec_K_I, xs_idx=4)
    xs_5 = compute_xs_scalars(xs_5_placement, gvec_J1_J, xs_idx=5)
    xs_6 = compute_xs_scalars(xs_6_placement, gvec_uJB1_localY, xs_idx=6)
    xs_7 = compute_xs_scalars(xs_7_placement, gvec_uJB1_localY, xs_idx=7)
    xs_8 = compute_xs_scalars(xs_8_placement, gvec_uJB1_localY, xs_idx=8)
    xs_9 = compute_xs_scalars(xs_9_placement, gvec_uJB1_localY, xs_idx=9)

    # --- Heel end cap row ---
    _cap_spread = 0.1  # mm — prevents NURBS singularity at seam end
    _cap_lat = App.Vector(0, _cap_spread, 0)
    _hp = bc_3d_heel.getPoles()  # [0]=top(C5), [1]=mid(H2_mod), [2]=sole(H)
    xs_heel_end_row = [
        _hp[2] - _cap_lat,  # H2: heel sole lateral (seam)
        App.Vector(_hp[2]),  # H3: heel sole center
        _hp[2] + _cap_lat,  # H1: heel sole medial
        _hp[1] + _cap_lat,  # T1: mid-heel medial
        _hp[0] + _cap_lat,  # C1: top-heel medial
        App.Vector(_hp[0]),  # C:  top-heel center
        _hp[0] - _cap_lat,  # C2: top-heel lateral
        _hp[1] - _cap_lat,  # T2: mid-heel lateral
        _hp[2] - _cap_lat,  # H2: heel sole lateral (close seam)
    ]

    # --- Heel near row: bc_3d_heel sampled at intermediate t values ---
    # Bows to heel_profile shape rather than being a parallel slice like xs_0.
    _t_c, _t_m, _t_h = 0.15, 0.30, 0.92
    _p_c = bc_3d_heel.value(_t_c)
    _p_m = bc_3d_heel.value(_t_m)
    _p_h = bc_3d_heel.value(_t_h)
    xs_heel_near_row = [
        _p_h - _cap_lat,       # H2: lateral (seam)
        App.Vector(_p_h),      # H3: center
        _p_h + _cap_lat,       # H1: medial
        _p_m + _cap_lat,       # T1: medial
        _p_c + _cap_lat,       # C1: medial
        App.Vector(_p_c),      # C:  top center
        _p_c - _cap_lat,       # C2: lateral
        _p_m - _cap_lat,       # T2: lateral
        _p_h - _cap_lat,       # H2: close seam
    ]

    # --- Toe end cap: binary search for last plane where insole half-width >= threshold ---
    _min_toe_half_width = 5.0  # mm — minimum for stable NURBS row
    _d_lo, _d_hi = jb1_len, _d_jb1_total
    for _ in range(30):
        _d_mid = (_d_lo + _d_hi) * 0.5
        if _insole_medial_y_at_spine_d(_d_mid) >= _min_toe_half_width:
            _d_lo = _d_mid
        else:
            _d_hi = _d_mid

    xs_toe_end_tvec = g_J + gvec_uJB1 * _d_lo
    xs_toe_end_placement = App.Placement(xs_toe_end_tvec,
                                         App.Rotation(hf.nX, xs_8_normal))
    last_profile.build_xs_plane_pi("xs_toe_end", xs_toe_end_placement,
                                   Show_Plane[10])
    print(
        f"xs_toe_end at d={_d_lo:.2f} mm from J  (insole half-width ≈ {_insole_medial_y_at_spine_d(_d_lo):.2f} mm)"
    )

    # --- Toe end cap row: geometry-driven from toe_profile intersections ---
    def _prof_to_3d(p):
        """Profile sketch local point → 3D world."""
        return last_profile.sketch_profile.Placement.multVec(
            App.Vector(p.X, p.Y, p.Z))

    _toe_cap_spread = 0.1
    _toe_cap_lat = App.Vector(0, _toe_cap_spread, 0)

    _hw_isects = control_curves.toe_profile.intersect(
        control_curves.T1_profile)
    _c1_isects = control_curves.toe_profile.intersect(
        control_curves.C1_profile)
    _c2_isects = control_curves.toe_profile.intersect(
        control_curves.C2_profile)

    _hw3  = _prof_to_3d(_hw_isects[0])
    _c1_3 = _prof_to_3d(_c1_isects[1])
    _c2_3 = _prof_to_3d(_c2_isects[1])
    # C center: average of C1 and C2 intersections — keeps C between C1 and C2 in x,
    # preventing face inversions at the xs_9→toe_end transition.
    _c_3  = App.Vector((_c1_3.x + _c2_3.x) / 2, 0, (_c1_3.z + _c2_3.z) / 2)

    print(
        f"toe_end_row  hw={_hw3}  C={_c_3}  C1={_c1_3}  C2={_c2_3}  B1={g_B1}")

    _g_B1_fe = g_B1 + gvec_uJB1_localY * 3.0  # feather-edge lift at toe tip
    _ter = [
        _g_B1_fe - _toe_cap_lat,  # H2: toe lateral (seam)
        App.Vector(_g_B1_fe),     # H3: toe center
        _g_B1_fe + _toe_cap_lat,  # H1: toe medial
        _hw3 + _toe_cap_lat,  # T1: highwater medial
        _c1_3 + _toe_cap_lat,  # C1: crown medial
        App.Vector(_c_3),  # C:  crown center
        _c2_3 - _toe_cap_lat,  # C2: crown lateral
        _hw3 - _toe_cap_lat,  # T2: highwater lateral
        _g_B1_fe - _toe_cap_lat,  # H2: close seam
    ]
    xs_toe_end_row_plain = _ter
    if True or CRISP_SOLE:
        xs_toe_end_row = [_ter[0], _ter[1], _ter[2], _ter[2]] + _ter[3:]
    else:
        xs_toe_end_row = _ter

    #_show_bsplineshapes()
    view = FreeCADGui.ActiveDocument.ActiveView
    if view and hasattr(view, 'viewFront'):
        view.viewFront()
        view.fitAll()
    last_profile.doc.recompute()
    print("\nThe end\n")


def _show_bsplineshapes():
    bc_compound_shape = Part.makeCompound(bc_3d_edge_list)
    obj_name = "BSplinesShape"
    if last_profile.doc.getObject(obj_name):
        last_profile.doc.removeObject(obj_name)
        gc.collect()
        print("Removed BSplines Shape")
    obj = last_profile.doc.addObject("Part::Feature", obj_name)
    obj.Shape = bc_compound_shape


build()


def main():
    print("xs_base main")
    print(f"g_K = {g_K}")


if __name__ == "__main__":
    main()
