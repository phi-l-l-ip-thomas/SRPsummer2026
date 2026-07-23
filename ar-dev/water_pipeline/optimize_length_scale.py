"""
optimize_length_scale.py
------------------------------
Implements Dr. Thomas's item 1 (June 30): automated length-scale
optimization via explicit train/test split RMSE minimization, rather
than sklearn's internal marginal likelihood approach.

The "best" length scale is the one that minimizes RMSE on a held-out
TEST set of points chosen at random displacements -- points that were
NOT used to build the fit. This is more physically interpretable than
marginal likelihood and directly measures generalization quality.

Strategy:
- Split the real data into training set (used for fitting) and test
  set (held out for evaluation)
- For each candidate length scale, fit a GPR on training set,
  evaluate RMSE on test set
- Choose the length scale that minimizes test RMSE
- Also report training RMSE so the train/test gap is visible
  (a large gap = overfitting)

Usage:
    python3 optimize_length_scale.py \\
        --points dataset_1d_mode1_with_wide_range.dat \\
        --mode 1 --freq 2170.10
"""

import argparse
import numpy as np
from sklearn.gaussian_process import GaussianProcessRegressor
from sklearn.gaussian_process.kernels import RBF, WhiteKernel

VIRTUAL_POINT_OFFSET = 0.001


def augment_with_virtual_points(Q, E, G):
    if G is None:
        return Q, E
    Q_aug, E_aug = [Q.copy()], [E.copy()]
    has_grad = ~np.isnan(G)
    Q_aug.extend([Q[has_grad] + VIRTUAL_POINT_OFFSET,
                  Q[has_grad] - VIRTUAL_POINT_OFFSET])
    E_aug.extend([E[has_grad] + G[has_grad] * VIRTUAL_POINT_OFFSET,
                  E[has_grad] - G[has_grad] * VIRTUAL_POINT_OFFSET])
    return np.concatenate(Q_aug), np.concatenate(E_aug)


def fit_and_evaluate(Q_train, E_train, G_train, Q_test, E_test,
                     length_scale, alpha=1e-10):
    Q_fit, E_fit = augment_with_virtual_points(Q_train, E_train, G_train)
    kernel = RBF(length_scale=length_scale,
                 length_scale_bounds="fixed") + \
              WhiteKernel(noise_level=alpha, noise_level_bounds="fixed")
    gpr = GaussianProcessRegressor(kernel=kernel, alpha=alpha,
                                    normalize_y=True)
    gpr.fit(Q_fit.reshape(-1, 1), E_fit)

    E_pred_train = gpr.predict(Q_train.reshape(-1, 1))
    E_pred_test = gpr.predict(Q_test.reshape(-1, 1))

    train_rmse = np.sqrt(np.mean((E_pred_train - E_train)**2))
    test_rmse = np.sqrt(np.mean((E_pred_test - E_test)**2))
    return train_rmse, test_rmse


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--points", type=str, required=True)
    parser.add_argument("--mode", type=int, required=True)
    parser.add_argument("--freq", type=float, required=True)
    parser.add_argument("--test-fraction", type=float, default=0.3,
                        help="Fraction of real points held out as test set")
    parser.add_argument("--length-scales", type=str,
                        default="0.1,0.2,0.3,0.5,0.75,1.0,1.5,2.0,3.0,5.0,7.0,10.0",
                        help="Comma-separated list of length scales to try")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--no-gradients", action="store_true")
    args = parser.parse_args()

    data = np.loadtxt(args.points, comments="#")
    Q = data[:, 0]
    E = data[:, 1]
    G = data[:, 2] if (data.shape[1] > 2 and not args.no_gradients) else None
    if G is not None and np.all(np.isnan(G)):
        G = None

    rng = np.random.RandomState(args.seed)
    n = len(Q)
    n_test = max(2, int(n * args.test_fraction))
    test_idx = rng.choice(n, size=n_test, replace=False)
    train_idx = np.setdiff1d(np.arange(n), test_idx)

    Q_train, E_train = Q[train_idx], E[train_idx]
    G_train = G[train_idx] if G is not None else None
    Q_test, E_test = Q[test_idx], E[test_idx]

    length_scales = [float(x) for x in args.length_scales.split(",")]

    print(f"\n=== Length-scale optimization: mode {args.mode} ===")
    print(f"  {len(Q_train)} training points, {len(Q_test)} test points")
    print(f"  Gradients: {'yes' if G is not None else 'no'}")
    print(f"\n  {'length_scale':>14s}  {'train_rmse':>12s}  {'test_rmse':>12s}")
    print(f"  {'-'*42}")

    best_ls = None
    best_test_rmse = float('inf')
    results = []

    for ls in length_scales:
        train_rmse, test_rmse = fit_and_evaluate(
            Q_train, E_train, G_train, Q_test, E_test, ls
        )
        results.append((ls, train_rmse, test_rmse))
        marker = " <-- best" if test_rmse < best_test_rmse else ""
        if test_rmse < best_test_rmse:
            best_test_rmse = test_rmse
            best_ls = ls
        print(f"  {ls:>14.3f}  {train_rmse:>12.4f}  {test_rmse:>12.4f}{marker}")

    print(f"\n  Best length_scale: {best_ls}  (test RMSE: {best_test_rmse:.4f} cm-1)")
    return best_ls, results


if __name__ == "__main__":
    main()
