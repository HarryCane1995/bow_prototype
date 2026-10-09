"""Verified local movement snapshot; no gameplay files are modified."""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
SNAPSHOT = ROOT / 'Docs/Reviews/LevelFreestyle01/metrics_snapshot.json'


def load_metrics():
    snapshot = json.loads(SNAPSHOT.read_text(encoding='utf-8-sig'))
    verification = {path: hashlib.sha256((ROOT / path).read_bytes()).hexdigest() == expected
                    for path, expected in snapshot['source_sha256'].items()}
    if not all(verification.values()):
        raise RuntimeError('Movement snapshot is stale: ' + str([p for p, ok in verification.items() if not ok]))
    c, m = snapshot['config'], snapshot['measurements']
    values = {
        'run_speed': c['MoveSpeed'], 'standing_height': c['StandingColliderHeight'],
        'slide_height': c['CrouchingColliderHeight'], 'diameter': .9,
        'standing_jump': m['standing']['range_m'], 'running_jump': m['running']['range_m'],
        'air_jump': m['double']['range_m'], 'slide_jump': m['slide_jump']['range_m'],
        'jump_rise': m['running']['rise_m'], 'air_rise': m['double']['rise_m'],
        'wallrun': m['wallrun_left']['range_m'], 'wallrun_rise': m['wallrun_left']['rise_m'],
        'wall_jump_chain': m['wall_jump']['range_m'], 'wall_jump_rise': m['wall_jump']['rise_m'],
        'wall_air_chain': m['wall_air_jump']['range_m'], 'wall_air_rise': m['wall_air_jump']['rise_m'],
        'wall_jump_lateral': 9.53, 'wall_air_lateral': 7.77,
        'grapple_range': c['MaxGrappleDistance'],
        'grapple_landings': [m['grapple_'+str(d)]['landing_range_m'] for d in (15,30,45)],
        'grapple_control_delay': c['PostLaunchControlDelay'],
        'gravity': c['ProjectGravity'] * c['GravityMultiplier'],
    }
    return {'snapshot': str(SNAPSHOT.relative_to(ROOT)), 'measured_date': snapshot['date'],
            'source_sha256': snapshot['source_sha256'], 'verified_current': verification,
            'values': values, 'range_policy': {'comfortable':[.50,.65], 'challenging':[.65,.82], 'near_observed_limit':[.82,.90]},
            'caveat':'Observed trajectories, not proven global maxima. Level topology is not a full traversal proof.'}


if __name__ == '__main__':
    report = load_metrics()
    target = ROOT / 'Docs/Reviews/GNLevelBlockout/movement_metrics.json'
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(report, indent=2), encoding='utf-8')
    print(json.dumps(report, indent=2))
