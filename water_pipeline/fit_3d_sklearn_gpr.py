"""
fit_3d_sklearn_gpr.py
-----------------------
Collects 3D MOPAC energies and fits a 3D sklearn GPR for the single
water (1,2,3) triple, evaluating train and test RMSE separately.

Usage:
    python3 fit_3d_sklearn_gpr.py --mol water --length-scale 3.0
"""

import os
import re
import csv
import argparse
import numpy as np
from sklearn.gaussian_process import GaussianProcessRegressor
from sklearn.gaussian_process.kernels import RBF, WhiteKernel
import joblib

KCAL_TO_CM1 = 349.7551


def parse_mopac_aux(filepath):
    if not os.path.exists(filepath):
        return None
    with open(filepath) as f:
        text = f.read()
    m = re.search(r"HEAT_OF_FORMATION:KCAL/MOL=([\d.\-+DE]+)", text)
    if m:
        return float(m.group(1).replace("D", "E"))
    return None


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--mol", type=str, default="water")
    parser.add_argument("--job-index", type=str, default="3d_job_index.csv")
    parser.add_argument("--mopac-dir", type=str, default="3d_mopac_inputs")
    parser.add_argument("--length-scale", type=float, default=3.0)
    parser.add_argument("--alpha", type=float, default=1e-10)
    parser.add_argument("--optimize-ls", action="store_true")
    args = parser.parse_args()

    with open(args.job_index) as f:
        jobs = list(csv.DictReader(f))

    train_pts, test_pts = [], []
    for job in jobs:
        aux_file = os.path.join(
            args.mopac_dir,
            os.path.basename(job["input_file"]).replace(".mop", ".aux")
        )
        energy_kcal = parse_mopac_aux(aux_file)
        if energy_kcal is None:
            print(f"  WARNING: no energy for {aux_file}")
            continue
        pt = {"q_i": float(job["q_i"]), "q_j": float(job["q_j"]),
              "q_k": float(job["q_k"]), "energy_kcal": energy_kcal}
        if job["split"] == "train":
            train_pts.append(pt)
        else:
            test_pts.append(pt)

    X_train = np.array([[p["q_i"], p["q_j"], p["q_k"]] for p in train_pts])
    E_train_kcal = np.array([p["energy_kcal"] for p in train_pts])
    X_test = np.array([[p["q_i"], p["q_j"], p["q_k"]] for p in test_pts])
    E_test_kcal = np.array([p["energy_kcal"] for p in test_pts])

    e_min = E_train_kcal.min()
    E_train = (E_train_kcal - e_min) * KCAL_TO_CM1
    E_test = (E_test_kcal - e_min) * KCAL_TO_CM1

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

    import time
    t0 = time.time()
    gpr.fit(X_train, E_train)
    t_fit = time.time() - t0

    E_pred_train = gpr.predict(X_train)
    E_pred_test = gpr.predict(X_test)
    train_rmse = np.sqrt(np.mean((E_pred_train - E_train)**2))
    test_rmse = np.sqrt(np.mean((E_pred_test - E_test)**2))

    print(f"\n=== 3D sklearn GPR fit: {args.mol} (1,2,3) ===")
    print(f"  kernel: {gpr.kernel_}")
    print(f"  {len(train_pts)} train, {len(test_pts)} test points")
    print(f"  train RMSE: {train_rmse:.2f} cm-1")
    print(f"  test RMSE:  {test_rmse:.2f} cm-1")
    print(f"  fit time:   {t_fit:.2f} s")

    model_file = f"3d_gpr_m1m2m3.joblib"
    joblib.dump(gpr, model_file)
    print(f"  Saved: {model_file}")


if __name__ == "__main__":
    main()
