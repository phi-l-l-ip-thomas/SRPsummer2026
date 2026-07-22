"""
fit_sklearn_gpr_gradients.py
---------------------------------
A genuine, complete replacement for fit_gpr_gradients.py's 1D fitting
approach, using scikit-learn's well-tested, well-regularized
GaussianProcessRegressor directly on the raw 1D coordinate -- NO
redundant-coordinate transform -- since that transform was confirmed
(June 30) to be the actual source of the edge-oscillation artifacts
that plagued our custom optGPRNN-based fits.

Uses the same gradient-enhanced virtual-point augmentation technique as
the original (Option B: E_virtual(q +/- eps) = E(q) +/- gradient*eps),
since that part of the approach was confirmed NOT to be the cause of
the artifacts (June 30, item 2 test) -- this keeps the genuinely useful
part of the original pipeline while replacing only the part that was
broken.

Usage:
    python3 fit_sklearn_gpr_gradients.py --mode 1 \\
        --points dataset_1d_mode1_with_wide_range.dat
"""

import argparse
import numpy as np
from sklearn.gaussian_process import GaussianProcessRegressor
from sklearn.gaussian_process.kernels import RBF, WhiteKernel

VIRTUAL_POINT_OFFSET = 0.001  # same default as the original pipeline


def load_dataset_with_gradients(filepath):
    data = np.loadtxt(filepath, comments="#")
    Q = data[:, 0]
    E = data[:, 1]
    G = data[:, 2] if data.shape[1] > 2 else None
    if G is not None and np.all(np.isnan(G)):
        G = None
    return Q, E, G


def augment_with_virtual_points(Q, E, G, offset=VIRTUAL_POINT_OFFSET):
    """Same virtual-point augmentation technique as the original pipeline."""
    if G is None:
        return Q, E
    Q_aug, E_aug = [Q.copy()], [E.copy()]
    has_grad = ~np.isnan(G)
    Q_plus = Q[has_grad] + offset
    E_plus = E[has_grad] + G[has_grad] * offset
    Q_minus = Q[has_grad] - offset
    E_minus = E[has_grad] - G[has_grad] * offset
    Q_aug.extend([Q_plus, Q_minus])
    E_aug.extend([E_plus, E_minus])
    return np.concatenate(Q_aug), np.concatenate(E_aug)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", type=int, required=True)
    parser.add_argument("--points", type=str, required=True)
    parser.add_argument("--no-gradients", action="store_true")
    parser.add_argument("--energy-threshold", type=float, default=None,
                        help="Drop points with E > threshold cm-1 (zeroed to "
                             "minimum). Use for modes like mode 12 where "
                             "bond-breaking points ruin the GPR fit.")
    parser.add_argument("--backend", type=str, default="sklearn",
                        choices=["sklearn", "sergei"],
                        help="GPR backend to use. 'sklearn' (default): uses "
                             "scikit-learn's GaussianProcessRegressor with "
                             "RBF+WhiteKernel, confirmed clean fits and "
                             "competitive timing. 'sergei': uses Sergei's "
                             "optGPRNN redundant-coordinate Monte Carlo "
                             "optimizer (NNviaHDMRGPR_prod.py) -- kept as "
                             "an option per Dr. Thomas's request in case "
                             "it's needed for future multidimensional work "
                             "or comparison with Sergei's fits.")
    parser.add_argument("--length-scale", type=float, default=None,
                        help="Fix length scale to this value (skip optimization). "
                             "If not set, sklearn optimizes via marginal likelihood.")
    parser.add_argument("--length-scale-bounds", type=str, default="1e-2,1e2")
    parser.add_argument("--alpha", type=float, default=1e-10)
    parser.add_argument("--outfile", type=str, default=None)
    args = parser.parse_args()

    # Backend routing -- per Dr. Thomas's request (June 30), keep the
    # option to swap to Sergei's optGPRNN if needed in future work
    if args.backend == "sergei":
        import subprocess, sys, os
        sergei_script = os.path.join(os.path.dirname(__file__),
                                     "fit_gpr_gradients.py")
        if not os.path.exists(sergei_script):
            sergei_script = os.path.expanduser(
                "~/my_container_build/stage4_mopac_inputs/"
                "wide_range_mopac_inputs/fit_gpr_gradients.py")
        cmd = [sys.executable, sergei_script,
               "--mode", str(args.mode),
               "--points", args.points,
               "--steps", "2000"]
        if args.no_gradients:
            cmd.append("--no-gradients")
        print(f"  Routing to Sergei's optGPRNN backend: {sergei_script}")
        result = subprocess.run(cmd)
        sys.exit(result.returncode)

    Q, E, G = load_dataset_with_gradients(args.points)

    # Apply energy threshold if specified
    if args.energy_threshold is not None:
        e_min = E.min()
        mask = (E - e_min) < args.energy_threshold
        print(f"  Energy threshold {args.energy_threshold} cm-1: "
              f"keeping {mask.sum()} of {len(Q)} points")
        Q = Q[mask]; E = E[mask]
        if G is not None: G = G[mask]

    if args.no_gradients:
        G = None

    Q_fit, E_fit = augment_with_virtual_points(Q, E, G)

    ls_min, ls_max = map(float, args.length_scale_bounds.split(","))
    if args.length_scale is not None:
        kernel = RBF(length_scale=args.length_scale,
                     length_scale_bounds="fixed") + \
                  WhiteKernel(noise_level=args.alpha, noise_level_bounds="fixed")
        gpr = GaussianProcessRegressor(kernel=kernel, alpha=args.alpha,
                                        normalize_y=True)
    else:
        kernel = RBF(length_scale=1.0, length_scale_bounds=(ls_min, ls_max)) + \
                  WhiteKernel(noise_level=args.alpha)
        gpr = GaussianProcessRegressor(kernel=kernel, alpha=args.alpha,
                                        n_restarts_optimizer=10, normalize_y=True)
    gpr.fit(Q_fit.reshape(-1, 1), E_fit)

    print(f"\n=== sklearn GPR fit, mode {args.mode} ===")
    print(f"  Optimized kernel: {gpr.kernel_}")
    print(f"  Real points: {len(Q)}  Total fit points (with virtual): {len(Q_fit)}")

    E_pred_real = gpr.predict(Q.reshape(-1, 1))
    rmse = np.sqrt(np.mean((E_pred_real - E) ** 2))
    print(f"  RMSE on real points: {rmse:.4f} cm-1")

    outfile = args.outfile or f"sklearn_gpr_mode{args.mode}.npz"
    q_dense = np.linspace(Q.min(), Q.max(), 500)
    V_dense, V_std = gpr.predict(q_dense.reshape(-1, 1), return_std=True)
    np.savez(outfile, q_grid=q_dense, V_pred=V_dense, V_std=V_std,
             X_train=Q, y_train=E, kernel_params=str(gpr.kernel_))

    import joblib
    model_file = outfile.replace(".npz", ".joblib")
    joblib.dump(gpr, model_file)
    print(f"  Saved: {outfile}")
    print(f"  Saved model: {model_file}")


if __name__ == "__main__":
    main()
