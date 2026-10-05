"""Serve a local-only, persistent draft editor for a finished report.

It never touches audit inputs or the stakeholder export. Draft changes are kept
next to the editable copy and are intentionally not publishable from this UI.
"""
from __future__ import annotations

import argparse
import json
import shutil
from datetime import datetime
from http import HTTPStatus
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse


EDITOR_SCRIPT = r"""
<style>
  #local-draft-toolbar{position:sticky;top:0;z-index:99;display:flex;gap:12px;align-items:center;padding:12px 18px;background:#202733;color:#fff;font:600 14px/1.3 system-ui,sans-serif;box-shadow:0 2px 12px #0003}
  #local-draft-toolbar button{border:0;border-radius:8px;padding:8px 12px;font:inherit;cursor:pointer}.draft-save{background:#ffd900;color:#202733}.draft-status{font-weight:400;color:#d8dde5}
  [data-draft-editing="true"]{outline:2px dashed #caa23b;outline-offset:4px;cursor:text}.issue-thumb[data-draft-editing="true"]{cursor:pointer}
</style>
<div id="local-draft-toolbar" data-editor-version="2"><strong>Local draft editor</strong><button id="draft-enable" type="button">Enable editing</button><button class="draft-save" id="draft-save" type="button" disabled>Save draft</button><span class="draft-status" id="draft-status">Loading saved draft…</span><span class="draft-status">Deployment is disabled in this editor.</span></div>
<input id="draft-image-input" type="file" accept="image/*" hidden>
<script>
(() => {
  const editable = [...document.querySelectorAll('[data-editable-field], [data-reco-editable], .issue-card h3')];
  const images = [...document.querySelectorAll('.issue-thumb')];
  const status = document.querySelector('#draft-status'); const save = document.querySelector('#draft-save');
  let enabled = false, dirty = false, selectedImage = null;
  editable.forEach((node, index) => node.dataset.draftKey = `text-${index}`);
  images.forEach((node, index) => node.dataset.draftImageKey = `image-${index}`);
  const setStatus = text => status.textContent = text;
  async function load() { const r = await fetch('/api/overrides'); const draft = r.ok ? await r.json() : {}; Object.entries(draft.text || {}).forEach(([key, value]) => { const node = document.querySelector(`[data-draft-key="${key}"]`); if (node) node.textContent = value; }); Object.entries(draft.images || {}).forEach(([key, value]) => { const node = document.querySelector(`[data-draft-image-key="${key}"]`); if (node) node.src = value; }); setStatus(draft.savedAt ? `Saved locally: ${new Date(draft.savedAt).toLocaleString()}` : 'No saved draft yet.'); }
  function setEnabled(next) { enabled = next; editable.forEach(node => { node.contentEditable = next ? 'true' : 'false'; node.dataset.draftEditing = String(next); }); images.forEach(node => node.dataset.draftEditing = String(next)); document.querySelector('#draft-enable').textContent = next ? 'Finish editing' : 'Enable editing'; }
  function markDirty() { dirty = true; save.disabled = false; setStatus('Unsaved local changes'); }
  async function persist() { const text = Object.fromEntries(editable.map(node => [node.dataset.draftKey, node.textContent])); const images = Object.fromEntries(imagesFromPage()); const r = await fetch('/api/overrides', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({text, images})}); if (!r.ok) throw new Error('Save failed'); const draft = await r.json(); dirty=false; save.disabled=true; setStatus(`Saved locally: ${new Date(draft.savedAt).toLocaleString()}`); }
  function imagesFromPage() { return images.filter(node => node.src.startsWith('data:image/')).map(node => [node.dataset.draftImageKey, node.src]); }
  document.querySelector('#draft-enable').addEventListener('click', () => setEnabled(!enabled));
  save.addEventListener('click', () => persist().catch(() => setStatus('Could not save draft.')));
  editable.forEach(node => node.addEventListener('input', markDirty));
  images.forEach(node => node.addEventListener('click', () => { if (enabled) { selectedImage = node; document.querySelector('#draft-image-input').click(); } }));
  document.querySelector('#draft-image-input').addEventListener('change', event => { const file = event.target.files && event.target.files[0]; if (!file || !selectedImage) return; const reader = new FileReader(); reader.onload = () => { selectedImage.src = reader.result; markDirty(); }; reader.readAsDataURL(file); });
  window.addEventListener('beforeunload', event => { if (dirty) { event.preventDefault(); event.returnValue = ''; } });
  load().catch(() => setStatus('No saved draft yet.'));
})();
</script>
"""


def prepare(report_dir: Path) -> tuple[Path, Path]:
    editable = report_dir / "editable"
    editable.mkdir(exist_ok=True)
    backup_root = report_dir / "backups"
    backup_root.mkdir(exist_ok=True)
    backup = backup_root / f"pre_manual_edit_{datetime.now():%Y%m%d_%H%M%S}"
    backup.mkdir()
    shutil.copy2(report_dir / "index.html", backup / "index.html")
    draft = editable / "index.html"
    # Controls must run after the report markup.  The older draft placed them
    # immediately after <body>, before any editable report fields existed.
    # Rebuilding this local shell preserves saved overrides in the separate
    # JSON draft file and never changes the stakeholder export.
    needs_draft_shell = not draft.exists() or 'data-editor-version="2"' not in draft.read_text(encoding="utf-8")
    if needs_draft_shell:
        html = (report_dir / "index.html").read_text(encoding="utf-8")
        html = html.replace("<head>", '<head><base href="../">', 1)
        html = html.replace("</body>", EDITOR_SCRIPT + "</body>", 1)
        draft.write_text(html, encoding="utf-8")
    overrides = editable / "manual_overrides.json"
    if not overrides.exists():
        overrides.write_text(json.dumps({"text": {}, "images": {}}, indent=2), encoding="utf-8")
    return draft, backup


class Handler(SimpleHTTPRequestHandler):
    directory: Path
    overrides: Path

    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(self.directory), **kwargs)

    def do_GET(self):
        if urlparse(self.path).path == "/api/overrides":
            body = self.overrides.read_bytes()
            self.send_response(HTTPStatus.OK); self.send_header("Content-Type", "application/json"); self.send_header("Content-Length", str(len(body))); self.end_headers(); self.wfile.write(body); return
        return super().do_GET()

    def do_POST(self):
        if urlparse(self.path).path != "/api/overrides":
            self.send_error(HTTPStatus.NOT_FOUND); return
        length = int(self.headers.get("Content-Length", "0"))
        if length > 25_000_000:
            self.send_error(HTTPStatus.REQUEST_ENTITY_TOO_LARGE); return
        try:
            value = json.loads(self.rfile.read(length).decode("utf-8"))
            if not isinstance(value.get("text"), dict) or not isinstance(value.get("images"), dict): raise ValueError
            value["savedAt"] = datetime.now().astimezone().isoformat()
            self.overrides.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")
            body = json.dumps(value, ensure_ascii=False).encode("utf-8")
            self.send_response(HTTPStatus.OK); self.send_header("Content-Type", "application/json"); self.send_header("Content-Length", str(len(body))); self.end_headers(); self.wfile.write(body)
        except (ValueError, json.JSONDecodeError):
            self.send_error(HTTPStatus.BAD_REQUEST)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--report-dir", required=True, type=Path)
    parser.add_argument("--port", type=int, default=8791)
    args = parser.parse_args()
    report = args.report_dir.resolve()
    draft, backup = prepare(report)
    Handler.directory = draft.parent
    Handler.overrides = draft.parent / "manual_overrides.json"
    server = ThreadingHTTPServer(("127.0.0.1", args.port), Handler)
    print(f"Editable report: http://127.0.0.1:{args.port}/")
    print(f"Draft: {draft}")
    print(f"Backup: {backup}")
    server.serve_forever()


if __name__ == "__main__":
    main()
