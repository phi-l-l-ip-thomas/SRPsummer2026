"""
fit_2d_sklearn_gpr.py
-----------------------
Collects 2D MOPAC energies and fits a 2D sklearn GPR for each mode
pair, evaluating train and test RMSE separately per Dr. Thomas's
item 4.

Usage:
    python3 fit_2d_sklearn_gpr.py --mol water --length-scale 1.0
"""

import os
import re
import csv
import argparse
import numpy as np
from sklearn.gaussian_process import GaussianProcessRegressor
from sklearn.gaussian_process.kernels import RBF, WhiteKernel


def parse_mopac_aux(filepath):
    if not os.path.exists(filepath):
        return None
    with open(filepath) as f:
        text = f.read()
    m = re.search(r"HEAT_OF_FORMATION:KCAL/MOL=([\d.\-+DE]+)", text)
    if m:
        return float(m.group(1).replace("D", "E"))
    return None


KCAL_TO_CM1 = 349.7551


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--mol", type=str, default="water")
    parser.add_argument("--job-index", type=str, default="2d_job_index.csv")
    parser.add_argument("--mopac-dir", type=str, default="2d_mopac_inputs")
    parser.add_argument("--length-scale", type=float, default=1.0)
    parser.add_argument("--alpha", type=float, default=1e-10)
    parser.add_argument("--optimize-ls", action="store_true",
                        help="Let sklearn optimize length scale via marginal "
                             "likelihood instead of using --length-scale fixed")
    args = parser.parse_args()

    with open(args.job_index) as f:
        jobs = list(csv.DictReader(f))

    # Group by mode pair
    pairs = {}
    for job in jobs:
        key = (int(job["mode_i"]), int(job["mode_j"]))
        pairs.setdefault(key, {"train": [], "test": []})
        aux_file = os.path.join(
            args.mopac_dir,
            os.path.basename(job["input_file"]).replace(".mop", ".aux")
        )
        energy_kcal = parse_mopac_aux(aux_file)
        if energy_kcal is None:
            print(f"  WARNING: no energy for {aux_file}")
            continue
        pairs[key][job["split"]].append({
            "q_i": float(job["q_i"]),
            "q_j": float(job["q_j"]),
            "energy_kcal": energy_kcal,
        })

    print(f"\n=== 2D sklearn GPR fits: {args.mol} ===")
    print(f"  length_scale={'optimized' if args.optimize_ls else args.length_scale}\n")

    results = {}
    for (mode_i, mode_j), data in sorted(pairs.items()):
        train = data["train"]
        test = data["test"]
        if not train or not test:
            print(f"  Pair ({mode_i},{mode_j}): missing train or test data")
            continue

        # Build feature matrix [q_i, q_j] and energy targets
        X_train = np.array([[p["q_i"], p["q_j"]] for p in train])
        E_train_kcal = np.array([p["energy_kcal"] for p in train])
        X_test = np.array([[p["q_i"], p["q_j"]] for p in test])
        E_test_kcal = np.array([p["energy_kcal"] for p in test])

        # Zero relative to training minimum
        e_min = E_train_kcal.min()
        E_train = (E_train_kcal - e_min) * KCAL_TO_CM1
        E_test = (E_test_kcal - e_min) * KCAL_TO_CM1

        # Fit 2D GPR
        if args.optimize_ls:
            kernel = RBF(length_scale=1.0, length_scale_bounds=(0.1, 10.0)) + \
                      WhiteKernel(noise_level=args.alpha)
            gpr = GaussianProcessRegressor(kernel=kernel, alpha=args.alpha,
                                            n_restarts_optimizer=5,
                                            normalize_y=True)
        else:
            kernel = RBF(length_scale=args.length_scale,
                         length_scale_bounds="fixed") + \
                      WhiteKernel(noise_level=args.alpha,
                                  noise_level_bounds="fixed")
            gpr = GaussianProcessRegressor(kernel=kernel, alpha=args.alpha,
                                            normalize_y=True)
        gpr.fit(X_train, E_train)

        E_pred_train = gpr.predict(X_train)
        E_pred_test = gpr.predict(X_test)
        train_rmse = np.sqrt(np.mean((E_pred_train - E_train)**2))
        test_rmse = np.sqrt(np.mean((E_pred_test - E_test)**2))

        print(f"  Pair ({mode_i},{mode_j}): kernel={gpr.kernel_}")
        print(f"    train RMSE={train_rmse:.2f} cm-1  "
              f"test RMSE={test_rmse:.2f} cm-1  "
              f"({len(train)} train, {len(test)} test pts)")

        import joblib
        model_file = f"2d_gpr_m{mode_i}m{mode_j}.joblib"
        joblib.dump(gpr, model_file)
        results[(mode_i, mode_j)] = {
            "train_rmse": train_rmse, "test_rmse": test_rmse,
            "model_file": model_file
        }
        print(f"    Saved: {model_file}")

    return results


if __name__ == "__main__":
    main()
