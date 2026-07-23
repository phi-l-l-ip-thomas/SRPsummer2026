"""
generate_2d_points.py
-----------------------
Generates 2D displacement MOPAC input files for water -- points where
TWO normal mode coordinates are displaced simultaneously, needed for
fitting the 2-mode coupling terms in the PES.

For each mode pair (i,j), generates:
  - A TRAINING grid: sparse Sobol-sequence points in (q_i, q_j) space
  - A TEST grid: different random points for error evaluation

Both use the corrected mass-weighted q-to-Bohr conversion.

Usage:
    python3 generate_2d_points.py --mol water --n-train 25 --n-test 15
"""

import os
import csv
import argparse
import numpy as np
from scipy.stats import qmc

AMU_TO_AU = 1822.888486
BOHR_TO_ANGSTROM = 0.529177
HARTREE_TO_CM1 = 219474.63

MOPAC_TEMPLATE = """1SCF GRADIENTS AUX(PRECISION=14 COMP) PM7 CHARGE=0
{title}
2D coupling point: modes {mode_i} and {mode_j}
{geometry}
"""


def q_to_bohr(q, freq_cm1, eigenvector_per_atom, atom_masses_amu):
    omega_hartree = freq_cm1 / HARTREE_TO_CM1
    masses_au = np.asarray(atom_masses_amu) * AMU_TO_AU
    mw_norm = np.sqrt(np.sum(masses_au[:, None] * eigenvector_per_atom**2))
    Q_mw = q / np.sqrt(omega_hartree)
    return Q_mw / mw_norm


def displace_geometry(geometry, vec1, step1_bohr, vec2, step2_bohr):
    """Displace along TWO normal modes simultaneously."""
    step1_ang = step1_bohr * BOHR_TO_ANGSTROM
    step2_ang = step2_bohr * BOHR_TO_ANGSTROM
    N = geometry.shape[0]
    return geometry + step1_ang * vec1.reshape(N, 3) + \
                      step2_ang * vec2.reshape(N, 3)


def write_mopac_input(filepath, title, mode_i, mode_j, atom_labels, geometry):
    geom_lines = [
        f"  {label:4s}  {xyz[0]:14.8f} 1  {xyz[1]:14.8f} 1  {xyz[2]:14.8f} 1"
        for label, xyz in zip(atom_labels, geometry)
    ]
    content = MOPAC_TEMPLATE.format(
        title=title, mode_i=mode_i, mode_j=mode_j,
        geometry="\n".join(geom_lines)
    )
    with open(filepath, "w") as f:
        f.write(content)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--mol", type=str, default="water")
    parser.add_argument("--n-train", type=int, default=25,
                        help="Training points per mode pair")
    parser.add_argument("--n-test", type=int, default=15,
                        help="Test points per mode pair")
    parser.add_argument("--q-max", type=float, default=4.0,
                        help="Max |q| for each mode in the 2D grid")
    parser.add_argument("--outdir", type=str, default="2d_mopac_inputs")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--only-pair", type=str, default=None,
                        help="Only generate for this pair, e.g. '2,3'")
    args = parser.parse_args()

    geometry = np.load("geometry.npy")
    atom_labels = np.load("atom_labels.npy")
    normal_modes = np.load("normal_modes.npy")
    frequencies = np.load("frequencies.npy")
    ATOMIC_MASSES = {"H": 1.007825, "O": 15.994910, "N": 14.003074, "C": 12.0}
    atom_masses = np.array([ATOMIC_MASSES[l] for l in atom_labels])
    n_atoms = len(atom_labels)
    n_modes = len(frequencies)

    os.makedirs(args.outdir, exist_ok=True)

    mode_pairs = [(i, j) for i in range(n_modes) for j in range(i+1, n_modes)]
    if args.only_pair:
        a, b = map(int, args.only_pair.split(","))
        mode_pairs = [(a-1, b-1)]
    print(f"\n=== 2D displacement generation: {args.mol} ===")
    print(f"  Mode pairs: {[(i+1,j+1) for i,j in mode_pairs]}")
    print(f"  Training points per pair: {args.n_train}")
    print(f"  Test points per pair: {args.n_test}")
    print(f"  q range: +/-{args.q_max}\n")

    all_jobs = []
    job_num = 0

    for mode_i_idx, mode_j_idx in mode_pairs:
        mode_i = mode_i_idx + 1
        mode_j = mode_j_idx + 1
        freq_i = frequencies[mode_i_idx]
        freq_j = frequencies[mode_j_idx]
        vec_i = normal_modes[mode_i_idx].reshape(n_atoms, 3)
        vec_j = normal_modes[mode_j_idx].reshape(n_atoms, 3)

        # Sobol sequence for training points -- better coverage than random
        sampler = qmc.Sobol(d=2, seed=args.seed)
        train_q = qmc.scale(
            sampler.random(args.n_train),
            [-args.q_max, -args.q_max],
            [args.q_max, args.q_max]
        )

        # Different random seed for test points -- genuinely held-out
        rng = np.random.RandomState(args.seed + 999)
        test_q = rng.uniform(-args.q_max, args.q_max, (args.n_test, 2))

        for split, q_points in [("train", train_q), ("test", test_q)]:
            for k, (qi, qj) in enumerate(q_points):
                step_i = q_to_bohr(qi, freq_i, vec_i, atom_masses)
                step_j = q_to_bohr(qj, freq_j, vec_j, atom_masses)
                disp_geom = displace_geometry(
                    geometry,
                    normal_modes[mode_i_idx], step_i,
                    normal_modes[mode_j_idx], step_j
                )
                label = f"m{mode_i}m{mode_j}_{split}{k:03d}"
                title = f"{args.mol}_{label}"
                filepath = os.path.join(args.outdir, f"{title}.mop")
                write_mopac_input(filepath, title, mode_i, mode_j,
                                  atom_labels, disp_geom)
                all_jobs.append({
                    "job_num": job_num, "mode_i": mode_i, "mode_j": mode_j,
                    "freq_i": freq_i, "freq_j": freq_j,
                    "q_i": qi, "q_j": qj,
                    "step_i_bohr": step_i, "step_j_bohr": step_j,
                    "split": split, "input_file": filepath
                })
                job_num += 1

        n_pts = args.n_train + args.n_test
        print(f"  Pair ({mode_i},{mode_j}): {n_pts} total points "
              f"({args.n_train} train + {args.n_test} test)")

    with open("2d_job_index.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=all_jobs[0].keys())
        w.writeheader()
        w.writerows(all_jobs)

    print(f"\n  Generated {job_num} MOPAC inputs in {args.outdir}/")
    print(f"  Saved 2d_job_index.csv")


if __name__ == "__main__":
    main()
