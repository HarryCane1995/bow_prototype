"""Summarize saved render-frame telemetry without modifying the source samples."""
import json
import math
from pathlib import Path

OUT = Path(__file__).resolve().parents[2] / ".godot/humanoid-base/v2-feedback"


def angle(a, b):
    cross = (a[1]*b[2]-a[2]*b[1], a[2]*b[0]-a[0]*b[2], a[0]*b[1]-a[1]*b[0])
    return math.degrees(math.atan2(math.sqrt(sum(x*x for x in cross)), sum(x*y for x,y in zip(a,b))))


summary = {}
for label in ("baseline", "fixed"):
    data = json.loads((OUT / f"{label}.json").read_text())
    summary[label] = {"failures": len(data["failures"]), "caps": {}}
    for cap in (60, 240):
        rows = [r for r in data["frames"] if r["fps_cap"] == cap]
        result = {"frames": len(rows)}
        for key in ("socket_delta_m", "camera_preik_error_m", "camera_pass_delta_m",
                    "camera_render_yaw_error_deg", "camera_render_position_error_m", "grip_error_m"):
            result[key] = max(r[key] for r in rows)
        result["rendered_camera_bow_error_deg"] = max(angle(r["bow"]["basis"][0], r["camera_render"]["basis"][2]) for r in rows)
        result["grounded_body_raw_camera_yaw_error_deg"] = max(r["body_yaw_error_deg"] for r in rows if not r["slide"])
        result["circle_socket_delta_m"] = max(r["socket_delta_m"] for r in rows if r["pattern"] == "circle")
        summary[label]["caps"][str(cap)] = result
(OUT / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
print(json.dumps(summary, indent=2))
