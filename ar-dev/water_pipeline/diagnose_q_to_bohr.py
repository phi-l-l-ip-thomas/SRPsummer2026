"""
Run this ON PERLMUTTER, in the wide_range_mopac_inputs directory.
Imports q_to_bohr directly from generate_3d_points.py (no hand-transcription,
full precision) and checks it against the known-correct training pairs from
wide_range_job_index.csv.
"""
import sys
sys.path.insert(0, ".")
import numpy as np
import importlib.util

spec = importlib.util.spec_from_file_location("gen3d", "generate_3d_points.py")
gen3d = importlib.util.module_from_spec(spec)
spec.loader.exec_module(gen3d)

geometry = np.load("geometry.npy")
atom_labels = np.load("atom_labels.npy")
normal_modes = np.load("normal_modes.npy")
frequencies = np.load("frequencies.npy")
n_atoms = len(atom_labels)

ATOMIC_MASSES = {"H": 1.007825, "O": 15.994910, "N": 14.003074, "C": 12.0}
atom_masses = np.array([ATOMIC_MASSES[l] for l in atom_labels])

print("frequencies.npy (full precision):", repr(frequencies))
print("normal_modes.npy (full precision):")
np.set_printoptions(precision=15, suppress=False)
print(normal_modes)
print()

known = [
    (0, 0.061431625327904395, 0.014469871131010273, "mode1"),
    (1, 0.061431625327904395, 0.010476406602894022, "mode2"),
    (2, 0.061431625327904395, 0.010172558568552075, "mode3"),
]

print(f"{'mode':>6} {'q':>10} {'computed_step_bohr':>20} {'expected_step_bohr':>20} {'ratio':>10}")
for mode_idx, q, expected, label in known:
    vec = normal_modes[mode_idx].reshape(n_atoms, 3)
    computed = gen3d.q_to_bohr(q, frequencies[mode_idx], vec, atom_masses)
    ratio = expected / computed
    print(f"{label:>6} {q:>10.6f} {computed:>20.10f} {expected:>20.10f} {ratio:>10.6f}")
