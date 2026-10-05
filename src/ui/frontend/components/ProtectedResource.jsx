import { useState } from "react";
import { Button, ErrorAlert } from "./Primitives.jsx";

// Authenticate only requests to this API origin. Never put a bearer in a URL.
function resourcePath(api, value, parent) {
  const base = new URL(api.url("/"), window.location.origin);
  const target = new URL(value, parent || base);
  if (target.origin !== base.origin || !/^\/(audits|artifacts|static|api\/audits)\//.test(target.pathname)) throw new Error("This resource is outside the audit server.");
  return target.pathname + target.search;
}
async function fetchResource(api, path) {
  const response = await api.request(path);
  if (!response.ok) await api.json(response, "This report or artifact is unavailable.");
  return response;
}
const dataUrl = blob => new Promise((resolve, reject) => { const reader = new FileReader(); reader.onload = () => resolve(reader.result); reader.onerror = reject; reader.readAsDataURL(blob); });
export async function prepareReport(api, path) {
  const response = await fetchResource(api, path);
  const doc = new DOMParser().parseFromString(await response.text(), "text/html");
  const parent = new URL(api.url(path), location.origin);
  // Embed protected assets so the isolated report does not need access to session credentials.
  await Promise.all([...doc.querySelectorAll("img[src],script[src],link[rel=stylesheet][href]")].map(async element => {
    const attribute = element.tagName === "LINK" ? "href" : "src";
    const source = element.getAttribute(attribute);
    if (!source || source.startsWith("data:")) return;
    const assetPath = resourcePath(api, source, parent);
    const asset = await fetchResource(api, assetPath);
    if (element.tagName === "SCRIPT") { element.removeAttribute("src"); element.textContent = await asset.text(); }
    else if (element.tagName === "LINK") { const style = doc.createElement("style"); style.textContent = await asset.text(); element.replaceWith(style); }
    else { element.setAttribute("src", await dataUrl(await asset.blob())); element.removeAttribute("srcset"); }
  }));
  doc.querySelectorAll("base").forEach(element => element.remove());
  const wrapper = document.implementation.createHTMLDocument("Audit report");
  wrapper.documentElement.lang = "en";
  const frame = wrapper.createElement("iframe");
  frame.title = "Audit report"; frame.setAttribute("sandbox", "allow-scripts");
  frame.setAttribute("style", "position:fixed;inset:0;width:100%;height:100%;border:0");
  frame.srcdoc = new XMLSerializer().serializeToString(doc);
  wrapper.body.append(frame);
  return new Blob([new XMLSerializer().serializeToString(wrapper)], { type: "text/html" });
}
export default function ProtectedResource({ api, path, children, variant = "secondary", report = false }) {
  const [busy, setBusy] = useState(false); const [error, setError] = useState(null);
  async function open() {
    setBusy(true); setError(null);
    // Reserve the tab during the user gesture, before the authenticated request.
    const tab = window.open("about:blank", "_blank");
    if (tab) tab.opener = null;
    try {
      if (!tab) throw new Error("Allow a new browser tab to open this resource.");
      const safePath = resourcePath(api, path);
      const blob = report ? await prepareReport(api, safePath) : await (await fetchResource(api, safePath)).blob();
      const url = URL.createObjectURL(blob);
      tab.location.replace(url);
      window.setTimeout(() => URL.revokeObjectURL(url), 60000);
    } catch (e) { tab?.close(); setError(e); } finally { setBusy(false); }
  }
  return <div className="resource-action"><Button variant={variant} disabled={busy} onClick={open}>{busy ? "Opening…" : children}</Button><ErrorAlert error={error} title="Couldn’t open this resource"/></div>;
}
