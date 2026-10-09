# First-person slide legs — blocking pass

2026-09-07. Visual-only prototype, pending human review; no commit/push.

## Result

Two asymmetric low-poly legs with thighs, knees, shins and boots. The editable Blender source contains 22 named mesh parts / 572 polygons, simple materials matching the hands, no textures, rig, torso or collision. The knees/boots are spread to remain readable beside the bow grip.

`FirstPersonSlideLegs` is a sibling of `ViewModelSwayRoot` inside the existing viewmodel viewport. It uses the existing render layer and lights without inheriting bow sway or shot transforms. Bow/hands remain in front of the legs. The source origin is near the knees to keep the full visual yaw sweep in the lower frame; this is camera composition, not a physical body pivot.

Only active slide with actual floor contact renders the layer. Jump, wallrun, grapple and ordinary movement hide it immediately. Existing airborne slide entry can keep the gameplay slide flag active; that alone does not show the legs.

Movement actions feed a continuous yaw: W 0°, WA +45°, WD −45°, A +90°, D −90°, SA +135°, SD −135°, S 180°. Exponential smoothing uses 18/s; releasing WASD retains the last direction. A new slide without input can seed direction from local horizontal velocity. The entry offset settles in 0.07 s. Composition, response and deadzone are Inspector exports.

## Quick Godot check

- W, both forward diagonals, A/D, both rear diagonals and S rendered; angles matched input. Fast A → D turned smoothly; releasing input retained D instead of resetting forward.
- Slide → jump and slide → canonical B wallrun hid the legs. Landing while Ctrl remained held correctly showed them again only after another grounded slide. Normal slide expiry removed them.
- Slide with idle bow, draw and release/shot rendered with the existing hands and bow animations. Centre aiming area remained clear; no obvious near-plane clipping was seen in the sampled views. Thigh ends intentionally extend below the frame, and the bow occludes some leg detail.
- Current runtime values: world FOV 98° at rest and about 120.4° during the tested slide, viewmodel FOV 65°, slide camera height 0.95 m. None were changed.
- `dotnet build --no-restore`: 0 warnings / 0 errors. Blender import completed. Ordinary Gym startup/shutdown without the synthetic driver completed with exit code 0.
- The final multi-scene external driver completed all cases, then hit native `0xC0000005` in `godotsharp_variant_destroy` during shutdown. This shutdown signature was already recorded in `CYBERBOW_SHOT_ANIMATION_PASS.md`; cause remains unestablished. No new gameplay exception was observed. The existing legacy `ArrowTipMarker` warning also remains.

Evidence and the external InputEvent driver are in `C:/Users/harry/Documents/Codex/2026-09-07/slide-legs-pass/` (`runtime.jsonl`, `final.jsonl`, `final_*.png`, `normal-smoke.log`). This was a quick blocking check, not exhaustive QA. Grapple hiding is implemented through its existing active/blocking flags; a separate grapple route was not replayed in this pass.

## Files and scope

- `Assets/Models/Player/FP_Slide_Legs.blend` and `.blend.import` — new editable source and Godot import metadata.
- `Tools/Blender/build_slide_legs.py` — source builder; refuses to overwrite an existing source unless explicitly run with `-- --rebuild`.
- `Scripts/Player/ViewModel/FirstPersonSlideLegs.cs` and `.cs.uid` — new presentation module.
- `Scenes/ViewModel/FirstPersonSlideLegs.tscn` — new lightweight visual wrapper.
- `Scenes/Player.tscn` — only a PackedScene reference and one instance were added in this pass.
- `Docs/FP_SLIDE_LEGS_PASS.md` — this report.

SHA-256 comparison with the pre-pass workspace snapshot found only `Scenes/Player.tscn` changed among existing files. Movement, slide physics, tuning, collision, camera, ability arbitration, bow and hands code were preserved, together with all unrelated working-tree changes.
