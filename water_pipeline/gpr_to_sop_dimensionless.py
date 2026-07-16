"""
gpr_to_sop_dimensionless.py
------------------------------
Converts sklearn GPR fits to MLCP sum-of-products format, correctly
using DIMENSIONLESS normal mode coordinates (q_dim) as MLCP expects,
rather than Bohr displacements.

The conversion is:
    q_dim = q_bohr * mw_norm * sqrt(omega_hartree)

where mw_norm = sqrt(sum_atoms m_a * |e_a|^2) is the mass-weighted
norm of the normal mode eigenvector.

This produces SOP coefficients in cm-1 in dimensionless q units,
which is what MLCP's fN files require (confirmed from reference
f2water.dat, f4water.dat in MLCP samples directory).

Usage:
    python3 gpr_to_sop_dimensionless.py --molecule water \\
        --modes 1 2 3 \\
        --freqs 2170.10 4139.81 4390.84 \\
        --mw-norms 42.695 42.695 42.695 \\
        --gpr-models sklearn_gpr_optimal_mode1.joblib \\
                     sklearn_gpr_optimal_mode2.joblib \\
                     sklearn_gpr_optimal_mode3.joblib \\
        --n-terms 8 --range-fraction 0.75
"""

import argparse
import numpy as np
import joblib

HARTREE_TO_CM1 = 219474.63


def tanh_basis_matrix(q_dim, alpha, n_terms):
    t = np.tanh(alpha * q_dim)
    return np.column_stack([t**p for p in range(1, n_terms+1)])


def fit_sop_1d(q_dim, V, alpha, n_terms, ridge=0.0):
    Phi = tanh_basis_matrix(q_dim, alpha, n_terms)
    if ridge > 0:
        A = Phi.T @ Phi + ridge * np.eye(n_terms)
        b = Phi.T @ V
        c = np.linalg.solve(A, b)
    else:
        c, _, _, _ = np.linalg.lstsq(Phi, V, rcond=None)
    rmse = np.sqrt(np.mean((Phi @ c - V)**2))
    return c, rmse


def optimize_alpha(q_dim, V, n_terms, alpha_min, alpha_max,
                   n_scan=60, ridge=0.0):
    alphas = np.linspace(alpha_min, alpha_max, n_scan)
    best_rmse, best_alpha, best_c = np.inf, None, None
    for alpha in alphas:
        c, rmse = fit_sop_1d(q_dim, V, alpha, n_terms, ridge)
        if rmse < best_rmse:
            best_rmse, best_alpha, best_c = rmse, alpha, c
    # Fine scan
    step = alphas[1] - alphas[0]
    fine = np.linspace(max(alpha_min, best_alpha-step),
                       min(alpha_max, best_alpha+step), 60)
    for alpha in fine:
        c, rmse = fit_sop_1d(q_dim, V, alpha, n_terms, ridge)
        if rmse < best_rmse:
            best_rmse, best_alpha, best_c = rmse, alpha, c
    return best_alpha, best_c, best_rmse


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--molecule", type=str, required=True)
    parser.add_argument("--modes", type=int, nargs="+", required=True)
    parser.add_argument("--freqs", type=float, nargs="+", required=True)
    parser.add_argument("--mw-norms", type=float, nargs="+", required=True)
    parser.add_argument("--gpr-models", type=str, nargs="+", required=True)
    parser.add_argument("--n-terms", type=int, default=8)
    parser.add_argument("--alpha-min", type=float, default=0.05)
    parser.add_argument("--alpha-max", type=float, default=2.0)
    parser.add_argument("--ridge", type=float, default=1.0)
    parser.add_argument("--range-fraction", type=float, default=0.75)
    parser.add_argument("--n-grid", type=int, default=200)
    parser.add_argument("--outdir", type=str, default=".")
    args = parser.parse_args()

    mol = args.molecule
    print(f"\n=== GPR -> MLCP SOP (dimensionless q) for {mol} ===")
    print(f"  n_terms={args.n_terms}, range_fraction={args.range_fraction}")

    alphas_out = []
    # Collect all (mode, power, coeff) for writing
    all_terms = []  # list of (mode, power, coeff)

    for mode, freq, mw_norm, model_file in zip(
            args.modes, args.freqs, args.mw_norms, args.gpr_models):

        omega_hartree = freq / HARTREE_TO_CM1
        # Conversion: q_dim = q_bohr * mw_norm * sqrt(omega_hartree)
        scale = mw_norm * np.sqrt(omega_hartree)

        gpr = joblib.load(model_file)
        # Get training data range in Bohr
        # Predict on a dense Bohr grid, then convert to dimensionless
        # Use a reasonable range based on typical water data (q_dim ~ ±7)
        q_dim_max = 7.0 * args.range_fraction
        q_dim_grid = np.linspace(-q_dim_max, q_dim_max, args.n_grid)
        q_bohr_grid = q_dim_grid / scale

        V_gpr = gpr.predict(q_bohr_grid.reshape(-1, 1))
        e_zero = V_gpr.min()
        V_gpr = V_gpr - e_zero  # zero to minimum

        alpha, coeffs, rmse = optimize_alpha(
            q_dim_grid, V_gpr, args.n_terms,
            args.alpha_min, args.alpha_max, ridge=args.ridge)

        print(f"\n  Mode {mode} ({freq:.1f} cm-1):")
        print(f"    scale = {scale:.6f}  alpha = {alpha:.6f}")
        print(f"    conversion RMSE = {rmse:.4f} cm-1")
        print(f"    max|coeff| = {np.abs(coeffs).max():.4e}")

        alphas_out.append((mode, alpha))
        for p, c in enumerate(coeffs, start=1):
            all_terms.append((mode, p, c))

    # Write per-order files
    by_order = {}
    for mode, p, c in all_terms:
        by_order.setdefault(p, []).append((mode, p, c))

    print(f"\n  Writing output files:")
    import os
    for order, lines in sorted(by_order.items()):
        fname = os.path.join(args.outdir, f"f{order}{mol}.dat")
        with open(fname, "w") as fout:
            for mode, p, c in lines:
                # fN file format: N repeated mode indices then coeff
                indices = "  ".join([str(mode)] * p)
                fout.write(f"  {indices}    {c:.10f}d0\n")
        print(f"    Wrote {fname} ({len(lines)} terms)")

    # Write alphas
    alpha_fname = os.path.join(args.outdir, f"alphas_{mol}.dat")
    with open(alpha_fname, "w") as f:
        for mode, alpha in alphas_out:
            f.write(f"  {mode}    {alpha:.8f}\n")
    print(f"    Wrote {alpha_fname}")

    # Sanity check: f2 coefficients should be close to omega/2
    print(f"\n  Sanity check (f2 coeff should be ~omega/2):")
    for mode, freq, mw_norm, model_file in zip(
            args.modes, args.freqs, args.mw_norms, args.gpr_models):
        f2_terms = [c for m, p, c in all_terms if m == mode and p == 2]
        if f2_terms:
            print(f"    Mode {mode}: f2={f2_terms[0]:.1f} cm-1, "
                  f"omega/2={freq/2:.1f} cm-1")


if __name__ == "__main__":
    main()
