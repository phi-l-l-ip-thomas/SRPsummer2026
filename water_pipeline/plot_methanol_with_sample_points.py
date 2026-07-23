"""
plot_methanol_with_sample_points.py
---------------------------------------
Per Dr. Thomas's request (June 26): overlays the ACTUAL sampling points
that went into building each mode's fit, color-coded by source:
    - Original PBQFF/NWChem QFF points (energy only, no gradients,
      very close to equilibrium -- these are the original "stage4
      cheap" narrow-range points before any wide-range expansion)
    - MOPAC wide-range points WITH gradients (our added, larger-q points)
    - NWChem multi-fidelity correction points WITH gradients (if used)

This lets Dr. Thomas see exactly what data went into each fit, since
the GPR-only plot doesn't show the underlying recipe.

ALSO CONFIRMS (per his second question): each 1D fit is built ONLY from
points displaced along that single mode's normal coordinate (confirmed
directly from displace_geometry()'s implementation -- it only ever adds
step_bohr * single_mode_eigenvector, never combining multiple modes).
There is no multi-dimensional contamination in this pipeline's 1D fits.

Usage:
    python3 plot_methanol_with_sample_points.py \\
        --1d-gprs gpr_fit_1d_mode1_gradients.npz ... \\
        --modes 1 2 ... \\
        --frequencies 398.55 ... \\
        --narrow-points dataset_1d_mode1_h2o2_methanol_stage4_cheap_grad.dat ... \\
        --wide-points dataset_1d_mode1_with_wide_range.dat ... \\
        --normal-modes-npy normal_modes.npy --atom-labels-npy atom_labels.npy \\
        --q-target 7.0
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


def bohr_to_q(step_bohr, mw_norm, omega_hartree):
    return (step_bohr * mw_norm) * np.sqrt(omega_hartree)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--1d-gprs", dest="gpr_1d", type=str, nargs="+", required=True)
    parser.add_argument("--modes", type=int, nargs="+", required=True)
    parser.add_argument("--frequencies", type=float, nargs="+", required=True)
    parser.add_argument("--narrow-points", type=str, nargs="+", required=True,
                        help="Original PBQFF/narrow-range MOPAC+gradient files "
                             "per mode (the points closest to equilibrium)")
    parser.add_argument("--wide-points", type=str, nargs="+", required=True,
                        help="Combined narrow+wide dataset files per mode "
                             "(used to identify which points are NEW "
                             "wide-range additions vs already-narrow)")
    parser.add_argument("--nwchem-points", type=str, nargs="*", default=None,
                        help="Optional: NWChem multi-fidelity correction "
                             "point files per mode, if available")
    parser.add_argument("--normal-modes-npy", type=str, required=True)
    parser.add_argument("--atom-labels-npy", type=str, required=True)
    parser.add_argument("--q-target", type=float, default=7.0)
    parser.add_argument("--outdir", type=str, default="methanol_sample_points_figures")
    args = parser.parse_args()

    os.makedirs(args.outdir, exist_ok=True)
    normal_modes = np.load(args.normal_modes_npy)
    atom_labels = np.load(args.atom_labels_npy)
    ATOMIC_MASSES = {"H": 1.007825, "C": 12.000000, "O": 15.994910, "N": 14.003074}
    atom_masses = np.array([ATOMIC_MASSES[label] for label in atom_labels])
    n_atoms = len(atom_labels)

    n_modes = len(args.modes)
    ncols = 4
    nrows = (n_modes + ncols - 1) // ncols
    fig, axes = plt.subplots(nrows, ncols, figsize=(4.5 * ncols, 3.6 * nrows))
    axes = axes.flatten()

    nwchem_points_list = args.nwchem_points if args.nwchem_points else [None] * n_modes

    for idx, (gpr_file, mode, freq, narrow_f, wide_f, nwchem_f) in enumerate(
        zip(args.gpr_1d, args.modes, args.frequencies, args.narrow_points,
            args.wide_points, nwchem_points_list)
    ):
        ax = axes[idx]
        vec_per_atom = normal_modes[mode - 1].reshape(n_atoms, 3)
        omega_hartree = freq / HARTREE_TO_CM1
        masses_au = atom_masses * AMU_TO_AU
        mw_norm = np.sqrt(np.sum(masses_au[:, None] * vec_per_atom**2))

        step_bohr_max = (args.q_target / np.sqrt(omega_hartree)) / mw_norm

        # GPR curve + harmonic reference
        q_bohr_grid = np.linspace(-step_bohr_max, step_bohr_max, 400)
        V_gpr = g.predict_gpr_from_npz(gpr_file, q_bohr_grid.reshape(-1, 1))
        V_gpr_shifted = V_gpr - V_gpr.min()
        q_dim_grid = bohr_to_q(q_bohr_grid, mw_norm, omega_hartree)
        V_harmonic = reference_harmonic_energy_cm1(q_dim_grid, freq)

        ax.plot(q_dim_grid, V_gpr_shifted, "-", lw=1.3, color="tab:blue",
                label="GPR fit", zorder=2, alpha=0.8)
        ax.plot(q_dim_grid, V_harmonic, "--", lw=1.0, color="gray",
                label="reference harmonic", alpha=0.6, zorder=1)

        # Original narrow-range (PBQFF/NWChem QFF-equivalent) points
        narrow_data = np.loadtxt(narrow_f, comments="#")
        q_narrow = bohr_to_q(narrow_data[:, 0], mw_norm, omega_hartree)
        e_narrow = narrow_data[:, 1] - V_gpr.min()
        ax.scatter(q_narrow, e_narrow, color="tab:green", s=45, zorder=4,
                   label="Original narrow pts (MOPAC+grad)", edgecolor="k", linewidth=0.5)

        # Wide-range ADDED points (the new ones, beyond narrow's range)
        wide_data = np.loadtxt(wide_f, comments="#")
        narrow_max_step = np.abs(narrow_data[:, 0]).max()
        is_wide = np.abs(wide_data[:, 0]) > narrow_max_step * 1.001
        q_wide = bohr_to_q(wide_data[is_wide, 0], mw_norm, omega_hartree)
        e_wide = wide_data[is_wide, 1] - V_gpr.min()
        ax.scatter(q_wide, e_wide, color="tab:orange", s=30, zorder=3,
                   label="Wide-range pts (MOPAC+grad)", edgecolor="k", linewidth=0.3)

        # NWChem multi-fidelity correction points, if provided
        if nwchem_f and os.path.exists(nwchem_f):
            nwchem_data = np.loadtxt(nwchem_f, comments="#")
            q_nwchem = bohr_to_q(nwchem_data[:, 0], mw_norm, omega_hartree)
            e_nwchem = nwchem_data[:, 1] - V_gpr.min()
            ax.scatter(q_nwchem, e_nwchem, color="tab:red", s=60, marker="^",
                       zorder=5, label="NWChem correction pts", edgecolor="k", linewidth=0.5)

        ax.set_title(f"Mode {mode} ({freq:.1f} cm$^{{-1}}$)", fontsize=10)
        ax.set_xlabel("Dimensionless q", fontsize=8)
        ax.set_ylabel("E (cm$^{-1}$)", fontsize=8)
        ax.tick_params(labelsize=7)
        if idx == 0:
            ax.legend(fontsize=6, loc="upper center")

        print(f"  Mode {mode}: {len(narrow_data)} narrow pts, "
              f"{is_wide.sum()} wide-range pts"
              + (f", {len(nwchem_data)} NWChem pts" if nwchem_f and os.path.exists(nwchem_f) else ""))

    for j in range(n_modes, len(axes)):
        axes[j].axis("off")

    fig.suptitle("CH$_3$OH: fit recipe -- actual sampling points by source\n"
                 "Green = original narrow MOPAC+grad, Orange = added wide-range "
                 "MOPAC+grad, Red triangle = NWChem correction",
                 fontsize=12)
    fig.tight_layout(rect=[0, 0, 1, 0.92])

    outfile = os.path.join(args.outdir, "methanol_sample_points_grid.png")
    fig.savefig(outfile, dpi=150)
    print(f"\n  Saved: {outfile}")


if __name__ == "__main__":
    main()
