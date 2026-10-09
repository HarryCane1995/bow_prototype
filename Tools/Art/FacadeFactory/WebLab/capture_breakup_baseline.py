"""One-time pre-change reference for the 0.2 baked renderer."""
import hashlib
import json
from pathlib import Path
from lab_backend import FINGERPRINT, config, Lab, ROOT, FACTORY

out = Path(__file__).parent / 'review' / 'breakup'
out.mkdir(parents=True, exist_ok=True)
if (out/'baseline.json').exists():
    raise SystemExit('Pre-change baseline already exists; refusing to replace it.')
lab = Lab(cache=out/'baseline_cache')
records = {}
for item in config()['presets']:
    result = lab.preview(item['defaults'])
    records[item['name']] = {k: result[k] for k in ('recipe','sha256','structure_hash')}
protected = {}
for directory in ('Assets/Textures/Levels/Level_01/FacadeFactory', 'Assets/Materials/Environment/FacadeFactory', 'Scripts/Player', 'Scenes/Player.tscn', 'Resources/Tuning'):
    path = ROOT/directory
    for file in ([path] if path.is_file() else path.rglob('*')):
        if file.is_file(): protected[file.relative_to(ROOT).as_posix()] = hashlib.sha256(file.read_bytes()).hexdigest()
source = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in FACTORY.glob('*.py')}
(out/'baseline.json').write_text(json.dumps(dict(fingerprint=FINGERPRINT,presets=records,protected=protected,source=source),indent=2),encoding='utf-8')
print(FINGERPRINT, len(records), 'baseline presets', len(protected), 'protected files')
