"""Backup before the runtime-only showcase pass; preserve current manual source."""
from pathlib import Path
import json,hashlib,shutil,datetime
ROOT=Path(__file__).resolve().parents[4];ART=ROOT/'Art/Environment/Highrise100';QA=ART/'RuntimeShowcase_QA';BACKUP=QA/'Backup'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
if BACKUP.exists():raise RuntimeError('Existing backup: inspect it, do not replace it')
BACKUP.mkdir(parents=True)
for name in ('Highrise100.blend','manifest.json','materials.json'):
    shutil.copy2(ART/name,BACKUP/name)
paths=[ROOT/'project.godot',ROOT/'AGENTS.md',ROOT/'Level_01_Blockout.blend',ROOT/'Level_CyberCity_Blockout.blend']
for directory in ('Scripts/Player','Scripts/Audio','Scripts/Levels','Scenes/Levels','Scenes/Player.tscn','Resources/Tuning','Tools/Blender/LocalProxyV06'):
    p=ROOT/directory
    paths.extend(p.rglob('*') if p.is_dir() else [p])
protected={p.relative_to(ROOT).as_posix():sha(p) for p in paths if p.is_file()}
report=dict(created_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),source_sha256=sha(ART/'Highrise100.blend'),protected=protected,free_bytes=shutil.disk_usage(ROOT).free)
(QA/'baseline.json').write_text(json.dumps(report,indent=2))
print('RUNTIME_BACKUP',report['source_sha256'],'protected',len(protected),'free_GiB',report['free_bytes']/1024**3)
