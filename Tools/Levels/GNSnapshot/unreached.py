"""Run ONLY after the human explicitly says the test session has ended."""
import argparse
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--session', type=Path, default=ROOT/'.godot/traversal-coverage/latest.json')
parser.add_argument('--human-test-finished', action='store_true', required=True)
args = parser.parse_args()
session = json.loads(args.session.read_text(encoding='utf-8'))
reached = [t for t in session['targets'] if t['reached']]
rows = []
for target in session['targets']:
    if target['reached']:
        continue
    nearest = min(reached, key=lambda t: math.dist(t['position'],target['position'])) if reached else None
    rows.append({k:target.get(k) for k in ['id','section_id','role','type','position','span_class','span_distance']} |
                {'height_m':target['position'][1], 'nearest_reached':nearest['id'] if nearest else None,
                 'nearest_reached_distance_m':round(math.dist(nearest['position'],target['position']),2) if nearest else None})
report = {'session_id':session['session_id'], 'reached':session['reached'], 'total':session['total'],
          'meaning':'Unvisited representative targets in this human session; unreachability is not proven.',
          'unreached':rows}
dest = args.session.with_name(args.session.stem+'_unreached.json')
dest.write_text(json.dumps(report,indent=2),encoding='utf-8')
print(dest)
