import React from "react";
import { CONFIG, TIERS, tierFromCount, clamp } from "../config";

export default function FlagMeter({ count }) {
  const marks = [
    { n: CONFIG.FLAG_WARN,  k: "warn" },
    { n: CONFIG.FLAG_WARN2, k: "warn2" },
    { n: CONFIG.FLAG_PANIC, k: "panic" },
  ];
  const max = CONFIG.FLAG_PANIC + 2;
  return (
    <div className="meter">
      <div className="meter-track">
        <div className="meter-fill" style={{ width: `${clamp(count / max, 0, 1) * 100}%`, background: TIERS[tierFromCount(count)].color }} />
        {marks.map((m) => (
          <span key={m.k} className="meter-mark" style={{ left: `${(m.n / max) * 100}%`, background: TIERS[m.k].color }} title={`${TIERS[m.k].label} @ ${m.n}`} />
        ))}
      </div>
      <div className="meter-legend">
        <span>0</span>
        <span style={{ color: TIERS.warn.color }}>Watch</span>
        <span style={{ color: TIERS.warn2.color }}>Attention</span>
        <span style={{ color: TIERS.panic.color }}>Critical</span>
      </div>
    </div>
  );
}
