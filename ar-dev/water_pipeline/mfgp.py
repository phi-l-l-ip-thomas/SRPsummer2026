"""
Multi-fidelity Gaussian Process regression using the "linear truncated kernel"
construction (Akram et al., J. Chem. Phys. 164, 114108 (2026), Sec. IV, Eqs. 15-19).

Key idea (this is the part that was almost certainly broken in the ad hoc
combined_kernel): fidelities are NOT symmetric. We build

    Cov(V, V)         = k0(x, x')
    Cov(V, V_LF)      = k0(x, x')
    Cov(V_LF, V_LF)   = k0(x, x') + k1(x, x')

i.e. the low-fidelity (cheap) surface is the high-fidelity surface plus an
independent bias process k1. k1 is only ever "active" between two low-fidelity
points. This means low-fidelity data can inform the shared latent process k0,
but its idiosyncratic bias cannot leak into the high-fidelity prediction.
That's the mechanism that prevents exactly the mode-2/mode-3 blowup you saw.

This module is data-format agnostic: you hand it two point sets
(X_hf, y_hf) and (X_lf, y_lf), each X being (N, d) arrays of geometry/mode
coordinates (reduced normal coordinates q_i, or (mode, step) turned into a
1D coordinate -- whatever your fN convention uses), and it returns a
predictor plus fitted hyperparameters.
"""

import numpy as np
from scipy.optimize import minimize
from scipy.spatial.distance import cdist


# ----------------------------------------------------------------------
# Matern 5/2 kernel (the paper's choice; swap in rbf_kernel below if you
# want to try that instead -- see note at bottom of file)
# ----------------------------------------------------------------------
def matern52(X1, X2, length_scale, sigma2):
    """
    X1: (N1, d), X2: (N2, d), length_scale: scalar or (d,) array (ARD),
    sigma2: scalar amplitude^2. Returns (N1, N2) covariance matrix.
    """
    X1 = np.atleast_2d(X1)
    X2 = np.atleast_2d(X2)
    ls = np.atleast_1d(length_scale)
    # scaled Euclidean distance, supports per-dimension length scales (ARD)
    ls = np.maximum(ls, 1e-8)
    d = cdist(X1 / ls, X2 / ls, metric="euclidean")
    sqrt5_d = np.sqrt(5.0) * d
    return sigma2 * (1.0 + sqrt5_d + (5.0 / 3.0) * d**2) * np.exp(-sqrt5_d)


def rbf_kernel(X1, X2, length_scale, sigma2):
    X1 = np.atleast_2d(X1)
    X2 = np.atleast_2d(X2)
    ls = np.atleast_1d(length_scale)
    ls = np.maximum(ls, 1e-8)
    d2 = cdist(X1 / ls, X2 / ls, metric="sqeuclidean")
    return sigma2 * np.exp(-0.5 * d2)


KERNELS = {"matern52": matern52, "rbf": rbf_kernel}


# ----------------------------------------------------------------------
# Multi-fidelity GP object
# ----------------------------------------------------------------------
class MultiFidelityGP:
    """
    Linear truncated kernel MFGP, matching Eqs. (15)-(19) of the paper.

    b = 1 for high-fidelity (HF) points, b = 0 for low-fidelity (LF) points.

        K_ij = sigma^2 [ k0(xi,xj) + (1-bi)(1-bj) k1(xi,xj) ] + sigma_n^2 delta_ij

    Note sigma^2 is factored OUT of k0/k1 here into a single shared amplitude,
    matching Eq. (17)-(18); if you want independent amplitudes for k0 and k1
    (sometimes helps when LF data is very noisy/biased) see fit() docstring.
    """

    def __init__(self, kernel="matern52"):
        self.kernel_fn = KERNELS[kernel]
        self.is_fit = False

    # -- internal: build full covariance for augmented dataset -----------
    def _K(self, X, b, params):
        sigma2, ls0, ls1, noise2 = params
        k0 = self.kernel_fn(X, X, ls0, sigma2)
        k1 = self.kernel_fn(X, X, ls1, sigma2)
        mask = np.outer(1 - b, 1 - b)  # 1 only where BOTH points are LF
        K = k0 + mask * k1
        K += noise2 * np.eye(len(X))
        return K

    def _k_star(self, X_train, b_train, X_test, params):
        # test points are always evaluated at HF fidelity (b=1), so the
        # k1 bias term never contributes to the cross-covariance --
        # this is the "triangular information flow" from the paper.
        sigma2, ls0, ls1, noise2 = params
        return self.kernel_fn(X_test, X_train, ls0, sigma2)

    # -- negative log marginal likelihood ---------------------------------
    def _nll(self, theta, X, b, y, mean):
        log_sigma2, log_ls0, log_ls1, log_noise2 = theta
        params = (np.exp(log_sigma2), np.exp(log_ls0), np.exp(log_ls1), np.exp(log_noise2))
        K = self._K(X, b, params)
        y_c = y - mean
        try:
            L = np.linalg.cholesky(K + 1e-10 * np.eye(len(X)))
        except np.linalg.LinAlgError:
            return 1e10
        alpha = np.linalg.solve(L.T, np.linalg.solve(L, y_c))
        nll = 0.5 * y_c @ alpha + np.sum(np.log(np.diag(L))) + 0.5 * len(X) * np.log(2 * np.pi)
        return nll

    def fit(self, X_hf, y_hf, X_lf, y_lf, n_restarts=8, noise2=1e-6, fix_noise=True,
            verbose=True):
        """
        X_hf, X_lf: (N, d) arrays of coordinates (same coordinate system!)
        y_hf, y_lf: (N,) arrays of energies (same units!)

        fix_noise: paper fixes sigma_y^2 = 1e-6 cm^-1 (essentially noiseless
        ab initio data) rather than fitting it -- recommended, keeps the
        optimizer well behaved with sparse HF data.
        """
        X = np.vstack([X_hf, X_lf])
        y = np.concatenate([y_hf, y_lf])
        b = np.concatenate([np.ones(len(X_hf)), np.zeros(len(X_lf))])
        mean = np.mean(y_hf)  # constant mean, learned from HF data as in the paper

        d = X.shape[1]
        best = None
        rng = np.random.default_rng(0)

        # --- data-driven length-scale bounds ---
        # With only ~11 HF points, an unconstrained length-scale search can
        # find a very short length scale that nearly interpolates each HF
        # point exactly (high marginal likelihood) while oscillating wildly
        # BETWEEN points -- this produces both bad predictions at held-out
        # test points AND severely underestimated uncertainty (the model is
        # "confident" near training points and blind to how wrong it is
        # in between). Bounding the length scale below the typical spacing
        # of the HF training data prevents this degenerate regime.
        hf_sorted = np.sort(np.unique(X_hf.ravel()))
        if len(hf_sorted) > 1:
            typical_spacing = np.median(np.diff(hf_sorted))
        else:
            typical_spacing = 1.0
        ls_lower_bound = max(typical_spacing * 0.5, 1e-3)

        for trial in range(n_restarts):
            # random init in log-space, spread over a few orders of magnitude
            log_sigma2 = rng.uniform(-2, 4)
            log_ls0 = rng.uniform(-1, 2, size=1)[0] if d == 1 else rng.uniform(-1, 2, size=d)
            log_ls1 = rng.uniform(-1, 2, size=1)[0] if d == 1 else rng.uniform(-1, 2, size=d)
            log_noise2 = np.log(noise2)

            theta0 = np.concatenate([
                [log_sigma2],
                np.atleast_1d(log_ls0),
                np.atleast_1d(log_ls1),
                [log_noise2],
            ])

            def objective(theta):
                ls_dim = d
                log_sigma2 = theta[0]
                log_ls0 = theta[1:1 + ls_dim]
                log_ls1 = theta[1 + ls_dim:1 + 2 * ls_dim]
                log_noise2_ = theta[-1] if not fix_noise else np.log(noise2)
                full_theta = np.concatenate([[log_sigma2], [np.mean(log_ls0)],
                                              [np.mean(log_ls1)], [log_noise2_]])
                # NOTE: for simplicity this driver treats length scales as
                # isotropic (scalar). For ARD (per-mode length scales) pass
                # ls0/ls1 as (d,) arrays through to _K/_k_star directly and
                # optimize theta of length 2+2d+1 -- straightforward
                # extension if your coordinate has multiple active modes.
                return self._nll(full_theta, X, b, y, mean)

            bounds = [(-5, 15)]  # sigma2: unrestricted
            bounds += [(np.log(ls_lower_bound), 15)] * d  # ls0: bounded below
            bounds += [(np.log(ls_lower_bound), 15)] * d  # ls1: bounded below
            bounds += [(-5, 15)]  # noise2 (unused if fix_noise)

            try:
                res = minimize(objective, theta0, method="L-BFGS-B", bounds=bounds)
            except Exception:
                continue

            if best is None or res.fun < best.fun:
                best = res

        log_sigma2, log_ls0, log_ls1, log_noise2 = best.x
        self.params = (np.exp(log_sigma2), np.exp(log_ls0), np.exp(log_ls1),
                        noise2 if fix_noise else np.exp(log_noise2))
        self.X, self.b, self.y, self.mean = X, b, y, mean
        K = self._K(X, b, self.params)
        self.L = np.linalg.cholesky(K + 1e-10 * np.eye(len(X)))
        self.alpha = np.linalg.solve(self.L.T, np.linalg.solve(self.L, y - mean))
        self.is_fit = True

        if verbose:
            sigma2, ls0, ls1, noise2_ = self.params
            print(f"[MFGP] fit complete: sigma2={sigma2:.4g}, ls0={ls0:.4g}, "
                  f"ls1={ls1:.4g}, noise2={noise2_:.4g}, nll={best.fun:.4f}")
        return self

    def predict(self, X_test, return_std=False):
        assert self.is_fit, "call fit() first"
        k_star = self._k_star(self.X, self.b, X_test, self.params)  # (n_test, N)
        mean_pred = self.mean + k_star @ self.alpha
        if not return_std:
            return mean_pred
        v = np.linalg.solve(self.L, k_star.T)
        sigma2, ls0, ls1, noise2_ = self.params
        k_ss = self.kernel_fn(X_test, X_test, ls0, sigma2)
        var = np.diag(k_ss) - np.sum(v**2, axis=0)
        var = np.maximum(var, 0.0)
        return mean_pred, np.sqrt(var)


# ----------------------------------------------------------------------
# Single-fidelity baseline (your "sequential" GP), for apples-to-apples
# comparison -- same kernel machinery, just no LF data / no b column.
# ----------------------------------------------------------------------
class SingleFidelityGP:
    def __init__(self, kernel="matern52"):
        self.kernel_fn = KERNELS[kernel]
        self.is_fit = False

    def fit(self, X, y, n_restarts=8, noise2=1e-6, verbose=True):
        mean = np.mean(y)
        best = None
        rng = np.random.default_rng(0)

        x_sorted = np.sort(np.unique(X.ravel()))
        if len(x_sorted) > 1:
            typical_spacing = np.median(np.diff(x_sorted))
        else:
            typical_spacing = 1.0
        ls_lower_bound = max(typical_spacing * 0.5, 1e-3)

        for _ in range(n_restarts):
            log_sigma2 = rng.uniform(-2, 4)
            log_ls = rng.uniform(-1, 2)
            log_noise2 = np.log(noise2)
            theta0 = np.array([log_sigma2, log_ls, log_noise2])

            def objective(theta):
                sigma2, ls, noise2_ = np.exp(theta)
                K = self.kernel_fn(X, X, ls, sigma2) + noise2 * np.eye(len(X))
                y_c = y - mean
                try:
                    L = np.linalg.cholesky(K + 1e-10 * np.eye(len(X)))
                except np.linalg.LinAlgError:
                    return 1e10
                alpha = np.linalg.solve(L.T, np.linalg.solve(L, y_c))
                return 0.5 * y_c @ alpha + np.sum(np.log(np.diag(L)))

            bounds = [(-5, 15), (np.log(ls_lower_bound), 15), (-5, 15)]

            try:
                res = minimize(objective, theta0, method="L-BFGS-B", bounds=bounds)
            except Exception:
                continue
            if best is None or res.fun < best.fun:
                best = res

        sigma2, ls, noise2_ = np.exp(best.x)
        self.params = (sigma2, ls, noise2)
        self.X, self.y, self.mean = X, y, mean
        K = self.kernel_fn(X, X, ls, sigma2) + noise2 * np.eye(len(X))
        self.L = np.linalg.cholesky(K + 1e-10 * np.eye(len(X)))
        self.alpha = np.linalg.solve(self.L.T, np.linalg.solve(self.L, y - mean))
        self.is_fit = True
        if verbose:
            print(f"[SFGP] fit complete: sigma2={sigma2:.4g}, ls={ls:.4g}")
        return self

    def predict(self, X_test):
        sigma2, ls, noise2_ = self.params
        k_star = self.kernel_fn(X_test, self.X, ls, sigma2)
        return self.mean + k_star @ self.alpha


def recheck_mode(mode, hf_data, lf_data, test_data, kernel="matern52", n_restarts=25):
    """Re-fit a single mode with more restarts -- useful for double-checking
    a mode where MFGP looked flat or slightly worse than single-fidelity,
    since Matern/RBF marginal likelihood surfaces are multimodal and a
    small n_restarts can land in a mediocre local optimum."""
    hf_steps = np.array([s for (m, s) in hf_data if m == mode], dtype=float)
    hf_y = np.array([hf_data[(mode, s)] for s in hf_steps])
    lf_steps = np.array([s for (m, s) in lf_data if m == mode], dtype=float)
    lf_y = np.array([lf_data[(mode, s)] for s in lf_steps])
    test_steps = np.array([s for (m, s) in test_data if m == mode], dtype=float)
    test_y = np.array([test_data[(mode, s)] for s in test_steps])

    X_hf, X_lf, X_test = hf_steps.reshape(-1, 1), lf_steps.reshape(-1, 1), test_steps.reshape(-1, 1)

    sfgp = SingleFidelityGP(kernel=kernel).fit(X_hf, hf_y, n_restarts=n_restarts, verbose=False)
    sf_rmse = np.sqrt(np.mean((sfgp.predict(X_test) - test_y) ** 2))

    mfgp = MultiFidelityGP(kernel=kernel).fit(X_hf, hf_y, X_lf, lf_y, n_restarts=n_restarts, verbose=False)
    mf_rmse = np.sqrt(np.mean((mfgp.predict(X_test) - test_y) ** 2))

    print(f"Mode {mode} (n_restarts={n_restarts}): SF={sf_rmse:.2f}  MF={mf_rmse:.2f}  "
          f"({'YES' if mf_rmse < sf_rmse else 'no'})")
    return sfgp, mfgp, sf_rmse, mf_rmse


# ----------------------------------------------------------------------
# Predictive uncertainty / calibration report
# ----------------------------------------------------------------------
def uncertainty_report(mode, hf_data, lf_data, test_data, kernel="matern52",
                        n_restarts=15):
    """
    Fits MFGP for one mode and reports predictive std alongside actual error
    at each test point -- tells you whether the model's uncertainty
    estimates are trustworthy (well-calibrated) or overconfident/underconfident.

    A well-calibrated model should have |error| roughly <= 2*std for most
    points (95% coverage under Gaussian assumption).
    """
    hf_steps = np.array([s for (m, s) in hf_data if m == mode], dtype=float)
    hf_y = np.array([hf_data[(mode, s)] for s in hf_steps])
    lf_steps = np.array([s for (m, s) in lf_data if m == mode], dtype=float)
    lf_y = np.array([lf_data[(mode, s)] for s in lf_steps])
    test_steps = np.array([s for (m, s) in test_data if m == mode], dtype=float)
    test_y = np.array([test_data[(mode, s)] for s in test_steps])

    X_hf, X_lf, X_test = hf_steps.reshape(-1, 1), lf_steps.reshape(-1, 1), test_steps.reshape(-1, 1)

    mfgp = MultiFidelityGP(kernel=kernel).fit(X_hf, hf_y, X_lf, lf_y,
                                                n_restarts=n_restarts, verbose=False)
    mean_pred, std_pred = mfgp.predict(X_test, return_std=True)
    errors = mean_pred - test_y

    within_1sig = np.mean(np.abs(errors) <= std_pred)
    within_2sig = np.mean(np.abs(errors) <= 2 * std_pred)

    print(f"\n--- Mode {mode} uncertainty calibration ---")
    print(f"{'step':>10} {'true (cm-1)':>14} {'pred (cm-1)':>14} "
          f"{'error':>10} {'std':>10} {'|err|/std':>10}")
    order = np.argsort(test_steps)
    for i in order:
        ratio = abs(errors[i]) / std_pred[i] if std_pred[i] > 0 else np.inf
        print(f"{test_steps[i]:>10.4f} {test_y[i]:>14.2f} {mean_pred[i]:>14.2f} "
              f"{errors[i]:>10.2f} {std_pred[i]:>10.2f} {ratio:>10.2f}")
    print(f"\nFraction within 1 std: {within_1sig:.2f} (want ~0.68 if well-calibrated)")
    print(f"Fraction within 2 std: {within_2sig:.2f} (want ~0.95 if well-calibrated)")
    return mfgp, mean_pred, std_pred, errors



def per_mode_rmse_report(hf_data, lf_data, test_data, kernel="matern52",
                          n_restarts=8):
    """
    hf_data, lf_data, test_data: dict[(mode, step)] -> energy, exactly like
    your existing test_data dict. This reproduces your table but with the
    corrected linear-truncated-kernel MFGP, plus a single-fidelity (HF-only)
    baseline for comparison.

    Coordinate convention: we use `step` as the 1D input coordinate per
    mode (matches your sequential_rmse baseline, which is fit mode-by-mode).
    If you want a joint multi-mode fit, stack (mode_index, step) as a 2D
    input instead -- flag if that's what you need and I'll extend this.
    """
    modes = sorted(set(m for (m, s) in hf_data.keys()))
    print(f"{'Mode':>5} {'SF (HF-only)':>14} {'MFGP':>12} {'Better?':>10}")
    print("-" * 46)

    results = {}
    for mode in modes:
        hf_steps = np.array([s for (m, s) in hf_data if m == mode], dtype=float)
        hf_y = np.array([hf_data[(mode, s)] for s in hf_steps])

        lf_steps = np.array([s for (m, s) in lf_data if m == mode], dtype=float)
        lf_y = np.array([lf_data[(mode, s)] for s in lf_steps])

        test_steps = np.array([s for (m, s) in test_data if m == mode], dtype=float)
        test_y = np.array([test_data[(mode, s)] for s in test_steps])

        if len(hf_steps) < 3 or len(test_steps) == 0:
            print(f"{mode:>5}  (skipped: insufficient HF/test points)")
            continue

        X_hf = hf_steps.reshape(-1, 1)
        X_lf = lf_steps.reshape(-1, 1)
        X_test = test_steps.reshape(-1, 1)

        # single-fidelity baseline (HF only)
        sfgp = SingleFidelityGP(kernel=kernel).fit(X_hf, hf_y, n_restarts=n_restarts,
                                                     verbose=False)
        sf_pred = sfgp.predict(X_test)
        sf_rmse = np.sqrt(np.mean((sf_pred - test_y) ** 2))

        # multi-fidelity
        mfgp = MultiFidelityGP(kernel=kernel).fit(X_hf, hf_y, X_lf, lf_y,
                                                    n_restarts=n_restarts, verbose=False)
        mf_pred = mfgp.predict(X_test)
        mf_rmse = np.sqrt(np.mean((mf_pred - test_y) ** 2))

        better = "YES" if mf_rmse < sf_rmse else "no"
        print(f"{mode:>5} {sf_rmse:>14.2f} {mf_rmse:>12.2f} {better:>10}")
        results[mode] = {"sf_rmse": sf_rmse, "mf_rmse": mf_rmse,
                          "sf_model": sfgp, "mf_model": mfgp}

    return results


if __name__ == "__main__":
    # -------------------------------------------------------------
    # Minimal smoke test with synthetic data so you can confirm the
    # module runs before pointing it at your real hf/lf/test dicts.
    # Replace this block with your actual data loading on Perlmutter.
    # -------------------------------------------------------------
    rng = np.random.default_rng(1)

    def true_pes(q):
        return 5000 * q**2 + 800 * q**3  # toy anharmonic mode

    def cheap_pes(q):
        # deliberately WRONG curvature at large |q| -- mimics a cheap
        # method that fails qualitatively far from equilibrium
        return true_pes(q) + 300 * np.sin(3 * q) + 200

    hf_data, lf_data, test_data = {}, {}, {}
    for mode in [1, 2, 3]:
        hf_steps = np.linspace(-1, 1, 7)
        lf_steps = np.linspace(-3, 3, 40)
        test_steps = np.linspace(-2.5, 2.5, 25)
        for s in hf_steps:
            hf_data[(mode, s)] = true_pes(s) + rng.normal(0, 1)
        for s in lf_steps:
            lf_data[(mode, s)] = cheap_pes(s) + rng.normal(0, 5)
        for s in test_steps:
            test_data[(mode, s)] = true_pes(s)

    per_mode_rmse_report(hf_data, lf_data, test_data, kernel="matern52")
