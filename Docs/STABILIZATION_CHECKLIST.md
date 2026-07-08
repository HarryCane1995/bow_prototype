# Stabilization Checklist

Manual smoke tests for small stabilization commits. Run from `Level_01.tscn` unless a test needs a different scene.

## Slide

- Do: sprint forward, press crouch/slide on flat ground, release after a short slide.
- Expected: player drops into slide, keeps forward momentum, then returns to normal height/control cleanly.
- Watch for: stuck crouch height, sudden stop, camera pop, slide starting while airborne when it should not.

## Slide Jump

- Do: start a slide, jump during the slide, then land and move again.
- Expected: slide jump launches with a readable boost and normal movement resumes after landing.
- Watch for: double-applied launch, missing jump, locked slide state, landing impulse repeating.

## Grapple Direct Hit

- Do: aim directly at a visible grapple anchor and fire grapple.
- Expected: grapple locks to the aimed anchor, pulls/launches according to tuning, then releases normally.
- Watch for: no lock on valid anchor, wrong anchor selection, pull fighting normal movement, state not releasing.

## Grapple Screen Assist

- Do: aim slightly near, but not exactly on, a valid anchor and fire grapple.
- Expected: screen assist can pick the intended nearby anchor within configured assist limits.
- Watch for: assist grabbing anchors behind the player, grabbing through obvious blockers, or ignoring close valid anchors.

## Grapple Pull/Launch

- Do: grapple from several ranges: close, medium, far, and while moving sideways.
- Expected: pull feels continuous, launch is readable, velocity returns to normal control after release.
- Watch for: velocity spikes, sideways snap, infinite pull, gravity/slide/wallrun fighting grapple priority.

## Wallrun

- Do: run beside a wall, jump or approach into wallrun, look around with the mouse, then jump off.
- Expected: wallrun starts on a valid wall, camera roll/tilt is additive on `CameraEffectsPivot`, mouse look remains free, wall jump pushes away from the wall, effects fade back to zero.
- Watch for: mouse look being overwritten, camera stuck rolled, direct pitch/roll on `CameraPivot` or `Camera3D`, repeated instant reattach to the same wall.

## Precision Bow

- Do: hold precision aim, shoot, release aim, then shoot normally.
- Expected: bow pose and FOV enter precision mode smoothly, shot uses precision behavior, normal bow state returns after release.
- Watch for: FOV stuck narrow, bow pose stuck, normal shot using precision state, projectile direction mismatch.

## Speed FOV

- Do: walk, sprint, slide, grapple, and stop while watching gameplay FOV.
- Expected: final `Camera3D.Fov` is owned by `PlayerCameraFovModule`; speed bonus ramps smoothly and fades without jumps.
- Watch for: FOV jitter, two systems fighting final FOV, precision aim and speed FOV stacking incorrectly.

## Viewmodel Sway

- Do: move, strafe, jump/land, aim, and shoot while watching the bow viewmodel.
- Expected: sway is visual only on `ViewModelSwayRoot`; gameplay camera, projectile direction, and `ShootPoint` remain stable.
- Watch for: bow scale/position changes after gameplay actions, viewmodel camera affecting gameplay camera, projectile leaving from visual-only offsets.

## Restart/Reset State

- Do: trigger restart/reset during normal movement, slide, grapple, wallrun, and precision aim.
- Expected: player returns to spawn with ability locks cleared, camera effects zeroed, FOV restored, viewmodel state sane.
- Watch for: retained velocity, stuck ability tag, rolled camera after reset, precision FOV stuck, hidden cursor/input mode mismatch.
