"""
End-to-end run: loads real hf_data / lf_data / test_data from disk and
reports per-mode RMSE comparing single-fidelity (HF-only) vs multi-fidelity
(linear truncated kernel) GP, per Akram et al. J. Chem. Phys. 164, 114108 (2026).
"""

from load_data import load_expensive_points, load_cheap_points
from load_test_data import load_test_points
from mfgp import per_mode_rmse_report

print("=" * 60)
print("Loading data")
print("=" * 60)

hf_data = load_expensive_points(".")
lf_data = load_cheap_points(".")
test_data = load_test_points()

print()
print("=" * 60)
print("Fitting GPs and reporting per-mode RMSE (cm^-1)")
print("=" * 60)

results = per_mode_rmse_report(hf_data, lf_data, test_data, kernel="matern52",
                                n_restarts=8)

print()
print("=" * 60)
print("Summary")
print("=" * 60)
for mode, r in results.items():
    improvement = 100 * (1 - r["mf_rmse"] / r["sf_rmse"])
    print(f"Mode {mode}: SF={r['sf_rmse']:.2f}  MF={r['mf_rmse']:.2f}  "
          f"({improvement:+.1f}% change)")
