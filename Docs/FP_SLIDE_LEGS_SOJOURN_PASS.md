# Slide legs — Sojourn-inspired pose

2026-09-07. Prototype, awaiting human review. No commit or push.

## Short reference research

Viewed browser footage from [Markus Hammarstedt's Sojourn / Ramattra animation reel](https://vimeo.com/826349362): first-person animation kit around 0:22–0:27, locomotion around 0:42, third-person sliding around 0:48–0:53 and the return to standing. Also inspected fragments of the [official Sojourn gameplay trailer](https://www.youtube.com/watch?v=rPNNTMu4iko), including the body/aiming views around 0:36–0:40.

Visual reading: the pelvis drops close to the floor, the torso inclines and remains oriented for shooting. One leg makes a long, nearly straight leading line; the other folds tightly underneath/alongside the pelvis. The leading heel/foot is far from the hips, while the second foot stays close. This low, asymmetric arrangement makes the body feel seated into the slide. It is not two parallel extended legs.

The reviewed first-person frames keep the weapon low/right and aiming space open; they do not expose a complete, measurable two-leg pose. The third-person sliding footage is the main pose reference here. Exact knee angles, the original camera-local turning rule and Blizzard's rig structure are not established by these clips. The author describes his animations as keyframed; no rig implementation is inferred from that.

## BowPrototype adaptation

- **Left leg extended**, with a slight knee bend and raised toe; **right leg tucked**, with a higher/outward knee and the foot back near the pelvis.
- A small dark pelvis block and editable `SeatedPoseRoot` connect the pose. No torso or skeleton was added.
- One fixed pose rotates as a unit. The follow-up below replaces the initial WASD-driven visual yaw with a world-space direction captured at slide entry. Individual leg proportions and joint positions never change with input.
- First-person cheats: longer leading leg, shortened folded shin, outward folded knee/foot to clear the right hand, raised leading toe, darker long panels and a composition pivot forward of the physical pelvis. These are deliberate silhouette choices for the wide CyberBow, not anatomy or a copy of Blizzard's camera rig.
- Existing 0.07 s entry and immediate exit remain. No knee oscillation, mirroring or vibration was added.

## Quick check

One external InputEvent pass covered W, WA, WD, A/D, S, A → D and input release, slide → jump, slide → canonical B wallrun, idle bow, draw and release. A second short composition pass checked W/diagonals/A/D/draw after shifting the tucked foot outward. Rendered captures showed the fixed pose rotating together; aiming centre remained clear, and the bow/hands stayed in front. Legs hid on the tested exits. Some leg detail remains intentionally occluded by the bow; anatomy and silhouette are still rough blocking.

Build: `dotnet build --no-restore`, 0 warnings / 0 errors. Blender import succeeded. First test batch exited 0. The second batch completed its cases, then repeated the previously recorded `godotsharp_variant_destroy` / `0xC0000005` finalizer crash during driver shutdown. Ordinary Gym startup/shutdown without the driver then exited 0. The legacy `ArrowTipMarker` warning remains. No exhaustive QA was performed.

External evidence: `C:/Users/harry/Documents/Codex/2026-09-07/sojourn-slide-pass/` — `runtime.jsonl`, `final.jsonl`, PNG captures, console logs and the source backup.

## Changed files

- `Assets/Models/Player/FP_Slide_Legs.blend` — editable pose: 23 meshes, one empty root, 598 polygons.
- `Tools/Blender/build_slide_legs.py` — updated source builder.
- `Docs/FP_SLIDE_LEGS_SOJOURN_PASS.md` — this report.

SHA-256 comparison against the start-of-pass snapshot found only the `.blend` and its builder changed among existing files. Gameplay, movement, collision, camera, bow/hands, the visibility/yaw module and scene wrappers were unchanged. Prior unrelated working-tree changes were preserved.

## Follow-up: lock direction at slide entry

`PlayerCrouchSlideModule.SlideDirection` now exposes the existing direction through a read-only getter. `FirstPersonSlideLegs` snapshots its horizontal world direction after the successful physics transition and clears the snapshot on ability exit. Visibility changes alone do not recapture it. Horizontal entry velocity is only a fallback for a degenerate direction.

During slide, the module reads no WASD. Each rendered frame transforms the locked direction into the player's yaw frame, which is also the camera's yaw frame in the current body-yaw / child-pitch hierarchy. Pitch and camera roll cannot distort that horizontal angle. Counter-rotation is exact: the old yaw smoothing is not applied, because lag would change apparent world orientation when turning the head. The old `TurnResponse` / `InputDeadzone` exports remain in a clearly marked unused compatibility group. The 0.07 s positional entry and all Sojourn pose geometry are unchanged.

One short run checked A/D during W slide (locked direction stayed forward), W+D entry (45°), camera right 90° / 180° (local pose left 90° / backwards 180°), exit and another diagonal slide (fresh capture), jump and canonical B wallrun (hidden and cleared). Sampled reconstructed world heading matched the stored direction. Existing weak gameplay steering remains unchanged; the visual snapshot intentionally does not follow it.

`dotnet build --no-restore`: 0 warnings / 0 errors. All driver cases completed, then the known external-driver finalizer crash repeated at shutdown; no new gameplay exception was observed. Ordinary Gym startup/shutdown without the driver then exited 0. Evidence: `C:/Users/harry/Documents/Codex/2026-09-07/slide-legs-world-lock/`.

Only the two C# files named above and this report changed in this follow-up. No movement/velocity/steering calculations, asset, scene or tuning changes. No commit/push.

## Follow-up: explicit pitch-independent slide body

The inspected hierarchy already separates Player yaw from child camera pitch/roll and renders the legs through a fixed, identity-transform viewmodel camera. A pure-pitch displacement of the old legs transform was not reproduced. The first baseline run included unsolicited OS mouse motion, so its simultaneous yaw changes are not evidence of a pitch defect.

`FirstPersonSlideLegs` now explicitly constructs its horizontal yaw frame from the Player right axis projected onto XZ. The Player is the camera's yaw carrier; no pitched Camera3D basis or near-vertical camera-forward projection is used. The visual root is `TopLevel` in the existing viewmodel SubViewport, and its transform is assigned as a pure yaw plus the existing entry position/scale. This isolates the legs from ancestor pose transforms. It relies on the current fixed viewmodel camera at the origin, verified both in the scene and at runtime. Locked entry direction, visibility rules, Sojourn pose and proportions are unchanged.

One short synthetic InputEvent run checked forward slide with pitch 0/60/+89.9/-89.9, yaw 90, yaw 180 at both pitch extremes, and combined yaw/pitch changes. All nine sampled poses remained visible; position stayed `(0, -0.9, -2)`, local up stayed `(0, 1, 0)`, and locked world direction stayed `(0, 0, -1)`. At fixed yaw, pitch did not alter pose orientation. Yaw 90/180 produced the corresponding counter-rotation; the +/-180 numeric wrap represents the same orientation. Rendered captures confirmed stable lower-frame leg composition across the pitch extremes. Bow/hands retain their existing independent response and occlusion.

`dotnet build --no-restore`: 0 warnings / 0 errors. Runtime completed and exited 0; the existing `ArrowTipMarker` warning remains. The external driver filtered unsolicited mouse motion only during its controlled run; no production input behavior was changed. Evidence: `C:/Users/harry/Documents/Codex/2026-09-07/slide-legs-pitch/` (`after.jsonl`, PNG captures, driver and logs).

This follow-up changes only `Scripts/Player/ViewModel/FirstPersonSlideLegs.cs` and this report. MouseLook, bow/hands, gameplay, slide physics, assets and scene files are unchanged. No commit/push.
