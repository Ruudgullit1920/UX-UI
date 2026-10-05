import { useState } from "react";
import { Button, Disclosure, ErrorAlert, Field, InlineAlert } from "../components/Primitives.jsx";
export default function MobileFields({ api, values, setValues, update }) {
  const [discovery, setDiscovery] = useState(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState(null);
  async function discover() {
    setBusy(true); setError(null);
    try {
      const result = await api.json(await api.request("/api/mobile/discovery"), "Unable to discover Android devices.");
      setDiscovery(result); setValues(old => ({ ...old, ...result.defaults, ...(result.currentApp || {}) }));
    } catch (e) { setError(e); } finally { setBusy(false); }
  }
  return <><div className="runtime-note"><p>Connect an Android device or emulator to the audit server. A running Appium server and ADB are required.</p><Button onClick={discover} disabled={busy}>{busy ? "Discovering…" : "Discover device & apps"}</Button></div><ErrorAlert error={error} title="Device discovery unavailable"/>{discovery && <InlineAlert tone="info" title={discovery.selectedDevice ? `${discovery.selectedDevice.deviceName} · ${discovery.selectedDevice.state}` : "No device found"}>{discovery.selectedDevice ? "Detected app and device details are filled below. Check them before starting." : "Connect and authorize a device, or enter its details manually."}{discovery.warnings?.length > 0 && <Disclosure title="Discovery details">{discovery.warnings.map((warning, index) => <p key={index}>{warning}</p>)}</Disclosure>}</InlineAlert>}{discovery?.launchableApps?.length > 0 && <Field label="Detected app" as="select" value={values.appPackage || ""} onChange={e => { const app = discovery.launchableApps.find(item => item.appPackage === e.target.value); if (app) setValues(old => ({ ...old, ...app })); }}><option value="">Choose an app</option>{discovery.launchableApps.map(app => <option key={app.appPackage} value={app.appPackage}>{app.appLabel} · {app.appPackage}</option>)}</Field>}<div className="field-grid"><Field label="App package" hint="The Android app identifier, such as com.example.app." required name="appPackage" value={values.appPackage || ""} onChange={update} placeholder="com.example.app"/><Field label="Launch activity" hint="The screen Android opens, such as .MainActivity." required name="appActivity" value={values.appActivity || ""} onChange={update} placeholder=".MainActivity"/></div><Disclosure title="Advanced · device & connection"><div className="field-grid">{[["appLabel", "App name"], ["appiumUrl", "Appium server URL"], ["deviceName", "Device name"], ["platformVersion", "Android version"], ["udid", "Device identifier (UDID)"]].map(([name, label]) => <Field key={name} label={label} name={name} type={name === "appiumUrl" ? "url" : "text"} value={values[name] || ""} onChange={update}/>)}</div></Disclosure></>;
}
