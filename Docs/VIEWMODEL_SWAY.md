# Viewmodel Sway

Procedural viewmodel sway добавляет луку лёгкую экранную инерцию без влияния на gameplay aim.

## ViewModelSwayRoot

Внутри viewmodel SubViewport есть отдельный визуальный pivot:

`CanvasLayer_ViewModel/ViewModelSubViewportContainer/ViewModelSubViewport/ViewModelRoot/ViewModelSwayRoot`

`PlayerViewModelSwayModule` двигает только `ViewModelSwayRoot`. Основная `Camera3D`, `ViewModelCamera3D`, `ShootPoint`, crosshair и projectile direction не меняются.

Текущая структура:

- `ViewModelRoot`;
- `ViewModelCamera3D`;
- `ViewModelLightRig`;
- `ViewModelSwayRoot`;
- `BowViewModelHolder`;
- `Bow_ViewModel`.

`PlayerBowVisualModule` продолжает работать с `BowViewModelHolder`, `AnimationPlayer` и `Arrow_Visual`, а sway применяется внешним additive-слоем поверх этого визуала.

## Эффекты

Mouse lag читает mouse look delta из `PlayerLookModule.ConsumeLookDelta()`. При резком повороте лук слегка отстаёт и затем догоняет базовую позицию.

Movement inertia считает изменение `CharacterBody3D.Velocity` между кадрами. Резкий старт, торможение, strafe, slide и slingshot могут дать небольшой offset/rotation, но эффект ограничен clamp-параметрами.

Landing impulse срабатывает на переходе из air в grounded и использует предыдущую вертикальную скорость. Слабые касания ниже `LandingMinImpactSpeed` игнорируются.

## Mouse Lag Smoothing

Mouse lag теперь проходит через две стадии экспоненциального сглаживания:

- `MouseLagInputSmoothSpeed` сглаживает сырой mouse delta до расчёта target offset;
- `MouseLagOutputSmoothSpeed` сглаживает готовый position/rotation offset от mouse lag;
- `RotationSmoothSpeed` и `PositionSmoothSpeed` сглаживают итоговый общий offset после mouse lag, movement inertia и landing sway.

При высоких `MouseLagPositionAmount`, `MouseLagRotationAmount` и movement inertia лучше снижать smooth speed: эффект становится тяжелее и плавнее, а лук перестаёт резко перескакивать между кадрами. Более высокие smooth speed делают viewmodel быстрее и отзывчивее.

Smoothing применяется только к визуальному `ViewModelSwayRoot`. Gameplay camera, crosshair, `ShootPoint`, projectile spawn и projectile direction не меняются.

## Aim-Stabilized Sway

Aim stabilization - это визуальный слой поверх обычного sway. `PlayerViewModelSwayModule` после mouse lag, movement inertia и landing sway смотрит на `ArrowTipMarker` в визуальной стреле и мягко доворачивает `ViewModelSwayRoot`, чтобы наконечник стремился к центральному лучу `ViewModelCamera3D`.

Это не gameplay aim:

- `PlayerBowShootModule` не меняется;
- `ArrowProjectile` не меняется;
- `ShootPoint`, crosshair и projectile direction не меняются;
- основная `Camera3D` и `ViewModelCamera3D` не двигаются.

`ArrowTipMarker` должен быть `Marker3D` на наконечнике визуальной стрелы:

`ViewModelSwayRoot/BowViewModelHolder/Bow_ViewModel/BowRig/NockPoint_Bone/Arrow_Bone/Arrow_Visual/ArrowTipMarker`

Если маркер не назначен или не найден, aim stabilization отключается без падения и пишет warning. Положение маркера можно подстроить вручную в сцене, если примерная позиция не совпадает с наконечником модели.

Основные параметры:

- `EnableAimStabilization` включает слой;
- `AimStabilizationStrength` задаёт силу доворачивания к center ray;
- `AimStabilizationSmoothSpeed` задаёт плавность догоняния;
- `MaxAimCorrectionDegrees` ограничивает угол коррекции;
- `AimStabilizationDeadZone` убирает микрокоррекцию, когда наконечник уже почти в центре;
- `StabilizeOnlyWhenAiming` ограничивает слой precision aiming.

## Runtime Tuning

В runtime tuning panel группа `ViewModel / Sway` содержит основные ручки:

- `EnableMouseLag`;
- `EnableViewModelSway`;
- `MouseLagPositionAmount`;
- `MouseLagRotationAmount`;
- `EnableMouseLagSmoothing`;
- `MouseLagInputSmoothSpeed`;
- `MouseLagOutputSmoothSpeed`;
- `EnableMovementInertia`;
- `MovementInertiaPositionAmount`;
- `MovementInertiaRotationAmount`;
- `EnableLandingSway`;
- `LandingPositionAmount`;
- `LandingRotationAmount`;
- `SwayFollowSpeed`;
- `SwayReturnSpeed`;
- `ImpulseReturnSpeed`;
- `EnableRotationSmoothing`;
- `RotationSmoothSpeed`;
- `PositionSmoothSpeed`.

Группа `ViewModel / Aim Stabilization` содержит:

- `EnableAimStabilization`;
- `AimStabilizationStrength`;
- `AimStabilizationSmoothSpeed`;
- `MaxAimCorrectionDegrees`;
- `AimStabilizationDeadZone`;
- `StabilizeOnlyWhenAiming`.

Safety clamps вроде `MouseLagMaxPositionOffset`, `MovementInertiaMaxPositionOffset` и `LandingMaxRotationDegrees` остаются локальными export-полями `PlayerViewModelSwayModule`, чтобы при экстремальном slide/slingshot лук не улетал за экран.

## Архитектурное правило

Viewmodel procedural effects являются только визуальным слоем. Они не должны менять:

- основную игровую камеру;
- viewmodel-камеру;
- `ShootPoint`;
- projectile spawn/direction;
- ballistic/projectile logic.
