# Architecture

Проект построен вокруг модульного FPS-персонажа. `PlayerController` координирует работу отдельных систем, но не должен содержать детальную логику движения, прыжка, обзора, стрельбы или визуала лука.

Для архитектуры взаимодействий действует отдельное правило из `Docs/INTERACTION_ARCHITECTURE.md`: Player expresses intent; world objects own their interaction behavior.

Для runtime-настройки используется `Docs/RUNTIME_TUNING.md`: централизованный tuning profile разрешён только как data-only ресурс, а gameplay logic остаётся в соответствующих модулях.

Skybox/HDRI workflow описан в `Docs/SKYBOX.md`: активная сцена использует существующую `WorldEnvironment`, а локальные `.hdr`/`.exr` ассеты не коммитятся.

## Основные части

- `PlayerController` - центральный координатор игрока. Собирает ссылки на модули, передаёт им нужные вызовы и связывает системы между собой.
- `PlayerMovementModule` - отвечает за горизонтальное движение игрока.
- `PlayerJumpModule` - отвечает за прыжок, coyote time, ground snap, simple double jump и redirect горизонтального движения на втором прыжке.
- `PlayerCrouchSlideModule` - отвечает за crouch/slide state, высоту коллайдера, высоту камеры, проверку потолка, горизонтальную скорость во время подката, airborne slide buffer и горизонтальную часть slide jump.
- `PlayerSlingshotGrappleModule` - отвечает за slingshot grapple: выбор `GrappleAnchor`, внешнее управление `Velocity` во время Pulling и выстрел игрока по сохранённому направлению от стартовой позиции к точке.
- `PlayerLookModule` - отвечает за mouse look, поворот камеры/игрока, mouse capture и dev hotkeys.
- `PlayerCameraFovModule` - отвечает за плавное изменение FOV основной камеры, включая precision aiming; это единственный runtime-модуль, который пишет в `Camera3D.Fov`.
- `PlayerSpeedFovModule` - считает speed-based FOV bonus по скорости игрока и отдаёт его `PlayerCameraFovModule`, но сам не владеет финальным FOV камеры.
- `PlayerBowShootModule` - отвечает за игровую логику выстрела, натяжения и создание projectile-стрелы.
- `PlayerBowVisualModule` - отвечает за визуальное состояние bow viewmodel, Draw-анимацию и precision-поворот лука.
- `PlayerViewModelRenderModule` - отвечает за отдельный SubViewport-рендер FPS viewmodel, cull mask камер, visual layer лука и FOV viewmodel-камеры.
- `PlayerViewModelSwayModule` - отвечает за procedural sway/inertia viewmodel через `ViewModelSwayRoot`; не меняет игровые камеры, `ShootPoint` или направление projectile.
- `PlayerTuningProfile` - data-only `Resource` с live-настройками игрока и оружия; не содержит gameplay logic.
- `RuntimeTuningPanel` - debug-окно для изменения `PlayerTuningProfile` во время Play.
- `ArrowProjectile` - отвечает за поведение выпущенной стрелы как отдельного projectile-объекта, включая ручную математическую баллистику без `RigidBody3D`.
- `GrappleAnchor` - специальная `Area3D`-точка в группе `grapple_anchor`, за которую разрешено цепляться slingshot grapple-модулю.
- `TargetHitbox` - отвечает за обработку попаданий по мишеням.
- `CrosshairUI` - отвечает за отображение и состояние прицела.

## Правила архитектуры

- `PlayerController` не должен превращаться в монолит и не должен содержать детальную логику отдельных систем.
- Каждый модуль отвечает за одну область поведения.
- Логика конкретных интерактивных объектов не должна жить в `PlayerController`: игрок выражает намерение, а объект сам реализует своё поведение через общий контракт взаимодействия.
- Crouch и Slide живут в `PlayerCrouchSlideModule`; `PlayerMovementModule` только учитывает `CurrentSpeedMultiplier` и не перезаписывает X/Z velocity во время `IsSliding`.
- Slide jump разделён по ответственности: `PlayerCrouchSlideModule` завершает slide и готовит горизонтальный boost, а `PlayerJumpModule` остаётся владельцем вертикального jump impulse, coyote time и double jump counters.
- Slingshot grapple живёт в `PlayerSlingshotGrappleModule`; когда модуль активен, обычные movement/jump/slide-модули должны уважать его флаги блокировки и не перетирать внешнюю `Velocity`.
- Double jump хранится в `PlayerJumpModule` как простой счётчик прыжков до приземления; не переносить эту логику в `PlayerController`.
- Double Jump Redirect применяется только на втором прыжке: если игрок держит WASD, `PlayerJumpModule` заменяет горизонтальную скорость направлением относительно камеры, а если ввода нет - оставляет текущий горизонтальный вектор.
- Precision shot не должен превращать `PlayerBowShootModule` в монолит: FOV остаётся в `PlayerCameraFovModule`, viewmodel-поза остаётся в `PlayerBowVisualModule`, полёт остаётся в `ArrowProjectile`.
- Viewmodel procedural effects применяются только к `ViewModelSwayRoot` и не должны менять игровую камеру, viewmodel-камеру или projectile direction.
- Speed FOV не должен создавать второго владельца `Camera3D.Fov`: `PlayerSpeedFovModule` считает только бонус, а итоговый `base/precision FOV + speed bonus` применяет `PlayerCameraFovModule`.
- Новые игровые настройки должны быть доступны через Inspector с помощью `[Export]`.
- Централизованный tuning profile разрешён только для данных настройки. Он не должен содержать gameplay logic, вызывать gameplay-методы или знать конкретные правила поведения модулей.
- Связи между системами должны оставаться явными и простыми для проверки в сцене.
- При добавлении новой системы предпочтительно создать отдельный модуль или отдельный компонент, а не расширять существующий класс несвязанной логикой.
- Подробные правила для дверей, сундуков, рычагов, терминалов и других interact-объектов описаны в `Docs/INTERACTION_ARCHITECTURE.md`.

Все новые `[Export]`-поля должны сопровождаться русским XML summary-комментарием, понятным названием, а при необходимости — `ExportGroup`, `Range` и suffix. В Godot C# XML summary не заполняет стандартный Inspector tooltip автоматически, поэтому читаемость Inspector достигается через названия, группы, диапазоны и единицы измерения. Inspector должен быть рабочим интерфейсом настройки, а не набором непонятных переменных.
