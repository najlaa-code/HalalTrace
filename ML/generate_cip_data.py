"""
Synthetic placeholder for the ESP32's raw turbidity/temp stream.

No real CIP hardware data exists yet. This generates per-second
turbidity (NTU) + temperature (C) readings for simulated cleaning cycles
and writes them to datasets/cip_raw_timeseries.csv in the exact schema
(cycle_id, t_sec, turbidity_ntu, temp_c, true_label) the rest of the CIP
pipeline expects -- so swapping in real ESP32 output later means dropping
a CSV in the same place, no code changes.

Cycle types generated:
  - PASS: turbidity clears below threshold and stays clear, temp holds
    the sanitation threshold for the full hold phase.
  - FAIL (residue): turbidity never fully clears (contaminant load
    proportional to a simulated flour/milk/oil concentration).
  - FAIL (recontamination): turbidity clears, then spikes again later
    in the cycle.
  - FAIL (cold): turbidity clears fine, but temp never reaches the
    sanitation threshold -- a "fake pass" a fixed turbidity-only
    threshold would miss, which is why cross_correlation is a feature.
"""

import numpy as np
import pandas as pd

from common.paths import DATASETS_DIR

OUT_PATH = DATASETS_DIR / "cip_raw_timeseries.csv"

CYCLE_LENGTH = 600  # seconds
TEMP_TARGET_MIN = 71.0
TEMP_TARGET_MAX = 82.0
N_CYCLES_PER_TYPE = 40
RANDOM_SEED = 42


def _simulate_turbidity(t, rng, clears=True, residue_level=0.0, recontam=False):
    baseline_noise = rng.normal(0, 1.5, size=len(t))
    if clears:
        decay_k = rng.uniform(0.02, 0.04)
        peak = rng.uniform(600, 900)
        turb = peak * np.exp(-decay_k * t) + residue_level + baseline_noise
    else:
        # never really clears: decays partway then plateaus above threshold
        decay_k = rng.uniform(0.005, 0.012)
        peak = rng.uniform(600, 900)
        turb = peak * np.exp(-decay_k * t) + residue_level + baseline_noise
    turb = np.clip(turb, 0, None)

    if recontam:
        spike_start = rng.integers(int(len(t) * 0.6), int(len(t) * 0.85))
        spike_len = rng.integers(15, 40)
        spike_end = min(spike_start + spike_len, len(t))
        turb[spike_start:spike_end] += rng.uniform(80, 200)

    return turb


def _simulate_temp(t, rng, reaches_threshold=True):
    ramp_time = rng.uniform(80, 150)
    target = rng.uniform(TEMP_TARGET_MIN + 1, TEMP_TARGET_MAX - 1) if reaches_threshold else rng.uniform(50, TEMP_TARGET_MIN - 2)
    start_temp = rng.uniform(18, 24)
    temp = start_temp + (target - start_temp) * (1 - np.exp(-t / (ramp_time / 3)))
    temp += rng.normal(0, 0.4, size=len(t))
    return temp


def _make_cycle(cycle_id, t, rng, kind):
    if kind == "pass":
        turb = _simulate_turbidity(t, rng, clears=True, residue_level=rng.uniform(0, 5))
        temp = _simulate_temp(t, rng, reaches_threshold=True)
        label = "PASS"
    elif kind == "fail_residue":
        turb = _simulate_turbidity(t, rng, clears=False, residue_level=rng.uniform(60, 150))
        temp = _simulate_temp(t, rng, reaches_threshold=True)
        label = "FAIL"
    elif kind == "fail_recontam":
        turb = _simulate_turbidity(t, rng, clears=True, residue_level=rng.uniform(0, 5), recontam=True)
        temp = _simulate_temp(t, rng, reaches_threshold=True)
        label = "FAIL"
    elif kind == "fail_cold":
        turb = _simulate_turbidity(t, rng, clears=True, residue_level=rng.uniform(0, 5))
        temp = _simulate_temp(t, rng, reaches_threshold=False)
        label = "FAIL"
    else:
        raise ValueError(kind)

    return pd.DataFrame({
        "cycle_id": cycle_id,
        "t_sec": t,
        "turbidity_ntu": turb,
        "temp_c": temp,
        "true_label": label,
    })


def generate(n_per_type: int = N_CYCLES_PER_TYPE, seed: int = RANDOM_SEED) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    t = np.arange(CYCLE_LENGTH)
    kinds = ["pass", "fail_residue", "fail_recontam", "fail_cold"]

    cycles = []
    cycle_id = 0
    for kind in kinds:
        for _ in range(n_per_type):
            cycles.append(_make_cycle(cycle_id, t, rng, kind))
            cycle_id += 1

    return pd.concat(cycles, ignore_index=True)


def main():
    df = generate()
    df.to_csv(OUT_PATH, index=False)
    n_cycles = df["cycle_id"].nunique()
    label_counts = df.drop_duplicates("cycle_id")["true_label"].value_counts()
    print(f"SYNTHETIC placeholder data (no real ESP32 hardware data yet).")
    print(f"Generated {n_cycles} cycles ({CYCLE_LENGTH}s each) -> {OUT_PATH}")
    print(label_counts.to_string())


if __name__ == "__main__":
    main()
