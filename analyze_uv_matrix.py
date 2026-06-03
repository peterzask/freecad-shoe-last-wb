import numpy as np
import FreeCAD as App
import helper_funcs as hf
import uv_0


def analyze_uv_matrix(matrix,
                       planarity_tol  = 0.5,
                       shear_min      = 20.0,
                       aspect_max     = 15.0,
                       curvature_tol  = 25.0):
    """
    Quantitative surface quality analysis of a U×V control-point grid.

    matrix        : numpy array (U, V, 3)
    planarity_tol : max allowed out-of-plane distance per quad (mm)
    shear_min     : min allowed grid angle between u/v edges (degrees)
    aspect_max    : max allowed longest/shortest edge ratio per quad
    curvature_tol : max allowed change-in-normal-angle between adjacent quads (degrees)
                    — detects creases / abrupt curvature changes
    """
    u_len, v_len, _ = matrix.shape
    n_patches = (u_len - 1) * (v_len - 1)
    print(f"\nAnalyzing {u_len}×{v_len} grid  ({n_patches} quads)")
    print("=" * 65)

    planarity = np.zeros((u_len - 1, v_len - 1))
    shear     = np.zeros((u_len - 1, v_len - 1))
    aspect    = np.zeros((u_len - 1, v_len - 1))
    normals   = np.zeros((u_len - 1, v_len - 1, 3))

    for i in range(u_len - 1):
        for j in range(v_len - 1):
            p00 = matrix[i,   j  ]
            p10 = matrix[i+1, j  ]
            p01 = matrix[i,   j+1]
            p11 = matrix[i+1, j+1]

            v1 = p10 - p00
            v2 = p01 - p00
            normal = np.cross(v1, v2)
            nlen   = np.linalg.norm(normal)

            if nlen > 1e-7:
                un = normal / nlen
                planarity[i, j] = abs(np.dot(un, p11 - p00))
                normals[i, j]   = un
            else:
                planarity[i, j] = 0.0
                normals[i, j]   = np.array([0.0, 0.0, 1.0])

            v1l = np.linalg.norm(v1)
            v2l = np.linalg.norm(v2)
            if v1l > 1e-7 and v2l > 1e-7:
                dot   = np.clip(np.dot(v1 / v1l, v2 / v2l), -1.0, 1.0)
                angle = np.degrees(np.arccos(dot))
                shear[i, j] = min(angle, 180.0 - angle)
            else:
                shear[i, j] = 90.0

            edges = [np.linalg.norm(p10 - p00),
                     np.linalg.norm(p11 - p10),
                     np.linalg.norm(p01 - p11),
                     np.linalg.norm(p00 - p01)]
            valid = [e for e in edges if e > 1e-7]
            aspect[i, j] = max(valid) / min(valid) if len(valid) >= 2 else 1.0

    # --- Normal consistency & flip detection ---
    adj_angles = []
    flips      = []
    for i in range(u_len - 1):
        for j in range(v_len - 1):
            for di, dj in [(1, 0), (0, 1)]:
                ni, nj = i + di, j + dj
                if ni >= u_len - 1 or nj >= v_len - 1:
                    continue
                n1  = normals[i,  j ]
                n2  = normals[ni, nj]
                dot = np.clip(np.dot(n1, n2), -1.0, 1.0)
                adj_angles.append(np.degrees(np.arccos(abs(dot))))
                if dot < 0.0:
                    flips.append((i, j, ni, nj, dot))

    adj_angles = np.array(adj_angles) if adj_angles else np.array([0.0])

    # --- Curvature continuity: change in normal-change angle ---
    crease_angles = []
    crease_locs   = []

    for i in range(1, u_len - 2):
        for j in range(v_len - 1):
            d1 = np.degrees(np.arccos(np.clip(np.dot(normals[i-1, j], normals[i,   j]), -1, 1)))
            d2 = np.degrees(np.arccos(np.clip(np.dot(normals[i,   j], normals[i+1, j]), -1, 1)))
            delta = abs(d2 - d1)
            crease_angles.append(delta)
            if delta > curvature_tol:
                crease_locs.append((i, j, 'U', delta))

    for i in range(u_len - 1):
        for j in range(1, v_len - 2):
            d1 = np.degrees(np.arccos(np.clip(np.dot(normals[i, j-1], normals[i, j  ]), -1, 1)))
            d2 = np.degrees(np.arccos(np.clip(np.dot(normals[i, j  ], normals[i, j+1]), -1, 1)))
            delta = abs(d2 - d1)
            crease_angles.append(delta)
            if delta > curvature_tol:
                crease_locs.append((i, j, 'V', delta))

    crease_angles = np.array(crease_angles) if crease_angles else np.array([0.0])

    # --- Helpers ---
    def stats(arr):
        return (f"min={arr.min():7.3f}  mean={arr.mean():7.3f}  "
                f"max={arr.max():7.3f}  std={arr.std():6.3f}")

    def worst_loc(arr, find_max=True):
        idx = np.unravel_index(
            np.argmax(arr) if find_max else np.argmin(arr), arr.shape)
        return f"[U:{idx[0]}, V:{idx[1]}]"

    def pct(n):
        return f"{n}/{n_patches}  ({100*n/n_patches:.1f}%)"

    # --- Report ---
    print(f"\n1. PLANARITY  — out-of-plane twist per quad (mm)   threshold < {planarity_tol}")
    print(f"   {stats(planarity)}")
    print(f"   worst: {worst_loc(planarity)} = {planarity.max():.3f} mm")
    n_bad = int((planarity > planarity_tol).sum())
    print(f"   quads over threshold: {pct(n_bad)}")

    print(f"\n2. SHEAR ANGLE — u/v grid angle (deg)              threshold > {shear_min}°")
    print(f"   {stats(shear)}")
    print(f"   worst: {worst_loc(shear, find_max=False)} = {shear.min():.1f}°")
    n_bad = int((shear < shear_min).sum())
    print(f"   quads under threshold: {pct(n_bad)}")

    print(f"\n3. ASPECT RATIO — longest/shortest edge             threshold < {aspect_max}")
    print(f"   {stats(aspect)}")
    print(f"   worst: {worst_loc(aspect)} = {aspect.max():.2f}")
    n_bad = int((aspect > aspect_max).sum())
    print(f"   quads over threshold: {pct(n_bad)}")

    print(f"\n4. NORMAL CONSISTENCY — angle between adjacent quad normals (deg)")
    print(f"   {stats(adj_angles)}")
    if flips:
        print(f"   !! NORMAL FLIPS: {len(flips)}")
        for f in flips:
            print(f"      [{f[0]},{f[1]}] -> [{f[2]},{f[3]}]  dot={f[4]:.4f}")
    else:
        print(f"   no normal flips")

    print(f"\n5. CURVATURE CONTINUITY — change in normal-angle between adjacent quads (deg)")
    print(f"   threshold < {curvature_tol}°  (high = crease or abrupt shape change)")
    print(f"   {stats(crease_angles)}")
    if crease_locs:
        print(f"   !! CREASES: {len(crease_locs)}")
        for c in sorted(crease_locs, key=lambda x: -x[3])[:10]:
            print(f"      [U:{c[0]}, V:{c[1]}] dir={c[2]}  delta={c[3]:.1f}°")
    else:
        print(f"   no creases above threshold")

    print("\n" + "=" * 65)


def main():
    # --- flat 4×4 test grid with one introduced twist ---
    if False:
        grid = np.zeros((4, 4, 3))
        for u in range(4):
            for v in range(4):
                grid[u, v] = [u * 10.0, v * 10.0, 0.0]
        grid[2, 3, 2] = 2.5
        analyze_uv_matrix(grid, planarity_tol=0.05)

    # --- actual last surface ---
    if True:
        grid = np.zeros((uv_0.u_count, uv_0.v_count, 3))
        for u, row in enumerate(uv_0.rows):
            for v, pv in enumerate(row):
                grid[u, v] = [pv.x, pv.y, pv.z]
        analyze_uv_matrix(grid)

if __name__ == "__main__":
    main()
