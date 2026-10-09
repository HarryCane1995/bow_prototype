# V2 pre-IK camera and render transform correction

The previous cadence fix synchronized the rendered bow with the CPU camera basis, but did not verify the camera transform uploaded by Godot's interpolation traversal. The user reported worse flashing. This pass measures both transforms and removes the remaining reverse dependency from procedural torso to camera position.

## Findings

The old early pass positioned the camera from the authored socket; the late pass positioned it again from the procedurally rotated chest/socket. Small circular input displaced the socket and camera by up to 5.33 mm; the bounded Slide flick reached 6.91 mm. Position coupling is confirmed. This is not evidence of an accumulating iterative solver divergence: the old solver already restored authored bones each frame and primarily used camera direction.

The larger phase error was in the rendered camera. Although Camera3D had interpolation OFF, its Player ancestor remained interpolated. Its rendered transform could differ from its raw global transform by **7.181 degrees and 42.93 mm at the 240 FPS cap** during a 10-degree flick. The V2 root/bow were already isolated, so they visually led the camera. Grounded body yaw and the raw MouseLook camera yaw agreed within 0.000006 degrees; changing the body yaw source was unnecessary.

Godot 4.6 interpolates an active ancestor chain and uploads descendant transforms even for an OFF descendant; `TopLevel` breaks that transform inheritance. See [SceneTreeFTI traversal](https://github.com/godotengine/godot/blob/4.6/scene/main/scene_tree_fti.cpp#L502-L541) and [Camera3D render upload](https://github.com/godotengine/godot/blob/4.6/scene/3d/camera_3d.cpp#L88-L93).

## Current ownership and sequence

While V2 is enabled, existing LookModule runs at -12, canonical wallrun effects at -11, and one complete V2 presentation callback at -10. Original priorities are restored on F9 OFF. Mouse sensitivity, pitch/yaw calculation, effects, physics priorities and gameplay movement remain unchanged. Weapon consumers still run after the final camera publication.

The single V2 callback samples interpolated Player translation/current yaw, restores exact authored bone locals, advances the authored animation, synchronously resolves and caches `FP_CAMERA_SOCKET` **world position before IK**, and snapshots this frame's MouseLook/effects basis. It computes the camera origin from that cache plus the calibrated offset. Torso/arm IK consumes that same immutable camera plan, then the final camera transform is published once. There is no late callback, second root write, post-IK camera socket read, or procedural-to-camera feedback.

The existing gameplay Camera3D stays at its existing scene path but becomes `TopLevel` while V2 is ON. Its world orientation is explicitly copied from the unchanged look/effects parent and calibrated view basis. This isolates render interpolation without modifying Player or globally disabling physics interpolation. F9 restores original parent transform inheritance, local transform, FOV owner, near/aspect, interpolation and module priorities. FOV remains source-calibrated.

BoneAttachment is the sole attachment writer through `skeleton_updated`; the previous direct `_grip.Transform` assignment is removed. The aim error readout derives the solved bow transform from hand + existing attachment calibration before the attachment notification. Frame-post-draw checks also measure the actual rendered attachment and bow.

Slide keeps full periodic yaw on spine_02 and locked pelvis/legs/root trajectory. The calibrated camera offset rotates analytically with relative view/body yaw around world vertical, then is added to the cached authored socket. It never reads the solved socket. No pose-specific camera heights, bow art corrections, new smoothing or damping are introduced.

## Validation

- 2400 render-frame samples at 60/240 FPS caps: slow yaw, slow pitch, circles and flicks for Idle and Slide. Final camera differs from independently reconstructed authored socket + offset by less than 0.00000007 m. Early/final camera difference and raw/rendered camera position difference are zero. Rendered camera/bow direction error remains below 0.00011 degrees; attachment error is zero.
- 721 samples at each cap through 0/90/180/270/360/720: full turret yaw, locked lower body, continuous seam, no accumulating drift. FP and external captures inspected; rear-facing camera is not inside the torso. Existing extreme waist twist/intersections remain outside this scope.
- Real moving Gym Slide: 720 degrees within one actual Slide, root remains locked, max solved aim error 0.000035 degrees. Exit returns to Idle.
- Source projection/height test PASS: Idle/Slide difference 0.509547 m, authored animation blend supplies intermediate heights, FOV/source framing and bow calibration unchanged, F10 and F9 restoration pass.
- Wallrun roll remains -19.5/+19.5 degrees in fallback and V2. Zero aim weights restore exact authored bones. Existing aim pitch clamp and reach limits remain.
- C# build: zero warnings/errors. Blender source, exported GLB, V2 scene, project settings, PlayerController, Look/WallRun/CrouchSlide/BowShoot hashes unchanged. Existing startup missing-arrow-marker warning and renderer light-unpair errors at test teardown remain unrelated.

Evidence: `.godot/humanoid-base/v2-feedback/{baseline,fixed,summary}.json`, `slide360_60.json`, `slide360_240.json`, screenshots; `.godot/v2-feedback-*.log`. Baseline samples preserve actual pre-late socket/chest values; fixed samples independently reconstruct pre-IK globals from the solver's saved authored locals. Telemetry runs only in the disposable fixture, with no per-frame production logging.

## Changed files

- Runtime: `Scripts/Player/Presentation/MainCharacterV2.cs`, `MainCharacterV2.Camera.cs`, `MainCharacterV2.Aim.cs`.
- Removed obsolete runtime callback: `V2AimLateUpdate.cs` and its `.uid`.
- Tests: `Tools/Character/V2AimProof.cs`, `verify_v2_slide360.gd`; added `verify_v2_feedback.gd` and `summarize_v2_feedback.py`.
- Documentation: this file and supersession note in `MAIN_CHARACTER_V2_CADENCE.md`.

No scenes/assets, Blender poses, movement/physics, commits or pushes changed in this pass.
