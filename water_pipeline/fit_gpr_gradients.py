"""
fit_gpr_gradients.py
---------------------
Gradient-enhanced GPR (GEGPR) fitting -- uses energy + gradient data to
build a 1D PES fit with fewer single-point calculations than energy-only
fitting requires.

APPROACH (Option B -- virtual point augmentation):
Rather than modifying optGPRNN's kernel to jointly model f(x) and f'(x)
(which would require deriving and coding new derivative-kernel math), we
exploit a simpler equivalent: at each point where we have both an energy
E(q) and a gradient dE/dq, we synthesize a small number of "virtual"
energy points nearby using a local linear (or quadratic, if curvature is
known) Taylor expansion:

    E_virtual(q + eps) = E(q) + (dE/dq) * eps

This effectively tells the GPR "the function looks like THIS locally"
without needing extra real quantum chemistry calculations. A single real
point + its gradient becomes 1 real point + N virtual points, all fit
with the existing, unmodified additive-kernel GPR engine.

This is a documented, valid technique (sometimes called "gradient-informed
virtual sampling") and is much simpler to implement and verify than
deriving a new derivative kernel, while still letting fewer real
calculations produce a well-constrained fit.

CONFIRMED DATA SOURCES (see parse_mopac.py and parse_nwchem_gradient.py):
  MOPAC : 1SCF GRADIENTS AUX(PRECISION=14 COMP) -> .aux file
  NWChem: TASK scf gradient -> "RHF ENERGY GRADIENTS" table

Both produce a flat Cartesian gradient (3N,), transformed into normal mode
gradients via g_nm = normal_modes @ g_cart (see parse_mopac.py).

Usage:
    python3 fit_gpr_gradients.py --mode 1 \\
        --points dataset_1d_mode1_with_gradients.dat \\
        --steps 500

Input file format (one new column vs the plain dataset_1d_modeN.dat):
    step_bohr   energy_cm1   gradient_cm1_per_bohr
(gradient column is optional -- points without it just don't get virtual
points added)
"""

import os
import sys
import argparse
import numpy as np

OPTGPR_DIR = os.path.expanduser("~/optGPRNN")
sys.path.insert(0, OPTGPR_DIR)

from NNviaHDMRGPR_prod import (
    generate_redundant_coordinates,
    optimize_redundant_coordinates,
    evaluate_additive_gpr,
)

DEFAULT_PARAMS = {
    "length_scale":  0.5,
    "noise":         1e-13,
    "num_redundant": 30,
    "max_steps":     2000,
    "train_frac":    0.8,
    "random_seed":   42,
}

# How far (in the same units as the step column) to place virtual points
# on either side of a real point with a known gradient. Small relative to
# the typical spacing between real points.
VIRTUAL_POINT_OFFSET = 0.001  # Bohr, for a typical step_bohr column


def load_dataset_with_gradients(filepath):
    """
    Load a 1D dataset that may or may not include a gradient column.

    Returns:
        Q          : np.ndarray (n,)      step/displacement values
        E          : np.ndarray (n,)      energies (cm-1)
        G          : np.ndarray (n,) or None   gradients (cm-1/unit), if present
    """
    data = np.loadtxt(filepath, comments="#")
    Q = data[:, 0]
    E = data[:, 1]
    G = data[:, 2] if data.shape[1] >= 3 else None
    return Q, E, G


def augment_with_virtual_points(Q, E, G, offset=VIRTUAL_POINT_OFFSET):
    """
    For every point with a known gradient, synthesize two virtual points
    using a local linear Taylor expansion:
        E_virtual(q +/- offset) = E(q) +/- gradient * offset

    Returns augmented (Q_aug, E_aug) arrays with virtual points appended.
    Points without a gradient (G is nan or None) are left as-is, no
    virtual points added for them.
    """
    Q_aug = list(Q)
    E_aug = list(E)

    if G is None:
        print("  No gradient column found -- returning original points unchanged.")
        return np.array(Q_aug), np.array(E_aug), 0

    n_virtual = 0
    for qi, ei, gi in zip(Q, E, G):
        if np.isnan(gi):
            continue
        # Linear Taylor expansion on both sides
        Q_aug.append(qi + offset)
        E_aug.append(ei + gi * offset)
        Q_aug.append(qi - offset)
        E_aug.append(ei - gi * offset)
        n_virtual += 2

    print(f"  Added {n_virtual} virtual points from {np.sum(~np.isnan(G))} "
          f"real gradients (offset = {offset})")
    return np.array(Q_aug), np.array(E_aug), n_virtual


def split_train_test(X, y, train_frac=0.8, seed=42):
    np.random.seed(seed)
    n = len(y)
    idx = np.random.permutation(n)
    n_train = max(int(n * train_frac), 2)
    n_test  = max(n - n_train, 1)
    return (X[idx[:n_train]], y[idx[:n_train]],
            X[idx[n_train:n_train+n_test]], y[idx[n_train:n_train+n_test]])


def fit_1d_with_gradients(mode, filepath, params, use_gradients=True):
    """
    Fit a 1D GPR using energy + (optionally) gradient-derived virtual
    points, with the SAME unmodified optGPRNN engine used elsewhere in
    the pipeline.
    """
    print(f"\n--- Gradient-enhanced 1D fit: mode {mode} ---")
    Q, E, G = load_dataset_with_gradients(filepath)
    print(f"  Real data points: {len(Q)}")
    if G is not None:
        n_with_grad = int(np.sum(~np.isnan(G)))
        print(f"  Points with gradient data: {n_with_grad}/{len(Q)}")
    else:
        print(f"  No gradient data in this file (energy-only fit).")

    if use_gradients and G is not None:
        Q_aug, E_aug, n_virtual = augment_with_virtual_points(Q, E, G, offset=params.get("offset", VIRTUAL_POINT_OFFSET))
    else:
        Q_aug, E_aug, n_virtual = Q, E, 0

    print(f"  Total training points (real + virtual): {len(Q_aug)}")

    X = Q_aug.reshape(-1, 1)
    y = E_aug

    X_train, y_train, X_test, y_test = split_train_test(
        X, y, params["train_frac"], params["random_seed"]
    )

    Y_train, S = generate_redundant_coordinates(
        X_train, params["num_redundant"], seed=params["random_seed"]
    )
    Y_test, _ = generate_redundant_coordinates(
        X_test, params["num_redundant"], seed=params["random_seed"]
    )

    W_opt = optimize_redundant_coordinates(
        X_train, y_train, X_test, y_test, S.copy(),
        max_steps=params["max_steps"], length_scale=params["length_scale"]
    )

    Y_tr = np.hstack([X_train, np.dot(X_train, W_opt.T)])
    Y_te = np.hstack([X_test,  np.dot(X_test,  W_opt.T)])
    rmse = evaluate_additive_gpr(
        Y_tr, y_train, Y_te, y_test,
        length_scale=params["length_scale"], noise=params["noise"]
    )

    print(f"\n  Final RMSE: {rmse:.4f} cm-1  "
          f"({len(Q)} real points + {n_virtual} virtual points)")

    outfile = f"gpr_fit_1d_mode{mode}_gradients.npz"
    np.savez(outfile, W_opt=W_opt, X_train=X_train, y_train=y_train,
             length_scale=params["length_scale"], noise=params["noise"],
             n_real_points=len(Q), n_virtual_points=n_virtual)
    print(f"  Saved: {outfile}")

    return {"mode": mode, "n_real": len(Q), "n_virtual": n_virtual, "rmse": rmse}


def main():
    parser = argparse.ArgumentParser(
        description="Gradient-enhanced GPR fitting via virtual point augmentation."
    )
    parser.add_argument("--mode", type=int, required=True,
                        help="Mode index being fit")
    parser.add_argument("--points", type=str, required=True,
                        help="Path to dataset file (step, energy[, gradient])")
    parser.add_argument("--steps", type=int, default=2000,
                        help="Monte Carlo steps (default: 2000)")
    parser.add_argument("--no-gradients", action="store_true",
                        help="Ignore gradient column even if present "
                             "(for comparison against energy-only fit)")
    parser.add_argument("--offset", type=float, default=VIRTUAL_POINT_OFFSET,
                        help=f"Virtual point offset (default: {VIRTUAL_POINT_OFFSET})")
    parser.add_argument("--length-scale", type=float, default=None, help="Override the default GPR length scale (default: 0.5)")
    args = parser.parse_args()

    params = DEFAULT_PARAMS.copy()
    params["max_steps"] = args.steps
    if args.length_scale is not None:
        params["length_scale"] = args.length_scale

    params["offset"] = args.offset

    result = fit_1d_with_gradients(
        args.mode, args.points, params, use_gradients=not args.no_gradients
    )

    print(f"\n=== Summary ===")
    print(f"  Mode {result['mode']}: RMSE = {result['rmse']:.4f} cm-1 "
          f"({result['n_real']} real + {result['n_virtual']} virtual points)")


if __name__ == "__main__":
    main()

