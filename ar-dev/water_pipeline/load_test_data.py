"""
Parser for nwchem_test_set/*.out -> test_data dict[(mode, step)] -> energy_cm1,
matching the same convention (zeroed at equilibrium, cm^-1) as
nwchem_mode{N}_expensive.dat / cheap.dat.

Filename convention (confirmed on Perlmutter):
    h2o_mode{N}_test_step{sign}{int}p{dec}_grad.out
e.g. h2o_mode1_test_stepm0p4138_grad.out
    -> mode = 1, sign = 'm' (minus), step = -0.4138

Energy convention: NWChem prints
    "Total SCF energy =    -74.950695321964"
(Hartree, absolute). We subtract the equilibrium energy and convert to cm^-1
using 1 Hartree = 219474.6314 cm^-1, matching the reference/zeroing convention
used in the expensive.dat / cheap.dat files (which are 0 at step 0).

Equilibrium reference: nwchem_pbqff_grid/h2o_equil_nwopt_grad.out
    Total SCF energy = -74.965901191187 Hartree
(confirmed correct -- the other candidate, nwchem_wide/h2o_equil_grad.out,
gives a physically implausible energy and is NOT used).
"""

import re
import os
import glob

HARTREE_TO_CM1 = 219474.6314

FILENAME_RE = re.compile(r"mode(\d+)_test_step([mp])(\d+)p(\d+)_grad")
# matches both the OLD variable-length format (h2o_mode1_test_stepm0p4138_grad.out)
# and the NEW fixed 4-decimal format from regenerate_test_set.py
# (h2o_mode1_test_stepm1p3392_grad.out) -- same pattern, works for both


def parse_step_from_filename(filename):
    """h2o_mode1_test_stepm0p4138_grad.out -> (mode=1, step=-0.4138)"""
    m = FILENAME_RE.search(filename)
    if m is None:
        return None, None
    mode = int(m.group(1))
    sign = -1.0 if m.group(2) == "m" else 1.0
    intpart, decpart = m.group(3), m.group(4)
    step = sign * float(f"{intpart}.{decpart}")
    return mode, step


def parse_scf_energy(out_path):
    """Return the LAST 'Total SCF energy' value in Hartree (final/converged)."""
    energy = None
    with open(out_path) as f:
        for line in f:
            if "Total SCF energy" in line:
                # e.g. "         Total SCF energy =    -74.950695321964"
                energy = float(line.split("=")[-1].strip())
    return energy


def get_equilibrium_energy(eq_path="nwchem_pbqff_grid/h2o_equil_nwopt_grad.out"):
    e_eq = parse_scf_energy(eq_path)
    if e_eq is None:
        raise RuntimeError(f"Could not parse equilibrium energy from {eq_path}")
    return e_eq


def load_test_points(test_dir="nwchem_test_set_v2",
                      eq_path="nwchem_pbqff_grid/h2o_equil_nwopt_grad.out",
                      modes=(1, 2, 3), verbose=True):
    """Returns dict[(mode, step)] -> energy_cm1, relative to equilibrium."""
    e_eq = get_equilibrium_energy(eq_path)
    if verbose:
        print(f"[test] equilibrium energy: {e_eq:.6f} Hartree "
              f"(from {eq_path})")

    test_data = {}
    out_files = sorted(glob.glob(os.path.join(test_dir, "*.out")))
    skipped = 0
    for path in out_files:
        fname = os.path.basename(path)
        mode, step = parse_step_from_filename(fname)
        if mode is None or mode not in modes:
            skipped += 1
            continue
        e_abs = parse_scf_energy(path)
        if e_abs is None:
            print(f"[WARN] no SCF energy found in {path}, skipping")
            skipped += 1
            continue
        e_rel_cm1 = (e_abs - e_eq) * HARTREE_TO_CM1
        test_data[(mode, step)] = e_rel_cm1

    if verbose:
        for mode in modes:
            n = sum(1 for (m, s) in test_data if m == mode)
            print(f"[test] mode {mode}: {n} points")
        print(f"[test] total: {len(test_data)} points, {skipped} skipped")

    return test_data


if __name__ == "__main__":
    test_data = load_test_points()
    print("\nSample entries:")
    for k in sorted(test_data.keys())[:10]:
        print(f"  {k} -> {test_data[k]:.3f} cm^-1")
