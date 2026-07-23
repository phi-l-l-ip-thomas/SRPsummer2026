"""
fit_morse_sop.py
-----------------
Fits a Morse-basis sum-of-products to GPR predictions for
ASYMMETRIC vibrational modes.

Morse basis: y_i = 1 - exp(-a * q_i)
SOP: V(q) = sum_p  c_p * y_i^p

Properties:
- At q=0: y=0, V=0 (equilibrium)
- At q->+inf: y->1 (dissociation, potential flattens)
- At q->-inf: y->-inf (compression, potential rises steeply)
- Naturally models asymmetric potentials

Usage:
    python3 fit_morse_sop.py --mode 2 --freq 4139.81 \\
        --gpr-model sklearn_gpr_optimal_mode2.joblib \\
        --mw-norm 42.695 --n-terms 8 --a-min 0.5 --a-max 10.0
"""

import argparse
import numpy as np
import joblib

HARTREE_TO_CM1 = 219474.63


def morse_basis_matrix(q_bohr, a, n_terms):
    """Build Morse basis matrix: columns are (1-exp(-a*q))^p for p=1..n_terms"""
    y = 1.0 - np.exp(-a * q_bohr)
    return np.column_stack([y**p for p in range(1, n_terms+1)])


def fit_morse_given_a(q_bohr, V, a, n_terms, ridge=0.0):
    Phi = morse_basis_matrix(q_bohr, a, n_terms)
    if ridge > 0:
        A = Phi.T @ Phi + ridge * np.eye(n_terms)
        b = Phi.T @ V
        c = np.linalg.solve(A, b)
    else:
        c, _, _, _ = np.linalg.lstsq(Phi, V, rcond=None)
    rmse = np.sqrt(np.mean((Phi @ c - V)**2))
    return c, rmse


def optimize_morse_a(q_bohr, V, n_terms, a_min, a_max,
                     n_scan=60, ridge=0.0):
    """Coarse-then-fine scan for optimal Morse parameter a."""
    alphas = np.linspace(a_min, a_max, n_scan)
    best_rmse, best_a, best_c = np.inf, None, None
    for a in alphas:
        c, rmse = fit_morse_given_a(q_bohr, V, a, n_terms, ridge)
        if rmse < best_rmse:
            best_rmse, best_a, best_c = rmse, a, c
    # Fine scan
    step = alphas[1] - alphas[0]
    fine = np.linspace(max(a_min, best_a-step),
                       min(a_max, best_a+step), 60)
    for a in fine:
        c, rmse = fit_morse_given_a(q_bohr, V, a, n_terms, ridge)
        if rmse < best_rmse:
            best_rmse, best_a, best_c = rmse, a, c
    return best_a, best_c, best_rmse


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", type=int, required=True)
    parser.add_argument("--freq", type=float, required=True)
    parser.add_argument("--gpr-model", type=str, required=True)
    parser.add_argument("--mw-norm", type=float, required=True)
    parser.add_argument("--n-terms", type=int, default=8)
    parser.add_argument("--a-min", type=float, default=0.5)
    parser.add_argument("--a-max", type=float, default=10.0)
    parser.add_argument("--ridge", type=float, default=1.0)
    parser.add_argument("--range-fraction", type=float, default=0.75)
    parser.add_argument("--q-max", type=float, default=1.2)
    args = parser.parse_args()

    omega_hartree = args.freq / HARTREE_TO_CM1
    scale = args.mw_norm * np.sqrt(omega_hartree)

    gpr = joblib.load(args.gpr_model)

    # Find GPR minimum
    q_fine = np.linspace(-args.q_max, args.q_max, 5000)
    V_fine = gpr.predict(q_fine.reshape(-1, 1))
    q_min_bohr = q_fine[np.argmin(V_fine)]
    V_min = V_fine.min()

    # Grid centered on minimum, restricted range
    half_range = args.q_max * args.range_fraction
    q_grid = np.linspace(q_min_bohr - half_range,
                          q_min_bohr + half_range, 300)
    # Shift so minimum is at q=0 for Morse basis
    q_shifted = q_grid - q_min_bohr

    V = gpr.predict(q_grid.reshape(-1, 1)) - V_min

    a, coeffs, rmse = optimize_morse_a(
        q_shifted, V, args.n_terms, args.a_min, args.a_max,
        ridge=args.ridge)

    print(f"\n=== Morse SOP fit: mode {args.mode} ({args.freq:.1f} cm-1) ===")
    print(f"  a = {a:.6f}  (Morse parameter)")
    print(f"  RMSE = {rmse:.4f} cm-1")
    print(f"  max|coeff| = {np.abs(coeffs).max():.4e}")
    for p, c in enumerate(coeffs, start=1):
        print(f"  power {p}: {c:.6f}")

    return a, coeffs, rmse


if __name__ == "__main__":
    main()
