# Mechanics Index

Краткий индекс текущих механик и главных файлов.

## Player Movement

Script: `Scripts/Player/Modules/PlayerMovementModule.cs`

- WASD, ground/air acceleration, deceleration, direction-change response.
- Не пишет horizontal velocity, если ability arbitration отдал канал другой механике.

## Jump / Double Jump

Script: `Scripts/Player/Modules/PlayerJumpModule.cs`

- Gravity, grounded vertical velocity, coyote time, double jump.
- Double jump redirect может менять horizontal velocity по направлению input/camera.
- Grapple и wall run могут восстанавливать air jump charge.

## Crouch / Slide

Script: `Scripts/Player/Modules/PlayerCrouchSlideModule.cs`

- Crouch height/camera height.
- Slide, airborne slide buffer, slide jump boost.
- Slide регистрируется в ability arbitration и держит `HorizontalVelocity`.

## Bow Normal / Charged Shot

Scripts:

- `PlayerBowShootModule.cs`
- `PlayerBowVisualModule.cs`
- `ArrowProjectile.cs`

- LMB стреляет.
- Hold/release дает charged shot.
- Projectile uses speed, damage, gravity, lifetime.

## Precision Shot

Script: `Scripts/Player/Modules/PlayerBowShootModule.cs`

- Alt + LMB.
- Быстрый прямой/сильный shot.
- Использует отдельные tuning values: speed, damage, armor piercing.

## Slingshot Grapple

Scripts:

- `PlayerSlingshotGrappleModule.cs`
- `GrappleAnchor.cs`

Scene: `Scenes/GrappleAnchor.tscn`

- Ищет anchors в группе `grapple_anchor`.
- Есть direct raycast, screen-space assist и fallback cone.
- Pull phase тянет к anchor; launch phase выстреливает по сохраненной геометрии.
- Grapple имеет priority выше slide/wallrun.

## Wall Run

Script: `Scripts/Player/Modules/PlayerWallRunModule.cs`

- Raycast left/right ищет стену.
- Бежит вдоль стены в направлении взгляда/input/velocity.
- Управляет horizontal и vertical velocity.
- Jump во время wallrun делает wall jump.
- Камера кренится от стены; FOV может получать boost.

## Runtime Tuning

Scripts:

- `Scripts/Debug/RuntimeTuningPanel.cs`
- `Scripts/Player/Tuning/PlayerTuningProfile.cs`

Resource:

- `Resources/Tuning/DefaultPlayerTuningProfile.tres`

- `F2` открывает tuning panel.
- Sliders/toggles меняют runtime profile.
- Можно reset/load/save runtime values/save as project defaults.

## Ability Arbitration

Script: `Scripts/Player/Modules/PlayerAbilityStateModule.cs`

Главные locks:

- `HorizontalVelocity`
- `VerticalVelocity`
- `Jump`
- `DoubleJump`
- `Slide`
- `Grapple`
- `Shooting`
- `LookInput`
- `FovControl`

Текущие важные приоритеты:

- Default movement: `0`
- Slide: `30`
- WallRun: `40`
- Slingshot grapple pull: `60`
- Slingshot grapple launch: `65`

Практический смысл:

- Slide перебивает обычное движение.
- WallRun перебивает обычное движение и slide, но не shooting.
- Grapple перебивает WallRun/slide/обычное движение.
- Bow проверяет `Shooting`, но текущие movement abilities его не блокируют.
