import { CONFIG, tierFromCount, clamp } from "./config";
import { SEED, H } from "./seed";
import { CYCLE_STATES, getStageDef } from "./cycleStages";

function stageTargets(stage, mode) {
  const def = getStageDef(stage.id);
  switch (stage.id) {
    case "pre_rinse":
      return { temp: 46, turb: 28 };
    case "caustic_wash":
      return { temp: 78, turb: 18 };
    case "intermediate_rinse":
      return { temp: 42, turb: 10 };
    case "sanitizing":
      return {
        temp: mode === "warm_hold" ? 76 : 84,
        turb: 6,
      };
    case "final_rinse":
      return { temp: 28, turb: 1.4 };
    default:
      return {
        temp: def.tempRangeC ? (def.tempRangeC[0] + def.tempRangeC[1]) / 2 : 30,
        turb: 8,
      };
  }
}

function emitCycleState(onMessage, ss) {
  onMessage({
    type: "cycle_state",
    sensorId: ss.id,
    cycleState: ss.cycleState,
    stageId: ss.stages[ss.stageIndex]?.id ?? null,
    stageIndex: ss.stageIndex,
    stageElapsedMin: +ss.stageElapsedMin.toFixed(2),
    cycleElapsedMin: +ss.cycleElapsedMin.toFixed(2),
    stageConfiguredMin: ss.stages[ss.stageIndex]?.configuredDurationMin ?? null,
  });
}

/**
 * Mock CIP feed: multi-stage CLEANING → VERIFYING (never auto-PASS on time).
 */
export function createMockBackend(onMessage) {
  const state = SEED.map((s) => ({
    id: s.id,
    stages: s.stages.map((st) => ({ ...st })),
    sanitizingMode: s.stageConfig.find((c) => c.id === "sanitizing")?.sanitizingMode ?? "hot_short",
    baseTemp: s.baseTemp,
    baseTurb: s.baseTurb,
    temp: s.baseTemp,
    turb: s.baseTurb,
    flags: s.seedFlags.map((f) => ({ ...f })),
    inject: 0,
    cycleState: CYCLE_STATES.CLEANING,
    stageIndex: 0,
    stageElapsedMin: 0,
    cycleElapsedMin: 0,
    verifyElapsedMin: 0,
    lastFlagAt: 0,
    lastTier: null,
    lastCount: -1,
    lastEmittedStage: null,
    lastEmittedCycleState: null,
  }));
  let timer = null;

  function emitConditionStatus(ss) {
    const cutoff = Date.now() - CONFIG.WINDOW_HOURS * H;
    const count = ss.flags.filter((f) => f.ts >= cutoff).length;
    const tier = tierFromCount(count);
    if (tier !== ss.lastTier || count !== ss.lastCount) {
      ss.lastTier = tier;
      ss.lastCount = count;
      onMessage({
        type: "status",
        sensorId: ss.id,
        tier,
        flagsInWindow: count,
        windowHours: CONFIG.WINDOW_HOURS,
      });
    }
  }

  function beginCleaning(ss) {
    ss.cycleState = CYCLE_STATES.CLEANING;
    ss.stageIndex = 0;
    ss.stageElapsedMin = 0;
    ss.cycleElapsedMin = 0;
    ss.verifyElapsedMin = 0;
    ss.temp = ss.baseTemp;
    ss.turb = ss.baseTurb;
  }

  function beginVerifying(ss) {
    // Time reaching 100% ends cleaning and starts verification — not PASS.
    ss.cycleState = CYCLE_STATES.VERIFYING;
    ss.verifyElapsedMin = 0;
    ss.stageElapsedMin = ss.stages[ss.stageIndex]?.configuredDurationMin ?? ss.stageElapsedMin;
  }

  function step(ss) {
    const now = Date.now();
    const dt = CONFIG.SIM_MIN_PER_TICK;

    if (ss.cycleState === CYCLE_STATES.IDLE) {
      beginCleaning(ss);
    }

    if (ss.cycleState === CYCLE_STATES.VERIFYING) {
      ss.verifyElapsedMin += dt;
      // Hold VERIFYING; do not invent PASS/FAIL from the clock.
      // Restart a fresh mock cycle after a short hold for continuous demo.
      if (ss.verifyElapsedMin >= CONFIG.VERIFY_HOLD_SIM_MIN) {
        beginCleaning(ss);
      }
    } else if (ss.cycleState === CYCLE_STATES.CLEANING) {
      const stage = ss.stages[ss.stageIndex];
      ss.stageElapsedMin += dt;
      ss.cycleElapsedMin += dt;

      if (ss.stageElapsedMin >= stage.configuredDurationMin) {
        if (ss.stageIndex < ss.stages.length - 1) {
          ss.stageIndex += 1;
          ss.stageElapsedMin = 0;
        } else {
          beginVerifying(ss);
        }
      }
    }

    const stage = ss.stages[Math.min(ss.stageIndex, ss.stages.length - 1)];
    const targets = stageTargets(stage, ss.sanitizingMode);
    const stageProg = Math.min(
      1,
      ss.stageElapsedMin / Math.max(0.01, stage.configuredDurationMin)
    );

    let temp =
      ss.temp +
      (targets.temp - ss.temp) * (0.18 + stageProg * 0.12) +
      (Math.random() - 0.5) * 0.8;
    let turb =
      ss.turb +
      (targets.turb - ss.turb) * (0.16 + stageProg * 0.14) +
      (Math.random() - 0.5) * 1.1;

    if (ss.cycleState === CYCLE_STATES.VERIFYING) {
      // Hold near final-rinse clarity while verifying — still not a verdict.
      temp = 26 + (Math.random() - 0.5) * 1.2;
      turb = Math.max(0.4, 1.2 + (Math.random() - 0.5) * 0.6);
    }

    if (ss.inject > 0) {
      turb += 16 + Math.random() * 10;
      temp -= 3 + Math.random() * 2;
      ss.inject -= 1;
    }

    ss.temp = clamp(temp, 15, 95);
    ss.turb = Math.max(0, turb);

    const stageId = stage.id;
    if (
      ss.cycleState !== ss.lastEmittedCycleState ||
      stageId !== ss.lastEmittedStage
    ) {
      ss.lastEmittedCycleState = ss.cycleState;
      ss.lastEmittedStage = stageId;
      emitCycleState(onMessage, ss);
    } else {
      // Keep UI timers fresh without spamming every tick as a "state change".
      onMessage({
        type: "cycle_progress",
        sensorId: ss.id,
        cycleState: ss.cycleState,
        stageId,
        stageIndex: ss.stageIndex,
        stageElapsedMin: +ss.stageElapsedMin.toFixed(2),
        cycleElapsedMin: +ss.cycleElapsedMin.toFixed(2),
        stageConfiguredMin: stage.configuredDurationMin,
      });
    }

    onMessage({
      type: "reading",
      ts: now,
      sensorId: ss.id,
      temp: ss.temp,
      turbidity: ss.turb,
    });

    if (
      ss.cycleState === CYCLE_STATES.CLEANING &&
      stage.id === "final_rinse" &&
      ss.turb >= (stage.turbidityMaxNtu ?? 2) &&
      now - ss.lastFlagAt >= CONFIG.FLAG_DEBOUNCE_MS
    ) {
      ss.lastFlagAt = now;
      ss.flags.push({ ts: now, temp: ss.temp, turbidity: ss.turb });
      onMessage({
        type: "flag",
        ts: now,
        sensorId: ss.id,
        temp: ss.temp,
        turbidity: ss.turb,
      });
    }

    emitConditionStatus(ss);
  }

  return {
    start() {
      if (timer) return;
      state.forEach((ss) => {
        beginCleaning(ss);
        emitCycleState(onMessage, ss);
        emitConditionStatus(ss);
      });
      timer = setInterval(() => state.forEach(step), CONFIG.EMIT_MS);
    },
    stop() {
      clearInterval(timer);
      timer = null;
    },
    inject(id) {
      const ss = state.find((s) => s.id === id);
      if (ss) ss.inject = CONFIG.INJECT_TICKS;
    },
  };
}
