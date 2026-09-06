import { CONFIG } from "./config";
import { buildLineStages } from "./cycleStages";

export const NOW0 = Date.now();
export const H = 3600 * 1000;

export function pastFlags(n, temps, turbs) {
  return Array.from({ length: n }, (_, i) => ({
    ts: NOW0 - Math.floor((i + 1) * (5 * H) / (n + 1)) - Math.random() * 600000,
    temp: temps + Math.random() * 1.5,
    turbidity: turbs + Math.random() * 2,
  }));
}

/** CIP-shaped history helper for sparklines. */
export function genCycleHist(start, end, n, noise = 1) {
  return Array.from({ length: n }, (_, i) => {
    const p = n <= 1 ? 1 : i / (n - 1);
    const eased = 1 - Math.exp(-2.4 * p);
    const v = start + (end - start) * eased + (Math.random() - 0.5) * noise;
    return {
      t: NOW0 - (n - i) * CONFIG.EMIT_MS,
      v: +Math.max(0, v).toFixed(2),
    };
  });
}

/**
 * Per-line stage durations stay inside typical ranges from cycleStages.js.
 * Line A: shorter CIP. Line B: longer wash / sanitize.
 */
export const SEED = [
  {
    id: "line_A",
    room: "Facility",
    shortLabel: "Line A",
    label: "Main processing line",
    baseTemp: 22,
    baseTurb: 48,
    stageConfig: [
      { id: "pre_rinse", configuredDurationMin: 12 },
      { id: "caustic_wash", configuredDurationMin: 25 },
      { id: "intermediate_rinse", configuredDurationMin: 7 },
      { id: "sanitizing", configuredDurationMin: 12, sanitizingMode: "hot_short" },
      { id: "final_rinse", configuredDurationMin: 12 },
    ],
    seedFlags: [],
  },
  {
    id: "line_B",
    room: "Facility",
    shortLabel: "Line B",
    label: "Secondary processing line",
    baseTemp: 21,
    baseTurb: 56,
    stageConfig: [
      { id: "pre_rinse", configuredDurationMin: 15 },
      { id: "caustic_wash", configuredDurationMin: 40 },
      { id: "intermediate_rinse", configuredDurationMin: 9 },
      { id: "sanitizing", configuredDurationMin: 18, sanitizingMode: "warm_hold" },
      { id: "final_rinse", configuredDurationMin: 14 },
    ],
    seedFlags: pastFlags(2, 45, 18),
  },
].map((line) => ({
  ...line,
  stages: buildLineStages(line.stageConfig),
}));

export function genHist(base, spread, n) {
  return Array.from({ length: n }, (_, i) => ({
    t: NOW0 - (n - i) * CONFIG.EMIT_MS,
    v: +(base + (Math.random() - 0.5) * spread).toFixed(2),
  }));
}
