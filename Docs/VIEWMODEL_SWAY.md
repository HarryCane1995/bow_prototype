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

## Runtime Tuning

В runtime tuning panel группа `ViewModel / Sway` содержит основные ручки:

- `EnableMouseLag`;
- `MouseLagPositionAmount`;
- `MouseLagRotationAmount`;
- `EnableMovementInertia`;
- `MovementInertiaPositionAmount`;
- `MovementInertiaRotationAmount`;
- `EnableLandingSway`;
- `LandingPositionAmount`;
- `LandingRotationAmount`;
- `SwayFollowSpeed`;
- `SwayReturnSpeed`;
- `ImpulseReturnSpeed`.

Safety clamps вроде `MouseLagMaxPositionOffset`, `MovementInertiaMaxPositionOffset` и `LandingMaxRotationDegrees` остаются локальными export-полями `PlayerViewModelSwayModule`, чтобы при экстремальном slide/slingshot лук не улетал за экран.

## Архитектурное правило

Viewmodel procedural effects являются только визуальным слоем. Они не должны менять:

- основную игровую камеру;
- viewmodel-камеру;
- `ShootPoint`;
- projectile spawn/direction;
- ballistic/projectile logic.
