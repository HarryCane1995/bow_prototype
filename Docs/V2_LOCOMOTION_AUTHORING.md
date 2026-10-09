# V2 Locomotion Authoring — 2026-09-12

Prepared animation routing and authoring infrastructure. No final animation cycle was authored.

## PoseLab

Source: `Assets/Characters/BaseHumanoid/Source/Humanoid_Male_PoseLab.blend`.

The audit found 25 existing Actions, including `BH01_WALLRUN_LEFT`, `BH01_WALLRUN_RIGHT`, `BH01_RUN_CONTACT`, and `BH01_RUN_FLIGHT`. All had frame-1 keys and explicit 1..1 ranges. Their keys, interpolation, handles, ranges and loop flags were preserved. Idle, Slide, RMB and Bow Actions were not edited.

Created only `BH01_RUN`: a copy of Contact's frame-1 pose, with a 1..25 playback range at the existing 24 FPS and looping enabled. It is an authoring container, currently a static placeholder. Contact/Flight remain separate references. All Actions have Fake User and are available in the Action Editor selector.

Live-session backups, including unsaved pose channels, are under `.godot/locomotion-authoring/`. `source_validation.json` and `handoff.json` record the before/after Action signatures. The final workspace is **BH01 PoseLab**, Male selected, Pose Mode, Wallrun Left at frame 1, controls visible, DEF/MCH hidden, CyberBow visible, FP cameras available, Action Editor and Timeline open.

## Authoring and export

1. Select an Action in the Action Editor and author its keys normally. Set the Action's **Manual Frame Range** start/end to include the whole intended clip. Timeline playback bounds alone do not change that Action's export range.
2. Set scene FPS in Output Properties. Duration is `(end - start) / FPS`; 1..25 at 24 FPS is one second. For a seamless loop, author a matching last/first pose yourself.
3. Set the Action's **Cyclic Animation** flag (`Action.use_cyclic`) for runtime looping. Off means play once and hold the final pose while the corresponding gameplay state continues. The Run container starts with this flag on; existing wallrun flags were preserved.
4. Save the source. Capture the desired Actions explicitly from the live Blender session (Python Console or Blender MCP):

```python
import bpy, runpy
from pathlib import Path
root = Path(bpy.data.filepath).parents[4]
runpy.run_path(str(root / 'Tools/Blender/HumanoidBase/capture_v2.py'), init_globals={
    'V2_EXTRA_ACTIONS': ['BH01_WALLRUN_LEFT', 'BH01_WALLRUN_RIGHT', 'BH01_RUN']
})
```

Capture preserves the current Action, frame/subframe, pose channels and NLA setting. It saves a disposable source snapshot, records start/end/FPS, source keys and interpolation, and evaluates constraints across the complete Action. `V2_SAMPLE_FPS` optionally increases sampling above the 60 Hz default. Idle/Slide always retain the previous frame-1 static behavior, including the active unkeyed pose capture rule.

From the repository root:

```powershell
blender --background --factory-startup --python-exit-code 1 --python Tools/Blender/HumanoidBase/export_v2.py -- .godot/humanoid-base/v2_source_capture.json
godot --headless --editor --path . --import
godot --headless --path . --script res://Tools/Blender/HumanoidBase/verify_v2.gd
```

Use `--factory-startup` only in this disposable background export process, never in the live MCP authoring session. Reload/restart the running Godot scene after export.

The exporter bakes evaluated TRS onto the existing 54-joint hierarchy: 53 deform bones plus the non-deforming `FP_CAMERA_SOCKET` under chest. Four skinned mesh regions share one skeleton. No controllers, MCH, authoring cameras or reference geometry enter the runtime GLB. Bezier interpolation and constraints are sampled; the runtime uses linear interpolation between baked samples. Constant source segments retain a narrow 1 ms transition around their boundary. Original source curves remain editable and unchanged.

Loop and duration travel in `BH01_Male_V2.animations.json`, consumed by `V2AnimationPostImport.gd`. Metadata is also embedded in the generated GLB to trigger import after loop-only edits. Keep the post-import hook and **Remove Immutable Tracks = false**: removing rest-valued tracks can retain a previous clip's pose during transitions.

## Runtime routing

- Slide → `BH01_SLIDE`.
- Active wallrun → `BH01_WALLRUN_LEFT` / `BH01_WALLRUN_RIGHT`, selected solely from the gameplay module's read-only `ActiveWallSide`.
- Grounded horizontal motion → `BH01_RUN`, entering at 2 m/s and leaving below 1 m/s (Inspector settings).
- Otherwise → `BH01_IDLE`, including the current unanimated air fallback.

`RunPlaybackSpeedScale` is an Inspector multiplier, default 1. Existing 0.12 s crossfade is retained. The existing RMB animation override retains its original precedence and fallback behavior. Clip duration never controls gameplay duration.

The render cadence remains: restore authored bones → advance base animation → cache pre-IK animated socket/camera plan → aim IK → publish the camera. Run and wallrun are base clips underneath the existing aim layer. Bow attachment, MouseLook, camera cadence, movement, canonical wallrun, slide, grapple and combat/projectile logic were not changed.

## Quick validation

- Build: 0 warnings / 0 errors.
- Production GLB: all five clips, 54 joints and shared socket calibration verified in Godot; representative bone-position error below 0.000006 m.
- Disposable full clip: frame 5..35 at 30 FPS, Bezier COG movement, constant root movement, animated socket, 63 captured/baked samples and loop metadata. First/middle/last poses verified after a Slide transition. The test Action never enters canonical PoseLab or the production GLB.
- Short real-input Godot fixture: Idle → Run → Idle, real Slide, real left/right canonical wall acquisition and exit, Run playback multiplier, F9 fallback and F10 view switching passed.
- A temporary moving clip was injected as Run in memory to check aim and camera on an animated base. Maximum sampled bow aim error < 0.000025 degrees; camera error from the pre-IK authored socket < 0.000031 m.
- 57 protected gameplay/tuning files match pre-pass hashes. Wallrun code changed only to expose its existing side read-only. No camera/IK foundation changes.

Evidence: `.godot/locomotion-authoring/runtime.json`, `runtime.log`, `verify_production.log`, `verify_multiframe.log`, `source_validation.json`, `handoff.json`. The runtime fixture also emits an existing legacy sway-reference warning and Godot renderer cleanup messages on shutdown; no C# exceptions or routing assertions failed. This is a short infrastructure check, not a claim that the placeholders are finished animations.

## Files changed in this pass

- `Scripts/Player/Presentation/MainCharacterV2.cs`
- `Scripts/Player/Presentation/MainCharacterV2.Locomotion.cs` (new, plus Godot UID)
- `Scripts/Player/Modules/PlayerWallRunModule.cs` (read-only side API)
- `Scripts/Editor/Import/V2AnimationPostImport.gd` (new, plus Godot UID)
- `Tools/Blender/HumanoidBase/capture_v2.py`
- `Tools/Blender/HumanoidBase/export_v2.py`
- `Tools/Blender/HumanoidBase/verify_v2.gd`
- `Tools/Blender/HumanoidBase/prepare_locomotion_authoring.py` (new)
- `Tools/Blender/HumanoidBase/test_multiframe_v2.py` (new, disposable fixture)
- `Tools/Character/verify_v2_locomotion.gd` (new, plus Godot UID)
- `Assets/Characters/BaseHumanoid/Source/Humanoid_Male_PoseLab.blend` (Run container/workspace)
- `Assets/Characters/BaseHumanoid/Exports/BH01_Male_V2.glb`, `.glb.import`, `.camera.json`, `.animations.json`
- `Assets/Characters/BaseHumanoid/Review/v2_export_manifest.json`
- `AGENTS.md`, `Docs/blender_pipeline.md`, this document.

No production scene edits in this pass. Unrelated pre-existing working-tree changes are preserved. No commit or push.
