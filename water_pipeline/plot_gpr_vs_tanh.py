"""
plot_gpr_vs_tanh.py
----------------------
Per Dr. Thomas's item 3 (June 30): plots the tanh sum-of-products fit
on the same graph as the GPR fit and the real MOPAC data, so we can
visually see how well the tanh basis represents the GPR surface.

Usage:
    python3 plot_gpr_vs_tanh.py \\
        --gpr-npz sklearn_gpr_optimal_mode1.npz \\
        --gpr-joblib sklearn_gpr_optimal_mode1.joblib \\
        --alphas-file alphas_water.dat \\
        --fdat-prefix f \\
        --molecule water \\
        --mode 1 --freq 2170.10 --mw-norm 42.695
"""

import argparse
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

HARTREE_TO_CM1 = 219474.63


def load_tanh_coeffs(fdat_prefix, molecule, mode, max_order=8):
    """Load all f1..f8 coefficients for this mode from the fN<mol>.dat files.
    Format: fN files have N mode indices followed by a coefficient.
    For 1D single-mode terms, all N indices are the same mode number."""
    coeffs = {}
    for order in range(1, max_order + 1):
        fname = f"{fdat_prefix}{order}{molecule}.dat"
        try:
            with open(fname) as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith("#"):
                        continue
                    # Remove Fortran d0/D0 notation before splitting
                    parts = line.replace("d0", "").replace("D0", "").split()
                    # fN files have N mode indices + 1 coefficient = N+1 parts
                    # For single-mode terms, all mode indices equal this mode
                    if len(parts) == order + 1:
                        indices = [int(p) for p in parts[:order]]
                        c = float(parts[order])
                        if all(idx == mode for idx in indices):
                            coeffs[order] = c
        except FileNotFoundError:
            pass
    return coeffs


def eval_tanh_sop(q_bohr, alpha, coeffs):
    """Evaluate the tanh sum-of-products at q_bohr values."""
    t = np.tanh(alpha * q_bohr)
    V = np.zeros_like(q_bohr)
    for order, c in coeffs.items():
        V += c * t**order
    return V


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--gpr-npz", type=str, required=True)
    parser.add_argument("--gpr-joblib", type=str, required=True)
    parser.add_argument("--alphas-file", type=str, required=True)
    parser.add_argument("--fdat-prefix", type=str, default="f")
    parser.add_argument("--molecule", type=str, required=True)
    parser.add_argument("--mode", type=int, required=True)
    parser.add_argument("--freq", type=float, required=True)
    parser.add_argument("--mw-norm", type=float, required=True)
    parser.add_argument("--outfile", type=str, default=None)
    args = parser.parse_args()

    import joblib
    gpr = joblib.load(args.gpr_joblib)

    data = np.load(args.gpr_npz)
    X_train = data["X_train"]
    y_train = data["y_train"]
    e_zero = y_train.min()

    # Load alpha for this mode
    alphas_data = np.loadtxt(args.alphas_file)
    if alphas_data.ndim == 1:
        alphas_data = alphas_data.reshape(1, -1)
    alpha_row = alphas_data[alphas_data[:, 0] == args.mode]
    if len(alpha_row) == 0:
        raise ValueError(f"Mode {args.mode} not found in {args.alphas_file}")
    alpha = float(alpha_row[0, 1])
    print(f"Mode {args.mode}: alpha={alpha:.6f}")

    # Load tanh coefficients
    coeffs = load_tanh_coeffs(args.fdat_prefix, args.molecule, args.mode)
    print(f"  Loaded {len(coeffs)} tanh terms: orders {sorted(coeffs.keys())}")

    # Dense grid for plotting
    margin = 0.15 * (X_train.max() - X_train.min())
    q_bohr_grid = np.linspace(X_train.min() - margin, X_train.max() + margin, 400)

    # GPR predictions
    V_gpr = gpr.predict(q_bohr_grid.reshape(-1, 1)) - e_zero

    # Tanh SOP predictions
    V_tanh = eval_tanh_sop(q_bohr_grid, alpha, coeffs)

    # Convert q_bohr to dimensionless q for x-axis
    omega_hartree = args.freq / HARTREE_TO_CM1
    q_dim_grid = (q_bohr_grid * args.mw_norm) * np.sqrt(omega_hartree)
    q_dim_train = (X_train * args.mw_norm) * np.sqrt(omega_hartree)

    # Harmonic reference
    V_harmonic = args.freq * 0.5 * q_dim_grid ** 2

    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(8, 9),
                                    gridspec_kw={"height_ratios": [3, 1]})

    # Main comparison plot
    ax1.plot(q_dim_grid, V_gpr, "-", lw=2, color="tab:blue",
             label="sklearn GPR (optimal length scale)", zorder=3)
    ax1.plot(q_dim_grid, V_tanh, "--", lw=1.8, color="tab:red",
             label=f"tanh SOP (alpha={alpha:.3f})", zorder=3)
    ax1.plot(q_dim_grid, V_harmonic, ":", lw=1.2, color="gray",
             label="reference harmonic", alpha=0.7, zorder=1)
    ax1.scatter(q_dim_train, y_train - e_zero, color="tab:green", s=40,
                zorder=4, label="real MOPAC+grad data", edgecolor="k", lw=0.5)

    e_margin = 0.15 * (y_train.max() - y_train.min())
    ax1.set_ylim(y_train.min() - e_zero - e_margin, y_train.max() - e_zero + e_margin)
    ax1.set_title(f"Mode {args.mode} ({args.freq:.1f} cm$^{{-1}}$) -- GPR vs tanh SOP")
    ax1.set_ylabel("E (cm$^{-1}$)")
    ax1.legend(fontsize=9)
    ax1.set_xlabel("Dimensionless q")

    # Residual plot (GPR - tanh SOP)
    residual = V_gpr - V_tanh
    ax2.plot(q_dim_grid, residual, "-", lw=1.5, color="tab:purple")
    ax2.axhline(0, color="gray", lw=0.8, ls="--")
    ax2.set_xlabel("Dimensionless q")
    ax2.set_ylabel("GPR - tanh (cm$^{-1}$)")
    ax2.set_title("Residual: GPR minus tanh SOP")

    fig.tight_layout()
    outfile = args.outfile or f"gpr_vs_tanh_mode{args.mode}.png"
    fig.savefig(outfile, dpi=150)
    print(f"  Saved: {outfile}")

    # Report the max residual in the data range
    mask = (q_bohr_grid >= X_train.min()) & (q_bohr_grid <= X_train.max())
    print(f"  Max |residual| in data range: {np.abs(residual[mask]).max():.2f} cm-1")


if __name__ == "__main__":
    main()
