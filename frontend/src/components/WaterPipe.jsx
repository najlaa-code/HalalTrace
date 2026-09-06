import React from "react";
import { CONFIG, clamp } from "../config";

export default function WaterPipe({ turbidity }) {
  const ratio = clamp(turbidity / CONFIG.TURB_VIS_MAX, 0, 1);
  const r = Math.round(72 + ratio * 70), g = Math.round(190 - ratio * 70), b = Math.round(205 - ratio * 150);
  return (
    <div className="pipe-wrap">
      <div className="pipe">
        <div className="pipe-water" style={{ background: `linear-gradient(180deg, rgba(${r},${g},${b},.55), rgba(${r - 20},${g - 20},${b - 10},.9))` }}>
          <span className="bubble b1" /><span className="bubble b2" /><span className="bubble b3" />
        </div>
        <div className="pipe-gloss" />
      </div>
      <div className="pipe-cap">{turbidity.toFixed(1)} <small>NTU</small></div>
    </div>
  );
}
