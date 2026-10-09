"""Promote checked candidate only if the original still matches the backup."""
import json,hashlib,shutil
from pathlib import Path
OUT=Path(__file__).resolve().parents[3]/'Art/Environment/Highrise100';QA=OUT/'UV_Material_QA'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
source=OUT/'Highrise100.blend';candidate=OUT/'Highrise100_UV_Candidate.blend';before=QA/'Before/Highrise100.blend'
assert sha(source)==sha(before),'Original source changed since backup; do not overwrite manual edits'
assert json.loads((QA/'candidate_geometry.json').read_text())['all100_exactly_unchanged']
assert json.loads((QA/'reproducibility.json').read_text())['passed']
assert json.loads((QA/'GodotSanity/runtime_validation.json').read_text())['passed']
comparison=json.loads((QA/'Independent/comparison.json').read_text())
assert not comparison['geometry_hash_changes'] and not comparison['missing_textures_after']
assert set(comparison['issues_after'])<= {'v_axis_slant_gt_15deg'}
shutil.copy2(candidate,source);shutil.copy2(QA/'candidate_manifest.json',OUT/'manifest.json')
(QA/'PROMOTED.json').write_text(json.dumps(dict(before_sha256=sha(before),candidate_sha256=sha(candidate),source_sha256=sha(source),source_equals_checked_candidate=sha(source)==sha(candidate)),indent=2))
print('PROMOTED_VERIFIED_CANDIDATE',sha(source))
