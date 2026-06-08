# Camera FOV

FOV основной камеры собирается в одном месте: `PlayerCameraFovModule` остаётся единственным runtime-владельцем `Camera3D.Fov`. Это важно, чтобы precision aim, speed FOV и будущие эффекты не перетирали друг друга каждый кадр.

## Базовый и precision FOV

`PlayerCameraFovModule` выбирает базовую цель:

- обычный режим: `PlayerFov`;
- precision aim: `PrecisionFov`.

После выбора базы модуль запрашивает speed bonus и применяет итог:

`targetFov = baseTargetFov + speedFovBonus`

Итог дополнительно ограничен разумным максимумом `140`, а сама камера плавно идёт к цели через `FovTransitionSpeed`.

## Speed FOV

`PlayerSpeedFovModule` не пишет в камеру. Он только читает `PlayerController.Velocity`, рассчитывает бонус от скорости и возвращает его владельцу FOV.

Формула:

`targetSpeedBonus = clamp((speed - MinSpeedForFov) * SpeedFovMultiplier, 0, MaxSpeedFovBonus)`

`SpeedFovMultiplier` - главная ручка силы эффекта. `MinSpeedForFov` отсекает обычную ходьбу, `MaxSpeedFovBonus` не даёт slide или slingshot launch раздуть FOV бесконечно.

Если `UseAxisBasedSpeedFov = true`, модуль не берёт общую длину горизонтальной скорости. Он раскладывает `Velocity` относительно камеры на две оси:

- forward/back: скорость вдоль направления взгляда на плоскости XZ;
- strafe: боковая скорость A/D вдоль camera-right на плоскости XZ.

Forward/back вклад считается через старый `SpeedFovMultiplier`, поэтому движение вперёд продолжает расширять FOV как раньше. Если `IncludeBackwardSpeedInForwardFov = true`, движение назад S использует тот же forward/back вклад; если false, отрицательная скорость назад игнорируется.

Strafe вклад считается отдельно:

`strafeBonus = max(0, strafeSpeedAbs - MinStrafeSpeedForFov) * StrafeSpeedFovMultiplier`

`StrafeSpeedFovMultiplier = 0` полностью отключает вклад чистого A/D в расширение FOV. Это полезно, чтобы убрать укачивание от бокового стрейфа, но оставить ощущение скорости от движения вперёд, slide и slingshot, когда движение преимущественно направлено вперёд.

Если `UseAxisBasedSpeedFov = false`, работает fallback по старой формуле через `velocity.Length()` или горизонтальную XZ-длину в зависимости от `UseFullVelocityForSpeedFov`.

## Smoothing

Speed bonus сглаживается отдельно от общего движения камеры:

- `SpeedFovSmoothUp` управляет расширением FOV при разгоне;
- `SpeedFovSmoothDown` управляет возвратом при замедлении.

Это убирает резкие скачки, когда velocity меняется ступенчато после slide, double jump redirect или slingshot launch.

## Precision aim

Если `DisableSpeedFovDuringPrecisionAim = true`, speed bonus сбрасывается в `0`, и итоговая цель остаётся `PrecisionFov`. Если флаг выключить, precision aim получит `PrecisionFov + speedFovBonus`, но финальный FOV всё равно ограничивается сверху.

Текущий Precision Ready включается удержанием Alt. Пока Alt зажат, `PlayerBowShootModule` вызывает `SetPrecisionAiming(true)`, и `PlayerCameraFovModule` плавно ведёт камеру к `PrecisionFov`. Сам Precision Shot остаётся мгновенным `Alt + ЛКМ press` и не использует старый таймер удержания ЛКМ.

## Runtime tuning

Все параметры speed FOV доступны в `PlayerTuningProfile` и runtime panel в группе `Camera / Speed FOV`:

- `EnableSpeedFov`;
- `SpeedFovMultiplier`;
- `MinSpeedForFov`;
- `MaxSpeedFovBonus`;
- `SpeedFovSmoothUp`;
- `SpeedFovSmoothDown`;
- `UseFullVelocityForSpeedFov`;
- `DisableSpeedFovDuringPrecisionAim`;
- `UseAxisBasedSpeedFov`;
- `StrafeSpeedFovMultiplier`;
- `MinStrafeSpeedForFov`;
- `IncludeBackwardSpeedInForwardFov`.

Если `UseFullVelocityForSpeedFov = true`, учитывается вся `Vector3`-скорость, включая вертикальный slingshot launch. Если false, берётся только горизонтальная XZ-скорость.

В axis-based режиме `UseFullVelocityForSpeedFov` не смешивает вертикальную скорость с боковым A/D: осевая модель работает с горизонтальными forward/strafe компонентами. При выключенном axis fallback сохраняет старое поведение этого флага.
