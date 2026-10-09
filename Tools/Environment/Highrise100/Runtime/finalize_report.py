"""Verify saved source/protected files and summarize the real Godot reports."""
from pathlib import Path
import collections
import datetime
import hashlib
import json

ROOT = Path(__file__).resolve().parents[4]
ART = ROOT / 'Art/Environment/Highrise100'
QA = ART / 'RuntimeShowcase_QA'
RUNTIME = ROOT / 'Assets/Environment/Highrise100_Runtime'

def read(path):
    return json.loads(path.read_text(encoding='utf-8'))

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

baseline = read(QA / 'baseline.json')
runtime = read(QA / 'runtime_gpu.json')
headless = read(QA / 'runtime_headless.json')
manifest = read(RUNTIME / 'export_manifest.json')
gltf = read(RUNTIME / 'Highrise100.gltf')
source = read(QA / 'source_inspection.json')
historic = read(QA / 'historical_73_of_75_godot.json')
changed = [p for p, digest in baseline['protected'].items() if not (ROOT / p).is_file() or sha(ROOT / p) != digest]
backups = {n: {'source': sha(ART / n), 'backup': sha(QA / 'Backup' / n)} for n in ['Highrise100.blend', 'manifest.json', 'materials.json']}
map_errors = []
for item in manifest['copied_maps']:
    if sha(RUNTIME / item['file']) != item['sha256'] or sha(ART / item['source']) != item['sha256']:
        map_errors.append(item['file'])
signatures = collections.defaultdict(list)
for material in gltf['materials']:
    signatures[json.dumps({k:v for k,v in material.items() if k != 'name'}, sort_keys=True)].append(material['name'])
duplicates = [names for names in signatures.values() if len(names) > 1]
heights = [b['height_m'] for b in runtime['buildings']]
stderr = (QA / 'validate_gpu.stderr.log').read_text(encoding='utf-8').strip()
report = {
    'created_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
    'source_sha256': backups['Highrise100.blend']['source'],
    'source_matches_baseline': backups['Highrise100.blend']['source'] == baseline['source_sha256'],
    'backups': backups,
    'protected_files_checked': len(baseline['protected']),
    'protected_files_changed': changed,
    'texture_copy_hashes_checked': len(manifest['copied_maps']),
    'texture_copy_errors': map_errors,
    'distinct_texture_payload_hashes': len({m['sha256'] for m in manifest['copied_maps']}),
    'duplicate_material_recipes': duplicates,
    'headless_passed': headless['passed'],
    'gpu_passed': runtime['passed'],
    'gpu_stderr': stderr,
    'buildings': runtime['buildings_loaded'],
    'materials': runtime['material_count'],
    'textures': runtime['unique_texture_count'],
    'triangles': runtime['triangles'],
    'surfaces': runtime['surfaces'],
    'textured_surfaces': runtime['textured_surfaces'],
    'intentional_flat_surfaces': len(runtime['flat_surfaces']),
    'native_shader_contracts_checked': len(runtime['native_shaders']),
    'height_range_m': [min(heights), max(heights)],
    'representatives': [b for b in runtime['buildings'] if b['id'] in runtime['representatives']],
    'performance': runtime['performance'],
    'historic_flat_surfaces': historic['flat_surfaces'],
    'controls': runtime['input_automated_test'],
}
report['passed'] = all([report['source_matches_baseline'], not changed, not map_errors, not duplicates, headless['passed'], runtime['passed'], not stderr, all(v['source'] == v['backup'] for v in backups.values())])
(QA / 'final_verification.json').write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding='utf-8')
print(json.dumps(report, indent=2, ensure_ascii=False))
assert report['passed'], 'Inspect final_verification.json'
