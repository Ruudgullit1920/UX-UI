import { useId } from "react";
import Icon from "./Icon.jsx";
export function Button({ variant = "secondary", className = "", children, ...props }) {
  return <button type="button" className={`button button-${variant} ${className}`} {...props}>{children}</button>;
}
export function Field({ label, hint, as: Control = "input", children, ...props }) {
  const id = useId();
  return <div className="field"><label htmlFor={id}>{label}</label><Control id={id} aria-describedby={hint ? `${id}-hint` : undefined} {...props}>{children}</Control>{hint && <p className="field-hint" id={`${id}-hint`}>{hint}</p>}</div>;
}
const labels = { unreviewed: "Not reviewed", "machine-unreviewed": "Not reviewed", in_review: "In review", changes_requested: "Changes requested", validated: "Validated", approved: "Approved", queued: "Queued", running: "Running", completed: "Completed", failed: "Failed", cancelled: "Cancelled", interrupted: "Interrupted" };
export function StatusBadge({ status }) { return <span className={`status-badge status-${status}`}><span aria-hidden="true" className="status-dot"/>{labels[status] || status}</span>; }
export function Disclosure({ title, children, ...props }) { return <details className="disclosure" {...props}><summary>{title}</summary><div className="disclosure-content">{children}</div></details>; }
export function InlineAlert({ title, children, tone = "error", details, action }) {
  return <div className={`inline-alert alert-${tone}`} role={tone === "error" ? "alert" : "status"}><Icon name="info"/><div><strong>{title}</strong>{children && <div>{children}</div>}{details && <Disclosure title="Details"><pre tabIndex={0}>{details}</pre></Disclosure>}{action}</div></div>;
}
export function ErrorAlert({ error, title, action }) {
  if (!error) return null;
  const auth = error.status === 401 || error.status === 403;
  return <InlineAlert title={auth ? "Your session needs attention" : title || "Something went wrong"} details={[error.message || String(error), error.requestId && `Request ID: ${error.requestId}`].filter(Boolean).join("\n")} action={action}>{auth ? "Sign in through your portal, then try again." : "Your changes are still here. Check the details and try again."}</InlineAlert>;
}
export function formatDate(value) {
  if (!value) return "";
  const date = new Date(typeof value === "number" ? value * 1000 : value);
  return Number.isNaN(date.getTime()) ? "" : date.toLocaleString(undefined, { dateStyle: "medium", timeStyle: "short" });
}
