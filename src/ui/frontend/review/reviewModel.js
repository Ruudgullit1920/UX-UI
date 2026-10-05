export function cleanChanges(changes) {
  return Object.fromEntries(Object.entries(changes).flatMap(([id, fields]) => {
    const cleaned = Object.fromEntries(Object.entries(fields).filter(([key, value]) => !((key === "reviewDecision" || key === "priorityOverride") && !value)));
    return Object.keys(cleaned).length ? [[id, cleaned]] : [];
  }));
}
export function validateChanges(changes) {
  const entries = Object.entries(changes);
  if (!entries.length) return "Add a review decision, note, or recommendation before saving.";
  if (entries.length > 100) return "A revision can contain at most 100 finding changes.";
  for (const [id, fields] of entries) {
    if (!id || id.length > 160) return "This finding does not have a supported identifier.";
    if (fields.suppressed && !fields.suppressionReason?.trim()) return "Add a suppression reason for every suppressed finding.";
    if (["reviewNote", "reviewedRecommendation", "suppressionReason"].some(key => (fields[key] || "").length > 1200)) return "Review text must be 1,200 characters or fewer.";
  }
  return "";
}
export function revisionActions(status, dirty, conflict, busy) {
  const blocked = dirty || conflict || busy;
  return { validate: status === "in_review" && !blocked, approve: status === "validated" && !blocked, publish: ["validated", "approved"].includes(status) && !blocked };
}
