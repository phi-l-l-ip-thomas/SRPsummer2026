"""
Loader for hf_data / lf_data from nwchem_mode{N}_expensive.dat and
nwchem_mode{N}_cheap.dat, matching the format:

    # step_bohr  energy_cm1
    -1.64900000  41749.870951
    ...

Returns dict[(mode, step)] -> energy, exactly what mfgp.per_mode_rmse_report
expects.
"""

import numpy as np
import glob
import os


def load_dat_file(path):
    """Parse a two-column (step, energy) whitespace-separated .dat file,
    skipping comment lines starting with '#'."""
    steps, energies = [], []
    with open(path) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            parts = line.split()
            if len(parts) < 2:
                continue
            steps.append(float(parts[0]))
            energies.append(float(parts[1]))
    return np.array(steps), np.array(energies)


def load_expensive_points(data_dir=".", modes=(1, 2, 3)):
    """Returns dict[(mode, step)] -> energy from nwchem_mode{N}_expensive.dat"""
    hf_data = {}
    for mode in modes:
        path = os.path.join(data_dir, f"nwchem_mode{mode}_expensive.dat")
        if not os.path.exists(path):
            print(f"[WARN] missing {path}, skipping mode {mode}")
            continue
        steps, energies = load_dat_file(path)
        for s, e in zip(steps, energies):
            hf_data[(mode, s)] = e
        print(f"[HF] mode {mode}: {len(steps)} points from {path}")
    return hf_data


def load_cheap_points(data_dir=".", modes=(1, 2, 3)):
    """Returns dict[(mode, step)] -> energy from nwchem_mode{N}_cheap.dat"""
    lf_data = {}
    for mode in modes:
        path = os.path.join(data_dir, f"nwchem_mode{mode}_cheap.dat")
        if not os.path.exists(path):
            print(f"[WARN] missing {path}, skipping mode {mode}")
            continue
        steps, energies = load_dat_file(path)
        for s, e in zip(steps, energies):
            lf_data[(mode, s)] = e
        print(f"[LF] mode {mode}: {len(steps)} points from {path}")
    return lf_data


if __name__ == "__main__":
    # quick sanity check when run directly on Perlmutter
    hf = load_expensive_points(".")
    lf = load_cheap_points(".")
    print(f"\nTotal HF points: {len(hf)}")
    print(f"Total LF points: {len(lf)}")
    print("\nSample HF entries:")
    for k in list(hf.keys())[:3]:
        print(f"  {k} -> {hf[k]}")
    print("\nSample LF entries:")
    for k in list(lf.keys())[:3]:
        print(f"  {k} -> {lf[k]}")
