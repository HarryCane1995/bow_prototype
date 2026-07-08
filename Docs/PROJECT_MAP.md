# Project Map

Короткая карта, куда смотреть в проекте.

## Главные сцены

| Что | Где |
|---|---|
| Текущая main scene | `res://Scenes/Levels/Level_01/Level_01.tscn` |
| Игрок | `res://Scenes/Player.tscn` |
| Старый/тестовый прототип | `res://Scenes/BowPrototypeScene.tscn` |
| Runtime tuning window | `res://Scenes/Debug/RuntimeTuningPanel.tscn` |
| Grapple anchor gameplay prefab | `res://Scenes/GrappleAnchor.tscn` |
| Arrow projectile | `res://Scenes/ArrowProjectile.tscn` |
| Enemy prefabs | `res://Scenes/Enemies/` |

## Level_01

- Wrapper scene: `Scenes/Levels/Level_01/Level_01.tscn`
- Blender source: `Level_01_Blockout.blend`
- Imported child in wrapper: `ImportedLevel`
- Runtime binder: `Scripts/Levels/ImportedLevelMarkerBinder.cs`
- Wrapper-owned gameplay containers: `Gameplay/Enemies`, `Gameplay/GrappleAnchors`, `Gameplay/Triggers`
- Wrapper-owned lighting/environment: `World/DirectionalLight3D`, `World/WorldEnvironment`
- Debug helpers: `Debug/TemporarySafetyFloor`, `Debug/RuntimeTuningPanel`

## Player

Root scene: `Scenes/Player.tscn`

Main script: `Scripts/Player/PlayerController.cs`

Camera stack:

`Player -> CameraPivot -> CameraEffectsPivot -> Camera3D`

- `PlayerLookModule.cs` owns base yaw/pitch: yaw through `Player.Rotation.Y`, pitch through `CameraPivot.Rotation.X`.
- `CameraEffectsPivot` is the additive camera effects layer for wallrun roll/tilt and future camera shake/lean.

Player modules:

- `PlayerMovementModule.cs` - WASD movement.
- `PlayerJumpModule.cs` - gravity, jump, double jump.
- `PlayerCrouchSlideModule.cs` - crouch, slide, slide jump.
- `PlayerSlingshotGrappleModule.cs` - grapple selection, pull, launch.
- `PlayerWallRunModule.cs` - wall run, wall jump, additive camera effects on `CameraEffectsPivot`, FOV boost request.
- `PlayerBowShootModule.cs` - light/charged/precision shots.
- `PlayerBowVisualModule.cs` - bow draw/release visuals.
- `PlayerLookModule.cs` - mouse look and dev mouse capture/reload.
- `PlayerCameraFovModule.cs` - final gameplay `Camera3D.Fov` owner.
- `PlayerSpeedFovModule.cs` - speed-based FOV bonus calculation only.
- `PlayerViewModelRenderModule.cs` - separate SubViewport viewmodel render.
- `PlayerViewModelSwayModule.cs` - viewmodel sway, inertia, aim stabilization.
- `PlayerAbilityStateModule.cs` - ability tags, locks, priorities.

## Runtime Tuning

- Data resource: `Resources/Tuning/DefaultPlayerTuningProfile.tres`
- Data class: `Scripts/Player/Tuning/PlayerTuningProfile.cs`
- UI: `Scripts/Debug/RuntimeTuningPanel.cs`
- Open panel in play: `F2`
- Runtime save path: `user://player_tuning_runtime.json`

## Assets

- Bow models/textures: `Assets/Models/Bow/`
- Materials: `Assets/Materials/`
- Skybox: `Art/Skyboxes/ferndale_studio_10_4k.exr`
- Blender helpers: `Tools/Blender/`

## Debug / Helpers

- Crosshair: `Scripts/UI/CrosshairUI.cs`
- Startup window mode: `Scripts/System/StartupWindowModeController.cs`
- Imported marker binding: `Scripts/Levels/ImportedLevelMarkerBinder.cs`
- Test skybox setup: `Scripts/Rendering/TestSkyboxEnvironment.cs`
- Training target: `Scenes/Debug/TrainingTarget.tscn`

## Existing Longer Docs

- Movement details: `Docs/PLAYER_MOVEMENT.md`
- Ability arbitration: `Docs/PLAYER_ABILITY_STATE.md`
- Grapple details: `Docs/SLINGSHOT_GRAPPLE.md`
- Bow details: `Docs/BOW_SHOOTING.md`
- Runtime tuning details: `Docs/RUNTIME_TUNING.md`
- Viewmodel render/sway: `Docs/VIEWMODEL_RENDERING.md`, `Docs/VIEWMODEL_SWAY.md`
