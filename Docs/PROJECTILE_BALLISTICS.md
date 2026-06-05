# Projectile Ballistics

Стрелы летят как отдельные projectile-объекты через `ArrowProjectile`, без `RigidBody3D` и без физической симуляции тела.

## Модель движения

`ArrowProjectile` использует ручную математическую баллистику:

- при запуске получает направление выстрела и скорость;
- сохраняет текущую `velocity`;
- каждый physics frame добавляет падение вниз через `ProjectileGravity`, если `FlightMode == Ballistic`;
- обновляет позицию по `velocity * delta`;
- делает ray sweep между старой и новой позицией, чтобы быстрые стрелы не пролетали сквозь мишени.

`ProjectileGravity` настраивается в Inspector. Увеличение делает дугу заметнее и короче, уменьшение делает траекторию прямее.

## Flight Mode

`ArrowProjectile` поддерживает два режима:

- `Ballistic` - обычная стрела с gravity и дугой.
- `Straight` - precision projectile без gravity, velocity не проседает по Y.

## Ориентация стрелы

Во время полёта projectile поворачивается по текущему вектору `velocity`, поэтому наконечник должен смотреть туда, куда стрела реально движется по дуге.

Если импортированная модель стрелы смотрит не вдоль ожидаемой локальной оси, `RotationOffsetDegrees` позволяет поправить ориентацию из Inspector без изменения кода.

## Связь со стрельбой

`PlayerBowShootModule` создаёт projectile-стрелу и передаёт ей направление, скорость, урон и время жизни.

- Light shot настроен на скорость `50 m/s`.
- Charged shot остаётся быстрее и летит визуально прямее.
- Precision shot использует `Straight` flight mode и летит без падения.
- Gravity действует на light shot и charged shot.

Projectile-стрелы не являются частью FPS viewmodel. Визуальная `Arrow_Visual` в луке остаётся viewmodel-стрелой, а летящая стрела остаётся отдельным объектом основной сцены.
