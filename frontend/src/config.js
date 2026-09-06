import {
  CheckCircle2, AlertTriangle, AlertOctagon, ShieldAlert,
} from "lucide-react";

export const CONFIG = {
  WARM_TEMP_C:     55,
  TURB_FLAG_NTU:   8,
  WINDOW_HOURS:    6,
  FLAG_WARN:        5,
  FLAG_WARN2:       10,
  FLAG_PANIC:       18,
  EMIT_MS:          400,
  INJECT_TICKS:     8,
  FLAG_DEBOUNCE_MS: 30000,
  HISTORY:         40,
  TURB_VIS_MAX:    80,
  /** Simulated minutes advanced per mock tick (compresses long CIP stages for demo). */
  SIM_MIN_PER_TICK: 0.35,
  /** How long to linger in VERIFYING before starting a fresh mock cycle (sim minutes). */
  VERIFY_HOLD_SIM_MIN: 4,
};

export const TIERS = {
  passed: { label: "Clear",      color: "#1fae6f", glow: "rgba(31,174,111,.45)",  icon: CheckCircle2 },
  warn:   { label: "Watch",      color: "#e8a800", glow: "rgba(232,168,0,.5)",    icon: AlertTriangle },
  warn2:  { label: "Attention",  color: "#f2790f", glow: "rgba(242,121,15,.55)",  icon: AlertOctagon },
  panic:  { label: "Critical",   color: "#e23b3b", glow: "rgba(226,59,59,.6)",    icon: ShieldAlert },
};

export function tierFromCount(n) {
  if (n >= CONFIG.FLAG_PANIC)  return "panic";
  if (n >= CONFIG.FLAG_WARN2)  return "warn2";
  if (n >= CONFIG.FLAG_WARN)   return "warn";
  return "passed";
}

export function flagDotColor(flagNum) {
  if (flagNum >= 5) return "#e23b3b";
  if (flagNum === 4) return "#f2790f";
  if (flagNum === 3) return "#e8a800";
  return "#ffffff";
}

export const clamp = (v, a, b) => Math.max(a, Math.min(b, v));
