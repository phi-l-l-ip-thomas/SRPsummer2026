"""
optimize_sop_range.py
----------------------
Optimizes the range fraction for SOP basis fitting per mode.
Works on a fitted GPR model (joblib), not raw MOPAC data.

For symmetric modes: sweeps range_fraction (symmetric around minimum)
For asymmetric modes: sweeps left_fraction and right_fraction separately

Usage:
    # Symmetric mode
    python3 optimize_sop_range.py --mode 1 --freq 2170.10 \
        --gpr-model sklearn_gpr_optimal_mode1.joblib \
        --basis tanh-even --n-terms 8

    # Asymmetric mode
    python3 optimize_sop_range.py --mode 2 --freq 4139.81 \
        --gpr-model sklearn_gpr_optimal_mode2.joblib \
        --basis morse --n-terms 20 --asymmetric
"""

import argparse
import numpy as np
import joblib


def sym_basis(q, alpha, n):
    t = np.tanh(alpha * q)
    return np.column_stack([np.ones(len(q))] + [t**(2*p) for p in range(1, n+1)])


def asym_basis(q, beta, n):
    y = 1.0 - np.exp(-beta * q)
    return np.column_stack([np.ones(len(q))] + [y**p for p in range(1, n+1)])


def fit_sop(q, V, basis_fn, p_min, p_max, n, ridge=1.0):
    """Optimize parameter and return best RMSE."""
    best = np.inf
    for p in np.linspace(p_min, p_max, 80):
        Phi = basis_fn(q, p, n)
        A = Phi.T @ Phi + ridge * np.eye(Phi.shape[1])
        c, _, _, _ = np.linalg.lstsq(A, Phi.T @ V, rcond=None)
        rmse = np.sqrt(np.mean((Phi @ c - V)**2))
        if rmse < best:
            best = rmse
    return best


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", type=int, required=True)
    parser.add_argument("--freq", type=float, required=True)
    parser.add_argument("--gpr-model", type=str, required=True)
    parser.add_argument("--basis", choices=["tanh-even", "morse"], default="tanh-even")
    parser.add_argument("--n-terms", type=int, default=8)
    parser.add_argument("--asymmetric", action="store_true",
                        help="Use asymmetric range (separate left/right fractions)")
    parser.add_argument("--q-max", type=float, default=1.5)
    parser.add_argument("--ridge", type=float, default=1.0)
    args = parser.parse_args()

    gpr = joblib.load(args.gpr_model)
    q_fine = np.linspace(-args.q_max, args.q_max, 5000)
    V_fine = gpr.predict(q_fine.reshape(-1, 1))
    q_min = q_fine[np.argmin(V_fine)]
    V_min = V_fine.min()

    basis_fn = asym_basis if args.basis == "morse" else sym_basis
    p_min, p_max = (0.1, 5.0) if args.basis == "morse" else (0.05, 3.0)

    print(f"\n=== SOP range optimization: mode {args.mode} ({args.freq:.1f} cm-1) ===")
    print(f"  Basis: {args.basis}, n_terms={args.n_terms}, q_min={q_min:.4f}")

    if args.asymmetric:
        print(f"\n  {'left':>6}  {'right':>6}  {'RMSE':>10}")
        print(f"  {'-'*26}")
        best_rmse = np.inf
        best_params = None
        for left in [0.20, 0.30, 0.40, 0.50, 0.60, 0.75]:
            for right in [0.30, 0.40, 0.50, 0.60, 0.75, 1.0]:
                q_grid = np.linspace(q_min - args.q_max*left,
                                     q_min + args.q_max*right, 300)
                q_shifted = q_grid - q_min
                V = gpr.predict(q_grid.reshape(-1, 1)) - V_min
                rmse = fit_sop(q_shifted, V, basis_fn, p_min, p_max,
                               args.n_terms, args.ridge)
                marker = " <-- best" if rmse < best_rmse else ""
                if rmse < best_rmse:
                    best_rmse = rmse
                    best_params = (left, right)
                print(f"  {left:>6.2f}  {right:>6.2f}  {rmse:>10.2f}{marker}")
        print(f"\n  Best: left={best_params[0]}, right={best_params[1]}, "
              f"RMSE={best_rmse:.2f} cm-1")
    else:
        print(f"\n  {'rf':>6}  {'RMSE':>10}")
        print(f"  {'-'*18}")
        best_rmse = np.inf
        best_rf = None
        for rf in [0.20, 0.30, 0.40, 0.50, 0.60, 0.75, 0.90, 1.0]:
            half = args.q_max * rf
            q_grid = np.linspace(q_min - half, q_min + half, 300)
            q_shifted = q_grid - q_min
            V = gpr.predict(q_grid.reshape(-1, 1)) - V_min
            rmse = fit_sop(q_shifted, V, basis_fn, p_min, p_max,
                           args.n_terms, args.ridge)
            marker = " <-- best" if rmse < best_rmse else ""
            if rmse < best_rmse:
                best_rmse = rmse
                best_rf = rf
            print(f"  {rf:>6.2f}  {rmse:>10.2f}{marker}")
        print(f"\n  Best range_fraction={best_rf}, RMSE={best_rmse:.2f} cm-1")


if __name__ == "__main__":
    main()
