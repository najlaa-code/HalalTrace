/**
 * CIP stage catalog for HalalTrace mock UI.
 * Durations/temps here are typical industry ranges; each line overrides
 * configuredDurationMin in seed.js. Swap this module for API payloads later.
 */

export const CYCLE_STATES = Object.freeze({
  IDLE: "idle",
  CLEANING: "cleaning",
  VERIFYING: "verifying",
  PASSED: "passed",
  FAILED: "failed",
});

export const CYCLE_STATE_LABELS = Object.freeze({
  idle: "Idle",
  cleaning: "Cleaning",
  verifying: "Verifying",
  passed: "Pass",
  failed: "Fail",
});

/** Ordered CIP stages — do not include ATP (not measured by this system). */
export const STAGE_DEFS = [
  {
    id: "pre_rinse",
    label: "Pre-Rinse",
    shortLabel: "Pre-Rinse",
    typicalMin: [10, 15],
    tempRangeC: [38, 55],
  },
  {
    id: "caustic_wash",
    label: "Caustic / Detergent Wash",
    shortLabel: "Caustic Wash",
    typicalMin: [20, 45],
    tempRangeC: [71, 85],
  },
  {
    id: "intermediate_rinse",
    label: "Intermediate Rinse",
    shortLabel: "Int. Rinse",
    typicalMin: [5, 10],
    tempRangeC: null,
  },
  {
    id: "sanitizing",
    label: "Sanitizing",
    shortLabel: "Sanitize",
    typicalMin: [10, 20],
    tempRangeC: [74, 85],
    /** Mock thermal options: either short hot hold or longer warm hold. */
    thermalOptions: [
      { minTempC: 82, holdSec: [15, 30], label: "≥82°C for 15–30 s" },
      { minTempC: 74, holdMin: 15, label: "≥74°C for 15 min" },
    ],
  },
  {
    id: "final_rinse",
    label: "Final Potable Water Rinse",
    shortLabel: "Final Rinse",
    typicalMin: [10, 15],
    tempRangeC: null,
    turbidityMaxNtu: 2.0,
  },
];

export function getStageDef(stageId) {
  return STAGE_DEFS.find((s) => s.id === stageId) ?? STAGE_DEFS[0];
}

export function formatTypicalRange(typicalMin) {
  if (!typicalMin || typicalMin.length < 2) return "—";
  return `${typicalMin[0]}–${typicalMin[1]} min`;
}

export function formatTempRange(tempRangeC) {
  if (!tempRangeC || tempRangeC.length < 2) return null;
  return `${tempRangeC[0]}–${tempRangeC[1]}°C`;
}

export function tempWithinRange(tempC, tempRangeC) {
  if (!tempRangeC || tempRangeC.length < 2) return null;
  return tempC >= tempRangeC[0] && tempC <= tempRangeC[1];
}

/**
 * Build a line's runtime stage list from seed config.
 * @param {Array<{ id: string, configuredDurationMin: number, sanitizingMode?: string }>} stageConfig
 */
export function buildLineStages(stageConfig) {
  return STAGE_DEFS.map((def) => {
    const override = stageConfig.find((s) => s.id === def.id) || {};
    const [lo, hi] = def.typicalMin;
    const configuredDurationMin = clamp(
      override.configuredDurationMin ?? (lo + hi) / 2,
      lo,
      hi
    );
    return {
      ...def,
      configuredDurationMin,
      sanitizingMode: override.sanitizingMode ?? "hot_short",
    };
  });
}

function clamp(v, a, b) {
  return Math.max(a, Math.min(b, v));
}

export function totalConfiguredMinutes(stages) {
  return stages.reduce((sum, s) => sum + s.configuredDurationMin, 0);
}
