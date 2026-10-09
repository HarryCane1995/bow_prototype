# V2 render cadence and Slide 360

**Historical pass.** The user subsequently reported worse flashing. Its CPU camera/bow metric did not catch interpolation inherited by the rendered camera. The early/late sequence described below has been replaced by the [pre-IK, single-pass camera correction](MAIN_CHARACTER_V2_FEEDBACK.md), with both CPU and rendered camera transforms verified.

Two local presentation fixes; no Blender, authored clips, movement, MouseLook, wallrun, projectile, bow art or animation timing changes.

## Measured jitter cause

The solver was already using the same rendered frame's camera basis: maximum solved direction error was below 0.000022°. However, the V2 root and Skeleton inherited physics interpolation while the camera and BoneAttachment did not. The bow's interpolated transform still received the interpolated ancestor frame. Comparing that transform with the current camera showed up to **0.02831° at 60 FPS / 0.48785° at 240 FPS**, despite the correct CPU solution and zero hand/attachment position error.

`MainCharacterV2` now disables physics interpolation on its complete render-authored presentation branch. Skeleton/meshes inherit OFF; BoneAttachment and its CyberBow hierarchy are consistent with the camera. Player physics interpolation is unchanged. The V2 root samples only the player's interpolated **position** for movement translation and uses current input yaw; the physics callback observes state without writing the presentation root. The late solver also refreshes the body frame after possible temporary look assist.

The existing sequence remains render based: early animation/camera pass (-10), existing look/weapon writers, late aim (+10), final bone/attachment/socket camera update, render. No smoothing, damping or extra input latency was added. The late camera still changes position only.

After the fix the measured interpolated bow error was **0.0000118° at 60 FPS / 0.0000139° at 240 FPS**. Actual rates were approximately 60.9 / 240.2 FPS with VSync disabled in the test fixture only. Slow yaw, very slow pitch, circular input and flick samples are included. No global project FPS/interpolation settings were edited.

Godot's current implementation can calculate an interpolated descendant transform even if that descendant is OFF while its ancestor is ON; see [Node3D get_global_transform_interpolated](https://github.com/godotengine/godot/blob/4.6/scene/3d/node_3d.cpp). This explains why checking the raw solved `GlobalTransform` alone missed the visual mismatch.

## Slide 360

Slide uses the full periodic relative yaw on **spine_02**, around world vertical expressed in skeleton space. Chest and the arms inherit this virtual rotary-joint layer; arm IK resolves the remaining grip/aim adjustment. Pelvis, thighs, legs and body-root yaw remain unchanged. Grounded yaw remains ±65°, pitch remains ±55° in both modes.

The full yaw is applied at one joint instead of splitting a wrapped angle into fractional rotations across two joints. Thus the basis is continuous at +180°/-180° and at every full revolution; there is no multi-turn accumulator and no accumulating winding error. Existing upper-body weight controls modest pitch/grounded support; in Slide any active aim influence enables full turret yaw. All three aim weights at zero still restore the authored pose.

The shared camera **position offset** rotates with the turret only during active Slide aim. Otherwise an offset pointing along the locked pelvis direction places the viewpoint behind the turned torso at 180°. Camera look remains wholly camera/MouseLook based, and the 0° Slide composition is preserved.

Debug readout now includes `AIM YAW` (wrapped relative degrees) and `SLIDE 360: ON/OFF`. A numeric wrap from +180 to -179 is expected; rendered bones do not snap.

## Verification / limits

- 721 rendered samples over two complete revolutions: spine followed the requested upper-body yaw, lower-body local poses/root heading stayed locked, and bow aim stayed aligned. Maximum measured one-degree spine step about 1.001°; no 358° jump.
- At 360° and 720°, local positions returned exactly; the same small quaternion comparison difference (<0.056° at float precision) was present after both turns, without growth.
- Real Gym input performed **720° within one actual Slide**, without changing duration, steering or trajectory. PASS; max bow direction error 0.000065°. Exit restored the ordinary mode.
- Existing source-camera projection/transition test PASS with aim weights zero. Its measurements now occur after render and relative to the interpolated V2 origin rather than the raw physics origin.
- First-person and external snapshots checked at 0/90/180/270/360°. Rear-view torso occlusion was corrected with the turret-relative position offset. Strong twisting/pinching around the waist and shoulder intersections remain at 180°/270°; this is the requested non-anatomical experiment, without mesh/finger polish. READY right-hand support remains; Nock/draw bridge is still deferred.
- Build: zero warnings/errors. Protected source/GLB, gameplay modules, V2 scene/attachment and project settings hashes unchanged. Existing renderer light-unpair messages can still occur during fixture teardown.

Telemetry and screenshots: `.godot/humanoid-base/v2-cadence/` (`baseline_yaw.csv`, `fixed_yaw.csv`, `summary.json`, `slide360.json`). `summarize_v2_cadence.py` derives headings from the captured camera basis without resampling.

Changed runtime files: `MainCharacterV2.cs`, `MainCharacterV2.Aim.cs`, `MainCharacterV2.Camera.cs`. Added bounded cadence/360 tests and telemetry summarizer; updated the existing live aim and source-camera fixtures. No scene or asset writes, commit or push.
