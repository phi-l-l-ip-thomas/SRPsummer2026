"""
fit_sop_hybrid.py
------------------
Implements Dr. Thomas's hybrid SOP specification:
  - Symmetric modes: even powers of tanh -- tanh^2, tanh^4, ..., tanh^(2n)
  - Asymmetric modes: powers of Morse variable y = 1-exp(-beta*q)
  - 2D/3D coupling: products of 1D basis functions, reusing alphas/betas

Saves alphas and betas to a file for reuse in 2D/3D fits.

Usage:
    # Step 1: fit 1D, save params
    python3 fit_sop_hybrid.py --step 1d \\
        --molecule water --modes 1 2 3 \\
        --freqs 2170.10 4139.81 4390.84 \\
        --gpr-models sklearn_gpr_optimal_mode{1,2,3}.joblib \\
        --asymmetric-modes 2 --n-even 8 --n-morse 8

    # Step 2: fit 2D coupling using saved params
    python3 fit_sop_hybrid.py --step 2d \\
        --molecule water --pair 1 2 \\
        --params-file water_sop_params.npz \\
        --job-index 2d_job_index_coupling12.csv \\
        --mopac-dir 2d_mopac_inputs_coupling \\
        --gpr-1d sklearn_gpr_optimal_mode1.joblib \\
                 sklearn_gpr_optimal_mode2.joblib \\
        --n-terms 4
"""

import argparse
import numpy as np
import joblib
import os
import re
import csv
import glob

KCAL_TO_CM1 = 349.7551


def parse_hof(f):
    if not os.path.exists(f):
        return None
    txt = open(f).read()
    m = re.search(r'HEAT_OF_FORMATION:KCAL/MOL=([\d.\-+DE]+)', txt)
    return float(m.group(1).replace('D', 'E')) if m else None


def sym_basis(q, alpha, n_even):
    """Even powers of tanh: [1, tanh^2, tanh^4, ..., tanh^(2*n_even)]"""
    t = np.tanh(alpha * q)
    return np.column_stack([np.ones(len(q))] + [t**(2*p) for p in range(1, n_even+1)])


def asym_basis(q, beta, n_morse):
    """Powers of Morse variable: [1, y, y^2, ..., y^n] where y=1-exp(-beta*q)"""
    y = 1.0 - np.exp(-beta * q)
    return np.column_stack([np.ones(len(q))] + [y**p for p in range(1, n_morse+1)])


def optimize_param(q, V, n_terms, p_min, p_max, basis_fn, ridge=1.0, n_scan=80):
    best = (np.inf, None, None)
    for p in np.linspace(p_min, p_max, n_scan):
        Phi = basis_fn(q, p, n_terms)
        A = Phi.T @ Phi + ridge * np.eye(Phi.shape[1])
        c = np.linalg.solve(A, Phi.T @ V)
        rmse = np.sqrt(np.mean((Phi @ c - V)**2))
        if rmse < best[0]:
            best = (rmse, p, c)
    step = (p_max - p_min) / n_scan
    for p in np.linspace(max(p_min, best[1]-step), min(p_max, best[1]+step), n_scan):
        Phi = basis_fn(q, p, n_terms)
        A = Phi.T @ Phi + ridge * np.eye(Phi.shape[1])
        c = np.linalg.solve(A, Phi.T @ V)
        rmse = np.sqrt(np.mean((Phi @ c - V)**2))
        if rmse < best[0]:
            best = (rmse, p, c)
    return best[1], best[2], best[0]


def get_1d_grid(gpr_file, q_max=1.2, range_fraction=0.75,
               left_fraction=None, right_fraction=None):
    gpr = joblib.load(gpr_file)
    q_fine = np.linspace(-q_max, q_max, 5000)
    V_fine = gpr.predict(q_fine.reshape(-1, 1))
    q_min = q_fine[np.argmin(V_fine)]
    if left_fraction is not None and right_fraction is not None:
        q_left = q_min - q_max * left_fraction
        q_right = q_min + q_max * right_fraction
    else:
        half = q_max * range_fraction
        q_left = q_min - half
        q_right = q_min + half
    q_grid = np.linspace(q_left, q_right, 300)
    q_shifted = q_grid - q_min
    V = gpr.predict(q_grid.reshape(-1, 1)) - V_fine.min()
    return q_shifted, V, q_min


def auto_optimize_range(gpr_file, is_asym, n_terms, q_max=1.5, ridge=1.0):
    """Automatically find best range fraction(s) for SOP fitting."""
    gpr = joblib.load(gpr_file)
    q_fine = np.linspace(-q_max, q_max, 5000)
    V_fine = gpr.predict(q_fine.reshape(-1, 1))
    q_min = q_fine[np.argmin(V_fine)]
    V_min = V_fine.min()

    def fit_rmse(q_shifted, V):
        p_range = np.linspace(0.1, 10.0, 60) if is_asym else np.linspace(0.05, 3.0, 60)
        basis_fn = asym_basis if is_asym else sym_basis
        best = np.inf
        for p in p_range:
            Phi = basis_fn(q_shifted, p, n_terms)
            A = Phi.T @ Phi + ridge * np.eye(Phi.shape[1])
            c, _, _, _ = np.linalg.lstsq(A, Phi.T @ V, rcond=None)
            r = np.sqrt(np.mean((Phi @ c - V) ** 2))
            if r < best:
                best = r
        return best

    if is_asym:
        best = (np.inf, 0.20, 0.40)
        for left in [0.05, 0.10, 0.15, 0.20, 0.30]:
            for right in [0.20, 0.30, 0.40, 0.50, 0.60]:
                q_grid = np.linspace(q_min - q_max*left, q_min + q_max*right, 300)
                q_shifted = q_grid - q_min
                V = gpr.predict(q_grid.reshape(-1, 1)) - V_min
                r = fit_rmse(q_shifted, V)
                if r < best[0]:
                    best = (r, left, right)
        return {'left': best[1], 'right': best[2], 'rmse': best[0]}
    else:
        best = (np.inf, 0.30)
        for rf in [0.15, 0.20, 0.25, 0.30, 0.40, 0.50, 0.60, 0.75]:
            half = q_max * rf
            q_grid = np.linspace(q_min - half, q_min + half, 300)
            q_shifted = q_grid - q_min
            V = gpr.predict(q_grid.reshape(-1, 1)) - V_min
            r = fit_rmse(q_shifted, V)
            if r < best[0]:
                best = (r, rf)
        return {'rf': best[1], 'rmse': best[0]}


def fit_1d(args):
    """Fit 1D SOP, save alphas/betas."""
    mol = args.molecule
    params = {}  # mode -> ('alpha'|'beta', value)

    print(f"\n=== 1D SOP fits: {mol} ===")
    print(f"{'Mode':>5} {'Freq':>8} {'Type':>6} {'Param':>8} {'Value':>8} {'RMSE':>10}")
    print("-" * 55)

    for mode, freq, gpr_file in zip(args.modes, args.freqs, args.gpr_models):
        is_asym = mode in args.asymmetric_modes

        # Auto-optimize range if requested
        if getattr(args, 'auto_range', False):
            n_terms = args.n_morse if is_asym else args.n_even
            range_info = auto_optimize_range(gpr_file, is_asym, n_terms)
            if is_asym:
                q, V, q_min = get_1d_grid(gpr_file,
                    left_fraction=range_info['left'],
                    right_fraction=range_info['right'])
            else:
                q, V, q_min = get_1d_grid(gpr_file, range_fraction=range_info['rf'])
        else:
            if is_asym:
                q, V, q_min = get_1d_grid(gpr_file,
                    left_fraction=args.morse_left,
                    right_fraction=args.morse_right)
            else:
                q, V, q_min = get_1d_grid(gpr_file,
                    range_fraction=args.range_fraction)

        if is_asym:
            beta, coeffs, rmse = optimize_param(
                q, V, args.n_morse, 0.1, 10.0, asym_basis)
            params[mode] = {'type': 'beta', 'value': beta, 'q_min': q_min}
            print(f"{mode:>5} {freq:>8.1f} {'asym':>6} {'beta':>8} {beta:>8.4f} {rmse:>10.2f}")
        else:
            alpha, coeffs, rmse = optimize_param(
                q, V, args.n_even, 0.05, 3.0, sym_basis)
            params[mode] = {'type': 'alpha', 'value': alpha, 'q_min': q_min}
            print(f"{mode:>5} {freq:>8.1f} {'sym':>6} {'alpha':>8} {alpha:>8.4f} {rmse:>10.2f}")

    # Save params file
    params_file = f"{mol}_sop_params.npz"
    save_dict = {}
    for mode, p in params.items():
        save_dict[f"mode{mode}_type"] = p['type']
        save_dict[f"mode{mode}_value"] = p['value']
        save_dict[f"mode{mode}_qmin"] = p['q_min']
    np.savez(params_file, **save_dict)
    print(f"\nSaved params to {params_file}")

    # Also write human-readable version
    txt_file = f"{mol}_sop_params.txt"
    with open(txt_file, 'w') as f:
        f.write(f"# SOP parameters for {mol}\n")
        f.write(f"# mode  type   value      q_min\n")
        for mode, p in params.items():
            f.write(f"  {mode:>4}  {p['type']:>5}  {p['value']:>10.6f}  {p['q_min']:>10.6f}\n")
    print(f"Saved human-readable params to {txt_file}")
    return params


def fit_2d(args):
    """Fit 2D coupling using saved 1D params."""
    mol = args.molecule
    mi, mj = args.pair

    # Load params
    data = np.load(f"{mol}_sop_params.npz", allow_pickle=True)
    type_i = str(data[f"mode{mi}_type"])
    val_i  = float(data[f"mode{mi}_value"])
    qmin_i = float(data[f"mode{mi}_qmin"])
    type_j = str(data[f"mode{mj}_type"])
    val_j  = float(data[f"mode{mj}_value"])
    qmin_j = float(data[f"mode{mj}_qmin"])

    print(f"\n=== 2D SOP fit: {mol} modes ({mi},{mj}) ===")
    print(f"  Mode {mi}: {type_i}={val_i:.4f}")
    print(f"  Mode {mj}: {type_j}={val_j:.4f}")

    # Load 1D GPR models for residual subtraction
    gpr_i = joblib.load(args.gpr_1d[0])
    gpr_j = joblib.load(args.gpr_1d[1])

    # Find reference energy
    E_ref = min(parse_hof(f) for f in glob.glob('water_mode1_*.aux')
                if parse_hof(f) is not None)

    # Load 2D MOPAC data and compute residual
    jobs = list(csv.DictReader(open(args.job_index)))
    Qi, Qj, R2d = [], [], []
    for job in jobs:
        aux = os.path.join(args.mopac_dir,
              os.path.basename(job['input_file']).replace('.mop', '.aux'))
        hof = parse_hof(aux)
        if hof is None:
            continue
        E2d = (hof - E_ref) * KCAL_TO_CM1
        qi = float(job['step_i_bohr']) - qmin_i
        qj = float(job['step_j_bohr']) - qmin_j
        R = E2d - gpr_i.predict([[qi + qmin_i]])[0] - gpr_j.predict([[qj + qmin_j]])[0]
        Qi.append(qi); Qj.append(qj); R2d.append(R)

    Qi = np.array(Qi); Qj = np.array(Qj); R2d = np.array(R2d)
    print(f"  {len(Qi)} points, residual RMS={np.sqrt(np.mean(R2d**2)):.2f} cm-1")

    # Build 2D basis: products of 1D basis functions
    def basis_1d(q, ptype, val, n):
        if ptype == 'alpha':
            t = np.tanh(val * q)
            return [t**(2*p) for p in range(1, n+1)]  # even powers
        else:
            y = 1.0 - np.exp(-val * q)
            return [y**p for p in range(1, n+1)]  # all powers

    n = args.n_terms
    cols_i = basis_1d(Qi, type_i, val_i, n)
    cols_j = basis_1d(Qj, type_j, val_j, n)
    cols_2d = [ci * cj for ci in cols_i for cj in cols_j]
    Phi = np.column_stack(cols_2d)

    c, _, _, _ = np.linalg.lstsq(Phi, R2d, rcond=None)
    rmse = np.sqrt(np.mean((Phi @ c - R2d)**2))
    n_terms_2d = len(cols_2d)
    print(f"  2D hybrid SOP ({n_terms_2d} terms): RMSE={rmse:.2f} cm-1")
    return rmse


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--step", choices=["1d", "2d"], required=True)
    parser.add_argument("--molecule", type=str, required=True)
    parser.add_argument("--modes", type=int, nargs="+")
    parser.add_argument("--freqs", type=float, nargs="+")
    parser.add_argument("--gpr-models", type=str, nargs="+")
    parser.add_argument("--gpr-1d", type=str, nargs="+")
    parser.add_argument("--asymmetric-modes", type=int, nargs="+", default=[])
    parser.add_argument("--n-even", type=int, default=8,
                        help="Number of even powers for symmetric modes")
    parser.add_argument("--n-morse", type=int, default=20,
                        help="Number of Morse powers for asymmetric modes")
    parser.add_argument("--n-terms", type=int, default=4,
                        help="Terms per dimension for 2D/3D fits")
    parser.add_argument("--range-fraction", type=float, default=0.75,
                        help="Fitting range fraction for symmetric modes")
    parser.add_argument("--morse-left", type=float, default=0.30,
                        help="Left (compression) range fraction for asymmetric modes")
    parser.add_argument("--morse-right", type=float, default=0.50,
                        help="Right (dissociation) range fraction for asymmetric modes")
    parser.add_argument("--auto-range", action="store_true",
                        help="Automatically optimize range fraction per mode")
    parser.add_argument("--pair", type=int, nargs=2)
    parser.add_argument("--params-file", type=str)
    parser.add_argument("--job-index", type=str)
    parser.add_argument("--mopac-dir", type=str)
    args = parser.parse_args()

    if args.step == "1d":
        fit_1d(args)
    elif args.step == "2d":
        fit_2d(args)


if __name__ == "__main__":
    main()
