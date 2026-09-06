export const CSS = `
@import url('https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,600;9..144,700&family=Source+Sans+3:wght@400;500;600;700&display=swap');

.app{
  --ink:#1a2e2a;
  --ink-soft:#5a6f68;
  --line:rgba(26,46,42,.12);
  --panel:rgba(255,255,255,.78);
  --accent:#0f6e5c;
  --accent-2:#1a8f78;
  --warn:#b7791f;
  --crit:#b42318;
  --ok:#1a7a4c;
  position:relative; min-height:100%; padding:20px 22px 28px;
  font-family:'Source Sans 3', system-ui, sans-serif; color:var(--ink);
  background:
    radial-gradient(90% 70% at 0% 0%, rgba(15,110,92,.14), transparent 55%),
    radial-gradient(70% 50% at 100% 0%, rgba(180,140,60,.08), transparent 45%),
    linear-gradient(165deg, #e4efe9 0%, #eef4f1 42%, #e8ebe6 100%);
  overflow-x:hidden;
}
.app *{box-sizing:border-box;}
.bg-orb{position:absolute;border-radius:50%;filter:blur(28px);opacity:.35;pointer-events:none;
  background:radial-gradient(circle at 30% 30%, rgba(255,255,255,.9), transparent 70%);}
.o1{width:280px;height:280px;top:-60px;right:12%;}
.o2{width:180px;height:180px;bottom:6%;left:4%;opacity:.25;}
.o3{display:none;}

.glass{
  position:relative;
  background:var(--panel);
  border:1px solid var(--line);
  border-radius:16px;
  box-shadow:0 8px 24px rgba(26,46,42,.06);
  backdrop-filter:blur(12px); -webkit-backdrop-filter:blur(12px);
}
.glass::before{content:none;}

.topbar{
  display:flex;align-items:center;justify-content:space-between;gap:16px;
  padding:16px 20px;margin-bottom:18px;
  animation:enter .45s ease both;
}
.brand{display:flex;align-items:center;gap:14px;min-width:0;}
.brand-mark{
  display:grid;place-items:center;width:44px;height:44px;border-radius:12px;color:#fff;flex:none;
  background:var(--accent);
}
.brand-name{font-family:'Fraunces', Georgia, serif;font-weight:700;font-size:1.55rem;letter-spacing:-.02em;line-height:1;}
.brand-name b{font-weight:700;color:var(--accent);}
.brand-sub{margin-top:3px;font-size:.86rem;color:var(--ink-soft);font-weight:500;}
.status-bar{
  display:flex;align-items:center;gap:12px;flex-wrap:wrap;justify-content:flex-end;
  font-size:.86rem;font-weight:600;color:var(--ink-soft);
}
.status-live{
  display:inline-flex;align-items:center;gap:6px;
  padding:6px 10px;border-radius:8px;background:rgba(255,255,255,.65);border:1px solid var(--line);
}
.live-clock{font-variant-numeric:tabular-nums;color:var(--ink);font-weight:600;}
.muted{color:var(--ink-soft);font-weight:500;}
.pulse{color:var(--ok);animation:pulse 1.8s ease-in-out infinite;}
@keyframes pulse{0%,100%{opacity:1}50%{opacity:.4}}
@keyframes enter{from{opacity:0;transform:translateY(8px)}to{opacity:1;transform:none}}

.layout{display:grid;grid-template-columns:260px minmax(0,1fr);gap:18px;align-items:start;}

.rail{padding:16px;align-self:start;position:sticky;top:18px;animation:enter .5s ease .04s both;}
.rail-title{
  display:flex;align-items:center;gap:8px;
  font-family:'Fraunces', Georgia, serif;font-weight:600;font-size:1rem;margin-bottom:14px;
}
.rail-room{margin-bottom:4px;}
.rail-room-name{display:none;}
.rail-item{
  display:grid;grid-template-columns:10px 1fr auto;grid-template-rows:auto auto;
  column-gap:10px;row-gap:2px;align-items:center;width:100%;text-align:left;cursor:pointer;
  padding:12px;margin-bottom:8px;border-radius:12px;border:1px solid transparent;
  background:rgba(255,255,255,.45);font-family:inherit;font-size:.92rem;color:var(--ink);transition:border-color .15s, background .15s;
}
.rail-item:hover{background:rgba(255,255,255,.8);border-color:rgba(15,110,92,.18);}
.rail-item.active{background:#fff;border-color:rgba(15,110,92,.35);}
.rail-dot{width:10px;height:10px;border-radius:50%;flex:none;grid-row:1 / span 2;}
.rail-item-label{font-weight:700;line-height:1.2;}
.rail-item-sub{grid-column:2;font-size:.78rem;color:var(--ink-soft);font-weight:500;}
.rail-item-turb{grid-column:3;grid-row:1 / span 2;font-variant-numeric:tabular-nums;font-weight:700;font-size:.88rem;color:var(--ink-soft);}
.rail-item-turb small{font-size:.7rem;font-weight:600;}
.rail-foot{font-size:.78rem;color:var(--ink-soft);line-height:1.45;margin-top:10px;padding:0 2px;}

.main{display:flex;flex-direction:column;gap:14px;min-width:0;animation:enter .55s ease .08s both;}

.hero{
  display:grid;grid-template-columns:1fr auto auto;align-items:center;gap:20px;
  padding:20px 22px;border-left:4px solid var(--tc);
}
.hero-room{font-size:.8rem;color:var(--ink-soft);font-weight:600;text-transform:uppercase;letter-spacing:.04em;}
.hero-label{font-family:'Fraunces', Georgia, serif;font-weight:700;font-size:1.55rem;line-height:1.15;margin:4px 0 8px;letter-spacing:-.02em;}
.hero-summary{font-size:.92rem;color:var(--ink-soft);max-width:36rem;line-height:1.4;margin:0;}
.hero-meta{margin-top:10px;}
.hero-meta .mono{
  font-size:.75rem;font-weight:600;color:var(--ink-soft);
  background:rgba(26,46,42,.06);padding:3px 8px;border-radius:6px;
}
.tier-badge{
  display:flex;align-items:center;gap:10px;padding:12px 16px;border-radius:12px;color:#fff;
  background:var(--tc);
}
.tier-label{font-family:'Fraunces', Georgia, serif;font-weight:700;font-size:1.15rem;line-height:1;}
.tier-sub{font-size:.78rem;opacity:.92;margin-top:3px;font-weight:500;}

.pipe-wrap{display:flex;flex-direction:column;align-items:center;gap:6px;}
.pipe{position:relative;width:44px;height:92px;border-radius:12px;overflow:hidden;
  background:rgba(255,255,255,.55);border:1px solid var(--line);}
.pipe-water{position:absolute;left:0;right:0;bottom:0;height:82%;border-radius:0 0 11px 11px;transition:background .5s;}
.pipe-gloss{position:absolute;top:0;left:6px;width:8px;height:100%;border-radius:8px;
  background:linear-gradient(180deg,rgba(255,255,255,.75),rgba(255,255,255,0));}
.bubble{position:absolute;width:5px;height:5px;border-radius:50%;background:rgba(255,255,255,.65);left:50%;bottom:6px;animation:rise 3.6s infinite;}
.b1{left:30%;animation-delay:0s;} .b2{left:58%;animation-delay:1.2s;width:4px;height:4px;} .b3{left:44%;animation-delay:2.3s;}
@keyframes rise{0%{transform:translateY(0);opacity:0}20%{opacity:.85}100%{transform:translateY(-68px);opacity:0}}
.pipe-cap{font-weight:700;font-size:.82rem;color:var(--ink);font-variant-numeric:tabular-nums;}
.pipe-cap small{font-size:.68rem;color:var(--ink-soft);font-weight:600;}

.grid2{display:grid;grid-template-columns:1fr 1fr;gap:14px;}
.tile{padding:16px 18px;transition:border-color .2s, box-shadow .2s;}
.tile-hot{border-color:rgba(180,35,24,.28);box-shadow:0 0 0 1px rgba(180,35,24,.08);}
.tile-head{display:flex;align-items:center;gap:8px;margin-bottom:2px;}
.tile-ico{display:grid;place-items:center;}
.tile-name{font-weight:700;font-size:.88rem;}
.tile-tag{margin-left:auto;font-size:.72rem;font-weight:700;color:var(--crit);background:rgba(180,35,24,.1);padding:3px 8px;border-radius:6px;}
.tile-val{font-family:'Fraunces', Georgia, serif;font-weight:700;font-size:2.05rem;line-height:1;margin:6px 0 2px;font-variant-numeric:tabular-nums;}
.tile-unit{font-size:.95rem;color:var(--ink-soft);font-weight:600;margin-left:3px;font-family:'Source Sans 3',sans-serif;}
.tile-hint{margin:0 0 6px;font-size:.78rem;color:var(--ink-soft);font-weight:500;}

.panel{padding:16px 18px;}
.panel-head{display:flex;align-items:center;gap:8px;font-family:'Fraunces', Georgia, serif;font-weight:600;font-size:1rem;margin-bottom:12px;}
.panel-note{font-size:.82rem;color:var(--ink-soft);line-height:1.45;margin:12px 0 0;}

.meter-track{position:relative;height:10px;border-radius:6px;background:rgba(26,46,42,.08);overflow:visible;}
.meter-fill{height:100%;border-radius:6px;transition:width .45s, background .45s;}
.meter-mark{position:absolute;top:-3px;width:2px;height:16px;border-radius:1px;transform:translateX(-50%);opacity:.85;}
.meter-legend{display:flex;justify-content:space-between;gap:8px;font-size:.72rem;font-weight:600;margin-top:10px;color:var(--ink-soft);}

.mon-bar{height:10px;border-radius:6px;background:rgba(26,46,42,.08);overflow:hidden;}
.mon-fill{height:100%;background:var(--accent);transition:width .8s;}
.mon-row{display:flex;justify-content:space-between;font-size:.82rem;font-weight:600;color:var(--ink-soft);margin:8px 0 0;gap:10px;flex-wrap:wrap;}
.mon-row-sub{margin-top:6px;font-weight:500;}
.tile-target{margin:2px 0 0;font-size:.82rem;color:var(--ink-soft);font-weight:600;}
.tile-status{margin:2px 0 6px;font-size:.8rem;font-weight:700;}
.tile-status.is-ok{color:var(--ok);}
.tile-status.is-hot{color:var(--crit);}

.stage-panel{padding:14px 16px;}
.stage-strip-label{
  font-size:.72rem;font-weight:700;text-transform:uppercase;letter-spacing:.04em;
  color:var(--ink-soft);margin-bottom:10px;
}
.stage-list{
  list-style:none;margin:0;padding:0;display:grid;
  grid-template-columns:repeat(5,minmax(0,1fr));gap:8px;
}
.stage-step{
  display:flex;flex-direction:column;gap:4px;align-items:flex-start;
  padding:10px 8px;border-radius:10px;border:1px solid var(--line);
  background:rgba(255,255,255,.45);min-height:64px;
}
.stage-step.is-current{
  border-color:rgba(15,110,92,.45);background:#fff;
  box-shadow:0 0 0 1px rgba(15,110,92,.12);
}
.stage-step.is-done{opacity:.72;background:rgba(15,110,92,.06);}
.stage-index{
  width:18px;height:18px;border-radius:50%;display:grid;place-items:center;
  font-size:.68rem;font-weight:700;background:rgba(26,46,42,.08);color:var(--ink-soft);
}
.stage-step.is-current .stage-index{background:var(--accent);color:#fff;}
.stage-name{font-size:.78rem;font-weight:700;line-height:1.25;}
.stage-verify-note{margin:10px 0 0;font-size:.82rem;color:var(--warn);font-weight:600;}

.demo{display:flex;align-items:center;gap:10px;flex-wrap:wrap;margin-top:14px;}
.demo-tag{font-size:.7rem;font-weight:700;text-transform:uppercase;letter-spacing:.04em;color:var(--ink-soft);}
.demo-btn{
  display:inline-flex;align-items:center;gap:7px;cursor:pointer;
  font-family:inherit;font-weight:600;font-size:.88rem;color:#fff;
  padding:10px 14px;border:none;border-radius:10px;background:var(--accent);transition:background .15s, transform .15s;
}
.demo-btn:hover{background:var(--accent-2);}
.demo-btn:active{transform:translateY(1px);}

.log-head,.log-row{display:grid;grid-template-columns:12px 22px 1.1fr 1fr 1fr;gap:8px;padding:9px 12px;font-size:.86rem;align-items:center;}
.log-head{font-size:.72rem;text-transform:uppercase;letter-spacing:.04em;color:var(--ink-soft);font-weight:700;}
.log{max-height:220px;overflow-y:auto;border-radius:10px;}
.log-row{border-radius:8px;background:rgba(255,255,255,.55);margin-bottom:5px;}
.log-row:first-child{animation:flash 1s ease;}
@keyframes flash{0%{background:rgba(183,121,31,.18)}100%{background:rgba(255,255,255,.55)}}
.log-row b{font-weight:700;font-variant-numeric:tabular-nums;}
.log-empty{padding:22px 12px;text-align:center;color:var(--ink-soft);font-size:.9rem;}
.mono{font-weight:600;font-variant-numeric:tabular-nums;}

.anim-char-wrap{position:relative;display:inline-block;height:1em;vertical-align:bottom;clip-path:inset(0);}
.anim-reel{display:flex;flex-direction:column;will-change:transform;animation:reelScroll var(--rd,0.4s) cubic-bezier(0.45,0,0.15,1) both;}
.anim-reel-digit{height:1em;display:flex;align-items:center;flex-shrink:0;}
@keyframes reelScroll{from{transform:translateY(var(--rf,0))}to{transform:translateY(var(--rt,0))}}

.flag-dots{display:flex;align-items:center;gap:4px;}
.flag-dot{width:8px;height:8px;border-radius:50%;border:1px solid rgba(26,46,42,.15);background:transparent;transition:.25s;}
.flag-dot.lit{border-color:transparent;}

.action-panel{display:flex;align-items:flex-start;gap:12px;padding:14px 16px;border-radius:12px;}
.action-panel.tier-warn{border-left:4px solid var(--warn);background:rgba(183,121,31,.08);}
.action-panel.tier-warn2{border-left:4px solid #c05621;background:rgba(192,86,33,.08);}
.action-panel.tier-panic{border-left:4px solid var(--crit);background:rgba(180,35,24,.08);}
.action-icon{display:none;}
.action-title{font-family:'Fraunces', Georgia, serif;font-weight:700;font-size:1rem;line-height:1.3;}
.action-sub{font-size:.86rem;color:var(--ink-soft);margin-top:4px;}
.panic-steps{margin:8px 0 0;padding-left:18px;}
.panic-steps li{font-size:.86rem;line-height:1.55;color:var(--ink);}

.log-flag-dot{width:8px;height:8px;border-radius:50%;flex:none;}
.log-flag-num{font-weight:700;font-size:.78rem;color:var(--ink-soft);font-variant-numeric:tabular-nums;}

@media(max-width:900px){
  .layout{grid-template-columns:1fr;}
  .rail{position:static;}
  .hero{grid-template-columns:1fr;gap:14px;justify-items:start;}
  .grid2{grid-template-columns:1fr;}
  .topbar{flex-direction:column;align-items:flex-start;}
  .status-bar{justify-content:flex-start;}
  .stage-list{grid-template-columns:1fr 1fr;}
}
`;
