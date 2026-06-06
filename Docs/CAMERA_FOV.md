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

## Smoothing

Speed bonus сглаживается отдельно от общего движения камеры:

- `SpeedFovSmoothUp` управляет расширением FOV при разгоне;
- `SpeedFovSmoothDown` управляет возвратом при замедлении.

Это убирает резкие скачки, когда velocity меняется ступенчато после slide, double jump redirect или slingshot launch.

## Precision aim

Если `DisableSpeedFovDuringPrecisionAim = true`, speed bonus сбрасывается в `0`, и итоговая цель остаётся `PrecisionFov`. Если флаг выключить, precision aim получит `PrecisionFov + speedFovBonus`, но финальный FOV всё равно ограничивается сверху.

## Runtime tuning

Все параметры speed FOV доступны в `PlayerTuningProfile` и runtime panel в группе `Camera / Speed FOV`:

- `EnableSpeedFov`;
- `SpeedFovMultiplier`;
- `MinSpeedForFov`;
- `MaxSpeedFovBonus`;
- `SpeedFovSmoothUp`;
- `SpeedFovSmoothDown`;
- `UseFullVelocityForSpeedFov`;
- `DisableSpeedFovDuringPrecisionAim`.

Если `UseFullVelocityForSpeedFov = true`, учитывается вся `Vector3`-скорость, включая вертикальный slingshot launch. Если false, берётся только горизонтальная XZ-скорость.
