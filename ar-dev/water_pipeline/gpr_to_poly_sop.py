"""
gpr_to_poly_sop.py
--------------------
Converts sklearn GPR fits to polynomial (power-of-q) sum-of-products
format for MLCP, using dimensionless normal mode coordinates.

Per Dr. Thomas (July 2): MLCP expects plain polynomial coefficients
(powers of q_i in dimensionless coordinates) in the fN files.
MLCP then applies morse-tanh transformation internally if pe_transform
is set. For now we run with pe_transform='none' to validate the
coordinate system.

The polynomial expansion is:
    V(q_i) = sum_p  c_p * q_i^p    (p = 2, 3, 4, ..., n_terms)

where q_i is the dimensionless normal mode coordinate:
    q_i = (q_bohr - q_min_bohr) * mw_norm_i * sqrt(omega_i_hartree)

Sanity check: f2 coefficient should be close to omega/2 (in cm-1)
since the harmonic term contributes 0.5*omega*q^2 to the potential.

Usage:
    python3 gpr_to_poly_sop.py --molecule water \\
        --modes 1 2 3 \\
        --freqs 2170.10 4139.81 4390.84 \\
        --mw-norms 42.695256972630645 42.6954522678662 42.695456 \\
        --gpr-models sklearn_gpr_optimal_mode1.joblib \\
                     sklearn_gpr_optimal_mode2.joblib \\
                     sklearn_gpr_optimal_mode3.joblib \\
        --n-terms 8 --q-max 1.2
"""

import argparse
import os
import numpy as np
import joblib

HARTREE_TO_CM1 = 219474.63


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--molecule", type=str, required=True)
    parser.add_argument("--modes", type=int, nargs="+", required=True)
    parser.add_argument("--freqs", type=float, nargs="+", required=True)
    parser.add_argument("--mw-norms", type=float, nargs="+", required=True)
    parser.add_argument("--gpr-models", type=str, nargs="+", required=True)
    parser.add_argument("--n-terms", type=int, default=8,
                        help="Max polynomial power (default 8)")
    parser.add_argument("--q-max", type=float, default=1.2,
                        help="Max q_bohr for fitting grid (default 1.2)")
    parser.add_argument("--n-grid", type=int, default=500)
    parser.add_argument("--reference-energy", type=float, default=None,
                        help="Reference energy in cm-1 to zero to (e.g. PBQFF "
                             "equilibrium energy). If not set, zeros to GPR minimum.")
    parser.add_argument("--outdir", type=str, default=".")
    args = parser.parse_args()

    mol = args.molecule
    powers = list(range(2, args.n_terms + 1))
    all_terms = []  # (mode, power, coeff)

    print(f"\n=== GPR -> polynomial SOP for {mol} ===")
    print(f"  powers: {powers}, q_max: +/-{args.q_max} Bohr")

    for mode, freq, mw_norm, model_file in zip(
            args.modes, args.freqs, args.mw_norms, args.gpr_models):

        omega_hartree = freq / HARTREE_TO_CM1
        scale = mw_norm * np.sqrt(omega_hartree)

        gpr = joblib.load(model_file)

        # Find actual GPR minimum -- search wider range to avoid missing it
        q_fine = np.linspace(-args.q_max, args.q_max, 5000)
        V_fine = gpr.predict(q_fine.reshape(-1, 1))
        q_min_bohr = q_fine[np.argmin(V_fine)]
        V_min = V_fine.min()

        # Fit polynomial on restricted range centered on minimum
        q_bohr_grid = np.linspace(q_min_bohr - args.q_max,
                                   q_min_bohr + args.q_max, args.n_grid)
        q_dim_grid = (q_bohr_grid - q_min_bohr) * scale
        V = gpr.predict(q_bohr_grid.reshape(-1, 1))
        if args.reference_energy is not None:
            V -= args.reference_energy
            print(f"    Zeroing to reference energy: {args.reference_energy:.4f} cm-1")
        else:
            V -= V_min  # zero to GPR minimum

        Phi = np.column_stack([q_dim_grid**p for p in powers])
        coeffs, _, _, _ = np.linalg.lstsq(Phi, V, rcond=None)
        rmse = np.sqrt(np.mean((Phi @ coeffs - V)**2))

        print(f"\n  Mode {mode} ({freq:.1f} cm-1):")
        print(f"    q_min_bohr={q_min_bohr:.6f} (q_dim={q_min_bohr*scale:.4f}), scale={scale:.4f}")
        print(f"    RMSE={rmse:.2f} cm-1")
        print(f"    f2={coeffs[0]:.2f} cm-1  (omega/2={freq/2:.1f} cm-1, "
              f"ratio={coeffs[0]/(freq/2):.3f})")

        for p, c in zip(powers, coeffs):
            all_terms.append((mode, p, c))

    # Write fN files (f2 through f{n_terms})
    by_order = {}
    for mode, p, c in all_terms:
        by_order.setdefault(p, []).append((mode, p, c))

    os.makedirs(args.outdir, exist_ok=True)

    # Write zero f1 (required by MLCP even if no linear terms)
    fname = os.path.join(args.outdir, f"f1{mol}.dat")
    with open(fname, "w") as f:
        for mode in args.modes:
            f.write(f"  {mode}    0.0000000000d0\n")
    print(f"\n  Wrote f1{mol}.dat (zeros)")

    for order, lines in sorted(by_order.items()):
        fname = os.path.join(args.outdir, f"f{order}{mol}.dat")
        with open(fname, "w") as f:
            for mode, p, c in lines:
                indices = "  ".join([str(mode)] * p)
                f.write(f"  {indices}    {c:.10f}d0\n")
        print(f"  Wrote f{order}{mol}.dat ({len(lines)} terms)")

    print(f"\n  Done. Run MLCP with pe_transform='none'")
    print(f"  Expected: bend ~1400 cm-1, O-H stretches ~2800-2900 cm-1")


if __name__ == "__main__":
    main()
