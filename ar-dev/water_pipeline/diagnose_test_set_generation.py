"""
Run ON PERLMUTTER. Decisive test: for the KNOWN-GOOD mode1 test point and the
KNOWN-BROKEN mode2 test point, reconstruct the geometry two different ways:

  (A) treating the filename's numeric label as q_dimensionless, run through
      the real q_to_bohr() from generate_3d_points.py using CURRENT
      frequencies.npy / normal_modes.npy
  (B) treating the filename's numeric label as a RAW bohr displacement,
      applied directly with no per-mode conversion at all

Then compares both reconstructions against the ACTUAL geometry found in the
.nw file. Whichever matches tells us definitively what the test-set generator
actually did.
"""
import sys
sys.path.insert(0, ".")
import numpy as np
import re
import importlib.util

spec = importlib.util.spec_from_file_location("gen3d", "generate_3d_points.py")
gen3d = importlib.util.module_from_spec(spec)
spec.loader.exec_module(gen3d)

geometry = np.load("geometry.npy")            # Angstrom, shape (3,3)
atom_labels = np.load("atom_labels.npy")
normal_modes = np.load("normal_modes.npy")
frequencies = np.load("frequencies.npy")
n_atoms = len(atom_labels)

ATOMIC_MASSES = {"H": 1.007825, "O": 15.994910, "N": 14.003074, "C": 12.0}
atom_masses = np.array([ATOMIC_MASSES[l] for l in atom_labels])

BOHR_TO_ANGSTROM = 0.529177


def displace_1mode(geometry, vec, step_bohr):
    N = geometry.shape[0]
    return geometry + (step_bohr * BOHR_TO_ANGSTROM) * vec.reshape(N, 3)


def parse_actual_geometry(nw_path):
    """Pull the geometry block out of a real .nw file."""
    coords = []
    with open(nw_path) as f:
        in_block = False
        for line in f:
            if "geometry units" in line:
                in_block = True
                continue
            if in_block:
                if line.strip() == "end":
                    break
                parts = line.split()
                coords.append([float(parts[1]), float(parts[2]), float(parts[3])])
    return np.array(coords)


def oh_bond_lengths(geom):
    O = geom[0]
    return [np.linalg.norm(geom[i] - O) for i in range(1, len(geom))]


cases = [
    (0, "nwchem_test_set/h2o_mode1_test_stepm1p5811_grad.nw", -1.5811, "mode1 (known-good)"),
    (1, "nwchem_test_set/h2o_mode2_test_stepm1p5811_grad.nw", -1.5811, "mode2 (known-broken)"),
]

for mode_idx, nw_path, label_value, tag in cases:
    print(f"=== {tag}: {nw_path} ===")
    actual = parse_actual_geometry(nw_path)
    print("ACTUAL geometry from file:")
    print(actual)
    print("ACTUAL O-H bond lengths:", oh_bond_lengths(actual))

    vec = normal_modes[mode_idx].reshape(n_atoms, 3)

    # (A) treat label as q_dimensionless, convert properly
    step_bohr_A = gen3d.q_to_bohr(label_value, frequencies[mode_idx], vec, atom_masses)
    geom_A = displace_1mode(geometry, vec, step_bohr_A)
    print(f"\n(A) proper q_to_bohr conversion: step_bohr={step_bohr_A:.6f}")
    print(geom_A)
    print("(A) O-H bond lengths:", oh_bond_lengths(geom_A))
    print("(A) matches actual?", np.allclose(geom_A, actual, atol=1e-3))

    # (B) treat label as raw bohr directly, no conversion
    geom_B = displace_1mode(geometry, vec, label_value)
    print(f"\n(B) raw bohr, no conversion: step_bohr={label_value:.6f}")
    print(geom_B)
    print("(B) O-H bond lengths:", oh_bond_lengths(geom_B))
    print("(B) matches actual?", np.allclose(geom_B, actual, atol=1e-3))
    print()
