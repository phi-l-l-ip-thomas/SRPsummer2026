"""
fit_multifidelity_combined.py
------------------------------
Implements the combined kernel multifidelity GPR from the He-benzene paper.

Instead of training MOPAC and delta GPRs separately, this trains a single
GPR with a combined kernel:
    K_mf([x,b], [x',b']) = K_cheap(x,x') + b*b'*K_expensive(x,x')

where b in {0,1} is the fidelity indicator (0=MOPAC, 1=NWChem/expensive).

This allows the cheap data to inform the overall shape and length scales,
while the expensive data corrects the values -- both jointly.

Usage:
    python3 fit_multifidelity_combined.py \\
        --mode 1 \\
        --cheap-dat nwchem_mode1_cheap.dat \\
        --expensive-dat nwchem_mode1_expensive.dat \\
        --n-restarts 5 \\
        --outfile mf_mode1.joblib
"""

import argparse
import numpy as np
from scipy.optimize import minimize
import joblib


def rbf_kernel(X1, X2, length_scale):
    """RBF kernel: K(x,x') = exp(-0.5*(x-x')^2/l^2)"""
    diff = X1[:, None] - X2[None, :]
    return np.exp(-0.5 * diff**2 / length_scale**2)


def combined_kernel(X1_aug, X2_aug, ls_cheap, ls_exp, sigma_cheap, sigma_exp, noise):
    """
    Combined multifidelity kernel.
    X_aug: [q, b] where b in {0,1} is fidelity indicator.
    K_mf = sigma_cheap^2 * K_rbf(q, ls_cheap) + b*b' * sigma_exp^2 * K_rbf(q, ls_exp)
    """
    q1 = X1_aug[:, 0]; b1 = X1_aug[:, 1]
    q2 = X2_aug[:, 0]; b2 = X2_aug[:, 1]

    K_cheap = sigma_cheap**2 * rbf_kernel(q1, q2, ls_cheap)
    K_exp   = sigma_exp**2   * rbf_kernel(q1, q2, ls_exp)

    # b*b' outer product
    bb = b1[:, None] * b2[None, :]

    K = K_cheap + bb * K_exp
    # Add noise on diagonal
    if X1_aug is X2_aug:
        K += noise**2 * np.eye(len(q1))
    return K


class MultifidelityGPR:
    def __init__(self, ls_cheap=0.3, ls_exp=0.3, sigma_cheap=1000.0,
                 sigma_exp=500.0, noise=10.0):
        self.ls_cheap    = ls_cheap
        self.ls_exp      = ls_exp
        self.sigma_cheap = sigma_cheap
        self.sigma_exp   = sigma_exp
        self.noise       = noise
        self.X_train     = None
        self.alpha_      = None
        self.y_mean      = None

    def _log_marginal_likelihood(self, params):
        ls_c, ls_e, sig_c, sig_e, noise = np.exp(params)
        K = combined_kernel(self.X_train, self.X_train,
                           ls_c, ls_e, sig_c, sig_e, noise)
        try:
            L = np.linalg.cholesky(K)
        except np.linalg.LinAlgError:
            return 1e10
        y = self.y_train_
        alpha = np.linalg.solve(L.T, np.linalg.solve(L, y))
        lml = -0.5 * y @ alpha - np.sum(np.log(np.diag(L)))
        return -lml  # minimize negative LML

    def fit(self, X_cheap, y_cheap, X_exp, y_exp, n_restarts=3):
        """
        X_cheap: (n_cheap,) array of q values (MOPAC)
        y_cheap: (n_cheap,) array of energies (cm-1, zeroed to min)
        X_exp:   (n_exp,) array of q values (NWChem)
        y_exp:   (n_exp,) array of energies (cm-1, zeroed to equilibrium)
        """
        # Build augmented training set [q, fidelity]
        X_cheap_aug = np.column_stack([X_cheap, np.zeros(len(X_cheap))])
        X_exp_aug   = np.column_stack([X_exp,   np.ones(len(X_exp))])
        self.X_train = np.vstack([X_cheap_aug, X_exp_aug])

        # Concatenate targets
        y_all = np.concatenate([y_cheap, y_exp])
        self.y_mean = y_all.mean()
        self.y_train_ = y_all - self.y_mean

        # Optimize hyperparameters
        best_lml = np.inf
        best_params = None
        np.random.seed(42)
        for _ in range(n_restarts):
            p0 = np.log([
                np.random.uniform(0.1, 1.0),   # ls_cheap
                np.random.uniform(0.1, 1.0),   # ls_exp
                np.random.uniform(100, 5000),  # sigma_cheap
                np.random.uniform(10, 1000),   # sigma_exp
                np.random.uniform(1, 100),     # noise
            ])
            try:
                result = minimize(self._log_marginal_likelihood, p0,
                                method='L-BFGS-B',
                                bounds=[(-3,3),(-3,3),(2,12),(1,10),(-2,5)])
                if result.fun < best_lml:
                    best_lml = result.fun
                    best_params = result.x
            except:
                pass

        if best_params is not None:
            p = np.exp(best_params)
            self.ls_cheap, self.ls_exp = p[0], p[1]
            self.sigma_cheap, self.sigma_exp = p[2], p[3]
            self.noise = p[4]

        # Compute alpha for prediction
        K = combined_kernel(self.X_train, self.X_train,
                           self.ls_cheap, self.ls_exp,
                           self.sigma_cheap, self.sigma_exp, self.noise)
        self.K_train_ = K
        self.alpha_ = np.linalg.solve(K, self.y_train_)
        print(f"  Optimized: ls_cheap={self.ls_cheap:.4f}, ls_exp={self.ls_exp:.4f}")
        print(f"             sigma_cheap={self.sigma_cheap:.2f}, sigma_exp={self.sigma_exp:.2f}")
        print(f"             noise={self.noise:.4f}")
        return self

    def predict(self, X_test, fidelity=1):
        """Predict at test points. fidelity=1 for expensive (NWChem) level."""
        b = fidelity * np.ones(len(X_test))
        X_test_aug = np.column_stack([X_test, b])
        K_star = combined_kernel(X_test_aug, self.X_train,
                                self.ls_cheap, self.ls_exp,
                                self.sigma_cheap, self.sigma_exp, 0.0)
        return K_star @ self.alpha_ + self.y_mean


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", type=int, required=True)
    parser.add_argument("--cheap-dat", type=str, required=True)
    parser.add_argument("--expensive-dat", type=str, required=True)
    parser.add_argument("--n-restarts", type=int, default=3)
    parser.add_argument("--outfile", type=str, default=None)
    args = parser.parse_args()

    cheap  = np.loadtxt(args.cheap_dat,     comments='#')
    exp    = np.loadtxt(args.expensive_dat, comments='#')

    X_cheap, y_cheap = cheap[:, 0], cheap[:, 1]
    X_exp,   y_exp   = exp[:, 0],   exp[:, 1]

    print(f"\n=== Multifidelity GPR (combined kernel): mode {args.mode} ===")
    print(f"  Cheap: {len(X_cheap)} pts, Expensive: {len(X_exp)} pts")

    mf = MultifidelityGPR()
    mf.fit(X_cheap, y_cheap, X_exp, y_exp, n_restarts=args.n_restarts)

    # Evaluate on training points
    y_pred_cheap = mf.predict(X_cheap.reshape(-1,1), fidelity=0)
    y_pred_exp   = mf.predict(X_exp.reshape(-1,1),   fidelity=1)
    rmse_cheap = np.sqrt(np.mean((y_pred_cheap - y_cheap)**2))
    rmse_exp   = np.sqrt(np.mean((y_pred_exp   - y_exp)**2))
    print(f"  Train RMSE cheap: {rmse_cheap:.4f} cm-1")
    print(f"  Train RMSE exp:   {rmse_exp:.4f} cm-1")

    outfile = args.outfile or f"mf_combined_mode{args.mode}.joblib"
    joblib.dump(mf, outfile)
    print(f"  Saved: {outfile}")


if __name__ == "__main__":
    main()
