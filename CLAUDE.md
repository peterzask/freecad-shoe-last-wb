# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What This Is

An open-source shoe last (form) generator for FreeCAD, intended for 3D printing and lathe-making of shoe lasts. It implements the geometric shoe last construction methods from George Koleff's *Last Designing and Making Manual* (1997), which trace back to Robert Knoefel's 1850s geometric pattern-making method. The goal is to make parametric last design accessible outside proprietary commercial tools.

## Running / Development

These are FreeCAD macro scripts — not a standalone Python project. They run inside FreeCAD:
- Macro menu → Execute Macro
- Or paste into FreeCAD's Python console

To back up working files: `./backup.sh` (copies `.cfg`, `.h`, `.py` to `zBack/` with numbered suffixes).

`helper_funcs.py` is in this directory and imported directly by all macros.

## Architecture

The data flows in one direction:

```
last_insole.py        →  cross-section macros  →  uv_0.py
last_profile.py       →  (heel, instep, waist,     (NURBS surface)
helper_funcs.py       →   joint, uHJh sections)
```

**Data layer** (`last_insole.py`, `last_profile.py`): Defines foot measurements and derived geometric constants using `@dataclass`. These are imported by every cross-section macro.

**Cross-section macros** (`slast_heel_*.py`, `slast_instep.py`, `slast_waist.py`, `slast_joint_xs.py`, `slast_uHJh_xs.py`): Each creates one section. Pattern:
1. Import insole + profile data + helper_funcs
2. Build a 4×4 placement matrix to position the section in 3D
3. Define a `*_lens_c` dataclass that computes control points (H, H1, H2, T, C, C1, C2, T1, T2…)
4. Draw circles and `Part.LineSegment` objects into a FreeCAD Sketch
5. Calculate perimeter, apply placement, recompute

**Surface macro** (`uv_0.py`): Collects control points from all four cross-sections and constructs a `Part.BSplineSurface` with explicit knot vectors and multiplicities.

**`helper_funcs.py`**: Shared utilities — `Doc_Sketch()` (find-or-create a FreeCAD Sketch), `p_vec()` (debug-print a vector), `intersect_lines()` (numpy pseudo-inverse line intersection), `line_intersect_plane()`, `point_on_plane()`, `get_plane_equation()`, and standard placement constants `xz_xy_place`/`yz_xy_place`.

## Planned Cross-Section File Naming

`readme.txt` documents a planned rename to clearer conventions:
```
xs_0_heel_0, xs_1_heel_1, xs_2_crown, xs_2_2_high_instep,
xs_3_instep, xs_4_waist, xs_5_joint, xs_6_1st_MTP_joint, xs_7_foot_length
```
Current cross-section files use older names (`slast_heel_*.py`, `slast_instep.py`, etc.).

## Key Conventions

- Control points use standard names: `H` (heel), `J` (joint), `C` (center/crown), `T` (toe), with numbered variants (`H1`, `H2`, `C1`…)
- `hf.p_vec()` is the debug printing utility for vectors
- `importlib.reload()` is used on imported modules to support iterative live development inside FreeCAD
- Measurements follow shoe-making conventions (ball, waist, instep, heel, ankle)
- Geometry references "George Koleff's drawing" — a source template for the last shape
