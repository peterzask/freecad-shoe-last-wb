import FreeCAD as App
import Part
import uv_0
import helper_funcs as hf
import xs_base

V = App.Vector

v_count = len(uv_0.rows[0])
u_count = len(uv_0.rows)
crisp   = (v_count == 10)

if crisp:
    v_names = ['H2','H3','H1','H1b','T1','C1','C','C2','T2','H2b']
else:
    v_names = ['H2','H3','H1','T1','C1','C','C2','T2','H2b']

row_names = ['heel_end','xs_0','xs_1','xs_2','xs_3','xs_4','xs_5','xs_6','xs_7','xs_8','toe_end']

# u/v parameterization — same as uv_0.py computes internally
uks_raw = [0.0]
C_idx   = v_count // 2 + 1
for u in range(1, u_count):
    uks_raw.append(uks_raw[-1] + (uv_0.rows[u][C_idx] - uv_0.rows[u-1][C_idx]).Length)
uks_raw = [k / uks_raw[-1] for k in uks_raw]

vks_raw = [0.0]
for v in range(1, v_count):
    vks_raw.append(vks_raw[-1] + (uv_0.rows[4][v] - uv_0.rows[4][v-1]).Length)
vks_raw = [k / vks_raw[-1] for k in vks_raw]

# -----------------------------------------------------------------------
# Table: surface value vs control point at T2 and H2 for each row
# -----------------------------------------------------------------------
T2_j = v_names.index('T2')
H2_j = 0   # lateral sole edge (first H2)

print(f"\n=== Surface vs Control Point  (u_count={u_count}, v_count={v_count}) ===")
print(f"{'row':<10}  {'col':<5}  {'ctrl.y':>8}  {'surf.y':>8}  {'dY':>7}  {'ctrl.z':>8}  {'surf.z':>8}  {'dZ':>7}")

for i, row in enumerate(uv_0.rows):
    rn = row_names[i] if i < len(row_names) else f"row_{i}"
    u_p = uks_raw[i]
    for j in (H2_j, T2_j):
        ctrl = row[j]
        sp   = uv_0.nurb.value(u_p, vks_raw[j])    # returns Base.Vector
        dY   = sp.y - ctrl.y
        dZ   = sp.z - ctrl.z
        print(f"{rn:<10}  {v_names[j]:<5}  {ctrl.y:>8.2f}  {sp.y:>8.2f}  {dY:>+7.3f}  "
              f"{ctrl.z:>8.2f}  {sp.z:>8.2f}  {dZ:>+7.3f}")

# -----------------------------------------------------------------------
# xs_8 single-row detail — all columns
# -----------------------------------------------------------------------
xs8_i = 9   # rows[9] = xs_8 row
print(f"\n=== xs_8 row detail (u_param={uks_raw[xs8_i]:.4f}) ===")
print(f"{'j':<3}  {'name':<5}  {'ctrl.x':>8}  {'ctrl.y':>8}  {'ctrl.z':>8}  "
      f"{'surf.x':>8}  {'surf.y':>8}  {'surf.z':>8}  {'dY':>7}  {'dZ':>7}")
for j, (ctrl, vn) in enumerate(zip(uv_0.rows[xs8_i], v_names)):
    sp = uv_0.nurb.value(uks_raw[xs8_i], vks_raw[j])
    print(f"{j:<3}  {vn:<5}  {ctrl.x:>8.2f}  {ctrl.y:>8.2f}  {ctrl.z:>8.2f}  "
          f"{sp.x:>8.2f}  {sp.y:>8.2f}  {sp.z:>8.2f}  {sp.y-ctrl.y:>+7.3f}  {sp.z-ctrl.z:>+7.3f}")

# -----------------------------------------------------------------------
# xs_8 scalar diagnosis (T2 vs H2 edge)
# -----------------------------------------------------------------------
sc = xs_base.xs_8
import last_insole
print(f"\n=== xs_8 insole-edge check ===")
print(f"  HH2={sc.HH2:.2f}  TT2={sc.TT2:.2f}  diff(T2-H2)={sc.TT2-sc.HH2:+.2f}  "
      f"(positive=T2 outside, negative=T2 inside)")
intersect_x = last_insole.insole_dwg.C.x + (xs_base.g_B2 - xs_base.g_H).dot(xs_base.g_uHJ)
print(f"  intersect_x={intersect_x:.2f}  (xs_8 plane X in insole coords)")

# -----------------------------------------------------------------------
# uIso rings: actual surface cross-section curves at each row's u param.
# These are the true surface profiles — not approximations from nurb.value().
# nurb.uIso(u) returns a BSplineCurve; ring.value(v) gives exact surface points.
# -----------------------------------------------------------------------
print(f"\n=== uIso T2-H2 relative position on actual surface ===")
print(f"{'row':<10}  {'uiso_T2.y':>10}  {'uiso_H2.y':>10}  {'T2-H2':>8}  (- = T2 outside H2)")

doc       = App.ActiveDocument
iso_shapes = []
for i, row in enumerate(uv_0.rows):
    rn   = row_names[i] if i < len(row_names) else f"row_{i}"
    ring = uv_0.nurb.uIso(uks_raw[i])          # BSplineCurve at this u slice
    iso_shapes.append(ring.toShape())
    pt_T2 = ring.value(vks_raw[T2_j])
    pt_H2 = ring.value(vks_raw[H2_j])
    diff  = pt_T2.y - pt_H2.y                  # negative = T2 more lateral (correct)
    flag  = "✓" if diff < 0 else "✗ INSIDE"
    print(f"{rn:<10}  {pt_T2.y:>10.3f}  {pt_H2.y:>10.3f}  {diff:>+8.3f}  {flag}")

obj_name = "uIso_rings"
obj = doc.getObject(obj_name) or doc.addObject("Part::Feature", obj_name)
obj.Shape = Part.makeCompound(iso_shapes)
doc.recompute()
print(f"\nShowing {len(iso_shapes)} uIso ring curves as '{obj_name}'")



"""
    === Surface vs Control Point  (u_count=11, v_count=10) ===
14:54:18  row         col      ctrl.y    surf.y       dY    ctrl.z    surf.z       dZ
14:54:18  heel_end    H2        -0.10     -0.10   +0.000     38.10     38.10   +0.000
14:54:18  heel_end    T2        -0.10     -0.10   -0.000     70.23     69.56   -0.670
14:54:18  xs_0        H2       -21.39    -15.81   +5.586     38.00     37.54   -0.456
14:54:18  xs_0        T2       -26.44    -16.63   +9.805     66.57     67.25   +0.688
14:54:18  xs_1        H2       -33.47    -31.51   +1.958     32.35     33.26   +0.917
14:54:18  xs_1        T2       -35.65    -30.40   +5.248     59.54     61.51   +1.967
14:54:18  xs_2        H2       -35.32    -35.56   -0.246     31.48     31.18   -0.295
14:54:18  xs_2        T2       -38.28    -34.16   +4.118     51.70     56.03   +4.327
14:54:18  xs_3        H2       -39.76    -41.75   -1.990     27.88     24.34   -3.540
14:54:18  xs_3        T2       -43.70    -40.87   +2.839     44.49     41.86   -2.633
14:54:18  xs_4        H2       -48.05    -48.44   -0.391     14.10     10.66   -3.448
14:54:18  xs_4        T2       -52.06    -47.61   +4.447     36.12     31.51   -4.616
14:54:18  xs_5        H2       -49.34    -48.92   +0.420      5.10      5.95   +0.855
14:54:18  xs_5        T2       -53.52    -48.23   +5.291     33.99     29.25   -4.739
14:54:18  xs_6        H2       -45.29    -46.68   -1.394      6.52      6.08   -0.440
14:54:18  xs_6        T2       -50.23    -46.32   +3.917     33.34     28.72   -4.618
14:54:18  xs_7        H2       -37.45    -36.62   +0.826     11.43     11.57   +0.144
14:54:18  xs_7        T2       -41.95    -36.42   +5.524     33.40     29.48   -3.921
14:54:18  xs_8        H2       -21.93    -16.88   +5.050     18.26     18.12   -0.143
14:54:18  xs_8        T2       -21.16    -15.67   +5.492     34.33     31.50   -2.831
14:54:18  toe_end     H2        -0.10     -0.10   +0.000     20.00     20.00   +0.000
14:54:18  toe_end     T2        -0.10     -0.10   -0.000     35.31     32.41   -2.900
14:54:18
=== xs_8 row detail (u_param=0.9552) ===
14:54:18  j    name     ctrl.x    ctrl.y    ctrl.z    surf.x    surf.y    surf.z       dY       dZ
14:54:18  0    H2       279.23    -21.93     18.26    281.81    -16.88     18.12   +5.050   -0.143
14:54:18  1    H3       279.77      0.00     15.31    281.96      9.41     17.31   +9.408   +2.001
14:54:18  2    H1       279.23     22.57     18.26    281.81     17.16     18.12   -5.409   -0.143
14:54:18  3    H1b      279.23     22.57     18.26    281.81     17.16     18.12   -5.409   -0.143
14:54:18  4    T1       276.05     18.79     35.64    277.54     14.02     37.41   -4.765   +1.766
14:54:18  5    C1       274.86     16.34     42.14    275.63     11.06     41.96   -5.282   -0.175
14:54:18  6    C        274.31      0.00     45.13    275.17      1.46     43.75   +1.463   -1.380
14:54:18  7    C2       275.14    -11.29     40.61    275.99     -7.20     41.17   +4.092   +0.559
14:54:18  8    T2       276.29    -21.16     34.33    279.10    -15.67     31.50   +5.492   -2.831
14:54:18  9    H2b      279.23    -21.93     18.26    281.81    -16.88     18.12   +5.050   -0.143
14:54:18
=== xs_8 insole-edge check ===
14:54:18    HH2=-21.93  TT2=-30.07  diff(T2-H2)=-8.14  (positive=T2 outside, negative=T2 inside)
14:54:18    intersect_x=291.63  (xs_8 plane X in insole coords)
14:54:18
Showing 11 surface T2 sample spheres as 'SurfT2_samples'
"""
