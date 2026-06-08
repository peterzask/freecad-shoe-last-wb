from dataclasses import dataclass


@dataclass
class foot_meas_raw:
    """Raw foot measurements in mm. Populated by meas_sheet; defaults are fallback values."""
    foot_len:    float = (11 + 1/8) * 25.4
    joint:       float = 25.4 * 11
    waist:       float = 25.4 * 9.5
    instep:      float = 25.4 * 9.75
    h_instep:    float = 25.4 * 10.5
    heel:        float = 25.4 * (13.5 - 0.5)
    heel_height: float = 25.4 * 1.5
    ankle:       float = 25.4 * 10
    toe_space:   float = 15.0
