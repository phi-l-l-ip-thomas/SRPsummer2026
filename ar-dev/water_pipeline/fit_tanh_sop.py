"""
Extracts a tanh(alpha*q)^p sum-of-products (SOP) expansion from a fitted
MFGP potential, per mode, matching the July 8 decision: ONE alpha per mode
(not a different alpha per coupling pair), stored in a single text file
that mlcp can read.

    V(q) ~= sum_{p=1}^{P} c_p * tanh(alpha * q)^p

Fit strategy: sample the trained MFGP densely over the mode's range, then
nonlinearly fit (alpha, c_1...c_P) jointly with scipy.optimize.curve_fit.
V(0) = 0 is automatically satisfied since tanh(0) = 0.

Outputs:
    alpha_water_fit.dat   -- mode, alpha, beta(placeholder), rmse_fit
    tanh_coeffs_mode{N}.dat -- p, c_p (in cm^-1) for each mode

IMPORTANT: this does NOT yet write directly into your existing f3water.dat
...f16water.dat files, because I don't know their exact index/format
convention. Once I see one example line from e.g. f3water.dat I can add a
merge step that writes these coefficients into the correct diagonal
[mode,mode,...,mode] slot without touching your existing coupling terms.
"""

import numpy as np
from scipy.optimize import curve_fit

from mfgp import MultiFidelityGP


def tanh_sop(q, alpha, *c):
    """V(q) = sum_p c[p-1] * tanh(alpha*q)^p"""
    t = np.tanh(alpha * q)
    v = np.zeros_like(q)
    tp = np.ones_like(q)  # tanh(alpha q)^0, will be multiplied up each loop
    for p, cp in enumerate(c, start=1):
        tp = tp * t  # now t^p
        v = v + cp * tp
    return v


def fit_tanh_sop_for_mode(mode, hf_data, lf_data, P=6, n_grid=400,
                           n_restarts_gp=15, kernel="matern52", q_pad=1.1):
    """
    Fits the MFGP for `mode`, samples it densely, then fits a P-term
    tanh(alpha q)^p expansion with a single shared alpha.

    q_pad: fraction to extend the sampling grid beyond the HF data range,
    to get slightly better behavior near the edges of your fit domain
    (do NOT extrapolate far beyond this -- MFGP is not reliable there).
    """
    hf_steps = np.array([s for (m, s) in hf_data if m == mode], dtype=float)
    hf_y = np.array([hf_data[(mode, s)] for s in hf_steps])
    lf_steps = np.array([s for (m, s) in lf_data if m == mode], dtype=float)
    lf_y = np.array([lf_data[(mode, s)] for s in lf_steps])

    X_hf = hf_steps.reshape(-1, 1)
    X_lf = lf_steps.reshape(-1, 1)

    mfgp = MultiFidelityGP(kernel=kernel).fit(X_hf, hf_y, X_lf, lf_y,
                                                n_restarts=n_restarts_gp, verbose=False)

    q_min, q_max = hf_steps.min() * q_pad, hf_steps.max() * q_pad
    q_grid = np.linspace(q_min, q_max, n_grid)
    v_grid = mfgp.predict(q_grid.reshape(-1, 1))

    # --- normalize for numerical conditioning ---
    # tanh(alpha*q)^p fits are notoriously ill-conditioned when q and V are
    # on very different scales (e.g. q ~ O(1) bohr, V ~ O(1e4) cm^-1) because
    # alpha and the c_p's trade off against each other during optimization.
    # Fit in normalized units, then rescale back.
    q_scale = np.max(np.abs(q_grid))
    v_scale = np.max(np.abs(v_grid))
    qn = q_grid / q_scale
    vn = v_grid / v_scale

    def model(q, alpha, *c):
        return tanh_sop(q, alpha, *c)

    # alpha in normalized units: tanh saturates by |alpha*q| ~ 2-3, and
    # qn ranges over roughly [-1, 1], so alpha0 ~ 2 is a good universal start
    alpha0 = 2.0
    c0 = [1.0] + [0.1] * (P - 1)
    p0 = [alpha0] + c0

    bounds_lo = [1e-3] + [-50.0] * P
    bounds_hi = [50.0] + [50.0] * P

    try:
        popt, pcov = curve_fit(model, qn, vn, p0=p0, maxfev=40000,
                                bounds=(bounds_lo, bounds_hi), method="trf")
    except RuntimeError as e:
        print(f"[WARN] mode {mode}: curve_fit did not converge ({e}); "
              f"try increasing P, adjusting p0, or checking data range")
        return None

    # rescale back to physical units: alpha_phys = alpha_norm / q_scale,
    # c_p_phys = c_p_norm * v_scale
    alpha_fit = popt[0] / q_scale
    c_fit = popt[1:] * v_scale

    v_fit = tanh_sop(q_grid, alpha_fit, *c_fit)
    rmse = np.sqrt(np.mean((v_fit - v_grid) ** 2))

    print(f"Mode {mode}: alpha={alpha_fit:.6f}, P={P} terms, "
          f"fit RMSE vs MFGP = {rmse:.4f} cm^-1 over grid "
          f"[{q_min:.3f}, {q_max:.3f}]")

    return {"mode": mode, "alpha": alpha_fit, "c": c_fit, "rmse": rmse,
            "mfgp": mfgp, "q_grid": q_grid, "v_grid": v_grid, "v_fit": v_fit}


def fit_all_modes_and_write(hf_data, lf_data, modes=(1, 2, 3), P=6,
                             out_alpha="alpha_water_fit.dat"):
    results = {}
    with open(out_alpha, "w") as f_alpha:
        f_alpha.write("# mode  alpha  beta  fit_rmse_cm1\n")
        for mode in modes:
            r = fit_tanh_sop_for_mode(mode, hf_data, lf_data, P=P)
            if r is None:
                continue
            results[mode] = r
            # beta placeholder: 0.0 (symmetric-mode convention from your
            # July 8 notes -- only alpha used for tanh modes; if this mode
            # is asymmetric/morse instead, beta needs separate handling --
            # see note below)
            f_alpha.write(f"{mode}  {r['alpha']:.8f}  0.0  {r['rmse']:.6f}\n")

            coeff_path = f"tanh_coeffs_mode{mode}.dat"
            with open(coeff_path, "w") as f_c:
                f_c.write(f"# mode {mode} tanh(alpha*q)^p coefficients, alpha={r['alpha']:.8f}\n")
                f_c.write("# p  c_p (cm^-1)\n")
                for p, cp in enumerate(r["c"], start=1):
                    f_c.write(f"{p}  {cp:.6f}\n")
            print(f"  -> wrote {coeff_path}")

    print(f"\nWrote {out_alpha}")
    return results


if __name__ == "__main__":
    from load_data import load_expensive_points, load_cheap_points
    hf_data = load_expensive_points(".")
    lf_data = load_cheap_points(".")
    fit_all_modes_and_write(hf_data, lf_data, modes=(1, 2, 3), P=6)
