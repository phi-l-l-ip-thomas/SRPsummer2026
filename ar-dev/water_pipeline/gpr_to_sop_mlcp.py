"""
gpr_to_sop_mlcp.py
---------------------
Converts a GPR-fitted PES into the exact f2xxx.dat / f3xxx.dat / f4xxx.dat
format MLCP reads, using [tanh(alpha_i * q_i)]^p as the basis instead of
q_i^p (polynomial). This is the genuinely new piece beyond gpr_to_sop.py:
real MLCP file format output, per-mode alpha, and 2D/3D term support.

CONFIRMED FORMAT (from real f2/f3/f4ch3cn.dat files):
    f2 (1-mode terms):  mode_i  mode_i           coefficient
    f3 (2-mode terms):  mode_i  mode_j  mode_j   coefficient (Fortran d0)
    f4 (3-mode terms):  mode_i  mode_j  mode_k  mode_k   coefficient (Fortran d0)

    Example real f3ch3cn.dat line:
      1  1  1    -176.0000d0
    Example real f4ch3cn.dat line:
      1  4  5  5       3.7500d0

NOTE on naming: MLCP's f2/f3/f4 naming refers to the ORDER of the Taylor
term (quadratic/cubic/quartic), not strictly the number of distinct modes
involved -- e.g. "1 1 1" in f3 is a single-mode cubic term (q1^3), while
"1 5 9" in f3 is a genuine 3-mode coupling term (q1*q5*q9).

CONFIRMED (June 23, from MLCP's actual source, FFPES.f90): there is NO
hardcoded ceiling at f4. MLCP loops over order k = 1 to ncp (a control
parameter) and looks for a file named f<k><system_id>.dat for each k,
simply skipping ahead if that file isn't found. So a tanh expansion of
ANY length is supported -- just write f5<mol>.dat, f6<mol>.dat, etc.
following the identical naming/format pattern, and set ncp high enough
in the MLCP input to cover the highest order actually used.

Our pipeline's 1D/2D/3D GPR hierarchy maps onto this as:
    1D fits  -> single-mode terms (now tanh-based), one file per power
    2D fits  -> 2-mode coupling terms (product of two tanh functions)
    3D fits  -> 3-mode coupling terms (product of three tanh functions)

THE NEW BASIS:
    Old (polynomial): V(q_i) = sum_p  c_p * q_i^p
    New (tanh):        V(q_i) = sum_p  c_p * [tanh(alpha_i * q_i)]^p

For 2-mode terms:
    Old: V(q_i,q_j) = sum  c_pq * q_i^p * q_j^q
    New: V(q_i,q_j) = sum  c_pq * [tanh(alpha_i*q_i)]^p * [tanh(alpha_j*q_j)]^q

alpha_i is fit PER MODE (confirmed with Dr. Thomas, June 23) -- each mode
gets its own width parameter, found by the same coarse-then-fine 1D scan
used in gpr_to_sop.py.

OUTPUT FILES:
    f2<mol>_tanh.dat   -- 1-mode terms
    alphas_<mol>.dat   -- mode_index  alpha   (REQUIRED for MLCP to know
                          how to evaluate the new functions)

Usage:
    python3 gpr_to_sop_mlcp.py --molecule h2o \
        --1d-gprs gpr_fit_1d_mode1.npz gpr_fit_1d_mode2.npz gpr_fit_1d_mode3.npz \
        --modes 1 2 3 --n-terms 8
"""

import os
import sys
import argparse
import numpy as np

OPTGPR_DIR = os.path.expanduser("~/optGPRNN")
sys.path.insert(0, OPTGPR_DIR)


def predict_gpr_from_npz(npz_file, X_query, length_scale=None, noise=None):
    data = np.load(npz_file, allow_pickle=True)
    # Auto-detect sklearn model: if no W_opt key, load the .joblib model instead
    if "W_opt" not in data:
        import joblib, os
        model_file = npz_file.replace(".npz", ".joblib")
        if not os.path.exists(model_file):
            raise FileNotFoundError(f"sklearn model not found: {model_file}")
        gpr = joblib.load(model_file)
        return gpr.predict(X_query)
    W_opt = data["W_opt"]
    X_train = data["X_train"]
    y_train = data["y_train"]
    ls = float(data["length_scale"]) if length_scale is None else length_scale
    nz = float(data["noise"]) if noise is None else noise

    Y_train = np.hstack([X_train, np.dot(X_train, W_opt.T)])
    Y_query = np.hstack([X_query, np.dot(X_query, W_opt.T)])

    num_train, num_query = Y_train.shape[0], Y_query.shape[0]
    num_features = Y_train.shape[1]

    K_train = np.zeros((num_train, num_train))
    K_query = np.zeros((num_query, num_train))
    for f in range(num_features):
        ytr = Y_train[:, f].reshape(-1, 1)
        yq  = Y_query[:, f].reshape(-1, 1)
        K_train += np.exp(-((ytr - ytr.T) ** 2) / (2 * ls ** 2))
        K_query += np.exp(-((yq  - ytr.T) ** 2) / (2 * ls ** 2))
    K_train += nz * np.eye(num_train)
    c = np.linalg.solve(K_train, y_train)
    return np.dot(K_query, c)


def tanh_basis_matrix_1d(q, alpha, n_terms):
    t = np.tanh(alpha * q)
    return np.column_stack([t**n for n in range(1, n_terms + 1)])


def fit_sop_given_alpha_1d(q, V, alpha, n_terms, ridge=0.0):
    """
    ridge: optional L2 regularization strength. When > 0, solves the
    ridge-regularized normal equations instead of plain least squares.
    This directly addresses the near-degeneracy problem found with
    wide-displacement-range data (small alpha -> tanh powers become
    nearly linearly dependent -> huge canceling coefficients). Ridge
    regularization penalizes large coefficients, which should suppress
    that symptom -- though it does NOT fix the underlying near-degeneracy
    itself, it just prevents the fit from exploiting it pathologically.
    """
    Phi = tanh_basis_matrix_1d(q, alpha, n_terms)
    if ridge > 0:
        A = Phi.T @ Phi + ridge * np.eye(Phi.shape[1])
        b = Phi.T @ V
        c = np.linalg.solve(A, b)
    else:
        c, _, _, _ = np.linalg.lstsq(Phi, V, rcond=None)
    V_pred = Phi @ c
    rmse = np.sqrt(np.mean((V_pred - V) ** 2))
    return c, rmse


def optimize_alpha_1d(q, V, n_terms, alpha_range=(0.5, 50.0), n_scan=60, ridge=0.0):
    """
    Coarse-then-fine 1D scan for the optimal alpha. The fine-scan window
    is proportional to the coarse step size (not a fixed constant), since
    a fixed window fails badly when the true optimum is much smaller than
    that constant (e.g. alpha ~0.001-0.01 for wide-range data).

    ridge: passed through to fit_sop_given_alpha_1d. Use ridge > 0 for
    wide-displacement-range data where small alpha causes tanh powers to
    become nearly linearly dependent, producing huge canceling
    coefficients (confirmed both empirically and per Dr. Thomas's
    confirmation that Tikhonov/ridge regularization is the standard fix
    for this kind of ill-conditioning, also used internally in MLCP's
    own ALS and generalized eigenvalue solvers).
    """
    alphas = np.linspace(alpha_range[0], alpha_range[1], n_scan)
    coarse_step = alphas[1] - alphas[0]
    best_rmse, best_alpha, best_c = np.inf, None, None
    for alpha in alphas:
        c, rmse = fit_sop_given_alpha_1d(q, V, alpha, n_terms, ridge=ridge)
        if rmse < best_rmse:
            best_rmse, best_alpha, best_c = rmse, alpha, c

    fine_half_width = max(coarse_step, best_alpha * 0.5)
    fine_min = max(alpha_range[0], best_alpha - fine_half_width)
    fine_max = min(alpha_range[1], best_alpha + fine_half_width)
    for alpha in np.linspace(fine_min, fine_max, 60):
        c, rmse = fit_sop_given_alpha_1d(q, V, alpha, n_terms, ridge=ridge)
        if rmse < best_rmse:
            best_rmse, best_alpha, best_c = rmse, alpha, c

    fine_half_width_2 = max(fine_half_width * 0.1, 1e-6)
    fine_min_2 = max(alpha_range[0], best_alpha - fine_half_width_2)
    fine_max_2 = min(alpha_range[1], best_alpha + fine_half_width_2)
    for alpha in np.linspace(fine_min_2, fine_max_2, 60):
        c, rmse = fit_sop_given_alpha_1d(q, V, alpha, n_terms, ridge=ridge)
        if rmse < best_rmse:
            best_rmse, best_alpha, best_c = rmse, alpha, c

    return best_alpha, best_c, best_rmse


def tanh_basis_matrix_2d(qi, qj, alpha_i, alpha_j, max_power):
    ti = np.tanh(alpha_i * qi)
    tj = np.tanh(alpha_j * qj)
    terms, powers = [], []
    for p in range(0, max_power + 1):
        for q in range(0, max_power + 1):
            if p == 0 and q == 0:
                continue
            if p + q > max_power:
                continue
            terms.append((ti**p if p > 0 else np.ones_like(ti)) *
                         (tj**q if q > 0 else np.ones_like(tj)))
            powers.append((p, q))
    return np.column_stack(terms), powers


def fit_sop_2d_given_alphas(qi, qj, V, alpha_i, alpha_j, max_power):
    Phi, powers = tanh_basis_matrix_2d(qi, qj, alpha_i, alpha_j, max_power)
    c, _, _, _ = np.linalg.lstsq(Phi, V, rcond=None)
    V_pred = Phi @ c
    rmse = np.sqrt(np.mean((V_pred - V) ** 2))
    return c, powers, rmse


def tanh_basis_matrix_3d(qi, qj, qk, alpha_i, alpha_j, alpha_k, max_power):
    ti, tj, tk = np.tanh(alpha_i*qi), np.tanh(alpha_j*qj), np.tanh(alpha_k*qk)
    terms, powers = [], []
    for p in range(0, max_power + 1):
        for q in range(0, max_power + 1):
            for r in range(0, max_power + 1):
                if p == 0 and q == 0 and r == 0:
                    continue
                if p + q + r > max_power:
                    continue
                term = ((ti**p if p > 0 else np.ones_like(ti)) *
                        (tj**q if q > 0 else np.ones_like(tj)) *
                        (tk**r if r > 0 else np.ones_like(tk)))
                terms.append(term)
                powers.append((p, q, r))
    return np.column_stack(terms), powers


def fit_sop_3d_given_alphas(qi, qj, qk, V, alpha_i, alpha_j, alpha_k, max_power):
    Phi, powers = tanh_basis_matrix_3d(qi, qj, qk, alpha_i, alpha_j, alpha_k, max_power)
    c, _, _, _ = np.linalg.lstsq(Phi, V, rcond=None)
    V_pred = Phi @ c
    rmse = np.sqrt(np.mean((V_pred - V) ** 2))
    return c, powers, rmse


def convert_1d_terms(gpr_files, modes, n_terms, alpha_range, n_grid=200, ridge=0.0, range_fraction=1.0):
    alphas = {}
    f2_lines = []

    for gpr_file, mode in zip(gpr_files, modes):
        print(f"\n  --- Mode {mode} (1D) ---")
        data = np.load(gpr_file, allow_pickle=True)
        X_train = data["X_train"]
        q_min, q_max = X_train.min(), X_train.max()
        margin = 0.2 * (q_max - q_min)
        if range_fraction < 1.0:
            center = 0.5 * (q_min + q_max)
            half_range = 0.5 * (q_max - q_min) * range_fraction
            q_min_fit = center - half_range
            q_max_fit = center + half_range
            print(f"    Range restricted to {range_fraction*100:.0f}%: [{q_min_fit:.4f}, {q_max_fit:.4f}] Bohr")
        else:
            q_min_fit, q_max_fit = q_min - margin, q_max + margin
        q_grid = np.linspace(q_min_fit, q_max_fit, n_grid)
        X_query = q_grid.reshape(-1, 1)
        V_gpr = predict_gpr_from_npz(gpr_file, X_query)

        alpha, coeffs, rmse = optimize_alpha_1d(q_grid, V_gpr, n_terms, alpha_range, ridge=ridge)
        alphas[mode] = alpha
        max_coeff = np.abs(coeffs).max()
        print(f"    alpha = {alpha:.6f}   conversion RMSE = {rmse:.4f} cm-1   "
              f"max|coeff| = {max_coeff:.4e}")
        if max_coeff > 1e6 and ridge == 0.0:
            print(f"    WARNING: very large coefficient detected -- this often "
                  f"means the fit is ill-conditioned (tanh powers nearly "
                  f"linearly dependent at this alpha). Consider --ridge > 0.")

        for p, c in enumerate(coeffs, start=1):
            f2_lines.append((mode, p, c))
            print(f"    power {p}: coefficient = {c:.6f}")

    return alphas, f2_lines


def convert_2d_terms(residual_2d_specs, alphas, max_power):
    f3_lines = []
    for spec in residual_2d_specs:
        mi, mj = spec["mode_i"], spec["mode_j"]
        print(f"\n  --- Modes ({mi},{mj}) (2D residual) ---")
        coeffs, powers, rmse = fit_sop_2d_given_alphas(
            spec["Qi"], spec["Qj"], spec["R_2d"],
            alphas[mi], alphas[mj], max_power
        )
        print(f"    conversion RMSE = {rmse:.4f} cm-1  ({len(powers)} terms)")
        for (p, q), c in zip(powers, coeffs):
            f3_lines.append((mi, p, mj, q, c))
    return f3_lines


def convert_3d_terms(residual_3d_specs, alphas, max_power):
    f4_lines = []
    for spec in residual_3d_specs:
        mi, mj, mk = spec["mode_i"], spec["mode_j"], spec["mode_k"]
        print(f"\n  --- Modes ({mi},{mj},{mk}) (3D residual) ---")
        coeffs, powers, rmse = fit_sop_3d_given_alphas(
            spec["Qi"], spec["Qj"], spec["Qk"], spec["R_3d"],
            alphas[mi], alphas[mj], alphas[mk], max_power
        )
        print(f"    conversion RMSE = {rmse:.4f} cm-1  ({len(powers)} terms)")
        for (p, q, r), c in zip(powers, coeffs):
            f4_lines.append((mi, p, mj, q, mk, r, c))
    return f4_lines


def split_1d_terms_by_order(f2_lines, max_order=20):
    """
    MLCP's f<k><id>.dat naming refers to polynomial ORDER (confirmed
    directly from MLCP's source, FFPES.f90: it loops k=1 to ncp and looks
    for a file named 'f'+k+id+'.dat' for each k, skipping ahead if not
    found -- there is NO hardcoded ceiling at f4. Any order k is
    supported as long as the corresponding f<k><id>.dat file exists and
    ncp in the MLCP input is set >= the highest order used.

    A single-mode term tanh(alpha*q)^p belongs in file f<p><id>.dat,
    for ANY p from 1 to max_order (default 20, comfortably above any
    realistic tanh expansion length).

    Returns: dict {order: [lines]} for order in 1..max_order
    """
    by_order = {k: [] for k in range(1, max_order + 1)}
    for mode, power, coeff in f2_lines:
        if power < 1 or power > max_order:
            raise ValueError(
                f"power {power} for mode {mode} is outside the supported "
                f"range [1, {max_order}]. Increase max_order if you "
                f"genuinely need a higher-order tanh expansion."
            )
        by_order[power].append((mode, power, coeff))
    return by_order


def write_mlcp_file(filepath, lines, n_mode_cols):
    """
    Write lines in MLCP's f-file format for a SPECIFIC polynomial order
    (n_mode_cols = order, e.g. 2 for f2, 3 for f3, 4 for f4). Each line's
    power must exactly equal n_mode_cols -- this writer does NOT truncate
    or pad across different orders; call split_1d_terms_by_order() first
    to route terms to the correct order/file.
    """
    written = 0
    with open(filepath, "w") as f:
        for entry in lines:
            *mode_power_pairs, coeff = entry
            mode_indices = []
            for i in range(0, len(mode_power_pairs), 2):
                mode = mode_power_pairs[i]
                power = mode_power_pairs[i + 1]
                mode_indices.extend([mode] * power)
            if len(mode_indices) != n_mode_cols:
                raise ValueError(
                    f"Term {entry} has {len(mode_indices)} mode-index "
                    f"columns after power expansion, but this file expects "
                    f"exactly {n_mode_cols} (order-{n_mode_cols} file). "
                    f"Route terms by order using split_1d_terms_by_order() "
                    f"before calling write_mlcp_file()."
                )
            mode_str = "  ".join(f"{m:2d}" for m in mode_indices)
            coeff_str = f"{coeff:.4f}d0"
            f.write(f"  {mode_str}     {coeff_str}\n")
            written += 1
    print(f"  Saved {filepath}  ({written} terms)")


def write_alpha_file(filepath, alphas):
    with open(filepath, "w") as f:
        for mode in sorted(alphas.keys()):
            f.write(f"{mode:3d}  {alphas[mode]:16.8f}\n")
    print(f"  Saved {filepath}  ({len(alphas)} modes)")


def main():
    parser = argparse.ArgumentParser(
        description="Convert GPR PES to MLCP f2/f3/f4 format using tanh basis."
    )
    parser.add_argument("--molecule", type=str, required=True)
    parser.add_argument("--1d-gprs", dest="gpr_1d", type=str, nargs="+", required=True)
    parser.add_argument("--modes", type=int, nargs="+", required=True)
    parser.add_argument("--n-terms", type=int, default=8)
    parser.add_argument("--alpha-min", type=float, default=0.5)
    parser.add_argument("--alpha-max", type=float, default=2000.0,
                        help="Upper bound for alpha search (default: 2000, "
                             "comfortably covers narrow-displacement-range "
                             "data where the true optimum can sit in the "
                             "600-1000 range; widen further only if RMSE is "
                             "still improving right at this boundary)")
    parser.add_argument("--outdir", type=str, default=".")
    parser.add_argument("--range-fraction", type=float, default=1.0,
                        help="Fraction of the full GPR range to use for tanh fitting. "
                             "1.0 = full range (default). Try 0.75 to exclude the steep "
                             "outer edges that cause ill-conditioning for asymmetric potentials.")
    parser.add_argument("--ridge", type=float, default=0.0,
                        help="Ridge (Tikhonov) regularization strength for "
                             "the 1D least-squares fit (default: 0, no "
                             "regularization). Use a positive value (e.g. "
                             "1.0-100.0) for wide-displacement-range data "
                             "where small alpha causes near-degenerate tanh "
                             "powers and huge canceling coefficients -- "
                             "confirmed by Dr. Thomas as the standard fix "
                             "for this kind of ill-conditioning (same "
                             "technique used in MLCP's own ALS and "
                             "generalized eigenvalue solvers).")
    args = parser.parse_args()

    print(f"\n=== GPR -> MLCP SOP format conversion (tanh basis) ===")
    print(f"  Molecule: {args.molecule}")
    print(f"  Modes: {args.modes}")
    print(f"  Ridge regularization: {args.ridge}")

    alphas, f2_lines = convert_1d_terms(
        args.gpr_1d, args.modes, args.n_terms, (args.alpha_min, args.alpha_max),
        ridge=args.ridge, range_fraction=args.range_fraction
    )

    alpha_file = os.path.join(args.outdir, f"alphas_{args.molecule}.dat")

    print(f"\n--- Routing terms by polynomial order (confirmed: MLCP supports any order via f<k>{args.molecule}.dat naming) ---")
    by_order = split_1d_terms_by_order(f2_lines, max_order=args.n_terms)
    for k in sorted(by_order.keys()):
        if by_order[k]:
            print(f"  Order {k} (-> f{k}{args.molecule}.dat): {len(by_order[k])} terms")

    print(f"\n--- Writing output files ---")
    for k in sorted(by_order.keys()):
        if by_order[k]:
            fpath = os.path.join(args.outdir, f"f{k}{args.molecule}.dat")
            write_mlcp_file(fpath, by_order[k], n_mode_cols=k)
    write_alpha_file(alpha_file, alphas)

    max_order_used = max(k for k in by_order if by_order[k])
    print(f"\n  Done. 1D (single-mode) conversion complete, routed by polynomial order.")
    print(f"  IMPORTANT: set ncp >= {max_order_used} in the MLCP input file's")
    print(f"  control settings, so MLCP looks for all the f1..f{max_order_used}{args.molecule}.dat")
    print(f"  files generated here (confirmed from FFPES.f90: MLCP loops k=1..ncp")
    print(f"  and skips any order where the file isn't found).")
    print(f"\n  2D and 3D conversion require residual data from fit_gpr.py's")
    print(f"  --dim 2 / --dim 3 runs -- call convert_2d_terms() / convert_3d_terms()")
    print(f"  directly (see function docstrings) once that residual data exists.")


if __name__ == "__main__":
    main()
