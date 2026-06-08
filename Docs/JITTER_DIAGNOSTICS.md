# Jitter Diagnostics

## A/D Strafe Around Target

Observed symptom: when the player strafes A/D around a target and keeps aiming at it with the mouse, the world target and viewmodel bow can show microstutter, like hard friction.

## Update Loops Checked

- `PlayerController._PhysicsProcess` updates movement velocity and calls `MoveAndSlide`.
- `PlayerMovementModule.UpdateHorizontalVelocity` runs from `_PhysicsProcess`.
- `PlayerLookModule.HandleInput` applies mouse yaw/pitch from `_Input`; `_Process` only updates temporary look assist.
- `PlayerLookModule.LastLookDelta` is consumed through `ConsumeLookDelta()` and reset to `Vector2.Zero`.
- `PlayerCameraFovModule._Process` updates FOV each rendered frame.
- `PlayerSpeedFovModule.UpdateSpeedFovBonus` uses exponential smoothing for the speed FOV bonus.
- `PlayerViewModelSwayModule._Process` updates visual sway each rendered frame.
- Viewmodel aim stabilization is inside `PlayerViewModelSwayModule` and runs after normal sway.
- `Camera3D` is a child of `Player/CameraPivot`; no separate camera position update loop was found.

## Project Settings Checked

- `physics/3d/physics_engine = "Jolt Physics"`.
- `physics/common/physics_ticks_per_second` was not explicitly set in `project.godot`; runtime readout shows the active engine value.
- `physics/common/physics_interpolation` is enabled for cadence testing.
- `application/run/max_fps` was not explicitly set.
- VSync mode was not explicitly set.

`StartupWindowModeController` has an opt-in dev override:

- `EnablePhysicsTickOverride = false`;
- `PhysicsTicksPerSecondOverride = 120`.

Enable it manually in Inspector to test whether higher physics cadence reduces the A/D strafe jitter.

## Runtime Isolation Order

1. Disable `EnableViewModelSway` and `EnableAimStabilization`.
2. Disable `EnableSpeedFov`.
3. Disable `EnableDirectionChangeAcceleration` and `EnableCounterStrafeBoost`.
4. Enable physics interpolation and retest.
5. Enable `PhysicsTicksPerSecondOverride = 120` in `StartupWindowModeController` and retest.
6. If needed, test a 60 FPS cap from project settings or driver settings.

Watch runtime readouts:

- `Speed FOV Debug`: `speed`, `forward`, `strafe`, `bonus`, `targetFov`, `cameraFov`.
- `Cadence Debug`: FPS, physics ticks, physics interpolation, velocity X/Z, horizontal speed, camera FOV, Speed FOV state/bonus.

## Likely Sources To Confirm

- Direction-change acceleration can switch response when A/D strafe and camera yaw continuously change the desired direction.
- Counter-strafe boost can amplify that switch when velocity and desired direction oppose each other.
- Viewmodel movement inertia uses velocity differences in `_Process`, while velocity is authored in `_PhysicsProcess`; this can make visual sway sensitive to render/physics cadence.
- Speed FOV is already smoothed, but its target can still change rapidly if speed axes oscillate while circling a target.
- If `PhysicsTicksPerSecondOverride = 120` reduces the jitter, the source is very likely discrete physics movement being rendered between physics ticks.

These toggles are diagnostic switches. Defaults stay enabled so existing movement, slide, grapple, shooting, and enemies keep their current behavior unless a tester disables a switch manually.
