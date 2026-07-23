"""
plot_data_centered.py
-------------------------
Per Dr. Thomas's request (item 1, June 29): plots the GPR fit with the
energy zero set to the DATA's own true minimum (not assumed at q=0),
and the y-axis scaled to fit the real data range (not the full
extrapolated curve) -- so the reference harmonic oscillator aligns with
the real MOPAC data, and fit quality near the center (where most data
lives) is actually visible.

It's fine if the GPR curve goes off-scale near the edges; that's
expected and informative on its own.
"""

import os
import sys
import argparse
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

OPTGPR_DIR = os.path.expanduser("~/optGPRNN")
sys.path.insert(0, OPTGPR_DIR)
import gpr_to_sop_mlcp as g

AMU_TO_AU = 1822.888486
HARTREE_TO_CM1 = 219474.63


def reference_harmonic_energy_cm1(q_dimensionless, freq_cm1):
    return freq_cm1 * 0.5 * q_dimensionless ** 2


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--gpr-file", type=str, required=True)
    parser.add_argument("--mode", type=int, required=True)
    parser.add_argument("--freq", type=float, required=True)
    parser.add_argument("--points-file", type=str, required=True,
                        help="The real combined dataset (e.g. the original "
                             "sparse-at-edges, points-concentrated-in-center "
                             "dataset from Saturday)")
    parser.add_argument("--normal-modes-npy", type=str, required=True)
    parser.add_argument("--atom-labels-npy", type=str, required=True)
    parser.add_argument("--outdir", type=str, default="centered_plot_figures")
    args = parser.parse_args()

    os.makedirs(args.outdir, exist_ok=True)
    normal_modes = np.load(args.normal_modes_npy)
    atom_labels = np.load(args.atom_labels_npy)
    ATOMIC_MASSES = {"H": 1.007825, "C": 12.000000, "O": 15.994910, "N": 14.003074}
    atom_masses = np.array([ATOMIC_MASSES[label] for label in atom_labels])
    n_atoms = len(atom_labels)

    vec_per_atom = normal_modes[args.mode - 1].reshape(n_atoms, 3)
    omega_hartree = args.freq / HARTREE_TO_CM1
    masses_au = atom_masses * AMU_TO_AU
    mw_norm = np.sqrt(np.sum(masses_au[:, None] * vec_per_atom**2))

    # Real data, used to set BOTH the energy zero AND the y-axis range
    data = np.loadtxt(args.points_file, comments="#")
    steps_real = data[:, 0]
    energies_real = data[:, 1]

    # CRITICAL: zero to the DATA's own true minimum (not q=0, not the
    # GPR's predicted minimum -- the actual lowest REAL data point)
    e_zero = energies_real.min()
    energies_real_zeroed = energies_real - e_zero

    q_real = (steps_real * mw_norm) * np.sqrt(omega_hartree)

    # GPR curve evaluated over the SAME range as the real data (not
    # extrapolated to q=+/-7) -- compute at the real data's actual q range
    q_min_data, q_max_data = q_real.min(), q_real.max()
    margin = 0.15 * (q_max_data - q_min_data)
    q_grid = np.linspace(q_min_data - margin, q_max_data + margin, 400)
    step_bohr_grid = (q_grid / np.sqrt(omega_hartree)) / mw_norm
    V_gpr = g.predict_gpr_from_npz(args.gpr_file, step_bohr_grid.reshape(-1, 1))
    V_gpr_zeroed = V_gpr - e_zero  # SAME zero as the real data, not GPR's own min

    V_harmonic = reference_harmonic_energy_cm1(q_grid, args.freq)

    fig, ax = plt.subplots(figsize=(7, 5))
    ax.plot(q_grid, V_gpr_zeroed, "-", lw=1.5, color="tab:blue", label="GPR fit", zorder=2)
    ax.plot(q_grid, V_harmonic, "--", lw=1.2, color="gray", label="reference harmonic", alpha=0.7, zorder=1)
    ax.scatter(q_real, energies_real_zeroed, color="tab:green", s=50, zorder=3,
               label="Real MOPAC+grad data", edgecolor="k", linewidth=0.5)

    # Y-AXIS SCALED TO THE REAL DATA (not the full GPR curve, which may
    # go off-scale at the edges -- that's expected and fine)
    e_margin = 0.15 * (energies_real_zeroed.max() - energies_real_zeroed.min())
    ax.set_ylim(energies_real_zeroed.min() - e_margin, energies_real_zeroed.max() + e_margin)
    ax.set_xlim(q_min_data - margin, q_max_data + margin)

    ax.set_title(f"Mode {args.mode} ({args.freq:.1f} cm$^{{-1}}$) -- "
                 f"zeroed to data minimum, y-axis spans real data")
    ax.set_xlabel("Dimensionless q")
    ax.set_ylabel("E (cm$^{-1}$)")
    ax.legend(fontsize=9)
    fig.tight_layout()

    outfile = os.path.join(args.outdir, f"mode{args.mode}_centered.png")
    fig.savefig(outfile, dpi=150)
    print(f"Saved: {outfile}")
    print(f"Data energy zero (raw): {e_zero:.4f}")
    print(f"Real data q range: [{q_min_data:.4f}, {q_max_data:.4f}]")
    print(f"Real data energy range (zeroed): [{energies_real_zeroed.min():.4f}, {energies_real_zeroed.max():.4f}]")


if __name__ == "__main__":
    main()
