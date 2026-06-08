from dataclasses import dataclass


@dataclass
class shape_params_c:
    # --- Highwater curves: fraction along K->(midpoint of J1/H1) range ---
    hw_med_pct_instep:  float = 0.85   # medial highwater position near instep
    hw_med_pct_joint:   float = 0.30   # medial highwater position near joint
    hw_lat_pct_instep:  float = 0.25   # lateral highwater position near instep
    hw_lat_pct_joint:   float = 0.25   # lateral highwater position near joint

    # --- Crown shoulder: same fractional range, above highwater ---
    crown_med_pct_instep:  float = 0.92
    crown_med_pct_joint:   float = 0.80
    crown_lat_pct_instep:  float = 0.70
    crown_lat_pct_joint:   float = 0.65
    crown_fraction:        float = 0.30  # width fraction placeholder — not yet wired to geometry

    # --- Insole crown curve Y-scale (relative to insole outline width) ---
    insole_crown_med_cf:  float = 0.70   # C1 medial poles
    insole_crown_lat_cf:  float = 0.50   # C2 lateral poles

    # --- Profile geometry ---
    toe_spring: float = 20.0   # BB1: vertical toe spring at toe tip B1 (mm)

    # --- NURBS surface ---
    nurbs_degree: int   = 2
    crisp_sole:   bool  = True

    # --- Girth compensation ---
    # NURBS surface lies inside the convex hull of its control rings (hull shrinkage).
    # Scale > 1.0 expands T1/C1/C/C2/T2 outward from H (insole contact center),
    # keeping H1/H2/H3 (insole footprint) locked, to hit target girth measurements.
    # t_boost_mm adds a direct mm offset to T1/T2 only — they pull in more than C/C1/C2
    # because they sit in the high-curvature part of the ring.
    girth_scale:  float = 1.04
    t_boost_mm:   float = 0.0


# Singleton — import this instance everywhere.
# Slider panel mutates fields, then calls build() on the affected layer(s).
shape_params = shape_params_c()
