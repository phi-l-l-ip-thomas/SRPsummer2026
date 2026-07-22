"""
fit_sklearn_gpr.py
----------------------
Per Dr. Thomas's item 4 (June 29): fits the SAME water mode data using
scikit-learn's GaussianProcessRegressor instead of our custom
redundant-coordinate Monte Carlo optimizer, to check whether the edge
oscillations persist with a different, well-tested GPR implementation
that has principled length-scale optimization (via marginal likelihood)
and built-in regularization (alpha/noise term).

Usage:
    python3 fit_sklearn_gpr.py --points dataset_1d_mode1_with_wide_range.dat
"""

import argparse
import numpy as np
from sklearn.gaussian_process import GaussianProcessRegressor
from sklearn.gaussian_process.kernels import RBF, WhiteKernel


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--points", type=str, required=True)
    parser.add_argument("--length-scale-bounds", type=str, default="1e-2,1e2",
                        help="Comma-separated min,max for the RBF length "
                             "scale search (sklearn optimizes within this "
                             "range via marginal likelihood)")
    parser.add_argument("--alpha", type=float, default=1e-10,
                        help="Noise regularization (sklearn's alpha, "
                             "analogous to our noise parameter)")
    parser.add_argument("--outfile", type=str, default="sklearn_gpr_predictions.npz")
    args = parser.parse_args()

    data = np.loadtxt(args.points, comments="#")
    steps = data[:, 0].reshape(-1, 1)
    energies = data[:, 1]

    ls_min, ls_max = map(float, args.length_scale_bounds.split(","))
    kernel = RBF(length_scale=1.0, length_scale_bounds=(ls_min, ls_max)) + \
              WhiteKernel(noise_level=args.alpha)

    gpr = GaussianProcessRegressor(kernel=kernel, alpha=args.alpha,
                                    n_restarts_optimizer=10, normalize_y=True)
    gpr.fit(steps, energies)

    print(f"\n=== scikit-learn GaussianProcessRegressor fit ===")
    print(f"  Optimized kernel: {gpr.kernel_}")

    q_grid = np.linspace(steps.min(), steps.max(), 400).reshape(-1, 1)
    V_pred, V_std = gpr.predict(q_grid, return_std=True)

    np.savez(args.outfile, q_grid=q_grid.flatten(), V_pred=V_pred, V_std=V_std,
             X_train=steps.flatten(), y_train=energies)
    print(f"  Saved predictions to {args.outfile}")
    print(f"  Max predicted |E| in outer 10% of range: "
          f"{np.abs(V_pred[np.abs(q_grid.flatten()) > 0.9*np.abs(steps).max()]).max():.2f} cm-1")


if __name__ == "__main__":
    main()
