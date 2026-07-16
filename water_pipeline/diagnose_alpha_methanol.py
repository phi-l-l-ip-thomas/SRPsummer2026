import numpy as np
import joblib
from scipy.optimize import minimize_scalar

# ---------------------------------------------------------------
# 0. Sanity check: are the mode2/mode3 GPR models actually distinct?
# ---------------------------------------------------------------
def check_models_distinct(files, q_test=np.linspace(-1.0, 1.0, 25)):
    preds = {}
    for f in files:
        gpr = joblib.load(f)
        preds[f] = gpr.predict(q_test.reshape(-1, 1))
    keys = list(preds.keys())
    print("Model distinctness check (max |V_i - V_j - const|, should be > ~1e-3):")
    for i in range(len(keys)):
        for j in range(i + 1, len(keys)):
            diff = preds[keys[i]] - preds[keys[j]]
            spread = diff.max() - diff.min()  # nonzero if predictions aren't identical up to a shift
            print(f"  {keys[i]} vs {keys[j]}: spread={spread:.6e}")
    return preds


# ---------------------------------------------------------------
# 1. Fit alpha with a fine grid + local polish, and return diagnostics
#    (fit quality, curvature of RMSE(alpha), and the fitted curve itself
#     so you can plot/inspect it)
# ---------------------------------------------------------------
def fit_tanh_alpha(gpr_file, q_max=1.5, rf=0.30, n=8, ridge=1.0,
                    alpha_bounds=(0.02, 6.0), n_coarse=400):
    gpr = joblib.load(gpr_file)
    q_fine = np.linspace(-q_max, q_max, 5000)
    V_fine = gpr.predict(q_fine.reshape(-1, 1))
    q_min = q_fine[np.argmin(V_fine)]
    V_min = V_fine.min()

    half = q_max * rf
    q_grid = np.linspace(q_min - half, q_min + half, 300)
    q_shifted = q_grid - q_min
    V = gpr.predict(q_grid.reshape(-1, 1)) - V_min

    def rmse_for_alpha(alpha):
        t = np.tanh(alpha * q_shifted)
        Phi = np.column_stack([np.ones(len(q_shifted))] + [t ** p for p in range(1, n + 1)])
        A = Phi.T @ Phi + ridge * np.eye(Phi.shape[1])
        c, *_ = np.linalg.lstsq(A, Phi.T @ V, rcond=None)
        return np.sqrt(np.mean((Phi @ c - V) ** 2)), c

    # coarse scan first (finer than the original 80 pts) to find the basin
    alphas_coarse = np.linspace(*alpha_bounds, n_coarse)
    rmses_coarse = np.array([rmse_for_alpha(a)[0] for a in alphas_coarse])
    i0 = np.argmin(rmses_coarse)
    a0 = alphas_coarse[i0]

    # local polish with a bounded scalar optimizer around the coarse minimum
    lo = max(alpha_bounds[0], a0 - 0.1)
    hi = min(alpha_bounds[1], a0 + 0.1)
    res = minimize_scalar(lambda a: rmse_for_alpha(a)[0], bounds=(lo, hi), method='bounded',
                           options={'xatol': 1e-5})
    alpha_best = res.x
    rmse_best, coeffs_best = rmse_for_alpha(alpha_best)

    # flatness diagnostic: how much does RMSE change over +/- 0.2 from optimum?
    rmse_lo, _ = rmse_for_alpha(max(alpha_bounds[0], alpha_best - 0.2))
    rmse_hi, _ = rmse_for_alpha(min(alpha_bounds[1], alpha_best + 0.2))
    flatness = max(rmse_lo, rmse_hi) - rmse_best  # small -> alpha poorly constrained

    return {
        "alpha": alpha_best,
        "rmse": rmse_best,
        "coeffs": coeffs_best,
        "q_min": q_min,
        "V_min": V_min,
        "q_shifted": q_shifted,
        "V": V,
        "flatness": flatness,
        "alphas_coarse": alphas_coarse,
        "rmses_coarse": rmses_coarse,
    }


def print_fit_diagnostic(mode, result):
    a, rmse, flat = result["alpha"], result["rmse"], result["flatness"]
    print(f"  Mode {mode}: alpha={a:.4f}  RMSE={rmse:.2f} cm-1  "
          f"flatness(+/-0.2)={flat:.2f} cm-1  "
          f"{'<-- POORLY CONSTRAINED' if flat < 2.0 else ''}")


# ---------------------------------------------------------------
# Mode info
# ---------------------------------------------------------------
modes       = [1, 2, 3]
freqs_pbqff = [2855.920572, 2809.934421, 1395.401993]
asymmetric  = [2]

model_files = [f'sklearn_gpr_optimal_mode{m}.joblib' for m in modes]
check_models_distinct(model_files)

data = np.load('water_sop_params.npz', allow_pickle=True)

print("\nFitting tanh alpha for all modes (for coupling terms)...")
tanh_alphas = {}
morse_betas = {}
fit_results = {}

for mode in modes:
    result = fit_tanh_alpha(f'sklearn_gpr_optimal_mode{mode}.joblib')
    fit_results[mode] = result
    tanh_alphas[mode] = result["alpha"]
    print_fit_diagnostic(mode, result)
    if mode in asymmetric:
        beta = float(data[f'mode{mode}_value'])
        morse_betas[mode] = beta
        print(f"  Mode {mode}: Morse beta={beta:.4f} (from saved params)")

# ---------------------------------------------------------------
# Flag if any two modes land within 1e-3 of each other -- worth a manual look
# ---------------------------------------------------------------
print("\nPairwise alpha proximity check:")
for i, m1 in enumerate(modes):
    for m2 in modes[i + 1:]:
        d = abs(tanh_alphas[m1] - tanh_alphas[m2])
        if d < 1e-3:
            print(f"  ⚠ Mode {m1} and Mode {m2} alphas match to within {d:.2e} -- verify this isn't a data-loading bug")
        else:
            print(f"  Mode {m1} vs Mode {m2}: |Δalpha| = {d:.4f}")

# ---------------------------------------------------------------
# Write output files (unchanged format from before)
# ---------------------------------------------------------------
with open('alpha_water.dat', 'w') as f:
    f.write("# Water SOP parameters\n")
    f.write("# mode  alpha(tanh)  beta(Morse, asymmetric only)\n")
    for mode in modes:
        if mode in asymmetric:
            f.write(f"  {mode}    {tanh_alphas[mode]:.6f}    {morse_betas[mode]:.6f}\n")
        else:
            f.write(f"  {mode}    {tanh_alphas[mode]:.6f}\n")

with open('omega_water.dat', 'w') as f:
    f.write("# Water harmonic frequencies\n")
    f.write("# mode  omega(cm-1)  source\n")
    for mode, freq in zip(modes, freqs_pbqff):
        f.write(f"  {mode}    {freq:.6f}    PBQFF/PM7\n")

print("\nalpha_water.dat:")
print(open('alpha_water.dat').read())
print("omega_water.dat:")
print(open('omega_water.dat').read())

# ---------------------------------------------------------------
# Optional: save fit diagnostics (q_shifted, V, coeffs, rmse curve) so
# you can plot V_gpr vs V_tanh_fit per mode without re-running the GPRs
# ---------------------------------------------------------------
np.savez('alpha_fit_diagnostics.npz',
         **{f'mode{m}_q_shifted': fit_results[m]['q_shifted'] for m in modes},
         **{f'mode{m}_V': fit_results[m]['V'] for m in modes},
         **{f'mode{m}_coeffs': fit_results[m]['coeffs'] for m in modes},
         **{f'mode{m}_alphas_coarse': fit_results[m]['alphas_coarse'] for m in modes},
         **{f'mode{m}_rmses_coarse': fit_results[m]['rmses_coarse'] for m in modes})
print("\nSaved alpha_fit_diagnostics.npz for plotting V_gpr vs V_tanh_fit per mode.")
