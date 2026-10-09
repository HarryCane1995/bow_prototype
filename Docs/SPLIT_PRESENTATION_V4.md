# V4 — independent 1POV / 3POV authoring and runtime

20 September 2026. Presentation/authoring restructuring only. No commit/push.

## Result and controls

Player defaults to V4 split. First person renders **ARMS + FP_CyberBow only**, including Slide. External view renders the complete **HEAD/TORSO/ARMS/LEGS + World_CyberBow**. Both visual skeletons advance regardless of the active local camera. No second controller, physics body, combat system or projectile producer was added.

- **F10**: normal / external review.
- **F12**: V4 split / preserved V3 reference. F6 remains audio settings, F7 mute.
- In reference mode, **F11** still selects V3 / V2; **F9** selects legacy presentation.
- **F4**: accepted cosmetic FP drift on/off. R/F1, movement and combat controls unchanged.

## Audit and runtime scenes

The previous hybrid had independent FP animation playback but still contained TORSO, exposed world LEGS during slide, used the same unindexed BH01 export, and drove the gameplay camera from the animated world socket. Those contracts remain in the preserved V2/V3 fallback, not in V4.

| Scene | Current purpose |
|---|---|
| `Scenes/Characters/MainCharacter1POV.tscn` | Dedicated transparent SubViewport/World3D, FP camera/lights, additive FPDriftRoot, FPArms/Body/Skeleton3D/ARMS, AnimationPlayer, Grip/FP_CyberBow |
| `Scenes/Characters/MainCharacter3POV.tscn` | Independent visual consumer, Body/Skeleton3D with all four regions, AnimationPlayer, Grip/World_CyberBow; no Player/camera owner |
| `Scenes/Characters/MainCharacterV4.tscn` | Local presentation host, the two scenes, independent gameplay-camera layer, external review camera, debug readout |
| `Scenes/Characters/LegacyHybrid1POV.tscn` | Exact previous FP scene, including torso, for V3 fallback |
| `Scenes/Characters/MainCharacterV3.tscn` | Previous controller now references LegacyHybrid1POV; controller/FP/drift code unchanged |
| `Scenes/Characters/MainCharacterV2.tscn` | Preserved original true-body presentation |
| `Scenes/Player.tscn` | Adds V4; old MainCharacterV2 node references its original scene directly |

**1POV source:** `Assets/Characters/BaseHumanoid/Exports/BH01_1POV.glb`, one ARMS mesh region. **3POV source:** `BH01_3POV.glb`, four body regions. Each has a separate instance of the compatible 54-joint skeleton (53 deform joints plus non-deforming FP_CAMERA_SOCKET). Hidden torso/leg/head driver bones in FP do not imply any corresponding geometry. Each branch owns its AnimationPlayer and a private AnimationLibrary/clip copy.

## Blender authoring

Canonical source remains `Assets/Characters/BaseHumanoid/Source/Humanoid_Male_PoseLab.blend`.

Backup including the unsaved live scene was made **before editing**:

`C:\Users\harry\Documents\bow_prototype\.godot\split-presentation\PoseLab_before_split_20260920_153901.blend`

An additional pre-migration backup is recorded in `Assets/Characters/BaseHumanoid/Review/split_authoring_manifest.json`.

Use Blender's **Scene selector** to switch between:

| Scene / collection | Rig | Camera / helper | Initial Action |
|---|---|---|---|
| `BH01_1POV` / `POSELAB_1POV` | `1POV_Male_Rig` | `CAM_1POV` / `CTRL_CAM_1POV` | `BH01_1POV_IDLE` |
| `BH01_3POV` / `POSELAB_3POV` | `3POV_Male_Rig` | `CAM_3POV` / `CTRL_CAM_3POV` | `BH01_3POV_IDLE` |

These are independent Scene configurations, intentionally using the existing two-view authoring layout instead of fragile workspace-change handlers. Each scene retains its active rig/Action, camera and mesh visibility. Both have Pose Mode/control rig and Action Editor. The original `BH01_Male_PoseLab`, its cameras and all 26 unindexed Actions remain.

CAM_1POV is a **fixed** camera calibrated from the actual neutral V3 runtime transform, vertical FOV 65°, 1280×720 authoring aspect. It does not follow an animated socket. CTRL_CAM_1POV can be moved deliberately to change framing on the next export. CAM_3POV is a separate external 3/4 full-body camera. Scene switching changes camera through the scene, not a pinned local-camera override.

The new FP source mesh contains only the same weight-defined ARMS region used by the exporter. The 3POV source retains the full body. Both rigs preserve compatible deform names and the existing controls/constraints; object/constraint/driver targets are remapped within each branch. Parent inverse matrices must be explicitly preserved when copying the bow hierarchy: Blender resets them on parent reassignment. This was fixed and the resulting FP Idle evaluated deform matrices match the old neutral source exactly (maximum difference 0).

## Complete slot list and migration

Every 3POV row is an **independent Action copy** of the corresponding legacy source in column three. Every 1POV row is an independent copy of `BH01_IDLE`, marked as a neutral placeholder. No final animation was authored.

| 1POV slot | 3POV slot | 3POV source |
|---|---|---|
| BH01_1POV_IDLE | BH01_3POV_IDLE | BH01_IDLE |
| BH01_1POV_RUN | BH01_3POV_RUN | BH01_RUN |
| BH01_1POV_CROUCH | BH01_3POV_CROUCH | BH01_CROUCH |
| BH01_1POV_SLIDE | BH01_3POV_SLIDE | BH01_SLIDE |
| BH01_1POV_WALLRUN_LEFT | BH01_3POV_WALLRUN_LEFT | BH01_WALLRUN_LEFT |
| BH01_1POV_WALLRUN_RIGHT | BH01_3POV_WALLRUN_RIGHT | BH01_WALLRUN_RIGHT |
| BH01_1POV_WALL_JUMP | BH01_3POV_WALL_JUMP | BH01_WALL_JUMP |
| BH01_1POV_JUMP_TAKEOFF | BH01_3POV_JUMP_TAKEOFF | BH01_JUMP_TAKEOFF |
| BH01_1POV_JUMP_AIR | BH01_3POV_JUMP_AIR | BH01_JUMP_AIR |
| BH01_1POV_FALL | BH01_3POV_FALL | BH01_FALL |
| BH01_1POV_LANDING | BH01_3POV_LANDING | BH01_LANDING |
| BH01_1POV_GRAPPLE_PULL | BH01_3POV_GRAPPLE_PULL | BH01_GRAPPLE_PULL |
| BH01_1POV_GRAPPLE_LAUNCH | BH01_3POV_GRAPPLE_LAUNCH | BH01_GRAPPLE_LAUNCH |
| BH01_1POV_GRAPPLE_FLIGHT | BH01_3POV_GRAPPLE_FLIGHT | BH01_GRAPPLE_FLIGHT |
| BH01_1POV_BOW_READY | BH01_3POV_BOW_READY | BH01_BOW_READY |
| BH01_1POV_BOW_DRAW_START | BH01_3POV_BOW_DRAW_START | BH01_BOW_DRAW_START |
| BH01_1POV_BOW_FULL_DRAW | BH01_3POV_BOW_FULL_DRAW | BH01_BOW_FULL_DRAW |
| BH01_1POV_BOW_RELEASE | BH01_3POV_BOW_RELEASE | BH01_BOW_RELEASE |
| BH01_1POV_BOW_FOLLOW_THROUGH | BH01_3POV_BOW_FOLLOW_THROUGH | BH01_BOW_FOLLOW_THROUGH |
| BH01_1POV_BOW_RECOVERY | BH01_3POV_BOW_RECOVERY | BH01_BOW_RECOVERY |
| BH01_1POV_RMB_ANTICIPATION | BH01_3POV_RMB_ANTICIPATION | BH01_RMB_ANTICIPATION |
| BH01_1POV_MELEE | BH01_3POV_MELEE | BH01_MELEE |
| BH01_1POV_PARRY | BH01_3POV_PARRY | BH01_PARRY |
| BH01_1POV_MELEE_RECOVERY | BH01_3POV_MELEE_RECOVERY | BH01_MELEE_RECOVERY |

`BH01_RUN_CONTACT` and `BH01_RUN_FLIGHT` remain legacy/reference authoring poses; the actual loop is `BH01_RUN`, so no new runtime phases were invented for them. The copied 3POV RUN preserves frames 1–25 at 24 FPS, cyclic. Other current indexed slots are static poses, exported as one-second holds.

All 24 FP slots need the user's future camera-specific posing/animation. In 3POV, 13 copies have the same keys as the pre-existing base placeholder: all six BOW states, CROUCH, FALL, GRAPPLE_PULL/LAUNCH/FLIGHT, JUMP_TAKEOFF and LANDING. The other 11 preserve distinct source Actions; this does not claim they are final animation. Legacy key/handle/interpolation hashes and independent 3POV copy equality passed.

## State routing, aim and bow

`SplitStateObserver` reads the existing movement/slide/wallrun/grapple modules, grounded velocity and bow/combat state. It publishes one `PresentationState` for both consumers. Existing RMB requested slot names are translated at one boundary only. `Resources/Presentation/Split1POVSlots.tres` and `Split3POVSlots.tres` map that enum to indexed clips. Missing clips fall back to **that branch's own Idle**. Short takeoff/landing/release holds are visual only; no clip changes gameplay state or duration.

The current POC prioritizes combat over locomotion for both full clips. Simultaneous upper/lower animation layering is not implemented. Slots are ready for authoring, not a finished combat animation set.

`SplitBodyVisual` is a visual consumer with `Present(state, delta, aimBasis, sliding)`. It has no Player reference. A future remote actor can instantiate only MainCharacter3POV, provide its root/aim/state and bow visual source, without creating FP. Networking/photo-mode features are not implemented.

FP_CyberBow and World_CyberBow are real instances of the existing CyberBow GLB. Both copy local bow-part transforms and arrow visibility from the original `PlayerBowVisualModule` source; neither copies the other branch's skeleton or global hand transform. The existing bow gameplay modules remain the single producer of charge/release/arrow/projectile state. Legacy hand presentation is suspended, and arrow visual ownership remains with the existing BowVisualModule while V4 is active.

FP retains the accepted 0.62 bow scale, neutral wrist stabilization, and original common-root drift after animation/wrist evaluation, with interpolation off. World has a separate bounded chest aim response (weight 0.3, skipped during slide); its authored hand/bow relationship remains intact. The former V2 camera-centered full arm IK remains available in fallback. These are deliberately separate solvers. Gameplay aim always uses the gameplay camera.

Blender previews the authored bow/grip. Runtime FP wrist stabilization and 0.62 bow scale are presentation adjustments, so the neutral body camera matches but the Blender bow is not a pixel-identical runtime draw preview. `StabilizeFpWrist` is separately adjustable on the FP visual consumer; future manual Actions need a runtime view check.

## Camera and layers

| Content | Layer | Normal gameplay camera | FP viewport camera | External camera |
|---|---:|---:|---:|---:|
| Full 3POV body and bow | 17 | hidden | hidden | visible |
| FP arms and bow, own World3D | 19 | hidden | visible | hidden |
| Legacy viewmodel | 20 | hidden | hidden | hidden |

Layer 18 remains reserved by legacy V3's slide-legs scheme, but V4 never exposes it to the gameplay camera. Nodes are retained; camera switches use masks and the local FP canvas/viewport visibility, not rebuilding a character.

`SplitGameplayCamera` reads only Player's interpolated position, camera pivot/crouch height and mouse-look/effects basis. No skeleton reference exists. The standing optical offset and world vertical FOV 98° preserve the current baseline; slide/crouch height comes from the existing pivot, not the world Action. Look → wallrun effects → camera runs before gameplay aim consumers. FP's camera-local rig can move freely without feedback. World animations cannot move the gameplay camera either. Animation-driven head bob/socket movement remains a V2/V3 reference feature.

## Export workflow

Do not run `setup_split.py` again on an authored split: it refuses to overwrite existing scenes. Normal iteration:

1. In PoseLab choose BH01_1POV or BH01_3POV and the indexed Action. Edit/key that Action; save. The branch rigs/Actions are separate, so edit the selected branch, not the legacy rig.
2. In Blender/MCP execute `Tools/Blender/HumanoidBase/capture_split.py` with `SPLIT_BRANCH='1POV'` or `'3POV'`:

```python
from pathlib import Path
p = Path(bpy.data.filepath).parents[4] / 'Tools/Blender/HumanoidBase/capture_split.py'
exec(compile(p.read_text(encoding='utf-8'), str(p), 'exec'),
     {'__file__': str(p), 'SPLIT_BRANCH': '1POV'})
```

3. From the project root: `python Tools/Blender/HumanoidBase/export_split.py --branch 1POV` (or 3POV/all).
4. Allow Godot reimport, then restart the running scene. Do not edit generated GLB/subresources.

Capture samples the selected branch rig across complete Action range/FPS, bakes evaluated control constraints, preserves the live scene/pose while sampling and creates a disposable source snapshot. Key authored changes before capture. The shared proven `export_v2.py` baker now accepts explicit rig/body/scene metadata, idle Action and mesh regions. Its default V2 behavior remains unchanged. Separate GLBs contain only their indexed clips, one skin each; FP exports ARMS only. `.animations.json` keeps length/loop metadata through the existing import hook; immutable tracks remain enabled. `.presentation.json` stores the fixed authoring camera calibration. Empty legacy-shaped `.camera.json` sidecars are not read by V4.

The existing V2 GLB, its sidecars, camera/socket pipeline and unindexed legacy Actions were not regenerated. Split animation edits do not automatically migrate back to V2/V3.

## Validation and limits

- C# build: **0 errors, 0 warnings**.
- Godot imported both GLBs and instantiated the real Gym with 24 clips per branch.
- Rendered quick smoke: Idle, Run, Slide, JumpTakeoff/JumpAir/Fall/Landing, canonical Wallrun L/R, actual grapple Pull/Launch/Flight, BowReady/draw/full/release and RMB anticipation; no world mesh leaks into FP, including slide.
- External full body visible; world AnimationPlayer keeps advancing in normal FP.
- Independent skeleton/library instances, branch-specific missing-clip fallback, F12 V3 reference, F11 V2 reference and return to split passed.
- Temporary +1 m world chest animation did not move the gameplay camera or FP rig; temporary FP hand key did not move the gameplay camera or leak into the world library.
- Real LMB draw/release incremented the existing shot sequence exactly once. Both visual bows mirror arrow visibility; no duplicate weapon logic was added.
- First capture found a copied bow parent-inverse issue; corrected in the authoring setup before final exports. The first shot check also needed input injection at a process-frame boundary; only the test driver was adjusted.
- Screenshots were inspected in the actual gameplay camera and external camera. This is a routing/architecture POC, not exhaustive QA or final animation polish.
- Hash comparison of the 53 preflight protected files found no changes, including the sampled gameplay/tuning/combat/audio/environment and original V2 export files. All original V2/V3 C# implementations remain unchanged.
- Existing legacy `ArrowTipMarker` warning still occurs during fallback initialization; no new runtime/import errors in the final smoke.

Reusable check: `godot --path . --script Tools/Character/verify_v4_split.gd`.
Evidence: `Assets/Characters/BaseHumanoid/Review/split_runtime_smoke.json`, `split_authoring_manifest.json`, `split_protected_files.json`; rendered screenshots/logs under `.godot/split-presentation/`.

## Changed files

- Source: `Humanoid_Male_PoseLab.blend` (additive scenes/rigs/cameras/indexed Actions/UI; legacy retained).
- New exports: `BH01_1POV.*`, `BH01_3POV.*` and their import configuration/manifests; new split review JSON files.
- New scripts: `MainCharacterV4.cs`, `MainCharacterV4.FPDrift.cs`, `PresentationState.cs`, `SplitStateObserver.cs`, `SplitAnimationSlots.cs`, `SplitBodyVisual.cs`, `SplitGameplayCamera.cs` and generated `.uid` companions.
- New mapping resources: `Split1POVSlots.tres`, `Split3POVSlots.tres`.
- Scenes: MainCharacter1POV/3POV rebuilt for split; MainCharacterV4/LegacyHybrid1POV added; MainCharacterV3 and Player wiring updated.
- Tooling: `setup_split.py`, `capture_split.py`, `export_split.py`, optional parameters in `export_v2.py`, `verify_v4_split.gd`.
- Documentation: this report, `Docs/blender_pipeline.md`, `Docs/HYBRID_PRESENTATION_SCENES.md`, `AGENTS.md`.

No movement, physics, gameplay combat, projectile, damage, sticky-slide trace, Surface Factory or VFX implementation changed. No commit/push.
