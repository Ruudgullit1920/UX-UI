import { useEffect, useState } from "react";
import Icon from "../components/Icon.jsx";
import Icon3D from "../components/Icon3D.jsx";
import capture from "./assets/w3c-bad-citylights.jpg";
import logo from "../assets/ey-studio-plus.png";

// Real capture of W3C's Before-and-After Demonstration (inaccessible home page). One finding per UX dimension:
// the contrast result is measured by axe-core 4.11 (assets/w3c-bad-axe.json); the others are expert observations
// of what is visible in this capture. Boxes are element bounds in the 780×560 capture.
const W = 780, H = 560, SCAN_MS = 3000;
const FINDINGS = [
  { dim: "Task & Interaction", text: "Quick menu is a bare dropdown with no label or Go button", severity: "High", source: "Expert review", box: [626, 33, 145, 19] },
  { dim: "Hierarchy & Consistency", text: "Three competing type styles in one column", severity: "Low", source: "Expert review", box: [175, 144, 434, 69] },
  { dim: "IA & Navigation", text: "Menu doesn’t show which page you’re on", severity: "Medium", source: "Expert review", box: [0, 146, 155, 140], below: true },
  { dim: "Accessibility", text: "Contrast 3.88:1, needs 4.5:1", severity: "High", source: "Measured · axe-core", box: [635, 149, 104, 16] },
  { dim: "Content & Guidance", text: "“MORE” links don’t say where they lead", severity: "Medium", source: "Expert review", box: [180, 487, 48, 16], below: true },
].map(item => ({ ...item, delay: 250 + Math.round(item.box[1] / H * SCAN_MS) }));
const DIMENSIONS = ["Task & Interaction", "IA & Navigation", "Accessibility", "Hierarchy & Consistency", "Content & Guidance"];
const SOURCES = [["website", "Website"], ["screenshot", "Screenshots"], ["mobile", "Android app"], ["figma", "Figma"]];

function reducedMotion() {
  try { return window.matchMedia("(prefers-reduced-motion: reduce)").matches; } catch { return false; }
}

function AuditDemo() {
  const [run, setRun] = useState(0);
  const [done, setDone] = useState(reducedMotion);
  useEffect(() => {
    if (reducedMotion()) { setDone(true); return undefined; }
    setDone(false);
    const timer = setTimeout(() => setDone(true), SCAN_MS + 600);
    return () => clearTimeout(timer);
  }, [run]);
  const pct = (value, total) => `${(value / total) * 100}%`;
  return <figure className={`lp-demo ${done ? "is-done" : "is-running"}`} key={run}>
    <div className="lp-browser">
      <div className="lp-browser-bar" aria-hidden="true"><i/><i/><i/><span>citylights · W3C demo site</span></div>
      <div className="lp-shot">
        <img src={capture} width={W} height={H} alt="Home page of Citylights, W3C’s intentionally inaccessible demonstration site."/>
        <span className="lp-scan" aria-hidden="true"/>
        {FINDINGS.map(({ dim, box: [x, y, w, h], delay, below, tagAt }) => <span key={dim} className={`lp-box ${below ? "is-below" : ""} ${tagAt === "right" ? "tag-right" : ""}`} aria-hidden="true" style={{ left: pct(x, W), top: pct(y, H), width: pct(w, W), height: pct(h, H), animationDelay: `${delay}ms` }}><b>{dim}</b></span>)}
      </div>
    </div>
    <div className="lp-log">
      <p className="lp-log-status" role="status">{done ? <><Icon name="check" size={14}/> UX/UI audit complete</> : <><span className="lp-spinner" aria-hidden="true"/> Auditing 5 UX dimensions…</>}</p>
      <ul className="lp-dims" aria-label="Dimensions checked">{DIMENSIONS.map(dim => { const hit = FINDINGS.find(item => item.dim === dim); return <li key={dim} style={{ animationDelay: `${hit.delay}ms` }}>{dim}</li>; })}</ul>
      <ol>{FINDINGS.map(({ dim, text, severity, source, delay }) => <li key={dim} style={{ animationDelay: `${delay}ms` }}><span className={`lp-impact is-${severity.toLowerCase()}`}>{severity}</span><span className="lp-row-dim">{dim}</span><strong>{text}</strong><span className="lp-wcag">{source}</span></li>)}</ol>
      <div className="lp-log-foot"><span><b>5</b> of 5 dimensions checked</span><button type="button" onClick={() => setRun(value => value + 1)} disabled={!done}>Replay</button></div>
    </div>
    <figcaption>Real capture of W3C’s Before-and-After Demonstration (inaccessible version). Contrast is measured by axe-core 4.11; the other findings are expert review of this capture.</figcaption>
  </figure>;
}

const BENEFITS = [
  { icon: "evidence", title: "Proof for every finding", text: "Each issue points to the element, the screen and the rule it breaks.", proof: <code>select · WCAG 4.1.2 · axe-core</code> },
  { icon: "coverage", title: "Scores you can trust", text: "Every score shows how much of the page was actually measured.", proof: <span className="lp-meter"><span>Coverage</span><i><b style={{ width: "85%" }}/></i><em>85%</em></span> },
  { icon: "review", title: "A specialist signs off", text: "Findings are reviewed and edited before a report is published.", proof: <span className="lp-flow"><span>Draft</span><Icon name="arrow" size={12}/><span>Saved</span><Icon name="arrow" size={12}/><span className="is-on">Deployed</span></span> },
];

export default function Landing() {
  return <div className="lp">
    <a className="skip-link" href="#main-content">Skip to content</a>
    <header className="lp-header"><a className="brand lp-brand" href="/" aria-label="EY Studio Plus home"><img className="brand-logo" src={logo} alt="" width="1000" height="390"/></a></header>
    <main id="main-content" tabIndex={-1} className="lp-main">
      <section className="lp-hero" aria-labelledby="lp-title">
        <div className="lp-intro">
          <p className="eyebrow">UX/UI Auditor</p>
          <h1 id="lp-title">UX/UI audits you can trace back to <span className="lp-word">evidence<i/><i/><i/><i/></span>.</h1>
          <p className="lp-lead">Point it at a product. It captures the screens, checks them against five UX dimensions and pins every issue to the element behind it, ready for your review.</p>
          <a className="lp-cta" href="/app">Start an audit<Icon name="arrow" size={18}/></a>
          <div className="lp-sources"><span>Website, screenshots, Android app or Figma</span><ul>{SOURCES.map(([id, label]) => <li key={id} title={label}><Icon3D name={id} size={30}/><span className="sr-only">{label}</span></li>)}</ul></div>
        </div>
        <AuditDemo/>
      </section>
      <ul className="lp-benefits" aria-label="Why teams use it">{BENEFITS.map(({ icon, title, text, proof }) => <li key={icon}><Icon3D name={icon} size={48}/><h2>{title}</h2><p>{text}</p><div className="lp-proof">{proof}</div></li>)}</ul>
    </main>
    <footer className="lp-footer"><span>Built around evidence. Refined by human judgment.</span><span>Automated checks support a WCAG review; they don’t replace it.</span></footer>
  </div>;
}
