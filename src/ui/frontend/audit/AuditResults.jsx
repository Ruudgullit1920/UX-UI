import Icon from "../components/Icon.jsx";
import { machineFindings } from "../api/artifacts.js";
import AuditOverview from "./AuditOverview.jsx";

export default function AuditResults({ job, machine }) {
  if (job.status !== "completed") return null;
  const data = machine?.data || machine;
  const findings = machineFindings(data);
  return <><a className="report-open-button" href={`/report/${encodeURIComponent(job.id)}`}><Icon name="report" size={18}/><span>Open report</span><span aria-hidden="true">↗</span></a><section className="audit-content audit-overview-panel"><AuditOverview machine={data} findings={findings}/></section></>;
}
