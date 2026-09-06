import React, { useState, useEffect, useRef } from "react";
import {
  Thermometer, Droplets, Flag, Activity,
  Waves, LayoutList, Clock, Radio,
} from "lucide-react";
import { CONFIG, TIERS, flagDotColor } from "./config";
import { SEED, NOW0, H, genCycleHist } from "./seed";
import { CSS } from "./styles";
import { createMockBackend } from "./mockBackend";
import { createRealBackend } from "./realBackend";
import {
  CYCLE_STATES,
  CYCLE_STATE_LABELS,
  formatTypicalRange,
  formatTempRange,
  tempWithinRange,
  getStageDef,
} from "./cycleStages";
import StatTile from "./components/StatTile";
import WaterPipe from "./components/WaterPipe";
import FlagMeter from "./components/FlagMeter";
import StageStrip from "./components/StageStrip";

const fmtTime = (ts) =>
  new Date(ts).toLocaleTimeString([], {
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
  });

function FlagDots({ count }) {
  const dots = [];
  if (count === 0) {
    for (let i = 0; i < 4; i++) dots.push({ lit: false, color: "transparent" });
  } else {
    const start = Math.max(1, count - 3);
    const empty = 4 - (count - start + 1);
    for (let i = 0; i < empty; i++) dots.push({ lit: false, color: "transparent" });
    for (let n = start; n <= count; n++)
      dots.push({ lit: true, color: flagDotColor(n) });
  }
  return (
    <div className="flag-dots" title="Recent condition events">
      {dots.map((d, i) => (
        <span
          key={i}
          className={"flag-dot" + (d.lit ? " lit" : "")}
          style={d.lit ? { background: d.color } : {}}
        />
      ))}
    </div>
  );
}

function ActionPanel({ tier, action, steps }) {
  const titles = {
    warn: "Rinse may need a closer look",
    warn2: "Cleaning is off target — check heat and clarity",
    panic: "Re-run this sanitation cycle before releasing the line",
  };
  return (
    <div className={`glass action-panel tier-${tier}`} role="status">
      <div>
        <div className="action-title" style={{ color: TIERS[tier].color }}>
          {titles[tier]}
        </div>
        {action && <div className="action-sub">{action}</div>}
        {tier === "panic" && steps && steps.length > 0 && (
          <ol className="panic-steps">
            {steps.map((s, i) => (
              <li key={i}>{s}</li>
            ))}
          </ol>
        )}
      </div>
    </div>
  );
}

function cycleStateColor(state) {
  switch (state) {
    case CYCLE_STATES.CLEANING:
      return "#0f6e5c";
    case CYCLE_STATES.VERIFYING:
      return "#b7791f";
    case CYCLE_STATES.PASSED:
      return "#1a7a4c";
    case CYCLE_STATES.FAILED:
      return "#b42318";
    case CYCLE_STATES.IDLE:
    default:
      return "#5a6f68";
  }
}

function cycleSummary(line) {
  const stage = line.stages?.[line.stageIndex];
  const label = stage?.shortLabel || stage?.label || "—";
  switch (line.cycleState) {
    case CYCLE_STATES.IDLE:
      return "Line is idle — waiting for the next cleaning cycle.";
    case CYCLE_STATES.CLEANING:
      return `Cleaning in progress · ${label}. Pass/fail is decided only after verification.`;
    case CYCLE_STATES.VERIFYING:
      return "Cleaning stages finished. Verifying turbidity & temperature — not a pass yet.";
    case CYCLE_STATES.PASSED:
      return "Cycle verified PASS from sensor traces.";
    case CYCLE_STATES.FAILED:
      return "Cycle verified FAIL from sensor traces.";
    default:
      return "Watching CIP sensors for this processing line.";
  }
}

function blankSensor(id) {
  const seed = SEED[0];
  return {
    id,
    room: "Facility",
    shortLabel: id,
    label: id,
    temp: 0,
    turbidity: 0,
    tempHist: [],
    turbHist: [],
    flags: [],
    tier: "passed",
    flagsInWindow: 0,
    windowHours: CONFIG.WINDOW_HOURS,
    stages: seed.stages,
    stageIndex: 0,
    stageId: seed.stages[0].id,
    stageElapsedMin: 0,
    cycleElapsedMin: 0,
    cycleState: CYCLE_STATES.IDLE,
    action: null,
    panicSteps: null,
  };
}

export default function HalalTraceDashboard() {
  const [sensors, setSensors] = useState(() => {
    const o = {};
    for (const s of SEED) {
      const cutoff = NOW0 - CONFIG.WINDOW_HOURS * H;
      const count = s.seedFlags.filter((f) => f.ts >= cutoff).length;
      const first = s.stages[0];
      o[s.id] = {
        id: s.id,
        room: s.room,
        shortLabel: s.shortLabel,
        label: s.label,
        temp: Math.round(s.baseTemp),
        turbidity: Math.round(s.baseTurb),
        tempHist: genCycleHist(s.baseTemp, first.tempRangeC?.[0] ?? 40, 24, 1.2),
        turbHist: genCycleHist(s.baseTurb, 12, 24, 2.0),
        flags: [...s.seedFlags].sort((a, b) => b.ts - a.ts),
        tier: "passed",
        flagsInWindow: count,
        windowHours: CONFIG.WINDOW_HOURS,
        stages: s.stages,
        stageIndex: 0,
        stageId: first.id,
        stageElapsedMin: 0,
        cycleElapsedMin: 0,
        cycleState: CYCLE_STATES.CLEANING,
        action: null,
        panicSteps: null,
      };
    }
    return o;
  });

  const [selected, setSelected] = useState("line_A");
  const [clock, setClock] = useState(Date.now());
  const [mode, setMode] = useState("demo"); // "demo" | "live"
  const backend = useRef(null);

  function handleMessage(msg) {
    const { sensorId } = msg;
    if (!sensorId) return;

    setSensors((prev) => {
      const s = prev[sensorId] ?? blankSensor(sensorId);

      if (msg.type === "cycle_state" || msg.type === "cycle_progress") {
        return {
          ...prev,
          [sensorId]: {
            ...s,
            cycleState: msg.cycleState ?? s.cycleState,
            stageId: msg.stageId ?? s.stageId,
            stageIndex: msg.stageIndex ?? s.stageIndex,
            stageElapsedMin: msg.stageElapsedMin ?? s.stageElapsedMin,
            cycleElapsedMin: msg.cycleElapsedMin ?? s.cycleElapsedMin,
          },
        };
      }

      if (msg.type === "reading") {
        const rawTurb = msg.turbidity;
        const rawTemp = msg.temp;
        if (!Number.isFinite(rawTurb) || rawTurb < 0 || rawTurb > 1000) return prev;
        if (!Number.isFinite(rawTemp) || rawTemp < -50 || rawTemp > 100) return prev;
        const newTurbHist = [...s.turbHist, { t: msg.ts, v: rawTurb }].slice(
          -CONFIG.HISTORY
        );
        const newTempHist = [...s.tempHist, { t: msg.ts, v: rawTemp }].slice(
          -CONFIG.HISTORY
        );
        const avg = (arr) => arr.reduce((a, e) => a + e.v, 0) / arr.length;
        return {
          ...prev,
          [sensorId]: {
            ...s,
            temp: Math.round(avg(newTempHist.slice(-4))),
            turbidity: Number(avg(newTurbHist.slice(-4)).toFixed(1)),
            tempHist: newTempHist,
            turbHist: newTurbHist,
          },
        };
      }

      if (msg.type === "flag") {
        return {
          ...prev,
          [sensorId]: {
            ...s,
            flags: [
              {
                ts: msg.ts,
                temp: msg.temp,
                turbidity: msg.turbidity,
                flagNumber: msg.flagNumber,
                flagTier: msg.flagTier,
              },
              ...s.flags,
            ].slice(0, 60),
          },
        };
      }

      if (msg.type === "status") {
        return {
          ...prev,
          [sensorId]: {
            ...s,
            tier: msg.tier,
            flagsInWindow: msg.flagsInWindow,
            windowHours: msg.windowHours,
            action: msg.action ?? s.action,
            panicSteps: msg.steps ?? s.panicSteps,
          },
        };
      }

      return prev;
    });
  }

  useEffect(() => {
    const clock_t = setInterval(() => setClock(Date.now()), 1000);
    return () => clearInterval(clock_t);
  }, []);

  useEffect(() => {
    // Reset to a blank slate on every mode switch so stale demo data (or a
    // stale live reading) doesn't linger under the other mode.
    setSensors(() => {
      const o = {};
      for (const s of SEED) o[s.id] = blankSensor(s.id);
      return o;
    });

    const client =
      mode === "live" ? createRealBackend(handleMessage) : createMockBackend(handleMessage);
    client.start();
    backend.current = client;
    return () => client.stop();
  }, [mode]);

  const sel = sensors[selected] ?? blankSensor(selected);
  const stage =
    sel.stages?.[sel.stageIndex] ??
    sel.stages?.[0] ??
    getStageDef(sel.stageId);
  const stageDef = getStageDef(stage.id);
  const stageConfiguredMin = stage.configuredDurationMin ?? 0;
  const stageElapsedMin = sel.stageElapsedMin ?? 0;
  const cycleElapsedMin = sel.cycleElapsedMin ?? 0;

  const monPct =
    sel.cycleState === CYCLE_STATES.VERIFYING ||
    sel.cycleState === CYCLE_STATES.PASSED ||
    sel.cycleState === CYCLE_STATES.FAILED
      ? 100
      : Math.max(
          0,
          Math.min(1, stageElapsedMin / Math.max(0.01, stageConfiguredMin))
        ) * 100;

  const tempRange = stageDef.tempRangeC;
  const tempOk = tempWithinRange(sel.temp, tempRange);
  const tempHot = tempRange ? tempOk === false : false;

  const isFinalRinse = stageDef.id === "final_rinse";
  const turbLimit = stageDef.turbidityMaxNtu;
  const turbHot = isFinalRinse && turbLimit != null ? sel.turbidity >= turbLimit : false;

  let tempTargetLine = null;
  let tempStatusLine = null;
  if (tempRange) {
    tempTargetLine = `Target: ${formatTempRange(tempRange)}`;
    if (tempOk === true) tempStatusLine = "Within target";
    else if (tempOk === false) tempStatusLine = "Outside target";
  } else if (stageDef.id === "sanitizing") {
    tempTargetLine = "Target: ≥82°C (15–30 s) or ≥74°C (15 min)";
  }

  let turbTargetLine = null;
  let turbStatusLine = null;
  if (isFinalRinse && turbLimit != null) {
    turbTargetLine = `Target: < ${turbLimit.toFixed(1)} NTU`;
    turbStatusLine =
      sel.turbidity < turbLimit ? "Within target" : "Above clear-rinse limit";
  }

  const lineList = Object.values(sensors);
  const stateColor = cycleStateColor(sel.cycleState);

  return (
    <div className="app">
      <style>{CSS}</style>
      <div className="bg-orb o1" />
      <div className="bg-orb o2" />

      <header className="topbar glass">
        <div className="brand">
          <span className="brand-mark" aria-hidden="true">
            <Waves size={22} />
          </span>
          <div>
            <div className="brand-name">
              Halal<b>Trace</b>
            </div>
            <div className="brand-sub">Halal Line Cleaning Verification</div>
          </div>
        </div>
        <div className="status-bar">
          <div className="mode-toggle" role="group" aria-label="Data source">
            <button
              type="button"
              className={"mode-btn" + (mode === "demo" ? " active" : "")}
              onClick={() => setMode("demo")}
            >
              Demo
            </button>
            <button
              type="button"
              className={"mode-btn" + (mode === "live" ? " active" : "")}
              onClick={() => setMode("live")}
            >
              Live hardware
            </button>
          </div>
          <span className="status-live">
            <Radio size={13} className="pulse" aria-hidden="true" />
            {mode === "live" ? "Live hardware" : "Live demo"}
          </span>
          <FlagDots count={sel.flagsInWindow} />
          <span className="live-clock">{new Date(clock).toLocaleTimeString()}</span>
        </div>
      </header>

      <div className="layout">
        <aside className="rail glass" aria-label="Processing lines">
          <div className="rail-title">
            <LayoutList size={16} aria-hidden="true" /> Processing lines
          </div>
          {lineList.map((s) => (
            <button
              key={s.id}
              type="button"
              className={"rail-item" + (selected === s.id ? " active" : "")}
              onClick={() => setSelected(s.id)}
            >
              <span
                className="rail-dot"
                style={{ background: cycleStateColor(s.cycleState) }}
              />
              <span className="rail-item-label">{s.shortLabel || s.label}</span>
              <span className="rail-item-turb">
                {CYCLE_STATE_LABELS[s.cycleState] || s.cycleState}
              </span>
              <span className="rail-item-sub">{s.label}</span>
            </button>
          ))}
          <p className="rail-foot">
            Pick a line to watch its multi-stage CIP cycle. Time alone never means
            PASS.
          </p>
        </aside>

        <main className="main">
          <section
            className="hero glass"
            style={{ "--tc": stateColor, "--tg": "transparent" }}
          >
            <div className="hero-id">
              <div className="hero-room">{sel.shortLabel || "Line"}</div>
              <div className="hero-label">{sel.label}</div>
              <p className="hero-summary">{cycleSummary(sel)}</p>
              <div className="hero-meta">
                <span className="mono">{sel.id}</span>
              </div>
            </div>
            <div className="tier-badge" style={{ "--tc": stateColor }}>
              <div>
                <div className="tier-label">
                  {CYCLE_STATE_LABELS[sel.cycleState] || sel.cycleState}
                </div>
                <div className="tier-sub">
                  {sel.cycleState === CYCLE_STATES.CLEANING
                    ? stage.shortLabel || stage.label
                    : sel.cycleState === CYCLE_STATES.VERIFYING
                      ? "Sensor verification"
                      : "Cycle state"}
                </div>
              </div>
            </div>
            <WaterPipe turbidity={sel.turbidity} />
          </section>

          <section className="glass panel stage-panel">
            <StageStrip stageId={sel.stageId} cycleState={sel.cycleState} />
          </section>

          {sel.tier !== "passed" && (
            <ActionPanel
              tier={sel.tier}
              action={sel.action}
              steps={sel.panicSteps}
            />
          )}

          <section className="grid2">
            <StatTile
              icon={Thermometer}
              name="Temperature"
              value={String(sel.temp)}
              unit="°C"
              hot={tempHot}
              data={sel.tempHist}
              color="#c45c26"
              hotLabel="outside target"
              targetLine={tempTargetLine}
              statusLine={tempStatusLine}
            />
            <StatTile
              icon={Droplets}
              name="Turbidity"
              value={String(sel.turbidity)}
              unit=" NTU"
              hot={turbHot}
              data={sel.turbHist}
              color="#0f6e5c"
              hotLabel="above limit"
              targetLine={turbTargetLine}
              statusLine={turbStatusLine}
            />
          </section>

          <section className="grid2">
            <div className="glass panel">
              <div className="panel-head">
                <Activity size={16} aria-hidden="true" /> Condition meter
              </div>
              <FlagMeter count={sel.flagsInWindow} />
              <p className="panel-note">
                Tracks off-target sensor events during the cycle. Reaching a stage
                timer never issues PASS by itself.
              </p>
            </div>

            <div className="glass panel">
              <div className="panel-head">
                <Clock size={16} aria-hidden="true" /> Cycle timing
              </div>
              <div className="mon-bar">
                <div className="mon-fill" style={{ width: `${monPct}%` }} />
              </div>
              <div className="mon-row">
                <span>{stageElapsedMin.toFixed(1)} min elapsed</span>
                {stageConfiguredMin > 0 ? (
                  <span>Configured target: {stageConfiguredMin} min</span>
                ) : (
                  <span>No stage target set</span>
                )}
              </div>
              <div className="mon-row mon-row-sub">
                <span>Stage: {stage.shortLabel || stage.label}</span>
                <span>Typical: {formatTypicalRange(stageDef.typicalMin)}</span>
              </div>
              <p className="panel-note">
                Cycle total {cycleElapsedMin.toFixed(1)} min · bar is this stage
                only. At 100% cleaning ends and verification starts — not PASS.
              </p>
              {mode === "demo" && (
                <div className="demo">
                  <span className="demo-tag">Try it</span>
                  <button
                    type="button"
                    className="demo-btn"
                    onClick={() => backend.current?.inject(selected)}
                  >
                    <Droplets size={15} aria-hidden="true" /> Spike a dirty rinse
                  </button>
                </div>
              )}
            </div>
          </section>

          <section className="glass panel">
            <div className="panel-head">
              <Flag size={16} aria-hidden="true" /> Event log
              <span className="muted"> · {sel.shortLabel || sel.label}</span>
            </div>
            <div className="log-head">
              <span></span>
              <span>#</span>
              <span>Time</span>
              <span>Turbidity</span>
              <span>Temp</span>
            </div>
            <div className="log">
              {sel.flags.length === 0 && (
                <div className="log-empty">
                  All clear so far — no off-target events on this line.
                </div>
              )}
              {sel.flags.map((f, i) => {
                const dc = flagDotColor(f.flagNumber ?? sel.flags.length - i);
                return (
                  <div className="log-row" key={f.ts + "-" + i}>
                    <span
                      className="log-flag-dot"
                      style={{ background: dc }}
                    />
                    <span className="log-flag-num">{f.flagNumber ?? "—"}</span>
                    <span className="mono">{fmtTime(f.ts)}</span>
                    <span>
                      <b>{f.turbidity.toFixed(1)}</b> NTU
                    </span>
                    <span>
                      <b>{f.temp.toFixed(1)}</b> °C
                    </span>
                  </div>
                );
              })}
            </div>
          </section>
        </main>
      </div>
    </div>
  );
}
