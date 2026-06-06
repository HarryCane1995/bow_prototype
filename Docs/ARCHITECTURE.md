# Architecture

Проект построен вокруг модульного FPS-персонажа. `PlayerController` координирует работу отдельных систем, но не должен содержать детальную логику движения, прыжка, обзора, стрельбы или визуала лука.

## Основные части

- `PlayerController` - центральный координатор игрока. Собирает ссылки на модули, передаёт им нужные вызовы и связывает системы между собой.
- `PlayerMovementModule` - отвечает за горизонтальное движение игрока.
- `PlayerJumpModule` - отвечает за прыжок, coyote time, ground snap, simple double jump и redirect горизонтального движения на втором прыжке.
- `PlayerCrouchSlideModule` - отвечает за crouch/slide state, высоту коллайдера, высоту камеры, проверку потолка и горизонтальную скорость во время подката.
- `PlayerLookModule` - отвечает за mouse look, поворот камеры/игрока, mouse capture и dev hotkeys.
- `PlayerCameraFovModule` - отвечает за плавное изменение FOV основной камеры, включая precision aiming.
- `PlayerBowShootModule` - отвечает за игровую логику выстрела, натяжения и создание projectile-стрелы.
- `PlayerBowVisualModule` - отвечает за визуальное состояние bow viewmodel, Draw-анимацию и precision-поворот лука.
- `PlayerViewModelRenderModule` - отвечает за отдельный SubViewport-рендер FPS viewmodel, cull mask камер, visual layer лука и FOV viewmodel-камеры.
- `ArrowProjectile` - отвечает за поведение выпущенной стрелы как отдельного projectile-объекта, включая ручную математическую баллистику без `RigidBody3D`.
- `TargetHitbox` - отвечает за обработку попаданий по мишеням.
- `CrosshairUI` - отвечает за отображение и состояние прицела.

## Правила архитектуры

- `PlayerController` не должен превращаться в монолит и не должен содержать детальную логику отдельных систем.
- Каждый модуль отвечает за одну область поведения.
- Crouch и Slide живут в `PlayerCrouchSlideModule`; `PlayerMovementModule` только учитывает `CurrentSpeedMultiplier` и не перезаписывает X/Z velocity во время `IsSliding`.
- Double jump хранится в `PlayerJumpModule` как простой счётчик прыжков до приземления; не переносить эту логику в `PlayerController`.
- Double Jump Redirect применяется только на втором прыжке: если игрок держит WASD, `PlayerJumpModule` заменяет горизонтальную скорость направлением относительно камеры, а если ввода нет - оставляет текущий горизонтальный вектор.
- Precision shot не должен превращать `PlayerBowShootModule` в монолит: FOV остаётся в `PlayerCameraFovModule`, viewmodel-поза остаётся в `PlayerBowVisualModule`, полёт остаётся в `ArrowProjectile`.
- Новые игровые настройки должны быть доступны через Inspector с помощью `[Export]`.
- Связи между системами должны оставаться явными и простыми для проверки в сцене.
- При добавлении новой системы предпочтительно создать отдельный модуль или отдельный компонент, а не расширять существующий класс несвязанной логикой.

Все новые `[Export]`-поля должны сопровождаться русским XML summary-комментарием, понятным названием, а при необходимости — `ExportGroup`, `Range` и suffix. В Godot C# XML summary не заполняет стандартный Inspector tooltip автоматически, поэтому читаемость Inspector достигается через названия, группы, диапазоны и единицы измерения. Inspector должен быть рабочим интерфейсом настройки, а не набором непонятных переменных.
