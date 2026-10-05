// These are existing, owner-protected artifact routes used by the pipelines.
export function machinePaths(job) {
  const id = encodeURIComponent(job.id);
  if (job.inputType === "screenshot") return [`/artifacts/shared/generated/screenshot-audits/${id}/screenshot_gtm_audit.json`];
  if (job.type === "mobile") return [`/artifacts/shared/generated/mobile-audits/${id}/mobile_gtm_audit.json`];
  if (job.type === "figma") return [`/artifacts/shared/generated/figma-audits/${id}/data/final_result.json`];
  return [`/artifacts/shared/audits/${id}/audit/gtm_audit.json`, `/artifacts/shared/audits/${id}/extraction/audit_results.json`];
}
export async function getMachineAudit(api, job) {
  if (job.artifactsDeleted) return null;
  for (const path of machinePaths(job)) {
    const response = await api.request(path);
    if (response.status === 404) continue;
    return { data: await api.json(response, "Unable to load audit evidence."), path };
  }
  return null;
}
export const findingId = finding => String(finding.findingId || finding.id || finding.deduplicationId || "");
export function machineFindings(machine) {
  const list = machine?.allFindings || machine?.findings || machine?.deduplicatedFindings || machine?.audit?.issues || (machine?.axes || []).flatMap(axis => (axis.painPoints || []).map(item => ({ ...item, axisId: axis.id, axisName: axis.name })));
  return Array.isArray(list) ? list.filter(item => item && typeof item === "object") : [];
}

// Accept only artifacts belonging to this run. Never send bearer credentials to a report-provided URL.
export function evidencePath(value, job) {
  if (typeof value !== "string" || /[?#\u0000]/.test(value)) return null;
  const normalized = value.replaceAll("\\", "/");
  if (normalized.split("/").some(part => part === ".." || part === ".") || /%|^https?:/i.test(normalized)) return null;
  const roots = [`shared/audits/${job.id}/`, ...["screenshot", "mobile", "figma"].map(kind => `shared/generated/${kind}-audits/${job.id}/`)];
  for (const root of roots) {
    const index = normalized.indexOf(root);
    if (index >= 0 && (index === 0 || normalized[index - 1] === "/")) return `/artifacts/${normalized.slice(index).split("/").map(encodeURIComponent).join("/")}`;
  }
  return null;
}
