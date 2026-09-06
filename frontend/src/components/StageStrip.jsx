import React from "react";
import { STAGE_DEFS } from "../cycleStages";

export default function StageStrip({ stageId, cycleState }) {
  const activeIndex = STAGE_DEFS.findIndex((s) => s.id === stageId);
  const verifying = cycleState === "verifying";
  const done = cycleState === "passed" || cycleState === "failed";

  return (
    <div className="stage-strip" aria-label="Cleaning stages">
      <div className="stage-strip-label">Current stage</div>
      <ol className="stage-list">
        {STAGE_DEFS.map((stage, index) => {
          let cls = "stage-step";
          if (verifying || done || (activeIndex >= 0 && index < activeIndex)) {
            cls += " is-done";
          }
          if (!verifying && !done && index === activeIndex) {
            cls += " is-current";
          }
          if (cycleState === "idle") {
            cls = "stage-step";
          }
          return (
            <li key={stage.id} className={cls}>
              <span className="stage-index">{index + 1}</span>
              <span className="stage-name">{stage.shortLabel || stage.label}</span>
            </li>
          );
        })}
      </ol>
      {verifying ? (
        <p className="stage-verify-note">
          Cleaning finished — verifying turbidity &amp; temperature trace (not a pass yet).
        </p>
      ) : null}
    </div>
  );
}
