import { Disclosure } from "../components/Primitives.jsx";
export const percent = value => Number.isFinite(value) && value >= 0 && value <= 1 ? `${Math.round(value * 100)}%` : "Not provided";
export default function AuditOverview({ machine, findings = [] }) {
  if (!machine) return <div className="empty-state"><h2 id="overview-title">Audit overview</h2><p>Structured report data is unavailable for this run. Open the report above to inspect its results.</p></div>;
  const summary = machine?.executiveSummary || {};
  const axes = Array.isArray(machine?.axes) ? machine.axes : [];
  const coverage = machine?.coverage?.summary;
  const counts = machine?.audit_extraction?.counts;
  const severities = ["critical", "high", "medium", "low", "info"];
  const unknownSeverity = findings.filter(item => !severities.includes(item.severity)).length;
  return <div className="audit-overview">
    <section className="overview-summary" aria-labelledby="overview-title">
      <div><p className="eyebrow">Measurement & evidence</p><h2 id="overview-title">Audit overview</h2><p className="reading">{summary.summary || "Inspect the measured dimensions, check the evidence, and record your judgment."}</p></div>
      <div className="overall-score"><span>Overall score</span><strong>{summary.overallScored !== false && Number.isFinite(summary.overallScore) ? <>{summary.overallScore}<small> / 100</small></> : "Not measured"}</strong><span>Measurement coverage · {percent(summary.overallCoverage)}</span></div>
    </section>
    <div className="overview-columns">
      <section className="axis-section" aria-labelledby="axes-title"><div className="section-row"><h3 id="axes-title">UX/UI dimensions</h3>{machine?.axisMethodologyVersion && <span className="metadata">Methodology v{machine.axisMethodologyVersion}</span>}</div><p className="section-caption">Score describes the result. Coverage describes how much was measured.</p>
      {axes.length ? <div className="axis-scorecard">{axes.map((axis, index) => {
        const score = axis.scored !== false && Number.isFinite(axis.score) ? axis.score : null;
        const measured = axis.signals?.measurementCoverage;
        return <Disclosure key={axis.id || index} title={<span className="axis-row"><span className="axis-name">{axis.name || axis.shortName || axis.id}</span><span className="axis-result"><strong>{score === null ? "Not measured" : `${score} / 100`}</strong><span className="score-track" aria-hidden="true">{score !== null && <i style={{ width: `${Math.max(0, Math.min(100, score))}%` }}/>}</span></span><span className="axis-coverage"><strong>{percent(measured)}</strong><span>coverage</span></span></span>}>
          {axis.summary && <p>{axis.summary}</p>}{axis.scoreReason && <p>{axis.scoreReason}</p>}
          <dl className="facts-inline">{Number.isFinite(axis.confidence) && <div><dt>Reported confidence</dt><dd>{percent(axis.confidence)} · not a statistical guarantee</dd></div>}{["measuredRules", "applicableRules", "unknownRules", "notMeasuredRules", "collectionFailedRules"].filter(key => Number.isFinite(axis.signals?.[key])).map(key => <div key={key}><dt>{({ measuredRules: "Measured rules", applicableRules: "Applicable rules", unknownRules: "Unknown rules", notMeasuredRules: "Not measured", collectionFailedRules: "Collection failed" })[key]}</dt><dd>{axis.signals[key]}</dd></div>)}</dl>
          {Number.isFinite(axis.signals?.visionScore) && <p>Model visual assessment: {axis.signals.visionScore} / 100. Separate from measured score.</p>}
          {axis.missingContext?.length > 0 && <p>Missing context: {Array.isArray(axis.missingContext) ? axis.missingContext.join(" · ") : axis.missingContext}</p>}
        </Disclosure>;
      })}</div> : <p className="empty-state">This report does not provide dimension scores. No scores have been inferred.</p>}
      {summary.overallReason && <p className="section-caption">{summary.overallReason}</p>}</section>
      <aside className="overview-attention">
        <section><h3>Findings summary</h3><p className="finding-total"><strong>{findings.length}</strong> issues detected</p><div className="distribution">{severities.filter(level => findings.some(item => item.severity === level)).map(level => <div key={level} className={`severity-count severity-${level}`}><span>{level}</span><strong>{findings.filter(item => item.severity === level).length}</strong></div>)}{unknownSeverity > 0 && <span>{unknownSeverity} with no mapped severity</span>}</div></section>
      </aside>
    </div>
    <section className="scope-section"><h3>Collection scope</h3>{coverage ? <><dl className="facts-inline">{["discovered", "selected", "completed", "failed", "excluded"].filter(key => Number.isFinite(coverage[key])).map(key => <div key={key}><dt>{key === "completed" ? "Pages collected" : `Pages ${key}`}</dt><dd>{coverage[key]}</dd></div>)}<div><dt>Collection coverage</dt><dd>{percent(coverage.coverageRatio)}{coverage.coverageStatus ? ` · ${coverage.coverageStatus}` : ""}</dd></div></dl><p className="section-caption">Collection coverage counts captured pages. Measurement coverage counts evaluated rules.</p></> : counts ? <dl className="facts-inline">{["pages", "frames", "nodes", "text_nodes"].filter(key => Number.isFinite(counts[key])).map(key => <div key={key}><dt>{key.replaceAll("_", " ")}</dt><dd>{counts[key]}</dd></div>)}</dl> : <p>Collection coverage is not provided by this report.</p>}
      {machine?.scannedPages?.length > 0 && <Disclosure title={`Captured pages · ${machine.scannedPages.length}`}><ul className="scope-pages">{machine.scannedPages.map((page, index) => <li key={index}><strong>{page.title || page.page_name}</strong><span>{page.page_url || "URL not provided"}</span></li>)}</ul></Disclosure>}
      {machine?.warnings?.length > 0 && <Disclosure title={`Source warnings · ${machine.warnings.length}`}><pre tabIndex={0}>{JSON.stringify(machine.warnings, null, 2)}</pre></Disclosure>}
      {machine?.draft_analysis?.draft_issues?.length > 0 && <p className="section-caption">Figma also returned {machine.draft_analysis.draft_issues.length} draft detections. These are not final findings; inspect the source artifact for detector details.</p>}
    </section>
  </div>;
}
