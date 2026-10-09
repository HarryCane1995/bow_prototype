# Main Character V2 — runtime arm aim experiment

BH01 animation remains the authoring layer. This pass adds bounded runtime rotations to the same Skeleton3D, so the existing CyberBow attachment on `hand.L` follows camera aim. Blender, exported clips, bone rests, attachment calibration, movement/physics and projectile code were not edited.

Current follow-up: [render cadence and Slide 360](MAIN_CHARACTER_V2_CADENCE.md) removes mixed presentation interpolation and replaces the Slide yaw clamp with a full rotary spine layer. The ±65° bound described below now applies only outside Slide; pitch remains ±55°.

## Wallrun comparison

The suspected sign inversion was not reproduced and the user confirmed it was a visual illusion. With the same canonical module state, WORLD roll is **Left −19.5°, Right +19.5°** in both fallback and V2 (difference below 0.00002°). Fallback keeps its viewmodel screen-horizontal; the previous V2 bow stayed body-horizontal and therefore appeared tilted relative to the rolled camera. No sign multiplier or canonical wallrun effect change was made.

Camera calibration sets the constant local orientation once on enable. Per-frame socket updates now write Position only. While V2 is enabled, its wallrun effects process runs before the early camera pass so position compensation reads the current effect transform. Its previous priority is restored on fallback.

## Runtime layer

`MainCharacterV2.Aim.cs` implements a small analytic two-bone solver using the [Skeleton3D pose API](https://docs.godotengine.org/en/4.6/classes/class_skeleton3d.html). It modifies rotations only, keeps bone lengths, uses the current authored elbow as a pole, and clamps targets to the arm's reachable distance. No AnimationTree rewrite, additional skeleton, runtime mesh rotation independent of the hand, or animation bake.

- `V2_BowAimTarget`: camera-derived world orientation, bounded relative to body yaw. Its -Z is the desired aim; CyberBow's measured -X shooting axis maps to it, with +Y limb span and +Z up.
- Bones modified: `spine_02`, `chest`; `upper_arm.L/R`, `forearm.L/R`, `hand.L/R`. Pelvis, legs and finger local poses are untouched.
- Grip targets orbit in the authored eye-relative vicinity. Modest torso support is distributed 40% to spine_02 and 60% to chest. The existing socket then follows the resulting chest position, never its rotation.
- Default `UpperBodyAimWeight=0.3`, `LeftArmIKWeight=1`, `RightArmIKWeight=1`; all are exported under **V2 Runtime Aim** on MainCharacterV2. Setting all three to zero restores the exact authored pose, including after a static clip has stopped.
- `AimYawLimit=65°`, `AimPitchLimit=55°`. Grounded body yaw retains its existing player-following behavior; Slide retains its locked trajectory yaw. Beyond the bounds IK clamps, while gameplay camera/shot direction remain unrestricted by IK.
- The right arm currently supports the rotated READY pose only. **Right-hand Nock/draw IK is deferred**, as explicitly permitted for this first left-arm/aim pass. Connecting the Blender Nock semantics requires a V2 string/draw presentation bridge: the current fallback string is owned by disabled procedural hands. No substitute draw timing/system was introduced; `RightArmIKWeight` currently controls READY support, not nock tracking.

Order: canonical effects → restore prior pre-IK local poses → manual AnimationPlayer.Advance → early socket camera (priority -10, before shooting) → existing weapon writers → late arm/torso IK (priority 10) → publish final `hand.L` to the same BoneAttachment → final socket camera position. Bone targets are calculated from fresh authored poses and camera orientation, not last frame's corrected bow, preventing cumulative IK/feedback. The late pass uses the same camera basis and cannot steer the projectile.

## Validation

- Build: 0 warnings/errors.
- `verify_v2_aim.gd`: controlled states in the real Gym, Idle/Slide center, ±45° yaw, ±40° pitch, diagonals, beyond-limit look, and external view. Bow forward error within the allowed range <0.00003°. Every lower-body local pose is unchanged; all-zero weights restore every authored bone local pose. Bow stays attached to the solved hand. Maximum measured reach shortfall in normal test angles ~2 cm in Idle looking up; solver retracts the hand rather than stretching the arm.
- `verify_v2_aim_live.gd`: real movement/slide input, changing yaw/pitch each frame, locked trajectory, and Idle return. PASS, maximum bow angle error 0.0000231°, final attachment checked against current hand each render frame.
- `verify_v2_camera.gd`: original Blender camera projection and real socket transition checks PASS with the optional aim weights disabled.
- Protected file hashes verified unchanged: PoseLab, V2 GLB, V2 scene/attachment and Player/Look/WallRun/Slide modules.

This is functional blocking, not polished anatomy: shoulders/elbows/wrists can pinch the simple mesh at steep angles; no collision avoidance or finger reposing. The right hand does not pull the string yet. Beyond aim limits the bow intentionally diverges from the camera; projectile direction still uses the existing camera path. The old ArrowTipMarker warning and renderer light-unpair teardown errors remain in the fixture, as before this pass.

Evidence: `.godot/humanoid-base/v2-aim/`, `.godot/v2-aim-baseline.log`, `.godot/v2-aim-proof.log`, `.godot/v2-aim-live.log`. Controlled wall states use a disposable test fixture with frozen motor, separate from the real-input Slide test.

## Changed files

- `Scripts/Player/Presentation/MainCharacterV2.cs`: initialize late aim layer, restore pre-IK pose before animation/fallback.
- `Scripts/Player/Presentation/MainCharacterV2.Camera.cs`: position-only frame writes/current-effect ordering.
- `Scripts/Player/Presentation/MainCharacterV2.Aim.cs`, `V2AimLateUpdate.cs`: solver, tuning, late presentation pass.
- `Tools/Character/V2AimProof.cs`, `verify_v2_aim.gd`, `verify_v2_aim_live.gd`: disposable fixtures/checks; generated script UIDs.
- `Tools/Character/verify_v2_camera.gd`: disable optional aim for source-only projection checks.
- This report and the existing V2 overview. No source asset/scene/clip changes or commit/push.
