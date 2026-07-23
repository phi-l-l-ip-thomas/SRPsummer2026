"""
fit_smolyak_gpr.py
--------------------
Fits a sklearn GPR to Smolyak grid MOPAC data and evaluates
train/test RMSE. Works for any dimensionality (2D, 3D, etc.)
by reading the Smolyak job index format.

Usage:
    python3 fit_smolyak_gpr.py --modes 1 2 3 --length-scale 3.0 \
        --job-index smolyak_job_index_3d_m123.csv \
        --mopac-dir smolyak_l2_1_2_3
"""

import os, re, csv, argparse, time
import numpy as np
from sklearn.gaussian_process import GaussianProcessRegressor
from sklearn.gaussian_process.kernels import RBF, WhiteKernel
import joblib

KCAL_TO_CM1 = 349.7551


def parse_hof(f):
    if not os.path.exists(f): return None
    txt = open(f).read()
    m = re.search(r'HEAT_OF_FORMATION:KCAL/MOL=([\d.\-+DE]+)', txt)
    return float(m.group(1).replace('D','E')) if m else None


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--modes", type=int, nargs="+", required=True)
    parser.add_argument("--job-index", type=str, required=True)
    parser.add_argument("--mopac-dir", type=str, required=True)
    parser.add_argument("--length-scale", type=float, default=3.0)
    parser.add_argument("--optimize-ls", action="store_true")
    parser.add_argument("--alpha", type=float, default=1e-10)
    args = parser.parse_args()

    jobs = list(csv.DictReader(open(args.job_index)))
    d = len(args.modes)

    train_X, train_Y, test_X, test_Y = [], [], [], []
    n_missing = 0
    for job in jobs:
        aux = os.path.join(args.mopac_dir,
              os.path.basename(job['input_file']).replace('.mop','.aux'))
        hof = parse_hof(aux)
        if hof is None:
            n_missing += 1
            continue
        q_vec = [float(job[f'step_{m}_bohr']) for m in args.modes]
        if job['split'] == 'train':
            train_X.append(q_vec); train_Y.append(hof)
        else:
            test_X.append(q_vec); test_Y.append(hof)

    if n_missing > 0:
        print(f"  WARNING: {n_missing} missing aux files")

    train_X = np.array(train_X); train_Y = np.array(train_Y)
    test_X  = np.array(test_X);  test_Y  = np.array(test_Y)

    e_min = train_Y.min()
    train_Y = (train_Y - e_min) * KCAL_TO_CM1
    test_Y  = (test_Y  - e_min) * KCAL_TO_CM1

    if args.optimize_ls:
        kernel = RBF(length_scale=1.0, length_scale_bounds=(0.1,10.0)) + \
                  WhiteKernel(noise_level=args.alpha)
        gpr = GaussianProcessRegressor(kernel=kernel, alpha=args.alpha,
                                        n_restarts_optimizer=5, normalize_y=True)
    else:
        kernel = RBF(length_scale=args.length_scale,
                     length_scale_bounds="fixed") + \
                  WhiteKernel(noise_level=args.alpha, noise_level_bounds="fixed")
        gpr = GaussianProcessRegressor(kernel=kernel, alpha=args.alpha,
                                        normalize_y=True)

    t0 = time.time()
    gpr.fit(train_X, train_Y)
    t_fit = time.time() - t0

    train_rmse = np.sqrt(np.mean((gpr.predict(train_X) - train_Y)**2))
    test_rmse  = np.sqrt(np.mean((gpr.predict(test_X)  - test_Y)**2))

    label = '_'.join(f'm{m}' for m in args.modes)
    print(f"\n=== Smolyak GPR fit: modes {args.modes} ===")
    print(f"  {len(train_X)} train, {len(test_X)} test points")
    print(f"  kernel: {gpr.kernel_}")
    print(f"  train RMSE: {train_rmse:.2f} cm-1")
    print(f"  test RMSE:  {test_rmse:.2f} cm-1")
    print(f"  fit time:   {t_fit:.2f} s")

    model_file = f"smolyak_gpr_{label}.joblib"
    joblib.dump(gpr, model_file)
    print(f"  Saved: {model_file}")


if __name__ == "__main__":
    main()
