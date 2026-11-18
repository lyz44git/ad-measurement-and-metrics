// Interactive figures for the ad-measurement repository. Data: data.js, built by build_data.py from the result files.
(() => {
"use strict";
const D = window.DATA, NS = "http://www.w3.org/2000/svg";
const reduce = matchMedia("(prefers-reduced-motion: reduce)").matches;
const $ = (s, r = document) => r.querySelector(s);
const fmt = (v, d = 0) => v.toLocaleString("en-US", { minimumFractionDigits: d, maximumFractionDigits: d });

/* ---------- small helpers ---------- */
function el(tag, attrs = {}, parent) {
  const e = document.createElementNS(NS, tag);
  for (const k in attrs) if (attrs[k] !== undefined && attrs[k] !== null) e.setAttribute(k, attrs[k]);
  if (parent) parent.appendChild(e);
  return e;
}
function txt(parent, x, y, s, attrs = {}) { const t = el("text", Object.assign({ x, y }, attrs), parent); t.textContent = s; return t; }
function svgIn(host, w, h) { host.innerHTML = ""; return el("svg", { width: w, height: h, viewBox: `0 0 ${w} ${h}`, role: "img" }, host); }
const lin = (d0, d1, r0, r1) => v => r0 + (v - d0) / (d1 - d0) * (r1 - r0);
const lg = (d0, d1, r0, r1) => { const a = Math.log10(d0), b = Math.log10(d1); return v => r0 + (Math.log10(v) - a) / (b - a) * (r1 - r0); };
const ease = t => t < .5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2;
function tween(dur, step, done) {
  if (reduce || dur <= 0 || document.hidden) { step(1); if (done) done(); return; }
  const t0 = performance.now();
  (function f(now) { const t = Math.min(1, (now - t0) / dur); step(ease(t)); if (t < 1) requestAnimationFrame(f); else if (done) done(); })(t0);
}
/* animate numeric attributes of several elements together */
function animate(items, dur = 650, done) {
  const from = items.map(([e, a]) => Object.fromEntries(Object.keys(a).map(k => [k, parseFloat(e.getAttribute(k)) || 0])));
  tween(dur, t => items.forEach(([e, a], i) => { for (const k in a) { let v = from[i][k] + (a[k] - from[i][k]) * t; if (k === "width" || k === "height") v = Math.max(0, v); e.setAttribute(k, v); } }), done);
}
function countTo(node, to, dur = 900, d = 0, suffix = "") {
  const from = parseFloat((node.dataset.v || "0")); node.dataset.v = to;
  node.textContent = fmt(to, d) + suffix; // final value first, in case animation frames do not run
  tween(dur, t => node.textContent = fmt(from + (to - from) * t, d) + suffix);
}
const tip = $("#tip");
function hoverTip(node, html) {
  node.addEventListener("pointermove", e => { tip.innerHTML = typeof html === "function" ? html() : html; tip.classList.add("on");
    const x = Math.min(e.clientX + 14, innerWidth - tip.offsetWidth - 8); tip.style.left = x + "px"; tip.style.top = (e.clientY + 14) + "px"; });
  node.addEventListener("pointerleave", () => tip.classList.remove("on"));
}
function segControl(host, onPick, init) {
  const btns = [...host.querySelectorAll("button")];
  const set = v => btns.forEach(b => b.setAttribute("aria-pressed", String(b.dataset.v === String(v))));
  btns.forEach(b => b.addEventListener("click", () => { set(b.dataset.v); onPick(b.dataset.v); }));
  set(init); return set;
}
function whenVisible(node, fn) {
  if (!("IntersectionObserver" in window)) return fn();
  const io = new IntersectionObserver(es => es.forEach(e => { if (e.isIntersecting) { io.disconnect(); fn(); } }), { threshold: .35 });
  io.observe(node);
}
const W = host => Math.max(280, host.clientWidth);
const redrawers = [];
let rt; addEventListener("resize", () => { clearTimeout(rt); rt = setTimeout(() => redrawers.forEach(f => f()), 150); });
function axisX(g, x, ticks, y, fmtT = String, label) {
  ticks.forEach(v => { el("line", { x1: x(v), x2: x(v), y1: y, y2: y + 4, class: "axis" }, g); txt(g, x(v), y + 17, fmtT(v), { "text-anchor": "middle" }); });
  if (label) txt(g, (x(ticks[0]) + x(ticks[ticks.length - 1])) / 2, y + 36, label, { "text-anchor": "middle", class: "t-muted" });
}
function gridY(g, y, ticks, x0, x1, fmtT = String) {
  ticks.forEach(v => { el("line", { x1: x0, x2: x1, y1: y(v), y2: y(v), class: "gridl" }, g); txt(g, x0 - 8, y(v) + 4, fmtT(v), { "text-anchor": "end" }); });
}

/* ---------- hero ---------- */
const E = D.experiment;
const heroVals = { users: [E.users, 0], convLift: [100 * E.conversion.relative_lift, 0], credited: [E.conversion.credited, 0], caused: [E.conversion.caused, 0] };
document.querySelectorAll("[data-count]").forEach(n => { const [v, d] = heroVals[n.dataset.count]; whenVisible(n, () => countTo(n, v, 1400, d)); });

/* ---------- 1.1 rates ---------- */
(function rates() {
  if (!document.getElementById("c-rates")) return;
  const host = $("#c-rates");
  function draw(animateIn) {
    // one shared index scale (control = 100) for both rows, so the two relative lifts compare by length
    const w = W(host), nar = w < 480, rowsH = 74, h = 2 * rowsH + 50, L = Math.max(125, Math.min(150, w * .28)), R = w - 16, top = 185, x = lin(0, top, L, R), ticks = [0, 50, 100, 150];
    const svg = svgIn(host, w, h), yA = 2 * rowsH + 4;
    ticks.forEach(v => { el("line", { x1: x(v), x2: x(v), y1: 14, y2: yA - 6, class: "gridl" }, svg); txt(svg, x(v), yA + 10, String(v), { "text-anchor": "middle", class: "t-muted", "font-size": 11 }); });
    txt(svg, (x(0) + x(150)) / 2, yA + 30, "% of control rate", { "text-anchor": "middle", class: "t-muted", "font-size": 11 });
    [["visit", "Visit rate"], ["conversion", "Conversion rate"]].forEach(([k, name], i) => {
      const r = E[k], g = el("g", { transform: `translate(0,${i * rowsH})` }, svg), y = 40, i1 = 100 * r.ad_rate / r.control_rate;
      txt(g, 0, y - 6, name, { class: "t-strong" });
      
      el("line", { x1: x(0), x2: R, y1: y, y2: y, class: "gridl", "stroke-width": 6, "stroke-linecap": "round" }, g);
      const bar = el("line", { x1: x(100), x2: x(100), y1: y, y2: y, "stroke-width": 6, "stroke-linecap": "round", class: "s-orange", opacity: .55 }, g);
      const c0 = el("circle", { cx: x(100), cy: y, r: 7, class: "f-grey s-card", "stroke-width": 2 }, g);
      const c1 = el("circle", { cx: x(100), cy: y, r: 8, class: "f-navy s-card", "stroke-width": 2 }, g);
      const l0 = txt(g, x(100) - 4, y - 16, `Control ${(100 * r.control_rate).toFixed(2)}%`, { "text-anchor": "end", class: "t-muted" });
      const l1 = txt(g, x(i1) + 4, y - 16, `${nar ? "Ad" : "Ad group"} ${(100 * r.ad_rate).toFixed(2)}%`, { "text-anchor": "start", class: "t-navy", opacity: 0 });
      l1.setAttribute("x", Math.min(x(i1) + 4, w - 2 - l1.getComputedTextLength()));
      const dl = txt(g, (x(100) + x(i1)) / 2, y + 22, `+${fmt(100 * r.relative_lift)}% relative`, { "text-anchor": "middle", class: "t-orange", "font-size": 11, opacity: 0 });
      hoverTip(c0, `Control group: ${(100 * r.control_rate).toFixed(2)}% (100% of control)`); hoverTip(c1, `Ad group: ${(100 * r.ad_rate).toFixed(2)}% (${fmt(i1)}% of control; +${(100 * (r.ad_rate - r.control_rate)).toFixed(k === "visit" ? 2 : 3)} pp)`);
      const go = () => animate([[c1, { cx: x(i1) }], [bar, { x2: x(i1) }], [l1, { opacity: 1 }], [dl, { opacity: 1 }]], 1100);
      if (animateIn) whenVisible(host, () => setTimeout(go, 200 + 250 * i)); else { c1.setAttribute("cx", x(i1)); bar.setAttribute("x2", x(i1)); l1.setAttribute("opacity", 1); dl.setAttribute("opacity", 1); }
    });
  }
  draw(true); redrawers.push(() => draw(false));
})();

/* ---------- 1.2 segments ---------- */
(function segments() {
  if (!document.getElementById("c-slope")) return;
  const S = D.segments, hostS = $("#c-slope"), hostP = $("#c-scatter"), ro = $("#ro-seg");
  let sel = 0, mode = "nopool", dots = [], res = [], played = false;
  const segHost = $("#seg-samples");
  S.forEach((s, i) => { const b = document.createElement("button"); b.type = "button"; b.dataset.v = i; b.textContent = s.sample; segHost.appendChild(b); });
  const setSample = segControl(segHost, v => pick(+v), 0);
  const setMode = segControl($("#seg-pool"), v => setM(v), "nopool");
  const mean = k => S.reduce((a, s) => a + s.rmse[k], 0) / S.length;

  function drawSlope() {
    const w = W(hostS), h = 300, x0 = 54, x1 = w - 64, y = lin(0.5, 1.4, h - 34, 18), svg = svgIn(hostS, w, h);
    gridY(svg, y, [0.6, 0.8, 1.0, 1.2, 1.4], x0 - 14, x1 + 14, v => v.toFixed(1));
    txt(svg, x0 - 44, 10, "RMSE (pp)", { class: "t-muted" });
    txt(svg, x0, h - 10, "Each segment", { "text-anchor": "middle", class: "t-ink" });
    txt(svg, x1, h - 10, "Multilevel", { "text-anchor": "middle", class: "t-ink" });
    S.forEach((s, i) => {
      const g = el("g", { class: "hot" }, svg), on = i === sel;
      el("line", { x1: x0, x2: x1, y1: y(s.rmse.nopool), y2: y(s.rmse.bayes), "stroke-width": 12, stroke: "transparent" }, g);
      el("line", { x1: x0, x2: x1, y1: y(s.rmse.nopool), y2: y(s.rmse.bayes), "stroke-width": on ? 2.6 : 1.1, class: on ? "s-orange" : "s-grey", opacity: on ? 1 : .55 }, g);
      el("circle", { cx: x0, cy: y(s.rmse.nopool), r: on ? 5 : 3, class: on ? "f-orange" : "f-grey" }, g);
      el("circle", { cx: x1, cy: y(s.rmse.bayes), r: on ? 5 : 3, class: on ? "f-orange" : "f-grey" }, g);
      g.addEventListener("click", () => { setSample(i); pick(i); });
      hoverTip(g, `Sample ${s.sample}: ${s.rmse.nopool.toFixed(2)} → ${s.rmse.bayes.toFixed(2)} pp`);
      if (on) svg.appendChild(g);
    });
    const m0 = mean("nopool"), m1 = mean("bayes");
    el("line", { x1: x0, x2: x1, y1: y(m0), y2: y(m1), "stroke-width": 4, class: "s-navy", "stroke-linecap": "round" }, svg);
    txt(svg, x1 + 8, y(m1) + 4, m1.toFixed(2), { class: "t-navy" });
    txt(svg, (x0 + x1) / 2, y(0.535), `Mean of 10: ${m0.toFixed(2)} → ${m1.toFixed(2)} pp`, { "text-anchor": "middle", class: "t-navy", "font-size": 11.5 });
  }
  let X, Y;
  function drawScatter() {
    const w = W(hostP), h = Math.min(330, Math.max(260, w * .64)), L = 40, B = h - 46, svg = svgIn(hostP, w, h);
    X = lin(-1, 9, L, w - 8); Y = lin(-3, 11, B, 8);
    gridY(svg, Y, [-2, 0, 2, 4, 6, 8, 10], L, w - 8);
    axisX(svg, X, [0, 2, 4, 6, 8], B, String, "Benchmark effect, other 98% of users (pp)");
    txt(svg, L - 34, 2, "Estimate (pp)", { class: "t-muted" });
    el("line", { x1: X(-1), y1: Y(-1), x2: X(9), y2: Y(9), class: "s-grey", "stroke-dasharray": "4 4" }, svg);
    txt(svg, X(8.8), Y(8.2) + 22, "estimate = benchmark", { "text-anchor": "end", class: "t-muted", "font-size": 11 });
    const s = S[sel], v = s[mode]; dots = []; res = [];
    const gr = el("g", {}, svg), gd = el("g", {}, svg);
    s.bench.forEach((b, i) => {
      res.push(el("line", { x1: X(b), x2: X(b), y1: Y(b), y2: Y(v[i]), class: mode === "bayes" ? "s-navy" : "s-grey", opacity: .35 }, gr));
      const c = el("circle", { cx: X(b), cy: Y(v[i]), r: 3.6, class: (mode === "bayes" ? "f-navy" : "f-grey") + " s-card", "stroke-width": 1 }, gd);
      hoverTip(c, () => `Segment ${i + 1}<br>Benchmark ${b.toFixed(2)} pp<br>Each segment ${s.nopool[i].toFixed(2)} · Multilevel ${s.bayes[i].toFixed(2)}`);
      dots.push(c);
    });
    readout();
  }
  function readout() {
    const s = S[sel];
    ro.innerHTML = `<div><div class="k">Each segment alone</div><div class="v" style="color:var(--grey)">${s.rmse.nopool.toFixed(2)} <small>pp RMSE</small></div></div>
      <div><div class="k">Multilevel model</div><div class="v" style="color:var(--navy)">${s.rmse.bayes.toFixed(2)} <small>pp RMSE</small></div></div>
      <div><div class="k">Change</div><div class="v" style="color:var(--orange)">${fmt(100 * (s.rmse.bayes / s.rmse.nopool - 1))}%</div></div>`;
  }
  function setM(m, dur = 1100) {
    mode = m; setMode(m); const s = S[sel], v = s[m];
    animate(dots.map((c, i) => [c, { cy: Y(v[i]) }]).concat(res.map((l, i) => [l, { y2: Y(v[i]) }])), dur);
    dots.forEach(c => c.setAttribute("class", (m === "bayes" ? "f-navy" : "f-grey") + " s-card"));
    res.forEach(l => l.setAttribute("class", m === "bayes" ? "s-navy" : "s-grey"));
  }
  function pick(i) { sel = i; drawSlope(); const m = mode; mode = "nopool"; drawScatter(); if (m === "bayes") setTimeout(() => setM("bayes"), 120); }
  $("#play-pool").addEventListener("click", () => { mode = "nopool"; setMode("nopool"); drawScatter(); setTimeout(() => setM("bayes", 1400), 250); });
  drawSlope(); drawScatter();
  whenVisible(hostP, () => { if (!played) { played = true; setTimeout(() => setM("bayes", 1500), 700); } });
  redrawers.push(() => { drawSlope(); const m = mode; mode = m; drawScatter(); });
})();

/* ---------- 2.1 credited vs caused ---------- */
(function gap() {
  if (!document.getElementById("c-gap")) return;
  const host = $("#c-gap"), hHost = $("#c-hundred"), lgH = $("#lg-hundred");
  let key = "conversion", parts = null;
  function build() {
    const w = W(host), h = 206, L = 12, R = w - 16, y = 104, svg = svgIn(host, w, h);
    const g = el("g", {}, svg);
    parts = { svg, w, L, R, y, ticks: el("g", {}, svg),
      band: el("rect", { x: L, y: y - 9, width: 0, height: 18, rx: 9, class: "f-osoft" }, g),
      ci: el("line", { x1: L, x2: L, y1: y, y2: y, class: "s-navy", "stroke-width": 2 }, g),
      ciA: el("line", { x1: L, x2: L, y1: y - 7, y2: y + 7, class: "s-navy", "stroke-width": 2 }, g),
      ciB: el("line", { x1: L, x2: L, y1: y - 7, y2: y + 7, class: "s-navy", "stroke-width": 2 }, g),
      caused: el("circle", { cx: L, cy: y, r: 9, class: "f-navy s-card", "stroke-width": 2 }, g),
      cred: el("rect", { x: L - 9, y: y - 9, width: 18, height: 18, transform: `rotate(45 ${L} ${y})`, class: "f-orange s-card", "stroke-width": 2 }, g),
      lCaused: txt(g, L, y + 32, "", { "text-anchor": "end", class: "t-navy" }),
      lCaused2: txt(g, L, y + 48, "", { "text-anchor": "end", class: "t-muted", "font-size": 11 }),
      lCred: txt(g, L, y + 32, "", { "text-anchor": "start", class: "t-orange" }),
      lCred2: txt(g, L, y + 48, "Credited by the count", { "text-anchor": "start", class: "t-muted", "font-size": 11 }),
      gapT: txt(g, L, y - 46, "", { "text-anchor": "middle", class: "t-strong", "font-size": 15 }),
      gapT2: txt(g, L, y - 27, "", { "text-anchor": "middle", class: "t-orange" }) };
    set(key, 0);
  }
  function set(k, dur = 900) {
    // one index scale (caused = 100) for both outcomes, so switching keeps the axis and the gaps compare by length
    key = k; const r = E[k], p = parts, x = lin(0, 185, p.L + 20, p.R), ia = 100 * r.credited / r.caused, ie = 100 * r.caused_ci / r.caused;
    p.ticks.innerHTML = "";
    [0, 50, 100, 150].forEach(v => { el("line", { x1: x(v), x2: x(v), y1: 28, y2: p.y + 58, class: "gridl" }, p.ticks); txt(p.ticks, x(v), p.y + 74, String(v), { "text-anchor": "middle", class: "t-muted", "font-size": 11 }); });
    txt(p.ticks, (x(0) + x(150)) / 2, p.y + 92, "% of caused", { "text-anchor": "middle", class: "t-muted", "font-size": 11 });
    const xc = x(100), xa = x(ia), xl = x(100 - ie), xh = x(100 + ie), mid = (xc + xa) / 2;
    const nar = p.w < 520, roomR = p.w - xa > (nar ? 70 : 135), xt = roomR ? xa - 10 : xa + 10;
    [p.lCred, p.lCred2].forEach(t => t.setAttribute("text-anchor", roomR ? "start" : "end"));
    animate([[p.band, { x: xc, width: xa - xc }], [p.ci, { x1: xl, x2: xh }], [p.ciA, { x1: xl, x2: xl }], [p.ciB, { x1: xh, x2: xh }],
      [p.caused, { cx: xc }], [p.cred, { x: xa - 9 }], [p.lCaused, { x: xc + 10 }], [p.lCaused2, { x: xc + 10 }], [p.lCred, { x: xt }], [p.lCred2, { x: xt }],
      [p.gapT, { x: mid }], [p.gapT2, { x: mid }]], dur);
    p.cred.setAttribute("transform", `rotate(45 ${xa} ${p.y})`);
    if (dur) { const from = parseFloat(p.cred.dataset.x || xa); tween(dur, t => p.cred.setAttribute("transform", `rotate(45 ${from + (xa - from) * t} ${p.y})`)); }
    p.cred.dataset.x = xa;
    p.lCaused.textContent = fmt(r.caused); p.lCaused2.textContent = nar ? "Caused" : `Caused (±${fmt(r.caused_ci)})`; p.lCred.textContent = fmt(r.credited);
    p.lCred2.textContent = nar ? "Credited" : "Credited by the count";
    p.gapT.textContent = `+${fmt(r.credited - r.caused)} ${k === "conversion" ? "conversions" : "visits"}`;
    p.gapT2.textContent = `${fmt(100 * (r.ratio - 1))}% more than caused`;
    hundred(k, dur);
  }
  let sq = [];
  function drawHundred() {
    const w = Math.min(W(hHost), 300), cell = Math.floor((w - 2) / 10), svg = svgIn(hHost, cell * 10, cell * 10);
    sq = [];
    for (let i = 0; i < 100; i++) { const c = i % 10, rr = Math.floor(i / 10);
      sq.push(el("rect", { x: c * cell + 1.5, y: rr * cell + 1.5, width: cell - 3, height: cell - 3, rx: 3, class: "sq f-pale" }, svg)); }
  }
  function hundred(k, dur) {
    const r = E[k], n = Math.round(100 * r.caused / r.credited);
    sq.forEach((s, i) => { s.style.transitionDelay = reduce ? "0ms" : `${(dur ? i * 7 : 0)}ms`; s.setAttribute("class", "sq " + (i < n ? "f-navy" : "f-osoft")); });
    lgH.innerHTML = `<span><i style="background:var(--navy)"></i>Caused by the ads <b>${n}</b></span><span><i style="background:var(--orange-soft)"></i>Would have occurred anyway <b>${100 - n}</b></span><span style="color:var(--muted)">${fmt(r.caused)} ÷ ${fmt(r.credited)}; a share of the total, not a label for each ${k === "conversion" ? "conversion" : "visit"}</span>`;
  }
  segControl($("#seg-gap"), v => set(v), key);
  drawHundred(); build();
  redrawers.push(() => { drawHundred(); build(); });
})();

/* ---------- 2.2 waffle and bidding ---------- */
(function waffle() {
  if (!document.getElementById("c-waffle")) return;
  const C = D.credit, host = $("#c-waffle"), lgW = $("#lg-waffle");
  const cats = [["last", "Last touch", "f-navy", "var(--navy)"], ["<1d", "Under 1 day earlier", "f-blue", "var(--blue)"], ["1-7d", "1 to 7 days earlier", "f-light", "var(--light)"], [">7d", "Over 7 days earlier", "f-pale", "var(--pale)"]];
  let rule = "cr_last", sq = [];
  function counts(r) { // largest remainder, so the squares sum to 100
    const v = cats.map(([k]) => C.rules[r][k]), base = v.map(Math.floor); let left = 100 - base.reduce((a, b) => a + b, 0);
    v.map((x, i) => [x - base[i], i]).sort((a, b) => b[0] - a[0]).forEach(([, i]) => { if (left-- > 0) base[i]++; });
    return base;
  }
  function draw() {
    const w = Math.min(W(host), 360), cell = Math.floor(w / 10), svg = svgIn(host, cell * 10, cell * 10); sq = [];
    for (let i = 0; i < 100; i++) { // fill column by column from the bottom left
      const c = Math.floor(i / 10), rr = 9 - (i % 10);
      const s = el("rect", { x: c * cell + 1.5, y: rr * cell + 1.5, width: cell - 3, height: cell - 3, rx: 3, class: "sq f-pale" }, svg);
      hoverTip(s, () => { const k = s.dataset.cat; const c2 = cats.find(x => x[0] === k); return `${c2[1]}: ${C.rules[rule][k].toFixed(1)}% of credit`; });
      sq.push(s);
    }
    set(rule, false);
  }
  function set(r, anim = true) {
    rule = r; const n = counts(r); let i = 0;
    cats.forEach(([k, , cls], j) => { for (let q = 0; q < n[j]; q++, i++) { const s = sq[i]; s.dataset.cat = k; s.style.transitionDelay = (anim && !reduce) ? `${i * 9}ms` : "0ms"; s.setAttribute("class", "sq " + cls); } });
    lgW.innerHTML = cats.map(([k, name, , col]) => `<span><i style="background:${col}"></i>${name} <b>${C.rules[r][k].toFixed(0)}%</b></span>`).join("");
  }
  const setRule = segControl($("#seg-rule"), v => set(v), rule);
  let cyc = null;
  $("#play-rule").addEventListener("click", e => {
    if (cyc) { clearInterval(cyc); cyc = null; e.target.textContent = "▶ Cycle"; return; }
    const order = ["cr_last", "cr_decay", "cr_linear", "cr_first"]; let j = order.indexOf(rule);
    e.target.textContent = "■ Stop";
    const stepR = () => { j = (j + 1) % 4; setRule(order[j]); set(order[j]); };
    stepR(); cyc = setInterval(stepR, 2200);
  });
  draw(); redrawers.push(draw);
  whenVisible(host, () => setTimeout(() => { if (rule === "cr_last" && !cyc) { setRule("cr_decay"); set("cr_decay"); } }, 1200));

  /* bidding */
  if (!document.getElementById("c-bid")) return;
  const hb = $("#c-bid"); let budget = "0.5", P = null;
  function drawBid() {
    const w = W(hb), h = 230, L = Math.min(132, w * .38), R = w - 18, svg = svgIn(hb, w, h);
    txt(svg, 0, 22, "Spend overlap", { class: "t-strong" });
    el("rect", { x: L, y: 10, width: R - L, height: 16, rx: 8, class: "f-pale" }, svg);
    const ov = el("rect", { x: L, y: 10, width: 0, height: 16, rx: 8, class: "f-navy" }, svg);
    const ovT = txt(svg, w < 520 ? 0 : L, 46, "", { class: "t-navy", "font-size": 13 });
    const x = lin(-1, 8, L, R), y0 = 92;
    txt(svg, 0, y0 - 14, "Credit lost", { class: "t-strong" });
    [0, 2, 4, 6, 8].forEach(v => { el("line", { x1: x(v), x2: x(v), y1: y0, y2: y0 + 96, class: v === 0 ? "axis" : "gridl" }, svg); txt(svg, x(v), y0 + 112, v + "%", { "text-anchor": "middle", class: "t-muted", "font-size": 11 }); });
    el("line", { x1: x(5), x2: x(5), y1: y0 - 4, y2: y0 + 96, class: "s-orange", "stroke-width": 1.5, "stroke-dasharray": "5 4" }, svg);
    const fit = x(5) + 100 < w; txt(svg, fit ? x(5) + 5 : x(5) - 5, y0 + 4, "pre-specified 5%", { class: "t-orange halo", "font-size": 11, "text-anchor": fit ? "start" : "end" });
    const rowsB = [["cr_last", "Scored by last touch"], ["cr_decay", "Scored by time decay"]].map(([k, name], i) => {
      const yy = y0 + 30 + i * 40; txt(svg, 0, yy + 4, name, { "font-size": 12 });
      const ln = el("line", { x1: x(0), x2: x(0), y1: yy, y2: yy, class: "s-navy", "stroke-width": 2.2 }, svg);
      const c = el("circle", { cx: x(0), cy: yy, r: 6, class: "f-navy s-card", "stroke-width": 2 }, svg);
      const t = txt(svg, x(0), yy - 11, "", { "text-anchor": "middle", class: "t-navy", "font-size": 12 });
      return { k, ln, c, t };
    });
    P = { ov, ovT, L, R, x, rowsB };
    setB(budget, 0);
  }
  function setB(b, dur = 800) {
    budget = b; const v = C.budgets[b];
    animate([[P.ov, { width: (P.R - P.L) * v.overlap / 100 }]], dur);
    countTo(P.ovT, v.overlap, dur, 1, "% of spend on the same impressions");
    P.rowsB.forEach(r => { const [m, lo, hi] = v.loss[r.k];
      animate([[r.ln, { x1: P.x(lo), x2: P.x(hi) }], [r.c, { cx: P.x(m) }], [r.t, { x: P.x(m) }]], dur);
      r.t.textContent = (m > 0 ? "" : "") + m.toFixed(1) + "%"; });
  }
  segControl($("#seg-budget"), v => setB(v), budget);
  drawBid(); redrawers.push(drawBid);
})();

/* ---------- 2.3 marketing mix ---------- */
(function mmm() {
  if (!document.getElementById("c-mmm")) return;
  const M = D.mmm, host = $("#c-mmm"), hs = $("#c-share");
  function draw(anim) {
    const w = W(host), h = 330, L = 46, B = h - 44, R = w - 10, svg = svgIn(host, w, h);
    const x = lg(0.03, 60, L, R), y = lg(0.6, 4000, B, 10);
    el("rect", { x: x(2), y: 10, width: R - x(2), height: B - 10, class: "f-pale", opacity: .55 }, svg);
    gridY(svg, y, [1, 10, 100, 1000], L, R, v => fmt(v));
    axisX(svg, x, [0.1, 1, 2, 10], B, v => String(v), "Signal-to-noise index (log scale)");
    txt(svg, L - 40, 2, "Error of estimated ROAS (%)", { class: "t-muted" });
    el("line", { x1: x(2), x2: x(2), y1: 6, y2: B, class: "s-orange", "stroke-width": 1.6, "stroke-dasharray": "5 4" }, svg);
    txt(svg, x(2) + 6, 22, "index = 2", { class: "t-orange", "font-size": 11 });
    const gm = el("g", {}, svg);
    [[0.03, 2, M.median_below, "s-grey", "t-muted"], [2, 60, M.median_above, "s-navy", "t-navy"]].forEach(([a, b, m, sc, tc]) => {
      el("line", { x1: x(a) + 2, x2: x(b) - 2, y1: y(m), y2: y(m), class: sc, "stroke-width": 1.6, "stroke-dasharray": "6 3" }, gm);
      txt(gm, a < 1 ? x(a) + 6 : x(b) - 6, y(m) - 7, `median ${fmt(m)}%`, { class: tc + " halo", "text-anchor": a < 1 ? "start" : "end", "font-size": 12 });
    });
    const pts = M.points.slice().sort((p, q) => p.index - q.index);
    pts.forEach((p, i) => {
      const xi = Math.max(p.index, 0.035), above = p.index >= 2;
      const c = el("circle", { cx: x(xi), cy: anim ? B : y(Math.max(p.error, 0.7)), r: 5, class: (above ? "f-navy" : "f-grey") + " s-card hot", "stroke-width": 1.2, opacity: anim ? 0 : 1 }, svg);
      hoverTip(c, `${p.channel === "google" ? "Google" : p.channel === "meta" ? "Meta" : p.channel} channel<br>Index ${p.index.toFixed(2)} · error ${fmt(p.error)}%`);
      if (anim) whenVisible(host, () => setTimeout(() => animate([[c, { cy: y(Math.max(p.error, 0.7)), opacity: 1 }]], 700), i * 18));
    });
    svg.appendChild(gm); // median lines and labels above the points
  }
  function drawShare(anim) {
    const w = W(hs), h = 200, L = 92, R = w - 52, svg = svgIn(hs, w, h);
    txt(svg, 0, 18, "Brand-channels with an index of 2 or more", { class: "t-strong" });
    [["W", "Weekly data", "f-grey"], ["D", "Daily data", "f-navy"]].forEach(([k, name, cls], i) => {
      const yy = 56 + i * 58, v = M.share[k].share;
      txt(svg, 0, yy + 18, name, {});
      el("rect", { x: L, y: yy, width: R - L, height: 28, rx: 6, class: "f-pale", opacity: .6 }, svg);
      const b = el("rect", { x: L, y: yy, width: anim ? 0 : (R - L) * v / 100, height: 28, rx: 6, class: cls }, svg);
      const t = txt(svg, R + 8, yy + 19, anim ? "0%" : fmt(v) + "%", { class: "t-strong", "font-size": 15 });
      txt(svg, L, yy + 44, `of ${M.share[k].n} brand-channels`, { class: "t-muted", "font-size": 11 });
      if (anim) whenVisible(hs, () => setTimeout(() => { animate([[b, { width: (R - L) * v / 100 }]], 1000); countTo(t, v, 1000, 0, "%"); }, 200 + i * 300));
    });
  }
  draw(true); drawShare(true); redrawers.push(() => { draw(false); drawShare(false); });
})();

/* ---------- 3.1 sample size ---------- */
(function size() {
  if (!document.getElementById("c-size")) return;
  const Z = D.sizing, host = $("#c-size"), sh = $("#seg-lift");
  Z.lifts.forEach((l, i) => { const b = document.createElement("button"); b.type = "button"; b.dataset.v = i; b.textContent = l + "%"; sh.appendChild(b); });
  let li = 1, P;
  function draw() {
    const w = W(host), nar = w < 520, h = nar ? 200 : 176, L = nar ? 0 : 112, R = nar ? w - 12 : w - 120, svg = svgIn(host, w, h);
    P = { L, R, nar, ticks: el("g", {}, svg), bars: {}, labels: {} };
    [["visit", "Visits", "f-grey"], ["conversion", "Conversions", "f-navy"]].forEach(([k, name, cls], i) => {
      const yy = (nar ? 44 : 20) + i * 62;
      txt(svg, 0, nar ? yy - 8 : yy + 22, name, { class: "t-strong" });
      P.bars[k] = el("rect", { x: L, y: yy, width: 0, height: 34, rx: 6, class: cls }, svg);
      P.labels[k] = txt(svg, L + 8, yy + 23, "0", { class: "t-strong", "font-size": 15 });
    });
    P.ratio = txt(svg, nar ? w - 4 : R + 60, nar ? 18 : 72, "", { "text-anchor": nar ? "end" : "middle", class: "t-orange", "font-size": nar ? 18 : 22 });
    P.ratio2 = txt(svg, R + 60, 92, nar ? "" : "as many users", { "text-anchor": "middle", class: "t-muted", "font-size": 11 });
    set(li, 0);
  }
  function set(i, dur = 800) {
    li = i; const v = Z.users.visit[i], c = Z.users.conversion[i], top = c * 1.02, x = lin(0, top, P.L, P.R);
    P.ticks.innerHTML = "";
    const step = Math.pow(10, Math.floor(Math.log10(top / 3))) * (top / Math.pow(10, Math.floor(Math.log10(top / 3))) > 15 ? 5 : 2);
    const tb = P.nar ? 164 : 140;
    for (let t = 0; t <= top; t += step * (P.nar ? 2 : 1)) { el("line", { x1: x(t), x2: x(t), y1: P.nar ? 34 : 10, y2: tb, class: "gridl" }, P.ticks); txt(P.ticks, x(t), tb + 20, t >= 1e6 ? (t / 1e6) + "M" : t >= 1e3 ? (t / 1e3) + "k" : String(t), { "text-anchor": "middle", class: "t-muted", "font-size": 11 }); }
    const wv = Math.max(4, x(v) - P.L), wc = x(c) - P.L;
    animate([[P.bars.visit, { width: wv }], [P.bars.conversion, { width: wc }], [P.labels.visit, { x: P.L + wv + 8 }], [P.labels.conversion, { x: P.L + wc - 8 }]], dur);
    P.labels.conversion.setAttribute("text-anchor", "end"); P.labels.conversion.setAttribute("class", "t-on"); P.labels.conversion.style.fontWeight = 650;
    countTo(P.labels.visit, v, dur, 0, " per arm"); countTo(P.labels.conversion, c, dur, 0, " per arm");
    if (P.nar) P.ratio.innerHTML = `×${(c / v).toFixed(1)}<tspan class="t-muted" font-size="11" font-weight="400"> as many users</tspan>`; else P.ratio.textContent = "×" + (c / v).toFixed(1);
  }
  segControl(sh, v => set(+v), li); draw(); redrawers.push(draw);
})();

/* ---------- 3.2 covariate adjustment ---------- */
(function cov() {
  if (!document.getElementById("c-cov")) return;
  const O = D.sizing.one_point, host = $("#c-cov");
  function draw(anim) {
    const w = W(host), h = 196, L = 4, R = w - 4, svg = svgIn(host, w, h);
    const items = [["D", "Unadjusted", "f-grey"], ["L", "Adjusted, 12 features", "f-blue"], ["M", "Adjusted, model prediction", "f-navy"]];
    const x = lin(0, O.D * 1.0, L, R - 4);
    items.forEach(([k, name, cls], i) => {
      const yy = 10 + i * 62, v = O[k];
      txt(svg, L, yy + 12, name, { "font-size": 12.5 });
      el("rect", { x: L, y: yy + 20, width: x(O.D) - L, height: 22, rx: 5, class: "f-pale", opacity: .5 }, svg);
      const b = el("rect", { x: L, y: yy + 20, width: anim ? 0 : x(v) - L, height: 22, rx: 5, class: cls }, svg);
      const t = txt(svg, x(v) - 8, yy + 36, fmt(v), { "text-anchor": "end", "font-size": 13, class: "t-on", style: "font-weight:650" });
      if (k !== "D") txt(svg, R, yy + 12, `${fmt(100 * (v / O.D - 1))}% users`, { "text-anchor": "end", class: "t-orange", "font-size": 12.5 });
      if (anim) { t.setAttribute("opacity", 0); whenVisible(host, () => setTimeout(() => animate([[b, { width: x(v) - L }], [t, { opacity: 1 }]], 900), i * 220)); }
    });
  }
  draw(true); redrawers.push(() => draw(false));
})();

/* ---------- 3.3 geo grid ---------- */
(function geo() {
  if (!document.getElementById("c-geo")) return;
  const Z = D.sizing, host = $("#c-geo"), ro = $("#c-geo-ro");
  let est = "adjusted", cell = "100|2", cells = {};
  const names = Object.fromEntries([...document.querySelectorAll("#seg-geo button")].map(b => [b.dataset.v, b.textContent]));
  const all = Object.keys(names).flatMap(k => Object.values(Z.geo[k])), lo = Math.min(...all), hi = Math.max(...all);
  const shade = v => { const t = (Math.log(v) - Math.log(lo)) / (Math.log(hi) - Math.log(lo)); return t; };
  function color(v) { // darker = smaller detectable effect
    const t = shade(v), dark = document.documentElement.dataset.theme === "dark" || (!document.documentElement.dataset.theme && matchMedia("(prefers-color-scheme: dark)").matches);
    const a = dark ? [143, 180, 224] : [31, 59, 92], b = dark ? [44, 58, 75] : [223, 230, 238];
    return `rgb(${a.map((c, i) => Math.round(c + (b[i] - c) * t)).join(",")})`;
  }
  function draw() {
    const w = W(host), L = 64, T = 26, cw = (w - L) / 4, ch = 46, svg = svgIn(host, w, T + 3 * ch + 30); cells = {};
    txt(svg, L + (w - L) / 2, 12, "Metros in the test", { "text-anchor": "middle", class: "t-muted", "font-size": 11 });
    Z.metros.forEach((m, i) => txt(svg, L + cw * i + cw / 2, T + 3 * ch + 18, m, { "text-anchor": "middle", class: "t-ink" }));
    Z.months.forEach((mo, j) => txt(svg, L - 10, T + ch * j + ch / 2 + 4, mo + (mo === 1 ? " month" : " months"), { "text-anchor": "end", class: "t-ink", "font-size": 11.5 }));
    Z.metros.forEach((m, i) => Z.months.forEach((mo, j) => {
      const key = `${m}|${mo}`, g = el("g", { class: "hot" }, svg);
      const r = el("rect", { x: L + cw * i + 2, y: T + ch * j + 2, width: cw - 4, height: ch - 4, rx: 7, style: `fill:${color(Z.geo[est][key])};transition:fill .5s` }, g);
      const t = txt(g, L + cw * i + cw / 2, T + ch * j + ch / 2 + 5, Z.geo[est][key].toFixed(1) + "%", { "text-anchor": "middle", "font-size": 14, style: "font-weight:650" });
      const ring = el("rect", { x: L + cw * i + 0.5, y: T + ch * j + 0.5, width: cw - 1, height: ch - 1, rx: 8, fill: "none", class: "s-orange", "stroke-width": 2.5, opacity: key === cell ? 1 : 0 }, g);
      g.addEventListener("click", () => { cell = key; refresh(); });
      hoverTip(g, () => `${m} metros, ${mo} month${mo > 1 ? "s" : ""}<br>${names[est]}: ${Z.geo[est][key].toFixed(1)}%`);
      cells[key] = { r, t, ring };
    }));
    refresh();
  }
  function refresh() {
    for (const k in cells) { const v = Z.geo[est][k], c = cells[k]; c.r.style.fill = color(v); c.t.textContent = v.toFixed(1) + "%";
      c.t.style.fill = shade(v) < .5 ? "var(--on)" : "var(--ink)"; c.ring.setAttribute("opacity", k === cell ? 1 : 0); }
    const [m, mo] = cell.split("|"), mx = Math.max(...Object.keys(names).map(e => Z.geo[e][cell]));
    ro.innerHTML = `<div class="legend" style="margin-top:6px"><span>${m} metros, ${mo} month${mo > 1 ? "s" : ""}:</span>` +
      Object.keys(names).map(e => `<span style="${e === est ? "color:var(--ink);font-weight:650" : ""}">${names[e]} <b>${Z.geo[e][cell].toFixed(1)}%</b></span>`).join("") + "</div>";
  }
  segControl($("#seg-geo"), v => { est = v; refresh(); }, est);
  draw(); redrawers.push(draw);
})();

/* ---------- 4.1 new customers ---------- */
(function newCust() {
  if (!document.getElementById("c-timeline")) return;
  const Cu = D.customers, ht = $("#c-timeline"), hb = $("#c-newbar");
  let open = false, P;
  const months = 18; // Dec 2009 to May 2011
  function draw() {
    const w = W(ht), nar = w < 620, h = nar ? 122 : 104, L = 4, R = w - 4, x = lin(0, months, L, R), svg = svgIn(ht, w, h);
    const band = (a, b, cls, label, sub, y, sy, anchor) => { const g = el("g", {}, svg);
      el("rect", { x: x(a) + 1, y, width: x(b) - x(a) - 2, height: 30, rx: 6, class: cls }, g);
      txt(g, x(a) + 8, y + 19, label, { "font-size": 12, class: "t-on", style: "font-weight:600" });
      const sx = anchor === "end" ? x(b) - 2 : anchor === "start" ? x(a) + 2 : (x(a) + x(b)) / 2;
      txt(g, sx, y + sy, sub, { class: "t-muted", "font-size": 10.5, "text-anchor": anchor }); return g; };
    const look = band(0, 12, "f-orange", nar ? "12 months earlier" : "Look further back: 12 months", "Dec 2009–Nov 2010", 16, 46, nar ? "start" : "middle");
    band(12, 15, "f-grey", nar ? "None" : "No purchase", "Dec 2010–Feb 2011", 16, 46, nar ? "end" : "middle");
    band(15, 18, "f-navy", nar ? "Buy" : "Purchase", "Mar–May 2011", 16, nar ? 62 : 46, nar ? "end" : "middle");
    look.setAttribute("class", "fade"); look.style.opacity = open ? 1 : .12;
    P = { look };
  }
  function drawBar(anim) {
    const w = W(hb), nar = w < 620, h = nar ? 136 : 120, L = 4, R = w - 4, svg = svgIn(hb, w, h), n = Cu.labeled_new, old = Cu.bought_before, x = lin(0, n, L, R);
    const t0 = txt(svg, L, 20, "", { class: "t-strong", "font-size": 15 });
    const bNew = el("rect", { x: L, y: 34, width: R - L, height: 40, rx: 8, class: "f-navy" }, svg);
    const bOld = el("rect", { x: R, y: 34, width: 0, height: 40, rx: 8, class: "f-orange" }, svg);
    const tNew = txt(svg, L + 12, 59, "", { class: "t-on", style: "font-weight:650", "font-size": 14 });
    const tOld = txt(svg, R - 12, 59, "", { "text-anchor": "end", class: "t-on", style: "font-weight:650", "font-size": 14, opacity: 0 });
    const lNew = txt(svg, L, 96, "", { class: "t-navy", "font-size": 12.5 });
    const lOld = txt(svg, R, nar ? 116 : 96, "", { "text-anchor": "end", class: "t-orange", "font-size": 12.5, opacity: 0 });
    P.bar = { t0, bNew, bOld, tNew, tOld, lNew, lOld, x, L, R, n, old };
    state(open, anim ? 900 : 0);
  }
  function state(o, dur = 900) {
    open = o; const b = P.bar, split = b.x(b.n - b.old);
    P.look.style.opacity = o ? 1 : .12;
    if (o) {
      animate([[b.bNew, { width: split - b.L - 2 }], [b.bOld, { x: split + 2, width: b.R - split - 2 }], [b.tOld, { opacity: 1 }], [b.lOld, { opacity: 1 }]], dur);
      b.t0.textContent = `${fmt(b.old)} of ${fmt(b.n)} had bought in the 12 months before`;
      countTo(b.tNew, b.n - b.old, dur); b.tOld.textContent = fmt(b.old);
      b.lNew.textContent = `No purchase in the prior 12 months (${fmt(100 * (b.n - b.old) / b.n, 1)}%)`;
      b.lOld.textContent = `Bought in the prior 12 months (${fmt(100 * b.old / b.n, 1)}%)`;
    } else {
      animate([[b.bNew, { width: b.R - b.L }], [b.bOld, { x: b.R, width: 0 }], [b.tOld, { opacity: 0 }], [b.lOld, { opacity: 0 }]], dur);
      b.t0.textContent = `${fmt(b.n)} accounts labeled new`; countTo(b.tNew, b.n, dur); b.lNew.textContent = "Labeled new under a 3-month look-back";
    }
  }
  $("#btn-look").addEventListener("click", () => state(true));
  $("#btn-reset").addEventListener("click", () => state(false));
  draw(); drawBar(false);
  redrawers.push(() => { draw(); drawBar(false); });
})();

/* ---------- 4.2 cohorts ---------- */
(function cohorts() {
  if (!document.getElementById("c-heat")) return;
  const Co = D.customers.cohorts, hh = $("#c-heat"), hc = $("#c-curve");
  let sel = Co.findIndex(c => c.month === "2011-03"); if (sel < 0) sel = 0;
  const top = Math.max(...Co.flatMap(c => c.rates.filter(v => v !== null)));
  function draw() {
    const w = W(hh), L = Math.min(118, w * .3), T = 6, cw = (w - L) / 11, ch = Math.max(26, Math.min(34, cw * .9)), svg = svgIn(hh, w, T + Co.length * ch + 40);
    const defs = el("defs", {}, svg), pat = el("pattern", { id: "hatch", width: 6, height: 6, patternUnits: "userSpaceOnUse", patternTransform: "rotate(45)" }, defs);
    el("line", { x1: 0, y1: 0, x2: 0, y2: 6, class: "gridl", "stroke-width": 3 }, pat);
    Co.forEach((c, i) => {
      const g = el("g", { class: "hot" }, svg), y = T + i * ch;
      el("rect", { x: 0, y: y + 1, width: w, height: ch - 2, rx: 6, class: "f-osoft", opacity: i === sel ? .9 : 0 }, g);
      txt(g, 6, y + ch / 2 + 4, c.month, { class: i === sel ? "t-strong" : "t-ink", "font-size": 12 });
      if (L > 100) txt(g, L - 8, y + ch / 2 + 4, `n=${c.size}`, { "text-anchor": "end", class: "t-muted", "font-size": 11 });
      c.rates.forEach((v, k) => {
        const x = L + k * cw;
        if (v === null) { el("rect", { x: x + 1, y: y + 2, width: cw - 2, height: ch - 4, rx: 4, fill: "url(#hatch)" }, g); return; }
        const t = v / top, cell = el("rect", { x: x + 1, y: y + 2, width: cw - 2, height: ch - 4, rx: 4, style: `fill:var(--navy);fill-opacity:${(0.12 + 0.88 * t).toFixed(3)}` }, g);
        if (cw > 26) txt(g, x + cw / 2, y + ch / 2 + 4, v.toFixed(0), { "text-anchor": "middle", "font-size": 11, style: t > .55 ? "fill:var(--card);font-weight:600" : "fill:var(--ink)" });
        hoverTip(cell, `Cohort ${c.month} (n=${c.size})<br>Month ${k + 1}: ${v.toFixed(1)}% bought again`);
      });
      g.addEventListener("click", () => { sel = i; draw(); curve(true); });
    });
    for (let k = 0; k < 11; k++) txt(svg, L + k * cw + cw / 2, T + Co.length * ch + 16, k + 1, { "text-anchor": "middle", class: "t-muted", "font-size": 11 });
    txt(svg, L + (w - L) / 2, T + Co.length * ch + 34, "Months since first purchase", { "text-anchor": "middle", class: "t-muted", "font-size": 11 });
  }
  function curve(anim) {
    const w = W(hc), h = 190, L = 40, R = w - 70, B = h - 30, svg = svgIn(hc, w, h);
    const x = lin(1, 11, L, R), y = lin(0, 30, B, 12);
    gridY(svg, y, [0, 10, 20, 30], L, R, v => v + "%");
    for (let k = 1; k <= 11; k += 2) txt(svg, x(k), B + 18, k, { "text-anchor": "middle", class: "t-muted", "font-size": 11 });
    const path = c => c.rates.map((v, k) => v === null ? null : [x(k + 1), y(v)]).filter(Boolean).map((p, i) => (i ? "L" : "M") + p.join(",")).join("");
    Co.forEach((c, i) => { if (i !== sel) el("path", { d: path(c), fill: "none", class: "s-grey", "stroke-width": 1, opacity: .45 }, svg); });
    const c = Co[sel], p = el("path", { d: path(c), fill: "none", class: "s-orange", "stroke-width": 2.6, "stroke-linejoin": "round" }, svg);
    c.rates.forEach((v, k) => { if (v !== null) el("circle", { cx: x(k + 1), cy: y(v), r: 3.4, class: "f-orange" }, svg); });
    const last = c.rates.map((v, k) => [v, k]).filter(([v]) => v !== null).pop();
    txt(svg, x(last[1] + 1) + 8, y(last[0]) + 4, `${c.month}`, { class: "t-orange", "font-size": 12 });
    txt(svg, R + 8, y(4) , "other cohorts", { class: "t-muted", "font-size": 11 });
    if (anim && !reduce) { const len = p.getTotalLength(); p.style.strokeDasharray = len; p.style.strokeDashoffset = len; tween(800, t => p.style.strokeDashoffset = len * (1 - t)); }
  }
  draw(); curve(false); redrawers.push(() => { draw(); curve(false); });
})();

/* ================= study pages ================= */
const S1 = D.s01, S2 = D.s02, S3 = D.s03, S4 = D.s04;
function makeSeg(host, items, init, fn) {
  host.innerHTML = ""; host.classList.add("seg");
  items.forEach(([v, l]) => { const b = document.createElement("button"); b.type = "button"; b.dataset.v = v; b.textContent = l; host.appendChild(b); });
  return segControl(host, fn, init);
}
const has = id => document.getElementById(id);
const pp = (v, d = 2) => (v > 0 ? "+" : "") + v.toFixed(d);
/* horizontal rows of point estimates with intervals; returns an updater */
function dotRows(host, opt) {
  const st = { rows: opt.rows, dom: opt.dom, ticks: opt.ticks || [], refs: opt.refs || [] };
  function draw() {
    const w = W(host), L = Math.min(opt.label || 170, w * .44), R = w - (opt.right || 52), rh = opt.rh || 40, top = 8, h = top + st.rows.length * rh + 34, svg = svgIn(host, w, h);
    const x = lin(st.dom[0], st.dom[1], L, R), g = el("g", {}, svg);
    st.ticks.forEach(t => { el("line", { x1: x(t), x2: x(t), y1: top, y2: h - 30, class: t === 0 ? "axis" : "gridl" }, g); txt(g, x(t), h - 12, opt.fmtT ? opt.fmtT(t) : t, { "text-anchor": "middle", class: "t-muted", "font-size": 11 }); });
    if (opt.band) el("rect", { x: x(opt.band[0]), y: top, width: x(opt.band[1]) - x(opt.band[0]), height: h - 30 - top, class: "f-pale", opacity: .55 }, g);
    st.refs.forEach(rf => { el("line", { x1: x(rf.v), x2: x(rf.v), y1: top - 2, y2: h - 30, class: rf.cls || "s-orange", "stroke-width": 1.5, "stroke-dasharray": "5 4" }, g);
      if (rf.label) txt(g, x(rf.v) + 5, top + 10, rf.label, { class: (rf.tcls || "t-orange") + " halo", "font-size": 11 }); });
    st.items = st.rows.map((r, i) => {
      const y = top + i * rh + rh / 2, gg = el("g", { class: "hot" }, svg);
      txt(gg, 0, y + 4, r.label, { class: r.strong ? "t-strong" : "t-ink", "font-size": 12.5 });
      const ln = el("line", { x1: x(r.lo), x2: x(r.hi), y1: y, y2: y, class: r.scls || "s-navy", "stroke-width": 2.4, "stroke-linecap": "round" }, gg);
      const c = el("circle", { cx: x(r.v), cy: y, r: 6.5, class: (r.fcls || "f-navy") + " s-card", "stroke-width": 2 }, gg);
      const t = txt(gg, x(r.hi) + 8, y + 4, r.text, { class: "t-strong", "font-size": 12.5 });
      if (r.tip) hoverTip(gg, r.tip);
      return { ln, c, t };
    });
    st.x = x;
  }
  draw(); redrawers.push(draw);
  return { update(rows, dom, ticks, refs, dur = 700) {
    const old = st.items && st.items.length === rows.length ? st.items.map(it => ({ x1: +it.ln.getAttribute("x1"), x2: +it.ln.getAttribute("x2"), cx: +it.c.getAttribute("cx"), tx: +it.t.getAttribute("x") })) : null;
    st.rows = rows; st.dom = dom; if (ticks) st.ticks = ticks; if (refs) st.refs = refs; draw();
    if (!old) return;
    const items = st.items, to = items.map(it => ({ x1: +it.ln.getAttribute("x1"), x2: +it.ln.getAttribute("x2"), cx: +it.c.getAttribute("cx"), tx: +it.t.getAttribute("x") }));
    items.forEach((it, i) => { it.ln.setAttribute("x1", old[i].x1); it.ln.setAttribute("x2", old[i].x2); it.c.setAttribute("cx", old[i].cx); it.t.setAttribute("x", old[i].tx); });
    animate(items.flatMap((it, i) => [[it.ln, { x1: to[i].x1, x2: to[i].x2 }], [it.c, { cx: to[i].cx }], [it.t, { x: to[i].tx }]]), dur);
  } };
}

/* ---------- 01a ---------- */
if (has("c-01a-eff")) (function () {
  const rowsFor = k => { const e = S1.effects[k]; return [
    { label: "Unadjusted", v: e.itt[0], lo: e.itt[0] - e.itt[1], hi: e.itt[0] + e.itt[1], text: `${pp(e.itt[0], k === "visit" ? 2 : 3)} pp` },
    { label: "Regression-adjusted", v: e.adj[0], lo: e.adj[0] - e.adj[1], hi: e.adj[0] + e.adj[1], text: `${pp(e.adj[0], k === "visit" ? 2 : 3)} pp`, fcls: "f-blue", scls: "s-blue" }]; };
  const dom = { visit: [0, 1.3], conversion: [0, 0.15] };
  const ticks = { visit: [0, .25, .5, .75, 1, 1.25], conversion: [0, .05, .1, .15] };
  let key = "visit";
  const chart = dotRows(has("c-01a-eff"), { rows: rowsFor(key), dom: dom[key], ticks: ticks[key], label: 150, rh: 44, fmtT: v => v + " pp" });
  makeSeg(has("seg-01a-eff"), [["visit", "Visits"], ["conversion", "Conversions"]], key, v => { key = v; chart.update(rowsFor(v), dom[v], ticks[v]); });
})();

if (has("c-01a-dec")) (function () {
  const host = has("c-01a-dec"), Dd = S1.deciles; let zoom = false, cur = [-1.5, 7.5];
  let P;
  function draw() {
    const w = W(host), h = 300, L = 46, R = w - 16, T = 14, B = h - 40, svg = svgIn(host, w, h);
    const x = lin(0.5, 10.5, L, R);
    P = { svg, w, L, R, T, B, x, gGrid: el("g", {}, svg), band: el("path", { class: "f-navy", opacity: .14 }, svg), zero: el("line", { x1: L, x2: R, class: "axis" }, svg),
      avg: el("line", { x1: L, x2: R, class: "s-grey", "stroke-dasharray": "5 4", "stroke-width": 1.3 }, svg),
      real: el("path", { fill: "none", class: "s-navy", "stroke-width": 2.4 }, svg), pred: el("path", { fill: "none", class: "s-orange", "stroke-width": 1.8, "stroke-dasharray": "1 0" }, svg),
      dotsR: Dd.map(() => el("circle", { r: 4.5, class: "f-navy s-card", "stroke-width": 1.5 }, svg)), dotsP: Dd.map(() => el("circle", { r: 3.5, class: "f-orange" }, svg)),
      note: el("g", {}, svg), cursor: el("line", { y1: T, y2: B, class: "s-grey", opacity: 0 }, svg) };
    Dd.forEach(d => txt(svg, x(d.d), B + 18, d.d, { "text-anchor": "middle", class: "t-muted", "font-size": 11 }));
    txt(svg, (L + R) / 2, B + 34, "Decile of predicted uplift (1 = highest)", { "text-anchor": "middle", class: "t-muted", "font-size": 11 });
    txt(svg, L - 40, 6, "Effect on visit rate (pp)", { class: "t-muted", "font-size": 11 });
    const hit = el("rect", { x: L, y: T, width: R - L, height: B - T, fill: "transparent" }, svg);
    hit.addEventListener("pointermove", e => { const b = svg.getBoundingClientRect(), dx = e.clientX - b.left; const d = Math.max(1, Math.min(10, Math.round((dx - L) / (R - L) * 10 + 0.5)));
      P.cursor.setAttribute("x1", x(d)); P.cursor.setAttribute("x2", x(d)); P.cursor.setAttribute("opacity", .6);
      const r = Dd[d - 1]; tip.innerHTML = `Decile ${d}<br>Realized ${pp(r.real)} pp (±${r.ci.toFixed(2)})<br>Predicted ${pp(r.pred)} pp`; tip.classList.add("on");
      tip.style.left = Math.min(e.clientX + 14, innerWidth - tip.offsetWidth - 8) + "px"; tip.style.top = (e.clientY + 14) + "px"; });
    hit.addEventListener("pointerleave", () => { tip.classList.remove("on"); P.cursor.setAttribute("opacity", 0); });
    place(cur);
  }
  function place(dm) {
    const { x, T, B, L, R } = P, y = lin(dm[0], dm[1], B, T), cl = v => Math.max(T - 6, Math.min(B + 6, y(v)));
    P.gGrid.innerHTML = "";
    const step = dm[1] - dm[0] > 4 ? 2 : 0.5;
    for (let v = Math.ceil(dm[0] / step) * step; v <= dm[1] + 1e-9; v += step) { el("line", { x1: L, x2: R, y1: y(v), y2: y(v), class: "gridl" }, P.gGrid); txt(P.gGrid, L - 8, y(v) + 4, (+v.toFixed(1)).toString(), { "text-anchor": "end", class: "t-muted", "font-size": 11 }); }
    P.zero.setAttribute("y1", y(0)); P.zero.setAttribute("y2", y(0)); P.avg.setAttribute("y1", y(S1.overall)); P.avg.setAttribute("y2", y(S1.overall));
    const top = Dd.map(d => [x(d.d), cl(d.real + d.ci)]), bot = Dd.map(d => [x(d.d), cl(d.real - d.ci)]).reverse();
    P.band.setAttribute("d", "M" + top.concat(bot).map(p => p.join(",")).join("L") + "Z");
    P.real.setAttribute("d", "M" + Dd.map(d => [x(d.d), cl(d.real)].join(",")).join("L"));
    P.pred.setAttribute("d", "M" + Dd.map(d => [x(d.d), cl(d.pred)].join(",")).join("L"));
    Dd.forEach((d, i) => { P.dotsR[i].setAttribute("cx", x(d.d)); P.dotsR[i].setAttribute("cy", cl(d.real)); P.dotsP[i].setAttribute("cx", x(d.d)); P.dotsP[i].setAttribute("cy", cl(d.pred));
      P.dotsR[i].setAttribute("opacity", y(d.real) < T - 4 ? 0 : 1); P.dotsP[i].setAttribute("opacity", y(d.pred) < T - 4 ? 0 : 1); });
    P.note.innerHTML = "";
    if (dm[1] < 3) { const d = Dd[9];
      el("line", { x1: x(10), x2: x(10), y1: y(d.pred), y2: y(d.real), class: "s-orange", "stroke-dasharray": "2 3" }, P.note);
      txt(P.note, x(10) - 10, y(d.real) - 12, `Decile 10: realized ${pp(d.real)}`, { "text-anchor": "end", class: "t-navy halo", "font-size": 11.5 });
      txt(P.note, x(10) - 10, y(d.pred) + 16, `predicted ${pp(d.pred)}`, { "text-anchor": "end", class: "t-orange halo", "font-size": 11.5 }); }
    else txt(P.note, x(1) + 12, y(Dd[0].real) + 4, `Decile 1: ${pp(Dd[0].real)} pp`, { class: "t-navy halo", "font-size": 11.5 });
  }
  function setZoom(z) { const to = z ? [-1.2, 1.6] : [-1.5, 7.5], from = cur.slice(); zoom = z;
    tween(800, t => { cur = [from[0] + (to[0] - from[0]) * t, from[1] + (to[1] - from[1]) * t]; place(cur); }); }
  makeSeg(has("seg-01a-dec"), [["all", "All deciles"], ["zoom", "Zoom on deciles 2–10"]], "all", v => setZoom(v === "zoom"));
  draw(); redrawers.push(draw);
})();

if (has("c-01a-qini")) (function () {
  const q = S1.qini.slice().sort((a, b) => b.qini - a.qini);
  dotRows(has("c-01a-qini"), { rows: q.map(m => ({ label: m.label, v: m.qini, lo: m.lo, hi: m.hi, text: m.qini.toFixed(1), strong: m.model === "t_learner" || m.model === "response",
      fcls: m.model === "t_learner" ? "f-navy" : m.model === "response" ? "f-orange" : "f-grey", scls: m.model === "t_learner" ? "s-navy" : m.model === "response" ? "s-orange" : "s-grey",
      tip: `${m.label}<br>Qini ${m.qini.toFixed(1)} (95% CI ${m.lo.toFixed(1)} to ${m.hi.toFixed(1)})<br>Top 20% of users hold ${m.top20}% of the extra visits` })),
    dom: [-2, 36], ticks: [0, 10, 20, 30], label: 160, rh: 34 });
})();

/* ---------- 01c ---------- */
if (has("c-01c-checks")) (function () {
  const host = has("c-01c-checks"), info = { "exposed without visit": 1, "rows identical to another": 1 };
  host.innerHTML = S1.checks.map(c => { const isInfo = info[c.name]; const v = typeof c.value === "number" ? fmt(c.value) : c.value;
    const share = c.name === "rows identical to another" ? ` <small>(${fmt(100 * c.value / S1.rows, 1)}% of rows)</small>` : "";
    return `<div class="chk ${isInfo ? "info" : "ok"}"><div class="k">${c.name}</div><div class="v">${v}${share}</div><div class="s">${isInfo ? "recorded" : (c.name === "rows" ? "loaded" : "pass")}</div></div>`; }).join("");
})();
if (has("c-01c-recon")) (function () {
  const host = has("c-01c-recon"), ro = has("ro-01c");
  const f = r => r.kind === "count" ? fmt(r.sql) : r.kind === "float_count" ? fmt(r.sql, 2) : (+r.sql).toFixed(6);
  function show(filter) {
    const rows = S1.reconciliation.filter(r => filter === "all" || r.metric.startsWith(filter));
    ro.innerHTML = `<div><div class="k">Agree</div><div class="v" style="color:var(--navy)">${rows.filter(r => r.agree).length} <small>of ${rows.length}</small></div></div><div><div class="k">Largest difference</div><div class="v">${Math.max(...rows.map(r => Math.abs(r.diff))).toFixed(0)}</div></div>`;
    host.innerHTML = `<table class="tbl"><thead><tr><th>Quantity</th><th>SQL</th><th>Python</th><th></th></tr></thead><tbody>` +
      rows.map((r, i) => `<tr style="animation-delay:${i * 18}ms"><td>${r.metric}</td><td class="num">${f(r)}</td><td class="num">${r.kind === "count" ? fmt(r.python) : r.kind === "float_count" ? fmt(r.python, 2) : (+r.python).toFixed(6)}</td><td class="ok">${r.agree ? "✓" : "✗"}</td></tr>`).join("") + "</tbody></table>";
  }
  makeSeg(has("seg-01c"), [["all", "All 29"], ["01a", "Study 01a"], ["02a", "Study 02a"]], "all", show); show("all");
})();

/* ---------- 01d ---------- */
if (has("c-01d-eps")) (function () {
  const names = { "0.1": "0.1", "0.5": "0.5", "1.0": "1", "5.0": "5", "inf": "No noise" };
  const host = has("c-01d-eps"), ro = has("ro-01d-eps"); let chart = null;
  const refsB = [{ v: S1.baseline, label: `each segment, no noise ${S1.baseline.toFixed(2)}`, cls: "s-grey", tcls: "t-muted" }];
  function rows(k) { const e = S1.eps.find(x => x.eps === k);
    return [{ label: "Each segment alone", v: e.nopool, lo: e.nopool, hi: e.nopool, text: e.nopool.toFixed(2), fcls: "f-grey", scls: "s-grey" },
            { label: "Multilevel model", v: e.ml, lo: e.ml, hi: e.ml, text: e.ml.toFixed(2), strong: true }]; }
  function set(k) { const e = S1.eps.find(x => x.eps === k), top = Math.max(e.nopool, S1.baseline) * 1.25, dom = [0, top];
    const t = top > 4 ? [0, 2, 4, 6, 8] : top > 2 ? [0, .5, 1, 1.5, 2] : [0, .25, .5, .75, 1, 1.25, 1.5];
    if (chart) chart.update(rows(k), dom, t, refsB); else chart = dotRows(host, { rows: rows(k), dom, ticks: t, label: 150, rh: 46, refs: refsB });
    ro.innerHTML = `<div><div class="k">Multilevel lower than each segment alone</div><div class="v" style="color:var(--navy)">${e.better ?? "–"} <small>of 10 samples</small></div></div>` +
      `<div><div class="k">Multilevel against the no-noise benchmark</div><div class="v" style="color:${e.ml <= S1.baseline ? "var(--navy)" : "var(--orange)"}">${e.ml.toFixed(2)} <small>vs ${S1.baseline.toFixed(2)} pp</small></div></div>`; }
  makeSeg(has("seg-01d-eps"), S1.eps.map(e => [e.eps, names[e.eps]]), "1.0", set); set("1.0");
})();
if (has("c-01d-alloc")) (function () {
  const host = has("c-01d-alloc"), ro = has("ro-01d-alloc");
  const labels = [["oracle", "True segment effects", "f-grey", "s-grey"], ["multilevel", "Lift, multilevel model", "f-navy", "s-navy"], ["nopool", "Lift, each segment", "f-blue", "s-blue"], ["response", "Response rate", "f-orange", "s-orange"], ["random", "Random order", "f-grey", "s-grey"]];
  let P;
  function draw(b) {
    const w = W(host), L = Math.min(160, w * .4), R = w - 56, rh = 34, h = labels.length * rh + 34, svg = svgIn(host, w, h), x = lin(0, 100, L, R);
    [0, 25, 50, 75, 100].forEach(t => { el("line", { x1: x(t), x2: x(t), y1: 4, y2: h - 30, class: "gridl" }, svg); txt(svg, x(t), h - 12, t + "%", { "text-anchor": "middle", class: "t-muted", "font-size": 11 }); });
    P = { x, bars: labels.map(([k, name, cls], i) => { const y = 6 + i * rh;
      txt(svg, 0, y + 15, name, { class: k === "multilevel" || k === "response" ? "t-strong" : "t-ink", "font-size": 12.5 });
      const r = el("rect", { x: x(0), y, width: 0, height: 20, rx: 5, class: cls, opacity: k === "oracle" || k === "random" ? .55 : 1 }, svg);
      const t = txt(svg, x(0) + 6, y + 15, "", { class: "t-strong", "font-size": 12.5 }); return { k, r, t }; }) };
    set(b, 0);
  }
  let cur = "10";
  function set(b, dur = 800) { cur = b; const a = S1.alloc[b];
    P.bars.forEach(o => { const v = o.k === "random" ? a.random : a.share[o.k]; animate([[o.r, { width: P.x(v) - P.x(0) }], [o.t, { x: P.x(v) + 6 }]], dur); o.t.textContent = v.toFixed(1) + "%"; });
    ro.innerHTML = `<div><div class="k">Lift (multilevel) beat response rate</div><div class="v" style="color:${a.ml_gt_response >= 8 ? "var(--navy)" : "var(--orange)"}">${a.ml_gt_response} <small>of 10 samples</small></div></div>` +
      `<div><div class="k">Lift (each segment) beat response rate</div><div class="v">${a.nopool_gt_response} <small>of 10</small></div></div>`; }
  makeSeg(has("seg-01d-budget"), [["10", "10%"], ["20", "20%"], ["30", "30%"]], "10", v => set(v));
  draw("10"); redrawers.push(() => draw(cur));
})();

/* ---------- 02a ---------- */
if (has("c-02a-exp")) (function () {
  const ex = S2.exposure, lo = Math.min(ex[0].v, ex[1].v), hi = Math.max(ex[0].v, ex[1].v);
  dotRows(has("c-02a-exp"), { rows: ex.map(e => ({ label: e.label, v: e.v, lo: e.v - e.ci, hi: e.v + e.ci, text: e.v.toFixed(1), strong: e.group === "exp",
      fcls: e.group === "exp" ? "f-navy" : e.label.startsWith("Exposed") ? "f-orange" : "f-blue", scls: e.group === "exp" ? "s-navy" : e.label.startsWith("Exposed") ? "s-orange" : "s-blue",
      tip: `${e.label}: ${e.v.toFixed(1)} pp (95% CI ±${e.ci.toFixed(1)})` })),
    dom: [15, 42], ticks: [15, 20, 25, 30, 35, 40], band: [lo, hi], label: 180, rh: 38, fmtT: v => v });
})();

/* ---------- 02b ---------- */
if (has("c-02b-heat")) (function () {
  const host = has("c-02b-heat"), C = D.credit, rules = [["cr_last", "Last touch"], ["cr_decay", "Time decay"], ["cr_linear", "Linear"], ["cr_first", "First touch"]];
  const cols = [["last", "Last touch"], ["<1d", "< 1 day earlier"], ["1-7d", "1–7 days earlier"], [">7d", "> 7 days earlier"]];
  host.innerHTML = `<table class="heat"><thead><tr><th>Rule</th>${cols.map(c => `<th>${c[1]}</th>`).join("")}</tr></thead><tbody>` +
    rules.map(([k, n]) => `<tr data-r="${k}"><th>${n}</th>${cols.map(([c], j) => { const v = C.rules[k][c]; return `<td data-c="${j}" style="--a:${(0.06 + 0.94 * v / 100).toFixed(3)}"><span>${v.toFixed(0)}%</span></td>`; }).join("")}</tr>`).join("") + "</tbody></table>";
  const tb = host.querySelector("table");
  tb.addEventListener("pointerover", e => { const td = e.target.closest("td,th"); if (!td) return; const tr = td.closest("tr"); tb.querySelectorAll(".hl").forEach(x => x.classList.remove("hl"));
    if (tr && tr.dataset.r) tr.classList.add("hl"); if (td.dataset.c !== undefined) tb.querySelectorAll(`td[data-c="${td.dataset.c}"]`).forEach(x => x.classList.add("hl"));
    if (tr && tr.dataset.r) document.dispatchEvent(new CustomEvent("rule-hover", { detail: tr.dataset.r })); });
  tb.addEventListener("pointerleave", () => { tb.querySelectorAll(".hl").forEach(x => x.classList.remove("hl")); document.dispatchEvent(new CustomEvent("rule-hover", { detail: null })); });
})();
if (has("c-02b-click")) (function () {
  const host = has("c-02b-click"), names = { cr_last: "Last touch", cr_decay: "Time decay", cr_linear: "Linear", cr_first: "First touch" };
  let hl = null;
  function draw() {
    const w = W(host), L = 110, R = w - 50, rh = 36, ks = Object.keys(names), h = ks.length * rh + 58, svg = svgIn(host, w, h), x = lin(40, 70, L, R), T0 = 22;
    [40, 50, 60, 70].forEach(t => { el("line", { x1: x(t), x2: x(t), y1: 4, y2: h - 30, class: "gridl" }, svg); txt(svg, x(t), h - 12, t + "%", { "text-anchor": "middle", class: "t-muted", "font-size": 11 }); });
    el("line", { x1: x(S2.share_clicked), x2: x(S2.share_clicked), y1: 14, y2: h - 30, class: "s-orange", "stroke-width": 1.5, "stroke-dasharray": "5 4" }, svg);
    txt(svg, x(S2.share_clicked), 10, `share of touches that were clicked: ${fmt(S2.share_clicked)}%`, { class: "t-orange halo", "font-size": 11, "text-anchor": "middle" });
    ks.forEach((k, i) => { const y = T0 + i * rh + rh / 2, v = S2.clicked[k], on = !hl || hl === k;
      txt(svg, 0, y + 4, names[k], { class: on ? "t-strong" : "t-muted", "font-size": 12.5 });
      el("line", { x1: x(S2.share_clicked), x2: x(v), y1: y, y2: y, class: "s-navy", "stroke-width": 2, opacity: on ? .5 : .15 }, svg);
      el("circle", { cx: x(v), cy: y, r: 6.5, class: "f-navy s-card", "stroke-width": 2, opacity: on ? 1 : .3 }, svg);
      txt(svg, x(v) + 10, y + 4, v.toFixed(0) + "%", { class: "t-strong", "font-size": 12.5, opacity: on ? 1 : .3 }); });
  }
  document.addEventListener("rule-hover", e => { hl = e.detail; draw(); });
  draw(); redrawers.push(draw);
})();

/* ---------- 02c ---------- */
if (has("c-02c-rec")) (function () {
  const host = has("c-02c-rec"), ro = has("ro-02c"); let f = "W";
  function draw(fade) {
    const w = W(host), h = Math.min(360, Math.max(280, w * .55)), L = 50, B = h - 44, R = w - 12, svg = svgIn(host, w, h);
    const x = lg(0.4, 5, L, R), y = lg(0.03, 1000, B, 10), Rr = S2.recovery[f];
    [0.1, 1, 10, 100, 1000].forEach(v => { el("line", { x1: L, x2: R, y1: y(v), y2: y(v), class: "gridl" }, svg); txt(svg, L - 8, y(v) + 4, fmt(v, v < 1 ? 1 : 0), { "text-anchor": "end", class: "t-muted", "font-size": 11 }); });
    [0.5, 1, 2, 4].forEach(v => txt(svg, x(v), B + 18, v, { "text-anchor": "middle", class: "t-muted", "font-size": 11 }));
    txt(svg, (L + R) / 2, B + 36, "Known channel ROAS (simulated, log scale)", { "text-anchor": "middle", class: "t-muted", "font-size": 11 });
    txt(svg, L - 44, 4, "Estimated ROAS, 90% interval", { class: "t-muted", "font-size": 11 });
    el("line", { x1: x(0.4), y1: y(0.4), x2: x(5), y2: y(5), class: "s-orange", "stroke-width": 1.5, "stroke-dasharray": "5 4" }, svg);
    txt(svg, x(4.6), y(4.6) - 8, "estimate = known", { "text-anchor": "end", class: "t-orange halo", "font-size": 11 });
    const g = el("g", { class: "fade", style: fade ? "opacity:0" : "" }, svg);
    Rr.points.forEach(p => { const gg = el("g", { class: "hot" }, g), cx = x(p.true);
      el("line", { x1: cx, x2: cx, y1: y(Math.max(p.lo, .031)), y2: y(Math.min(p.hi, 990)), class: "s-navy", "stroke-width": 1.2, opacity: .45 }, gg);
      el("circle", { cx, cy: y(p.est), r: 4.5, class: "f-navy s-card", "stroke-width": 1.2 }, gg);
      hoverTip(gg, `Known ${p.true.toFixed(2)} · estimated ${p.est.toFixed(2)}<br>90% interval ${p.lo.toFixed(2)} to ${p.hi.toFixed(2)}`); });
    if (fade) requestAnimationFrame(() => requestAnimationFrame(() => g.style.opacity = 1));
    ro.innerHTML = `<div><div class="k">Rank correlation</div><div class="v">${Rr.spearman.toFixed(2)}</div></div><div><div class="k">90% intervals covering the truth</div><div class="v">${Rr.coverage}%</div></div><div><div class="k">Median error</div><div class="v">${Rr.median_err}%</div></div>`;
  }
  makeSeg(has("seg-02c-freq"), [["W", "Weekly data"], ["D", "Daily data"]], f, v => { f = v; draw(true); document.dispatchEvent(new CustomEvent("freq", { detail: v })); });
  draw(false); redrawers.push(() => draw(false));
})();
if (has("c-02c-hold")) (function () {
  const host = has("c-02c-hold"), ro = has("ro-02c-hold"); let f = "W", P;
  const ms = [["mmm", "With media", "f-navy"], ["b0", "Without media", "f-blue"], ["naive", "Seasonal naive", "f-grey"]];
  function draw() {
    const w = W(host), L = 120, R = w - 56, rh = 36, h = ms.length * rh + 36, svg = svgIn(host, w, h), x = lin(0, 50, L, R);
    [0, 10, 20, 30, 40, 50].forEach(t => { el("line", { x1: x(t), x2: x(t), y1: 2, y2: h - 30, class: "gridl" }, svg); txt(svg, x(t), h - 12, t + "%", { "text-anchor": "middle", class: "t-muted", "font-size": 11 }); });
    P = { x, bars: ms.map(([k, n, cls], i) => { const y = 6 + i * rh; txt(svg, 0, y + 16, n, { class: k === "mmm" ? "t-strong" : "t-ink", "font-size": 12.5 });
      return { k, r: el("rect", { x: x(0), y, width: 0, height: 22, rx: 5, class: cls }, svg), t: txt(svg, x(0), y + 16, "", { class: "t-strong", "font-size": 12.5 }) }; }) };
    set(f, 0);
  }
  function set(v, dur = 700) { f = v; const H = S2.holdout[v];
    P.bars.forEach(b => { const val = H.wmape[b.k]; animate([[b.r, { width: P.x(val) - P.x(0) }], [b.t, { x: P.x(val) + 6 }]], dur); b.t.textContent = val.toFixed(1) + "%"; });
    ro.innerHTML = `<p class="sub" style="margin-top:8px">With media lower than without in <b>${H.better}</b> of ${H.brands} brands. Mean difference, with minus without: <b>${H.diff >= 0 ? "+" : ""}${H.diff.toFixed(3)}</b> (95% CI ${H.diff_ci[0].toFixed(3)} to ${H.diff_ci[1].toFixed(3)}); the interval includes 0, so the pre-specified rule was not met.</p>`; }
  document.addEventListener("freq", e => set(e.detail));
  draw(); redrawers.push(draw);
})();

/* ---------- 02d composition ---------- */
if (has("c-02d-comp")) (function () {
  const host = has("c-02d-comp"); let b = "0.5", P;
  const cats = [["within_24h_of_last_click", "Within 24 hours of the user's last click"], ["no_earlier_click", "Users with no earlier click"], ["first_logged_impression", "A user's first logged impression"]];
  const ser = [["cr_last", "Last-touch bidder", "f-grey"], ["cr_decay", "Time-decay bidder", "f-navy"], ["all", "All logged spend", "f-pale"]];
  function draw() {
    const w = W(host), L = 4, R = w - 56, gh = 86, h = cats.length * gh + 30, svg = svgIn(host, w, h), x = lin(0, 50, L, R);
    P = { x, rows: cats.map(([c, name], i) => { const y0 = 6 + i * gh; txt(svg, L, y0 + 12, name, { class: "t-strong", "font-size": 12.5 });
      return ser.map(([s, sn, cls], j) => { const y = y0 + 20 + j * 20;
        const r = el("rect", { x: L, y, width: 0, height: 15, rx: 4, class: cls }, svg), t = txt(svg, L, y + 12, "", { "font-size": 11.5, class: "t-ink" });
        hoverTip(r, () => `${sn}: ${r.dataset.v}% of spend`); return { c, s, r, t }; }); }).flat() };
    set(b, 0);
  }
  function set(v, dur = 700) { b = v; P.rows.forEach(o => { const val = o.s === "all" ? S2.all_spend[o.c] : S2.composition[v][o.s][o.c]; o.r.dataset.v = val.toFixed(1);
    animate([[o.r, { width: P.x(val) - P.x(0) }], [o.t, { x: P.x(val) + 6 }]], dur); o.t.textContent = val.toFixed(1) + "%"; }); }
  document.querySelectorAll("#seg-budget button").forEach(bt => bt.addEventListener("click", () => set(bt.dataset.v)));
  draw(); redrawers.push(draw);
})();

/* ---------- 03a ---------- */
if (has("c-03a-power")) (function () {
  const host = has("c-03a-power"), ro = has("ro-03a"), Pw = S3.power; let sel = 2;
  const binom = (p, n) => 196 * Math.sqrt(p / 100 * (1 - p / 100) / n);
  function draw() {
    const w = W(host), L = 48, R = w - 14, ph = 150, gap = 58, h = 2 * ph + gap + 52, svg = svgIn(host, w, h);
    const x = lin(-0.4, Pw.n.length - 0.6, L, R);
    const panels = [[["power_z", "z-test", "navy"], ["bayes_detect", "Bayesian", "blue"]], [["aa_false_positive_z", "z-test", "navy"], ["aa_false_positive_bayes", "Bayesian", "blue"]]];
    const doms = [[0, 100], [0, 10]], refs = [80, 5], titles = ["Studies detecting a one-point lift (%)", "A/A studies reporting a lift (%)"];
    panels.forEach((ser, pi) => { const T = 30 + pi * (ph + gap), B = T + ph, y = lin(doms[pi][0], doms[pi][1], B, T);
      txt(svg, L - 40, T - 16, titles[pi], { class: "t-strong", "font-size": 12 });
      (pi ? [0, 2, 4, 6, 8, 10] : [0, 20, 40, 60, 80, 100]).forEach(v => { el("line", { x1: L, x2: R, y1: y(v), y2: y(v), class: "gridl" }, svg); txt(svg, L - 8, y(v) + 4, v, { "text-anchor": "end", class: "t-muted", "font-size": 11 }); });
      el("line", { x1: L, x2: R, y1: y(refs[pi]), y2: y(refs[pi]), class: "s-orange", "stroke-width": 1.4, "stroke-dasharray": "5 4" }, svg);
      txt(svg, R, y(refs[pi]) - 5, pi ? "nominal 5%" : "80% power", { "text-anchor": "end", class: "t-orange halo", "font-size": 11 });
      ser.forEach(([k, n, c], si) => { const off = si ? 5 : -5;
        el("path", { d: "M" + Pw[k].map((v, i) => [x(i) + off, y(v)].join(",")).join("L"), fill: "none", class: "s-" + c, "stroke-width": 2 }, svg);
        Pw[k].forEach((v, i) => { const e = binom(v, Pw.studies); el("line", { x1: x(i) + off, x2: x(i) + off, y1: y(Math.max(0, v - e)), y2: y(Math.min(doms[pi][1], v + e)), class: "s-" + c, "stroke-width": 1.2 }, svg);
          el("circle", { cx: x(i) + off, cy: y(v), r: 4.2, class: "f-" + c + " s-card", "stroke-width": 1.4 }, svg); });
        txt(svg, x(Pw.n.length - 1) + off + 4, y(Pw[k][Pw.n.length - 1]) + (si ? 14 : -8), n, { "text-anchor": "end", class: "t-" + (c === "navy" ? "navy" : "muted") + " halo", "font-size": 11 }); });
    });
    Pw.n.forEach((n, i) => { txt(svg, x(i), h - 22, fmt(n), { "text-anchor": "middle", class: i === sel ? "t-strong" : "t-muted", "font-size": 11 });
      const hit = el("rect", { x: x(i) - (x(1) - x(0)) / 2, y: 0, width: x(1) - x(0), height: h - 30, fill: "transparent", class: "hot" }, svg);
      const pick = () => { if (sel !== i) { sel = i; draw(); } }; hit.addEventListener("click", pick); hit.addEventListener("pointerenter", pick); });
    svg.insertBefore(el("rect", { x: x(sel) - 16, y: 4, width: 32, height: h - 34, rx: 8, class: "f-orange", opacity: .1 }), svg.firstChild);
    txt(svg, (L + R) / 2, h - 4, "Users per arm", { "text-anchor": "middle", class: "t-muted", "font-size": 11 });
    ro.innerHTML = `<div><div class="k">${fmt(Pw.n[sel])} users per arm</div><div class="v">${Pw.power_z[sel].toFixed(0)}% <small>power (z-test)</small></div></div><div><div class="k">A/A false positives</div><div class="v">${Pw.aa_false_positive_z[sel].toFixed(1)}% <small>z-test</small></div></div>`;
  }
  draw(); redrawers.push(draw);
})();
if (has("c-03a-mde")) (function () {
  const host = has("c-03a-mde"), Cv = S3.cov, one = D.sizing.one_point;
  const ser = [["D", "Unadjusted", "grey"], ["L", "Adjusted, 12 features", "blue"], ["M", "Adjusted, model prediction", "navy"]];
  function draw() {
    const w = W(host), L = 44, R = w - 14, T = 12, B = 220, h = B + 40, svg = svgIn(host, w, h), x = lg(800, 25000, L, R), y = lin(0, 3, B, T);
    [0, .5, 1, 1.5, 2, 2.5, 3].forEach(v => { el("line", { x1: L, x2: R, y1: y(v), y2: y(v), class: "gridl" }, svg); txt(svg, L - 8, y(v) + 4, v, { "text-anchor": "end", class: "t-muted", "font-size": 11 }); });
    Cv.n.forEach(n => txt(svg, x(n), B + 18, fmt(n), { "text-anchor": "middle", class: "t-muted", "font-size": 11 }));
    txt(svg, (L + R) / 2, B + 34, "Users per arm (log scale)", { "text-anchor": "middle", class: "t-muted", "font-size": 11 });
    txt(svg, L - 40, 4, "Minimum detectable lift (pp)", { class: "t-muted", "font-size": 11 });
    el("line", { x1: L, x2: R, y1: y(1), y2: y(1), class: "s-orange", "stroke-width": 1.4, "stroke-dasharray": "5 4" }, svg);
    ser.forEach(([k, n, c], si) => { el("path", { d: "M" + Cv.n.map((nn, i) => [x(nn), y(Cv.mde[k][i])].join(",")).join("L"), fill: "none", class: "s-" + c, "stroke-width": 2.2 }, svg);
      Cv.n.forEach((nn, i) => el("circle", { cx: x(nn), cy: y(Cv.mde[k][i]), r: 3.6, class: "f-" + c }, svg));
      const nx = one[k], g = el("g", { class: "hot" }, svg);
      el("line", { x1: x(nx), x2: x(nx), y1: y(1), y2: B, class: "s-" + c, "stroke-dasharray": "2 3", opacity: .8 }, g);
      el("circle", { cx: x(nx), cy: y(1), r: 6, class: "f-" + c + " s-card", "stroke-width": 2 }, g);
      txt(g, x(nx) + (si === 0 ? 8 : -8), si === 0 ? y(1) - 10 : y(1) + 4 + si * 15, `${n}: ${fmt(nx)}`, { "text-anchor": si === 0 ? "start" : "end", class: "t-" + (c === "grey" ? "muted" : "navy") + " halo", "font-size": 11.5 });
      hoverTip(g, `${n}: ${fmt(nx)} users per arm for a one-point lift`); });
  }
  draw(); redrawers.push(draw);
})();
if (has("c-03a-var")) (function () {
  const Cv = S3.cov, rows = [];
  Cv.n.forEach((n, i) => [["L", "12 features", "f-blue", "s-blue"], ["M", "Model prediction", "f-navy", "s-navy"]].forEach(([k, lab, f, s]) => { const [v, lo, hi] = Cv.ratio[k][i];
    rows.push({ label: `${fmt(n)} · ${lab}`, v, lo, hi, text: v.toFixed(2), fcls: f, scls: s }); }));
  dotRows(has("c-03a-var"), { rows, dom: [0.5, 1.05], ticks: [0.5, 0.6, 0.7, 0.8, 0.9, 1.0], refs: [{ v: 1, label: "unadjusted", cls: "s-grey", tcls: "t-muted" }], label: 170, rh: 24 });
})();

/* ---------- 03b ---------- */
if (has("c-03b-fp")) (function () {
  const host = has("c-03b-fp"), ms = D.sizing.metros, binom = (p, n) => 196 * Math.sqrt(p / 100 * (1 - p / 100) / n);
  function draw() {
    const w = W(host), L = 40, R = w - 16, T = 14, B = 200, h = B + 40, svg = svgIn(host, w, h), x = lin(-0.4, 3.4, L, R), y = lin(0, 12, B, T);
    [0, 2, 4, 6, 8, 10, 12].forEach(v => { el("line", { x1: L, x2: R, y1: y(v), y2: y(v), class: "gridl" }, svg); txt(svg, L - 8, y(v) + 4, v + "%", { "text-anchor": "end", class: "t-muted", "font-size": 11 }); });
    el("line", { x1: L, x2: R, y1: y(5), y2: y(5), class: "s-orange", "stroke-width": 1.4, "stroke-dasharray": "5 4" }, svg);
    txt(svg, R, y(5) - 6, "nominal 5%", { "text-anchor": "end", class: "t-orange halo", "font-size": 11 });
    [["t", "t-test", "grey", -6], ["ri", "Randomization inference", "navy", 6]].forEach(([k, n, c, off]) => {
      const vals = ms.map(m => k === "t" ? S3.vw_fp[`${m}|2`][0] : S3.ri[m].ri), ns = ms.map(m => k === "t" ? S3.vw_fp[`${m}|2`][1] : S3.ri[m].ri_draws);
      el("path", { d: "M" + vals.map((v, i) => [x(i) + off, y(v)].join(",")).join("L"), fill: "none", class: "s-" + c, "stroke-width": 2 }, svg);
      vals.forEach((v, i) => { const e = binom(v, ns[i]), g = el("g", { class: "hot" }, svg);
        el("line", { x1: x(i) + off, x2: x(i) + off, y1: y(v - e), y2: y(v + e), class: "s-" + c, "stroke-width": 1.2 }, g);
        el("circle", { cx: x(i) + off, cy: y(v), r: 4.5, class: "f-" + c + " s-card", "stroke-width": 1.4 }, g);
        hoverTip(g, `${ms[i]} metros, ${n}: ${v.toFixed(1)}% of placebo tests rejected`); });
      txt(svg, x(0) + off + 8, y(vals[0]) + (k === "t" ? -10 : 18), n, { class: (c === "navy" ? "t-navy" : "t-muted") + " halo", "font-size": 11.5 }); });
    ms.forEach((m, i) => txt(svg, x(i), B + 18, m, { "text-anchor": "middle", class: "t-muted", "font-size": 11 }));
    txt(svg, (L + R) / 2, B + 34, "Metros in a two-month test", { "text-anchor": "middle", class: "t-muted", "font-size": 11 });
  }
  draw(); redrawers.push(draw);
})();

/* ---------- 03c ---------- */
if (has("c-03c-multi")) (function () {
  const host = has("c-03c-multi"), Hz = S3.horizon, levels = [["US", "Nation"], ["division", "Divisions"], ["state", "States"], ["metro", "Metros"]];
  const meth = [["base", "Unreconciled", "grey"], ["bu", "Bottom-up", "blue"], ["mint_shrink", "MinT-shrink", "navy"], ["ols", "OLS", "orange"], ["wls_struct", "WLS-structural", "light"], ["td", "Top-down", "grey"]];
  let on = new Set(["base", "bu", "mint_shrink"]), hcur = null;
  const seg = has("seg-03c");
  seg.classList.add("seg"); seg.innerHTML = meth.map(([k, n]) => `<button type="button" data-v="${k}" aria-pressed="${on.has(k)}">${n}</button>`).join("");
  seg.querySelectorAll("button").forEach(b => b.addEventListener("click", () => { const k = b.dataset.v; on.has(k) ? on.delete(k) : on.add(k); b.setAttribute("aria-pressed", on.has(k)); draw(); }));
  function draw() {
    const w = W(host), cols = w < 560 ? 1 : 2, pw = (w - (cols - 1) * 24) / cols, ph = 170, rows = Math.ceil(4 / cols), h = rows * (ph + 50), svg = svgIn(host, w, h);
    levels.forEach(([lv, name], i) => { const c = i % cols, r = Math.floor(i / cols), ox = c * (pw + 24), oy = r * (ph + 50) + 18, L = ox + 36, R = ox + pw - 8, T = oy + 8, B = oy + ph;
      const x = lin(1, 12, L, R), y = lin(0.3, 1.4, B, T), g = el("g", {}, svg);
      txt(g, ox, oy - 2, `${String.fromCharCode(65 + i)}. ${name}${S3.nodes[lv] > 1 ? ` (${S3.nodes[lv]} series)` : ""}`, { class: "t-strong", "font-size": 12.5 });
      [0.4, 0.6, 0.8, 1.0, 1.2].forEach(v => { el("line", { x1: L, x2: R, y1: y(v), y2: y(v), class: "gridl" }, g); txt(g, L - 6, y(v) + 4, v.toFixed(1), { "text-anchor": "end", class: "t-muted", "font-size": 10.5 }); });
      [1, 3, 6, 9, 12].forEach(v => txt(g, x(v), B + 16, v, { "text-anchor": "middle", class: "t-muted", "font-size": 10.5 }));
      el("line", { x1: L, x2: R, y1: y(1), y2: y(1), class: "s-orange", "stroke-width": 1.3, "stroke-dasharray": "5 4" }, g);
      meth.forEach(([k, n, col]) => { if (!on.has(k)) return; const v = Hz[lv][k];
        el("path", { d: "M" + v.map((u, j) => [x(j + 1), y(u)].join(",")).join("L"), fill: "none", class: "s-" + col, "stroke-width": k === "base" ? 1.8 : 2.2, "stroke-dasharray": k === "bu" ? "6 3" : k === "td" ? "2 3" : null }, g); });
      if (hcur) { el("line", { x1: x(hcur), x2: x(hcur), y1: T, y2: B, class: "s-grey", opacity: .7 }, g);
        const vals = meth.filter(([k]) => on.has(k)).map(([k, n]) => `${n.split(" ")[0]} ${Hz[lv][k][hcur - 1].toFixed(2)}`);
        vals.forEach((s, j) => txt(g, R, T + 12 + j * 13, s, { "text-anchor": "end", class: "t-ink halo", "font-size": 10.5 })); }
      const hit = el("rect", { x: L, y: T, width: R - L, height: B - T, fill: "transparent" }, g);
      hit.addEventListener("pointermove", e => { const b = svg.getBoundingClientRect(), hh = Math.max(1, Math.min(12, Math.round((e.clientX - b.left - L) / (R - L) * 11) + 1)); if (hh !== hcur) { hcur = hh; draw(); } });
      hit.addEventListener("pointerleave", () => { hcur = null; draw(); });
    });
    txt(svg, w / 2, h - 4, hcur ? `Horizon ${hcur} months · RMSSE relative to a no-change forecast` : "Horizon (months) · RMSSE relative to a no-change forecast; below 1 is better", { "text-anchor": "middle", class: "t-muted", "font-size": 11 });
  }
  draw(); redrawers.push(draw);
})();
if (has("c-03c-gap")) (function () {
  const host = has("c-03c-gap"), items = [["US", "Nation vs. sum of divisions"], ["division", "Divisions vs. sum of states"], ["state", "States vs. sum of metros"]]; let after = false, P;
  function draw() {
    const w = W(host), L = Math.min(190, w * .45), R = w - 50, rh = 38, h = items.length * rh + 34, svg = svgIn(host, w, h), x = lin(0, 6, L, R);
    [0, 2, 4, 6].forEach(t => { el("line", { x1: x(t), x2: x(t), y1: 2, y2: h - 30, class: "gridl" }, svg); txt(svg, x(t), h - 12, t + "%", { "text-anchor": "middle", class: "t-muted", "font-size": 11 }); });
    P = { x, bars: items.map(([k, n], i) => { const y = 6 + i * rh; txt(svg, 0, y + 16, n, { "font-size": 12.5 });
      return { k, r: el("rect", { x: x(0), y, width: x(S3.gap[k]) - x(0), height: 22, rx: 5, class: "f-orange" }, svg), t: txt(svg, x(S3.gap[k]) + 6, y + 16, S3.gap[k].toFixed(1) + "%", { class: "t-strong", "font-size": 12.5 }) }; }) };
    set(after, 0);
  }
  function set(a, dur = 900) { after = a; P.bars.forEach(b => { const v = a ? 0 : S3.gap[b.k]; animate([[b.r, { width: P.x(v) - P.x(0) }], [b.t, { x: P.x(v) + 6 }]], dur); b.t.textContent = a ? "0" : v.toFixed(1) + "%";
    b.r.setAttribute("class", a ? "f-navy" : "f-orange"); }); }
  makeSeg(has("seg-03c-gap"), [["before", "Before reconciliation"], ["after", "After bottom-up"]], "before", v => set(v === "after"));
  draw(); redrawers.push(draw);
})();

/* ---------- 04 ---------- */
const segName = s => { const [r, t] = s.split("|"); return `${t[0].toUpperCase() + t.slice(1)} value · ${r === "recent<=60d" ? "≤60 days" : r === "61-120d" ? "61–120 days" : ">120 days"}`; };
const segShort = s => { const [r, t] = s.split("|"); return `${t[0].toUpperCase() + t.slice(1)} · ${r === "recent<=60d" ? "≤60d" : r === "61-120d" ? "61–120d" : ">120d"}`; };
if (has("c-04-dumb")) (function () {
  const host = has("c-04-dumb"), hm = has("c-04-mean"); let order = "rule", P;
  const sorted = () => { const s = S4.segments.slice(); if (order === "sales") s.sort((a, b) => b.sales - a.sales); else if (order === "gap") s.sort((a, b) => (b.sales - b.acc) - (a.sales - a.acc)); return s; };
  function draw() {
    const w = W(host), L = w < 480 ? 92 : Math.min(150, w * .42), R = w - 20, rh = 30, h = S4.segments.length * rh + 40, svg = svgIn(host, w, h), x = lin(0, 80, L, R);
    [0, 20, 40, 60, 80].forEach(t => { el("line", { x1: x(t), x2: x(t), y1: 2, y2: h - 30, class: "gridl" }, svg); txt(svg, x(t), h - 12, t + "%", { "text-anchor": "middle", class: "t-muted", "font-size": 11 }); });
    const pos = Object.fromEntries(sorted().map((s, i) => [s.seg, 6 + i * rh + rh / 2]));
    P = { rows: S4.segments.map(s => { const y = pos[s.seg], g = el("g", { class: "hot", transform: `translate(0,${y})` }, svg);
      txt(g, 0, 4, w < 480 ? segShort(s.seg) : segName(s.seg), { "font-size": 12, class: s.seg === "recent<=60d|high" ? "t-strong" : "t-ink" });
      el("line", { x1: x(s.acc), x2: x(s.sales), y1: 0, y2: 0, class: s.sales > s.acc ? "s-navy" : "s-grey", "stroke-width": 3, opacity: .45 }, g);
      el("circle", { cx: x(s.acc), cy: 0, r: 5.5, class: "f-grey s-card", "stroke-width": 1.5 }, g);
      el("circle", { cx: x(s.sales), cy: 0, r: 6.5, class: "f-navy s-card", "stroke-width": 1.5 }, g);
      hoverTip(g, `${segName(s.seg)} (${fmt(s.n)} accounts)<br>${s.acc.toFixed(1)}% of accounts · ${s.sales.toFixed(1)}% of next-six-month sales`);
      return { s, g, y }; }) };
    drawMean(pos);
  }
  function drawMean(pos) {
    if (!hm) return; const w = W(hm), L = w < 480 ? 92 : Math.min(150, w * .42), R = w - 20, rh = 30, h = S4.segments.length * rh + 40, svg = svgIn(hm, w, h), x = lg(150, 6000, L, R);
    (w < 480 ? [200, 1000, 5000] : [200, 500, 1000, 5000]).forEach(t => { el("line", { x1: x(t), x2: x(t), y1: 2, y2: h - 30, class: "gridl" }, svg); txt(svg, x(t), h - 12, "£" + fmt(t), { "text-anchor": "middle", class: "t-muted", "font-size": 11 }); });
    P.mean = S4.segments.map(s => { const g = el("g", { class: "hot", transform: `translate(0,${pos[s.seg]})` }, svg);
      txt(g, 0, 4, w < 480 ? segShort(s.seg) : segName(s.seg), { "font-size": 12 }); el("line", { x1: x(s.lo), x2: x(s.hi), y1: 0, y2: 0, class: "s-navy", "stroke-width": 2 }, g);
      el("circle", { cx: x(s.mean), cy: 0, r: 5.5, class: "f-navy s-card", "stroke-width": 1.5 }, g);
      hoverTip(g, `${segName(s.seg)}: £${fmt(s.mean)} per account (95% CI £${fmt(s.lo)} to £${fmt(s.hi)})`); return { s, g }; });
  }
  function resort(o) { order = o; const pos = Object.fromEntries(sorted().map((s, i) => [s.seg, 6 + i * 30 + 15]));
    const all = P.rows.map(r => [r.g, pos[r.s.seg]]).concat((P.mean || []).map(r => [r.g, pos[r.s.seg]]));
    const from = all.map(([g]) => parseFloat(g.getAttribute("transform").match(/,([\d.]+)/)[1]));
    tween(700, t => all.forEach(([g, to], i) => g.setAttribute("transform", `translate(0,${from[i] + (to - from[i]) * t})`))); }
  makeSeg(has("seg-04-sort"), [["rule", "Rule order"], ["sales", "By share of sales"], ["gap", "By sales minus accounts"]], "rule", resort);
  draw(); redrawers.push(draw);
})();
if (has("c-04-auc")) (function () {
  const A = S4.auc;
  dotRows(has("c-04-auc"), { rows: [{ label: "Recency alone", v: A.recency[0], lo: A.recency[1], hi: A.recency[2], text: A.recency[0].toFixed(2), fcls: "f-grey", scls: "s-grey" },
    { label: "Purchase model", v: A.model[0], lo: A.model[1], hi: A.model[2], text: A.model[0].toFixed(2), strong: true }], dom: [0.68, 0.84], ticks: [0.7, 0.75, 0.8], label: 130, rh: 44 });
  const h2 = has("c-04-terc");
  if (h2) { const f = () => { const w = W(h2), L = 4, R = w - 4, h = 150, svg = svgIn(h2, w, h), bw = (R - L) / 3, y = lin(0, 100, 118, 14);
    A.terciles.forEach((t, i) => { const x0 = L + i * bw + 10, ww = bw - 20, g = el("g", { class: "hot" }, svg);
      el("rect", { x: x0, y: y(t.rate), width: ww, height: 118 - y(t.rate), rx: 6, class: ["f-light", "f-blue", "f-navy"][i] }, g);
      el("line", { x1: x0 + ww / 2, x2: x0 + ww / 2, y1: y(t.lo), y2: y(t.hi), class: "s-card", "stroke-width": 2 }, g);
      txt(g, x0 + ww / 2, y(t.rate) - 6, t.rate.toFixed(1) + "%", { "text-anchor": "middle", class: "t-strong", "font-size": 13 });
      txt(g, x0 + ww / 2, 136, `${t.t[0].toUpperCase() + t.t.slice(1)} third of scores`, { "text-anchor": "middle", class: "t-muted", "font-size": 11 });
      hoverTip(g, `${t.t} tercile, ${t.n} accounts: ${t.rate}% bought again (95% CI ${t.lo}–${t.hi}%)`); }); }; f(); redrawers.push(f); }
})();
if (has("c-04-rank")) (function () {
  const host = has("c-04-rank"), ro = has("ro-04-rank"); let k = "6", chart;
  const rows = k => { const R = S4.rank[k]; return [{ label: "Purchase model", v: R.model[0], lo: R.model[1], hi: R.model[2], text: R.model[0].toFixed(3), strong: true },
    { label: "Past-sales rule", v: R.rule[0], lo: R.rule[1], hi: R.rule[2], text: R.rule[0].toFixed(3), fcls: "f-grey", scls: "s-grey" }]; };
  chart = dotRows(host, { rows: rows(k), dom: [0.54, 0.70], ticks: [0.55, 0.6, 0.65, 0.7], label: 130, rh: 44 });
  const note = k => { const R = S4.rank[k]; ro.innerHTML = `<p class="sub" style="margin-top:8px">Holdout: ${R.label}, ${fmt(R.n)} accounts. ${R.model[0] > R.rule[0] ? "The model ranks better." : "The past-sales rule ranks better; the pre-specified rule was not met."} The two holdouts are different samples, not a trend.</p>`; };
  makeSeg(has("seg-04-rank"), [["6", "6 months ahead"], ["12", "12 months ahead"]], k, v => { chart.update(rows(v), [0.54, 0.70]); note(v); }); note(k);
})();
if (has("c-04-cal")) (function () {
  const host = has("c-04-cal");
  function draw() { const w = W(host), L = 50, R = w - 12, T = 10, B = 240, h = B + 40, svg = svgIn(host, w, h), x = lg(100, 12000, L, R), y = lg(100, 12000, B, T);
    [100, 1000, 10000].forEach(v => { el("line", { x1: L, x2: R, y1: y(v), y2: y(v), class: "gridl" }, svg); txt(svg, L - 8, y(v) + 4, "£" + fmt(v), { "text-anchor": "end", class: "t-muted", "font-size": 11 }); txt(svg, x(v), B + 18, "£" + fmt(v), { "text-anchor": "middle", class: "t-muted", "font-size": 11 }); });
    el("line", { x1: x(100), y1: y(100), x2: x(12000), y2: y(12000), class: "s-orange", "stroke-dasharray": "5 4", "stroke-width": 1.4 }, svg);
    [["ML_lgbm_tweedie", "Gradient boosting", "grey"], ["BGNBD_GG", "Purchase model", "navy"]].forEach(([k, n, c]) => { const v = S4.calibration[k];
      el("path", { d: "M" + v.map(p => [x(p[0]), y(Math.max(p[1], 100))].join(",")).join("L"), fill: "none", class: "s-" + c, "stroke-width": 2 }, svg);
      v.forEach((p, i) => { const cc = el("circle", { cx: x(p[0]), cy: y(Math.max(p[1], 100)), r: 4, class: "f-" + c }, svg); hoverTip(cc, `${n}, decile ${i + 1}: predicted £${fmt(p[0])}, actual £${fmt(p[1])}`); });
      txt(svg, x(v[v.length - 1][0]) - 8, y(v[v.length - 1][1]) + (c === "navy" ? 16 : -10), n, { "text-anchor": "end", class: (c === "navy" ? "t-navy" : "t-muted") + " halo", "font-size": 11.5 }); });
    txt(svg, (L + R) / 2, B + 34, "Mean predicted next-six-month sales, by decile of the prediction", { "text-anchor": "middle", class: "t-muted", "font-size": 11 }); }
  draw(); redrawers.push(draw);
})();
/* ---------- nav and theme ---------- */
const page = document.body.dataset.page;
document.querySelectorAll("#nav a").forEach(a => a.classList.toggle("on", a.dataset.page === page));
$("#theme").addEventListener("click", () => {
  const r = document.documentElement, dark = r.dataset.theme ? r.dataset.theme === "dark" : matchMedia("(prefers-color-scheme: dark)").matches;
  r.dataset.theme = dark ? "light" : "dark"; redrawers.forEach(f => f());
});
})();
