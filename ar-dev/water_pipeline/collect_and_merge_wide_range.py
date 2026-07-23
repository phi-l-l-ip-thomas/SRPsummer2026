"""
collect_and_merge_wide_range.py
-----------------------------------
Collects the wide-range MOPAC energies+gradients and merges them with
the EXISTING narrow-range dataset per mode, producing a single combined
dataset spanning both regions. Per Dr. Thomas's instructions: the
original near-equilibrium points are preserved UNCHANGED, this only
adds the new wide-range points on top.

Usage:
    python3 collect_and_merge_wide_range.py
    (reads wide_range_job_index.csv, looks for existing
    dataset_1d_modeN_*_cheap_grad.dat files to merge with)
"""

import os
import re
import csv
import glob
import numpy as np

KCAL_TO_CM1 = 349.7551


def parse_mopac_aux(filepath):
    if not os.path.exists(filepath):
        return None, None
    with open(filepath) as f:
        text = f.read()
    energy = None
    m = re.search(r"HEAT_OF_FORMATION:KCAL/MOL=([\d.\-+DE]+)", text)
    if m:
        energy = float(m.group(1).replace("D", "E"))
    gradients = None
    m = re.search(
        r"GRADIENTS:KCAL/MOL/ANGSTROM\[\d+\]=\s*\n((?:\s*[-+\d.]+\s*)+)",
        text
    )
    if m:
        gradients = np.array([float(v) for v in m.group(1).split()])
    return energy, gradients


def main():
    with open("wide_range_job_index.csv") as f:
        reader = csv.DictReader(f)
        jobs = list(reader)

    normal_modes = np.load("../normal_modes.npy")

    by_mode = {}
    for job in jobs:
        mode = int(job["mode"])
        mop_file = job["input_file"]
        aux_file = os.path.basename(mop_file).replace(".mop", ".aux")

        energy_kcal, g_cart_kcal_ang = parse_mopac_aux(aux_file)
        if energy_kcal is None:
            print(f"  WARNING: no energy found in {aux_file}")
            continue

        by_mode.setdefault(mode, []).append({
            "step": float(job["step_bohr"]),
            "energy_kcal": energy_kcal,
            "g_cart_kcal_ang": g_cart_kcal_ang,
        })

    for mode, points in sorted(by_mode.items()):
        existing_files = glob.glob(f"../dataset_1d_mode{mode}_*cheap_grad.dat")
        if not existing_files:
            print(f"  WARNING: no existing narrow-range data found for mode {mode}, "
                  f"saving wide-range data alone")
            existing_rows = np.empty((0, 3))
        else:
            existing_rows = np.loadtxt(existing_files[0], comments="#")
            print(f"  Mode {mode}: found existing data {existing_files[0]} "
                  f"({len(existing_rows)} points)")

        wide_energies_kcal = np.array([p["energy_kcal"] for p in points])
        wide_min_kcal = wide_energies_kcal.min()

        wide_rows = []
        for p in points:
            e_cm1 = (p["energy_kcal"] - wide_min_kcal) * KCAL_TO_CM1
            if p["g_cart_kcal_ang"] is not None and len(p["g_cart_kcal_ang"]) == normal_modes.shape[1]:
                g_nm_kcal_ang = normal_modes[mode - 1] @ p["g_cart_kcal_ang"]
                g_nm_cm1 = g_nm_kcal_ang * KCAL_TO_CM1
            else:
                g_nm_cm1 = np.nan
            wide_rows.append([p["step"], e_cm1, g_nm_cm1])
        wide_rows = np.array(wide_rows)

        if len(existing_rows) > 0:
            existing_max_step = np.abs(existing_rows[:, 0]).max()
            wide_min_step = np.abs(wide_rows[:, 0]).min()
            gap_ratio = wide_min_step / existing_max_step if existing_max_step > 0 else float('inf')
            print(f"    Gap check: wide-range starts at step={wide_min_step:.6f}, "
                  f"existing data ends at step={existing_max_step:.6f}, "
                  f"ratio={gap_ratio:.2f}x")

        combined = np.vstack([existing_rows, wide_rows]) if len(existing_rows) > 0 else wide_rows
        combined = combined[combined[:, 0].argsort()]

        outfile = f"dataset_1d_mode{mode}_with_wide_range.dat"
        np.savetxt(outfile, combined, fmt="%16.8f",
                   header=f"step_bohr  energy_cm1  gradient_cm1_per_bohr  "
                          f"(mode {mode}, combined narrow + GAP-FREE wide-range MOPAC data)")
        print(f"  Saved {outfile}: {len(combined)} total points "
              f"({len(existing_rows)} existing + {len(wide_rows)} new wide-range)")


if __name__ == "__main__":
    main()
