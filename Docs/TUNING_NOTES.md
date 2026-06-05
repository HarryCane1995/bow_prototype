# Tuning Notes

Этот файл хранит удачные Inspector-настройки, которые стоит учитывать в будущих итерациях. Если значения меняются в редакторе и ощущаются лучше, обновлять этот файл вместе со сценой.

## BowPrototypeScene

`Scenes/BowPrototypeScene.tscn` сейчас является основным tuned playground для проверки ощущения движения, стрельбы и viewmodel.

### Movement

- `PlayerMovementModule.MoveSpeed = 10.0`
- `PlayerMovementModule.Acceleration = 60.0`
- `PlayerMovementModule.AirControlMultiplier = 0.5`

Ощущение: быстрый FPS movement с резким стартом/сменой направления.

### Jump

- `PlayerJumpModule.JumpVelocity = 10.0`
- `PlayerJumpModule.GravityMultiplier = 5.0`
- `PlayerJumpModule.GroundedVerticalVelocity = -3.2`
- `PlayerJumpModule.FloorSnapLength = 1.0`

Ощущение: высокий, быстрый и довольно аркадный прыжок с сильным падением.

### Look

- `PlayerLookModule.MouseSensitivity = 0.001`

Ощущение: более точное наведение, чем дефолтный `0.003`.

### Bow Shoot

- `PlayerBowShootModule.LightShotSpeed = 50.0`
- `PlayerBowShootModule.ChargedShotSpeed = 100.0`
- `PlayerBowShootModule.ChargeTime = 0.4`
- `PlayerBowShootModule.PrecisionChargeTime = 1.3`
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
- `PlayerCameraFovModule.DefaultFov = 75.0`
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
