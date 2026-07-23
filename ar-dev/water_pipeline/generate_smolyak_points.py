"""
generate_smolyak_points.py
-----------------------------
Generates Smolyak sparse grid displacement points for multidimensional
PES sampling, as an alternative to the Sobol sequence we've been using.

Smolyak quadrature uses nested Clenshaw-Curtis points:
- Dense sampling along coordinate axes (1D cuts)
- Sparser sampling at off-axis combinations
- Nested grids: higher levels contain all lower-level points
- Point count grows as O(n * log(n)^(d-1)) vs O(n^d) for tensor product

This is exactly what Dr. Thomas suggested (July 1 meeting) as a better
3D sampling strategy.

Usage:
    python3 generate_smolyak_points.py --mol water --level 2 --modes 1 2 3
    python3 generate_smolyak_points.py --mol water --level 2 --modes 1 2  # 2D
"""

import os
import csv
import argparse
import numpy as np
from itertools import product as iproduct

AMU_TO_AU = 1822.888486
BOHR_TO_ANGSTROM = 0.529177
HARTREE_TO_CM1 = 219474.63

MOPAC_TEMPLATE = """1SCF GRADIENTS AUX(PRECISION=14 COMP) PM7 CHARGE=0
{title}
Smolyak level {level} point: modes {modes}
{geometry}
"""


def cc_points(level):
    """Clenshaw-Curtis points for a given level (nested, on [-1,1])."""
    if level == 0:
        return np.array([0.0])
    n = 2**level + 1
    return np.array([-np.cos(np.pi * i / (n-1)) for i in range(n)])


def smolyak_grid(d, max_level, q_max):
    """
    Build Smolyak sparse grid for d dimensions on [-q_max, q_max]^d.
    Uses the standard Smolyak formula with nested Clenshaw-Curtis nodes.
    """
    points = set()
    level_range = range(max_level + 1)

    for indices in iproduct(level_range, repeat=d):
        s = sum(indices)
        if max_level <= s <= max_level + d - 1:
            grids = [cc_points(i) for i in indices]
            for combo in iproduct(*grids):
                # Round to avoid floating point duplicates
                pt = tuple(round(x * q_max, 10) for x in combo)
                points.add(pt)

    return np.array(sorted(points))


def q_to_bohr(q, freq_cm1, eigenvector_per_atom, atom_masses_amu):
    omega_hartree = freq_cm1 / HARTREE_TO_CM1
    masses_au = np.asarray(atom_masses_amu) * AMU_TO_AU
    mw_norm = np.sqrt(np.sum(masses_au[:, None] * eigenvector_per_atom**2))
    return (q / np.sqrt(omega_hartree)) / mw_norm


def write_mopac_input(filepath, title, modes, level, atom_labels, geometry):
    geom_lines = [
        f"  {label:4s}  {xyz[0]:14.8f} 1  {xyz[1]:14.8f} 1  {xyz[2]:14.8f} 1"
        for label, xyz in zip(atom_labels, geometry)
    ]
    content = MOPAC_TEMPLATE.format(
        title=title, level=level,
        modes=' '.join(str(m) for m in modes),
        geometry="\n".join(geom_lines)
    )
    with open(filepath, "w") as f:
        f.write(content)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--mol", type=str, default="water")
    parser.add_argument("--level", type=int, default=2,
                        help="Smolyak level (1=coarse, 2=medium, 3=fine)")
    parser.add_argument("--modes", type=int, nargs="+", required=True,
                        help="Mode indices (1-based)")
    parser.add_argument("--q-max", type=float, default=3.0)
    parser.add_argument("--outdir", type=str, default=None)
    parser.add_argument("--test-fraction", type=float, default=0.25,
                        help="Fraction of points to hold out as test set")
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    d = len(args.modes)
    outdir = args.outdir or f"smolyak_l{args.level}_{'_'.join(str(m) for m in args.modes)}"
    os.makedirs(outdir, exist_ok=True)

    geometry = np.load("geometry.npy")
    atom_labels = np.load("atom_labels.npy")
    normal_modes = np.load("normal_modes.npy")
    frequencies = np.load("frequencies.npy")
    ATOMIC_MASSES = {"H": 1.007825, "O": 15.994910, "N": 14.003074, "C": 12.0}
    atom_masses = np.array([ATOMIC_MASSES[l] for l in atom_labels])
    n_atoms = len(atom_labels)

    # Generate Smolyak grid
    q_grid = smolyak_grid(d, args.level, args.q_max)
    print(f"\n=== Smolyak grid: {args.mol}, modes {args.modes} ===")
    print(f"  Level: {args.level}, d={d}, q_max=+/-{args.q_max}")
    print(f"  Total grid points: {len(q_grid)}")

    # Split into train/test
    rng = np.random.RandomState(args.seed)
    n_test = max(1, int(len(q_grid) * args.test_fraction))
    test_idx = rng.choice(len(q_grid), n_test, replace=False)
    train_idx = np.setdiff1d(np.arange(len(q_grid)), test_idx)
    print(f"  Train: {len(train_idx)}, Test: {len(test_idx)}")

    mode_indices = [m - 1 for m in args.modes]
    freqs = [frequencies[i] for i in mode_indices]
    vecs = [normal_modes[i].reshape(n_atoms, 3) for i in mode_indices]

    all_jobs = []
    for split, indices in [("train", train_idx), ("test", test_idx)]:
        for k, idx in enumerate(indices):
            q_vals = q_grid[idx]
            steps_bohr = [q_to_bohr(q_vals[j], freqs[j], vecs[j], atom_masses)
                          for j in range(d)]

            # Displace geometry along all modes simultaneously
            disp_geom = geometry.copy()
            for j in range(d):
                disp_geom = disp_geom + \
                    (steps_bohr[j] * BOHR_TO_ANGSTROM) * vecs[j]

            label = f"sm{'_'.join(f'm{m}' for m in args.modes)}_{split}{k:03d}"
            title = f"{args.mol}_{label}"
            filepath = os.path.join(outdir, f"{title}.mop")
            write_mopac_input(filepath, title, args.modes, args.level,
                              atom_labels, disp_geom)

            job = {"split": split, "input_file": filepath}
            for j, m in enumerate(args.modes):
                job[f"mode_{m}"] = args.modes[j]
                job[f"q_{m}"] = q_vals[j]
                job[f"step_{m}_bohr"] = steps_bohr[j]
            all_jobs.append(job)

    with open("smolyak_job_index.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=all_jobs[0].keys())
        w.writeheader()
        w.writerows(all_jobs)

    print(f"  Generated {len(all_jobs)} MOPAC inputs in {outdir}/")
    print(f"  Saved smolyak_job_index.csv")


if __name__ == "__main__":
    main()
