# First-person hands: blocking pass

Editable source: `Assets/Models/Player/FP_Hands_Blocking.blend`, directly imported by Godot. The current CyberBow sources/GLB are preserved. `Scenes/ViewModel/FirstPersonHands.tscn` instances the hands under the shared Player's existing `ViewModelSwayRoot`.

The source contains 704 vertices / 572 polygon faces, metre units, 11 bones: Root plus Upper, Forearm, Hand, Fingers and Thumb for each side. Rigid weights, faceted gloves and segmented forearm shells are intentional blocking. No torso or detailed finger anatomy. The `Heavy` shape key compares A (0, selected slim) and B (1, +22% segment thickness).

`FirstPersonHands.cs` reads presentation state from `PlayerBowVisualModule`: DrawAmount, IsPrecisionAiming and ShotVisualSequence. It uses a small two-segment arm solve, wrist rotation and a coarse finger opening on release. It never reads input or writes player velocity, camera FOV or gameplay state. Idle, draw, charged hold, release/reset and precision are procedural poses; no production animation library is implied. Existing sway is inherited from the shared parent.

The visible CyberBow preview has no draw animation or deforming limb rig. The legacy hidden bow AnimationPlayer remains in place. The new presentation adds two simple string segments and moves/rotates the existing arrow through its bow rest as the right hand pulls. The existing arrow visibility and shot contracts remain authoritative. CyberBow limbs are still rigid. This is the intended minimum prototype for the current visual pipeline.

The shared BowViewModelHolder was raised 0.08 m and moved forward 0.18 m to leave room for the hands. Its asset scale is unchanged. The existing independent 65-degree viewmodel FOV isolates proportions from world speed/precision FOV. In the quick checks, world FOV ranged from 31 to 121 degrees.

For manual refinement:

1. Open the `.blend`; edit `Hands_Blocking`, its Heavy shape key or `HandsRig` in Edit/Pose Mode. The guide empties show bow grip and idle/drawn nock positions in the calibrated FPS space.
2. Save and reimport in Godot. Do not edit `.godot/imported` output.
3. Adjust the presentation-only settings on `FirstPersonHands`: DrawOffset, PrecisionHandLift, NockIdle, string tips, pose/release response and HeavyProportions. The wrist bind pose comes from the source skeleton, so changes to rest positions may need a corresponding nock/guide adjustment.
4. Check LMB draw/release and Alt precision in `Level_01` or Movement Gym. Keep movement/tuning unchanged when adjusting the hands.

`Tools/Blender/build_player_hands.py` records the original blocking construction. It refuses to overwrite an existing source unless run with `-- --rebuild`; that flag replaces manual edits to this asset. Prefer editing the saved `.blend` for subsequent art work.

Validation: Godot import, .NET build, idle/A/B/draw/charged/release/reset/precision screenshots and one continuous slide → jump → wallrun → wall jump → grapple run with firing. The hands stayed below the aiming area in the inspected frames. Forearms intentionally continue beyond the lower screen edges. No exhaustive animation/clipping audit was performed. The earlier missing ArrowTipMarker/aim-stabilization warning remains outside this pass.
