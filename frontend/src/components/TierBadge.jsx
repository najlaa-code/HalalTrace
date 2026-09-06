import React from "react";
import { TIERS } from "../config";

export default function TierBadge({ tier, count, windowHours }) {
  const t = TIERS[tier] || TIERS.passed;
  const Icon = t.icon;
  return (
    <div className="tier-badge" style={{ "--tc": t.color, "--tg": t.glow }}>
      <Icon size={26} />
      <div>
        <div className="tier-label">{t.label}</div>
        <div className="tier-sub">
          {count === 0 ? "No issues in this window" : `${count} off-target event${count === 1 ? "" : "s"} · last ${windowHours} h`}
        </div>
      </div>
    </div>
  );
}
