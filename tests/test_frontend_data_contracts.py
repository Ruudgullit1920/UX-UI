"""Security and normalization contracts for report-provided frontend data."""
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_frontend_artifact_paths_are_owned_and_do_not_forward_credentials():
    module = (ROOT / "src/ui/frontend/api/artifacts.js").as_uri()
    script = """
      const { evidencePath, machineFindings, machinePaths } = await import(MODULE);
      const job = {id: 'abc123', type: 'website'};
      const allowed = [
        'C:/repo/shared/audits/abc123/screenshots/page.png',
        'shared/generated/mobile-audits/abc123/capture.png',
        '/artifacts/shared/audits/abc123/audit/evidence.json'
      ];
      const blocked = [
        'https://evil.test/shared/audits/abc123/image.png',
        'shared/audits/other/image.png',
        'shared/audits/abc123/../other/image.png',
        'shared/audits/abc123/%2e%2e/image.png',
        'shared/audits/abc123/file.png?token=secret',
        'unowned.png'
      ];
      for (const path of allowed) if (!evidencePath(path, job)?.startsWith('/artifacts/shared/')) throw new Error(path);
      for (const path of blocked) if (evidencePath(path, job) !== null) throw new Error(path);
      const canonical = {deduplicatedFindings: [], axes:[{id:'a',painPoints:[{title:'Not canonical'}]}]};
      if (machineFindings(canonical).length !== 0) throw new Error('Empty canonical collection replaced');
      const legacy = machineFindings({axes:[{id:'accessibility',name:'Accessibility',painPoints:[{title:'Check'}]}]});
      if (legacy[0].axisName !== 'Accessibility') throw new Error('Lost source dimension');
      if (!machinePaths({id:'abc123',type:'figma'})[0].endsWith('/data/final_result.json')) throw new Error('Figma path');
    """.replace("MODULE", json.dumps(module))
    subprocess.run(["node", "--input-type=module", "-e", script], cwd=ROOT, check=True, capture_output=True, text=True)
