import React, { useState, useEffect, useRef } from "react";
import Sparkline from "./Sparkline";

function buildReel(oldCh, newCh) {
  const o = parseInt(oldCh, 10);
  const n = parseInt(newCh, 10);
  if (isNaN(o) || isNaN(n) || o === n) return null;
  const lo = Math.min(o, n);
  const hi = Math.max(o, n);
  return Array.from({ length: hi - lo + 1 }, (_, i) => String(lo + i));
}

const H = 1;

function AnimatedChar({ ch, version }) {
  const [anim, setAnim] = useState(null);
  const prevRef = useRef({ ch, version });
  const timerRef = useRef(null);

  useEffect(() => {
    const { ch: prevCh, version: prevVer } = prevRef.current;
    if (prevVer === version) return;
    prevRef.current = { ch, version };
    clearTimeout(timerRef.current);

    const reel = buildReel(prevCh, ch);
    if (!reel) {
      setAnim(null);
      return;
    }

    const oldIdx = reel.indexOf(prevCh);
    const newIdx = reel.indexOf(ch);
    const dur = Math.max(200, 700 - reel.length * 55);

    setAnim({
      reel,
      from: `${-oldIdx * H}em`,
      to: `${-newIdx * H}em`,
      dur: `${dur}ms`,
    });
    timerRef.current = setTimeout(() => setAnim(null), dur + 80);
    return () => clearTimeout(timerRef.current);
  }, [version, ch]);

  if (!anim) {
    return (
      <span className="anim-char-wrap">
        <span className="anim-reel-digit">{ch}</span>
      </span>
    );
  }

  return (
    <span className="anim-char-wrap">
      <span
        className="anim-reel"
        style={{ "--rf": anim.from, "--rt": anim.to, "--rd": anim.dur }}
      >
        {anim.reel.map((d, i) => (
          <span key={i} className="anim-reel-digit">
            {d}
          </span>
        ))}
      </span>
    </span>
  );
}

function AnimatedValue({ value }) {
  const str = String(value);
  const prevRef = useRef(str);
  const versionsRef = useRef(str.split("").map(() => 0));

  const prev = prevRef.current;
  if (prev !== str) {
    const old = versionsRef.current;
    versionsRef.current = str.split("").map((ch, i) => {
      const changed =
        str.length !== prev.length || i >= prev.length || prev[i] !== ch;
      return changed ? (old[i] ?? 0) + 1 : (old[i] ?? 0);
    });
    prevRef.current = str;
  }

  return (
    <>
      {str.split("").map((ch, i) =>
        /\d/.test(ch) ? (
          <AnimatedChar key={i} ch={ch} version={versionsRef.current[i] ?? 0} />
        ) : (
          <span key={i}>{ch}</span>
        )
      )}
    </>
  );
}

export default function StatTile({
  icon: Icon,
  name,
  value,
  unit,
  hot,
  data,
  color,
  hotLabel = "attention",
  hint,
  targetLine,
  statusLine,
}) {
  return (
    <div className={"glass tile" + (hot ? " tile-hot" : "")}>
      <div className="tile-head">
        <span className="tile-ico" style={{ color }}>
          <Icon size={18} />
        </span>
        <span className="tile-name">{name}</span>
        {hot && <span className="tile-tag">{hotLabel}</span>}
      </div>
      <div className="tile-val">
        <AnimatedValue value={value} />
        <span className="tile-unit">{unit}</span>
      </div>
      {targetLine ? <p className="tile-target">{targetLine}</p> : null}
      {statusLine ? (
        <p className={"tile-status" + (hot ? " is-hot" : " is-ok")}>{statusLine}</p>
      ) : null}
      {hint ? <p className="tile-hint">{hint}</p> : null}
      <Sparkline data={data} color={color} />
    </div>
  );
}
