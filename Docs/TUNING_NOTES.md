# Tuning Notes

Этот файл хранит удачные Inspector-настройки, которые стоит учитывать в будущих итерациях. Если значения меняются в редакторе и ощущаются лучше, обновлять этот файл вместе со сценой.

## BowPrototypeScene

`Scenes/BowPrototypeScene.tscn` сейчас является основным tuned playground для проверки ощущения движения, стрельбы и viewmodel.

### Movement

- `PlayerMovementModule.MoveSpeed = 10.0`
- `PlayerMovementModule.GroundAcceleration = 24.0`
- `PlayerMovementModule.GroundDeceleration = 28.0`
- `PlayerMovementModule.GroundDirectionChangeAcceleration = 55.0`
- `PlayerMovementModule.CounterStrafeBoost = 1.25`
- `PlayerMovementModule.DirectionChangeDotThreshold = 0.35`
- `PlayerMovementModule.AirAcceleration = 8.0`
- `PlayerMovementModule.AirDeceleration = 2.0`
- `PlayerMovementModule.AirDirectionChangeAcceleration = 12.0`

Ощущение: быстрый FPS movement с инерцией, но более отзывчивым counter-strafe при D -> A и W -> S. В воздухе управление мягче, чтобы double jump redirect оставался отдельным сильным действием.

### Jump

- `PlayerJumpModule.JumpVelocity = 10.0`
- `PlayerJumpModule.GravityMultiplier = 5.0`
- `PlayerJumpModule.EnableDoubleJump = true`
- `PlayerJumpModule.MaxJumpCount = 2`
- `PlayerJumpModule.DoubleJumpVelocityMultiplier = 1.0`
- `PlayerJumpModule.EnableDoubleJumpRedirect = true`
- `PlayerJumpModule.DoubleJumpRedirectSpeed = 8.0`
- `PlayerJumpModule.DoubleJumpRedirectKeepsVerticalVelocity = false`
- `PlayerJumpModule.DoubleJumpRedirectMinInput = 0.1`
- `PlayerJumpModule.GroundedVerticalVelocity = -3.2`
- `PlayerJumpModule.FloorSnapLength = 1.0`

Ощущение: высокий, быстрый и довольно аркадный прыжок с сильным падением; один дополнительный air jump восстанавливается после приземления. Второй прыжок может резко заменить горизонтальную скорость направлением текущего WASD-ввода относительно камеры.

### Crouch / Slide

- `PlayerCrouchSlideModule.CrouchSpeedMultiplier = 0.55`
- `PlayerCrouchSlideModule.SlideMinStartSpeed = 5.0`
- `PlayerCrouchSlideModule.SlideInitialSpeed = 11.0`
- `PlayerCrouchSlideModule.SlideDuration = 0.55`
- `PlayerCrouchSlideModule.SlideCooldown = 0.35`
- `PlayerCrouchSlideModule.SlideFriction = 14.0`
- `PlayerCrouchSlideModule.SlideSteeringStrength = 0.25`

Ощущение: Ctrl/C на месте даёт плавный crouch, а на скорости запускает короткий резкий slide с быстрым затуханием и лёгкой коррекцией направления.

### Look

- `PlayerLookModule.MouseSensitivity = 0.001`

Ощущение: более точное наведение, чем дефолтный `0.003`.

### Bow Shoot

- `PlayerBowShootModule.LightShotSpeed = 50.0`
- `PlayerBowShootModule.ChargedShotSpeed = 100.0`
- `PlayerBowShootModule.ChargeTime = 0.4`
- `PlayerBowShootModule.EnablePrecisionShot = true`
- `PlayerBowShootModule.PrecisionShotSpeed = 180.0`
- `PlayerBowShootModule.PrecisionShotDamage = 60.0`
- `PlayerBowShootModule.PrecisionShotArmorPiercing = true`

`LightShotSpeed` и `ChargedShotSpeed` могут приходить из дефолтов скрипта, если Godot не хранит их как scene override.

### Projectile Ballistics

- `ArrowProjectile.Speed = 50.0`
- `ArrowProjectile.ProjectileGravity = 18.0`
- `ArrowProjectile.Lifetime = 5.0`
- `ArrowProjectile.AlignToVelocity = true`

Ощущение: light shot быстро летит, но заметно уходит в дугу; charged shot визуально прямее, но gravity всё равно действует.

### Viewmodel

- `ViewModelCamera3D.Fov = 65.0`
- `PlayerCameraFovModule.PlayerFov = 75.0`
- `PlayerCameraFovModule.PrecisionFov = 45.0`
- `PlayerCameraFovModule.FovTransitionSpeed = 90.0`
- `ViewModelLightRig/MainLight.light_energy = 1.8`
- `ViewModelLightRig/FillLight.light_energy = 0.45`
- `BowViewModelHolder` scale в `BowPrototypeScene`: `0.185`
- `BowViewModelHolder` position в `BowPrototypeScene`: `(0.007, -0.35, -1.07)`
- `Bow_ViewModel` local Z offset: `-2.7132912`

Ощущение: лук рендерится в отдельном SubViewport и должен оставаться читаемым на тёмном фоне.

### World

- `WorldEnvironment.background_color` намеренно чёрный или дефолтно отсутствующий после сохранения в Godot, чтобы белые/светлые стрелы лучше читались.

## Player.tscn

`Scenes/Player.tscn` пока хранит более базовые/default значения и не обязан полностью совпадать с tuned playground:

- `MoveSpeed = 6.0`
- `Acceleration = 18.0`
- `AirControlMultiplier = 0.35`
- `JumpVelocity = 5.0`
- `GravityMultiplier = 1.0`
- `MouseSensitivity = 0.003`

Если нужно сделать prefab игрока источником истины, перенести удачные значения из `BowPrototypeScene.tscn` в `Player.tscn` отдельной явной задачей.
