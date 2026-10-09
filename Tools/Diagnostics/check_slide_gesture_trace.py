"""Verify integration evidence from verify_slide_gesture.gd; never mutate source logs."""
import collections
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
TRACE = ROOT / ".godot/movement-traces"
OUT = TRACE / "slide-gesture-regression"
rows = [json.loads(line) for line in (TRACE / "latest_regression_session.jsonl").read_text(encoding="utf-8").splitlines()]
archive = Path(rows[0]["details"]["archive_path"])
assert archive.read_bytes() == (TRACE / "latest_regression_session.jsonl").read_bytes()
assert rows[-1]["kind"] == "SESSION_END"
assert [r["sequence"] for r in rows] == list(range(1, len(rows) + 1))
runtime = json.loads((OUT / "runtime_assertions.json").read_text())
assert runtime["passed"], runtime["failures"]

groups = collections.defaultdict(list)
case = "setup"
for row in rows:
    if row["kind"] == "REGRESSION_CASE":
        case = row["reason"]
    groups[case].append(row)

expected = {"A_NORMAL_SLIDE": (1, 1), "B_HOLD_AFTER_TIMER": (1, 1), "C_AIR_BUFFER": (1, 1),
            "D_REAL_LEVEL01_WINDOW": (1, 1), "E_SLIDE_JUMP": (1, 1),
            "F_REPEATED_JUMP_HELD_CTRL": (0, 0), "G_DELIBERATE_REENTRY": (2, 2),
            "H_AIRBORNE_SECOND_GESTURE": (2, 2), "I_SIMULTANEOUS_JUMP_CTRL": (1, 1),
            "J_AIR_BUFFER_TTL": (1, 0)}

def ctrl_down(row):
    return (row["kind"] == "SLIDE_INPUT_DOWN" and row["details"].get("source") == "raw_event"
            and row["details"].get("physical_key") == "Ctrl")

case_counts = {}
for name, wanted in expected.items():
    events = groups[name]
    observed = (sum(ctrl_down(e) for e in events), sum(e["kind"] == "SLIDE_ENTER" for e in events))
    assert observed == wanted, (name, observed, wanted)
    case_counts[name] = {"ctrl_down": observed[0], "slide_enter": observed[1], "result": "PASS"}

entries = [e for e in rows if e["kind"] == "SLIDE_ENTER"]
acquisitions = collections.Counter()
violations = []
for e in entries:
    before, after = e["details"]["before"], e["snapshot"]
    gesture = (after["player_instance_id"], after["slide"]["gesture_id"])
    acquisitions[gesture] += 1
    if before["slide"]["gesture_consumed"] or before["slide"]["gesture_state"] != "Available":
        violations.append(e["sequence"])
    assert after["slide"]["gesture_consumed"] and after["slide"]["airborne_buffer_timer"] == 0
    assert not after["slide"]["airborne_intent_armed"]
    assert not after["slide"]["jump_consumed_this_tick"]
assert not violations
assert all(count == 1 for count in acquisitions.values())
assert all(not e["snapshot"]["slide"]["is_sliding"] and not e["snapshot"]["slide"]["gesture_consumed"]
           for e in rows if e["kind"] == "SLIDE_AIR_BUFFER_ARM")
assert not any(e["kind"] == "SLIDE_AIR_BUFFER_REFRESH" for e in rows)

# The imported window test must actually encounter the original ray-only sill contact,
# then lose that contact while sliding; generic successful flat-floor motion is insufficient.
window = groups["D_REAL_LEVEL01_WINDOW"]
entry = next(e for e in window if e["kind"] == "SLIDE_ENTER")
assert entry["snapshot"]["contact"]["ray_collider"]["path"].endswith("/CB_CrossWindowSill/StaticBody3D")
assert not entry["snapshot"]["on_floor"] and entry["snapshot"]["grounded"]
lost = next(e for e in window if e["kind"] == "GROUNDED_LOST" and e["snapshot"]["slide"]["is_sliding"])
assert lost["snapshot"]["slide"]["airborne_buffer_timer"] == 0
exit_event = next(e for e in window if e["kind"] == "SLIDE_EXIT")
assert "_slideTimer <= 0" in exit_event["reason"]
assert exit_event["snapshot"]["input"]["held"] and exit_event["snapshot"]["slide"]["airborne_buffer_timer"] == 0

rapid = [e for e in rows if e["kind"] == "SLIDE_RAPID_REENTRY"]
assert len(rapid) == 1 and rapid[0] in groups["G_DELIBERATE_REENTRY"]
assert rapid[0]["snapshot"]["input"]["just_pressed"]
assert rapid[0]["details"]["time_since_exit"] > 0
audio = collections.Counter((e["kind"], e["details"]["layer"]) for e in rows if e["kind"].startswith("SLIDE_AUDIO_"))
assert audio[("SLIDE_AUDIO_START", "one_shot")] == len(entries) == audio[("SLIDE_AUDIO_STOP", "one_shot")]
assert audio[("SLIDE_AUDIO_START", "loop")] == audio[("SLIDE_AUDIO_STOP", "loop")]

protected = json.loads((TRACE / "sticky-fix-baseline/protected-hashes.json").read_text(encoding="utf-8-sig"))
for item in protected:
    assert hashlib.sha256(Path(item["Path"]).read_bytes()).hexdigest().upper() == item["Hash"], item["Path"]

result = {"result": "PASS", "archive": str(archive), "events": len(rows),
          "synthetic_ctrl_down": sum(ctrl_down(e) for e in rows), "slide_enter": len(entries),
          "consumed_gesture_acquisitions": len(violations), "max_acquisitions_per_gesture": max(acquisitions.values()),
          "same_tick_jump_acquisitions": 0, "rapid_markers": len(rapid),
          "rapid_marker_explanation": "G: new release/press, valid fresh gesture; no phantom re-entry",
          "rapid_gap_seconds": rapid[0]["details"]["time_since_exit"],
          "audio": {f"{k[0]}:{k[1]}": v for k, v in audio.items()}, "cases": case_counts,
          "original_trace_geometry_tuning_audio_hashes_unchanged": True,
          "window_evidence_sequences": [entry["sequence"], lost["sequence"], exit_event["sequence"]]}
(OUT / "trace_verification.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(json.dumps(result, ensure_ascii=False, indent=2))
