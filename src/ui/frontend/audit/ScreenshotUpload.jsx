import { useRef, useState } from "react";
import { Button, InlineAlert } from "../components/Primitives.jsx";
import Icon from "../components/Icon.jsx";
export default function ScreenshotUpload({ files, onChange }) {
  const input = useRef(null);
  const [dragging, setDragging] = useState(false);
  const [error, setError] = useState("");
  function add(incoming) {
    const supported = [...incoming].filter(file => ["image/png", "image/jpeg", "image/webp"].includes(file.type));
    setError(supported.length !== incoming.length ? "Choose PNG, JPEG, or WebP images. Other files were not added." : "");
    const combined = [...files];
    for (const file of supported) if (!combined.some(item => item.name === file.name && item.size === file.size && item.lastModified === file.lastModified)) combined.push(file);
    onChange(combined);
  }
  return <div className="upload-section"><div className={`upload-zone ${dragging ? "is-dragging" : ""}`} onDragOver={e => { e.preventDefault(); setDragging(true); }} onDragLeave={() => setDragging(false)} onDrop={e => { e.preventDefault(); setDragging(false); add(e.dataTransfer.files); }}><Icon name="upload" size={30}/><strong>Drop your screenshots here</strong><span>or select images from your device</span><Button onClick={() => input.current.click()}>Choose files</Button><input ref={input} className="sr-only" tabIndex={-1} type="file" aria-label="Choose screenshots" accept="image/png,image/jpeg,image/webp" multiple onChange={e => { add(e.target.files); e.target.value = ""; }}/><p className="field-hint">PNG, JPEG, WebP · File size, dimensions, and count are checked by the server.</p></div>{error && <InlineAlert title="Unsupported file">{error}</InlineAlert>}<p className="sr-only" role="status">{files.length} screenshots selected</p>{files.length > 0 && <ul className="file-list">{files.map((file, index) => <li key={`${file.name}-${file.lastModified}`}><Icon name="screenshot"/><div><strong>{file.name}</strong><span>{(file.size / 1024 / 1024).toFixed(2)} MB</span></div><Button variant="quiet" aria-label={`Remove ${file.name}`} onClick={() => onChange(files.filter((_, i) => i !== index))}><Icon name="close" size={18}/></Button></li>)}</ul>}</div>;
}
