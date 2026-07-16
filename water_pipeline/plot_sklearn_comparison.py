
"""
plot_sklearn_comparison.py
-------------------------------
Plots the scikit-learn GPR fit against the real data and reference
harmonic oscillator, same format as our other comparison plots, to
check directly whether sklearn's GPR shows the same edge oscillations
our custom implementation does.
"""

import argparse
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

HARTREE_TO_CM1 = 219474.63


def reference_harmonic_energy_cm1(q_dimensionless, freq_cm1):
    return freq_cm1 * 0.5 * q_dimensionless ** 2


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--sklearn-npz", type=str, required=True)
    parser.add_argument("--freq", type=float, required=True)
    parser.add_argument("--mw-norm", type=float, required=True,
                        help="Mass-weighted norm for this mode (to convert "
                             "Bohr displacement to dimensionless q)")
    parser.add_argument("--outfile", type=str, default="sklearn_comparison.png")
    args = parser.parse_args()

    data = np.load(args.sklearn_npz)
    q_grid_bohr = data["q_grid"]
    V_pred = data["V_pred"]
    V_std = data["V_std"]
    X_train = data["X_train"]
    y_train = data["y_train"]

    omega_hartree = args.freq / HARTREE_TO_CM1
    q_grid = (q_grid_bohr * args.mw_norm) * np.sqrt(omega_hartree)
    q_train = (X_train * args.mw_norm) * np.sqrt(omega_hartree)
    V_harmonic = reference_harmonic_energy_cm1(q_grid, args.freq)

    e_zero = y_train.min()

    fig, ax = plt.subplots(figsize=(7, 5))
    ax.plot(q_grid, V_pred - e_zero, "-", lw=1.5, color="tab:purple", label="sklearn GPR fit", zorder=2)
    ax.fill_between(q_grid, V_pred - e_zero - 2*V_std, V_pred - e_zero + 2*V_std,
                    color="tab:purple", alpha=0.15, zorder=1)
    ax.plot(q_grid, V_harmonic, "--", lw=1.2, color="gray", label="reference harmonic", alpha=0.7, zorder=1)
    ax.scatter(q_train, y_train - e_zero, color="tab:green", s=50, zorder=3,
               label="Real MOPAC+grad data", edgecolor="k", linewidth=0.5)

    e_margin = 0.15 * (y_train.max() - y_train.min())
    ax.set_ylim(y_train.min() - e_zero - e_margin, y_train.max() - e_zero + e_margin)

    ax.set_title(f"sklearn GaussianProcessRegressor comparison ({args.freq:.1f} cm$^{{-1}}$)")
    ax.set_xlabel("Dimensionless q")
    ax.set_ylabel("E (cm$^{-1}$)")
    ax.legend(fontsize=9)
    fig.tight_layout()
    fig.savefig(args.outfile, dpi=150)
    print(f"Saved: {args.outfile}")


if __name__ == "__main__":
    main()
