"""
generate_3d_points.py
-----------------------
Generates 3D displacement MOPAC input files for water -- points where
THREE normal mode coordinates are displaced simultaneously.

For water's single 3-mode combination (1,2,3), generates:
  - Training points: Sobol sequence in (q1, q2, q3) space
  - Test points: different random seed, genuinely held out

Usage:
    python3 generate_3d_points.py --mol water --n-train 64 --n-test 32
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
3D point: modes {mode_i}, {mode_j}, {mode_k}
{geometry}
"""


def q_to_bohr(q, freq_cm1, eigenvector_per_atom, atom_masses_amu):
    omega_hartree = freq_cm1 / HARTREE_TO_CM1
    masses_au = np.asarray(atom_masses_amu) * AMU_TO_AU
    mw_norm = np.sqrt(np.sum(masses_au[:, None] * eigenvector_per_atom**2))
    return (q / np.sqrt(omega_hartree)) / mw_norm


def displace_geometry(geometry, vecs, steps_bohr):
    """Displace along THREE normal modes simultaneously."""
    N = geometry.shape[0]
    disp = geometry.copy()
    for vec, step in zip(vecs, steps_bohr):
        disp = disp + (step * BOHR_TO_ANGSTROM) * vec.reshape(N, 3)
    return disp


def write_mopac_input(filepath, title, mode_i, mode_j, mode_k,
                       atom_labels, geometry):
    geom_lines = [
        f"  {label:4s}  {xyz[0]:14.8f} 1  {xyz[1]:14.8f} 1  {xyz[2]:14.8f} 1"
        for label, xyz in zip(atom_labels, geometry)
    ]
    content = MOPAC_TEMPLATE.format(
        title=title, mode_i=mode_i, mode_j=mode_j, mode_k=mode_k,
        geometry="\n".join(geom_lines)
    )
    with open(filepath, "w") as f:
        f.write(content)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--mol", type=str, default="water")
    parser.add_argument("--n-train", type=int, default=64)
    parser.add_argument("--n-test", type=int, default=32)
    parser.add_argument("--q-max", type=float, default=3.0)
    parser.add_argument("--outdir", type=str, default="3d_mopac_inputs")
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    geometry = np.load("geometry.npy")
    atom_labels = np.load("atom_labels.npy")
    normal_modes = np.load("normal_modes.npy")
    frequencies = np.load("frequencies.npy")
    ATOMIC_MASSES = {"H": 1.007825, "O": 15.994910, "N": 14.003074, "C": 12.0}
    atom_masses = np.array([ATOMIC_MASSES[l] for l in atom_labels])
    n_atoms = len(atom_labels)

    os.makedirs(args.outdir, exist_ok=True)

    # Water: only one 3-mode combination
    mode_triples = [(0, 1, 2)]

    print(f"\n=== 3D displacement generation: {args.mol} ===")
    print(f"  n_train={args.n_train}, n_test={args.n_test}, q_max=+/-{args.q_max}\n")

    all_jobs = []
    job_num = 0

    for mi, mj, mk in mode_triples:
        mode_i, mode_j, mode_k = mi+1, mj+1, mk+1
        freqs = [frequencies[mi], frequencies[mj], frequencies[mk]]
        vecs = [normal_modes[mi].reshape(n_atoms, 3),
                normal_modes[mj].reshape(n_atoms, 3),
                normal_modes[mk].reshape(n_atoms, 3)]

        # Sobol for training, random for test
        sampler = qmc.Sobol(d=3, seed=args.seed)
        train_q = qmc.scale(sampler.random(args.n_train),
                            [-args.q_max]*3, [args.q_max]*3)
        rng = np.random.RandomState(args.seed + 999)
        test_q = rng.uniform(-args.q_max, args.q_max, (args.n_test, 3))

        for split, q_points in [("train", train_q), ("test", test_q)]:
            for k, (qi, qj, qk) in enumerate(q_points):
                steps = [
                    q_to_bohr(qi, freqs[0], vecs[0], atom_masses),
                    q_to_bohr(qj, freqs[1], vecs[1], atom_masses),
                    q_to_bohr(qk, freqs[2], vecs[2], atom_masses),
                ]
                disp_geom = displace_geometry(geometry, vecs, steps)
                label = f"m{mode_i}m{mode_j}m{mode_k}_{split}{k:03d}"
                title = f"{args.mol}_{label}"
                filepath = os.path.join(args.outdir, f"{title}.mop")
                write_mopac_input(filepath, title, mode_i, mode_j, mode_k,
                                  atom_labels, disp_geom)
                all_jobs.append({
                    "job_num": job_num,
                    "mode_i": mode_i, "mode_j": mode_j, "mode_k": mode_k,
                    "q_i": qi, "q_j": qj, "q_k": qk,
                    "step_i_bohr": steps[0], "step_j_bohr": steps[1],
                    "step_k_bohr": steps[2],
                    "split": split, "input_file": filepath
                })
                job_num += 1

        print(f"  Triple ({mode_i},{mode_j},{mode_k}): "
              f"{args.n_train + args.n_test} total points")

    with open("3d_job_index.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=all_jobs[0].keys())
        w.writeheader()
        w.writerows(all_jobs)

    print(f"\n  Generated {job_num} MOPAC inputs in {args.outdir}/")
    print(f"  Saved 3d_job_index.csv")


if __name__ == "__main__":
    main()
