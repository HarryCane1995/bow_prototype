# Architecture

Проект построен вокруг модульного FPS-персонажа. `PlayerController` координирует работу отдельных систем, но не должен содержать детальную логику движения, прыжка, обзора, стрельбы или визуала лука.

Для архитектуры взаимодействий действует отдельное правило из `Docs/INTERACTION_ARCHITECTURE.md`: Player expresses intent; world objects own their interaction behavior.

Для runtime-настройки используется `Docs/RUNTIME_TUNING.md`: централизованный tuning profile разрешён только как data-only ресурс, а gameplay logic остаётся в соответствующих модулях.

Skybox/HDRI workflow описан в `Docs/SKYBOX.md`: активная сцена использует существующую `WorldEnvironment`, а локальные `.hdr`/`.exr` ассеты не коммитятся.

## Основные части

- `PlayerController` - центральный координатор игрока. Собирает ссылки на модули, передаёт им нужные вызовы и связывает системы между собой.
- `PlayerAbilityStateModule` - arbitration layer для ability/motor authority. Хранит active ability requests, priorities и lock-флаги, но не реализует slide, grapple, jump, shooting или другие механики.
- `PlayerMovementModule` - отвечает за горизонтальное движение игрока.
- `PlayerJumpModule` - отвечает за прыжок, coyote time, ground snap, simple double jump и redirect горизонтального движения на втором прыжке.
- `PlayerCrouchSlideModule` - отвечает за crouch/slide state, высоту коллайдера, высоту камеры, проверку потолка, горизонтальную скорость во время подката, airborne slide buffer и горизонтальную часть slide jump.
- `PlayerSlingshotGrappleModule` - отвечает за slingshot grapple: выбор `GrappleAnchor`, screen-space aim assist, внешнее управление `Velocity` во время Pulling и выстрел игрока по сохранённому направлению от стартовой позиции к точке.
- `PlayerLookModule` - отвечает за mouse look, поворот камеры/игрока, temporary look assist для grapple camera snap, mouse capture и dev hotkeys.
- `PlayerCameraFovModule` - отвечает за плавное изменение FOV основной камеры, включая precision aiming; это единственный runtime-модуль, который пишет в `Camera3D.Fov`.
- `PlayerSpeedFovModule` - считает speed-based FOV bonus по скорости игрока и отдаёт его `PlayerCameraFovModule`, но сам не владеет финальным FOV камеры.
- `PlayerBowShootModule` - отвечает за игровую логику выстрела, натяжения и создание projectile-стрелы.
- `PlayerBowVisualModule` - отвечает за визуальное состояние bow viewmodel, Draw-анимацию и precision-поворот лука.
- `PlayerViewModelRenderModule` - отвечает за отдельный SubViewport-рендер FPS viewmodel, cull mask камер, visual layer лука и FOV viewmodel-камеры.
- `PlayerViewModelSwayModule` - отвечает за procedural sway/inertia viewmodel через `ViewModelSwayRoot`; не меняет игровые камеры, `ShootPoint` или направление projectile.
- `PlayerTuningProfile` - data-only `Resource` с live-настройками игрока и оружия; не содержит gameplay logic.
- `RuntimeTuningPanel` - debug-окно для изменения `PlayerTuningProfile` во время Play.
- `ArrowProjectile` - отвечает за поведение выпущенной стрелы как отдельного projectile-объекта, включая ручную математическую баллистику без `RigidBody3D`.
- `BasicPatrolShooterEnemy` - простая временная combat-цель: сама владеет патрулём, стрельбой по игроку, здоровьем и смертью.
- `EnemyProjectile` - отдельный projectile врага: сам летит прямо, обрабатывает попадание в игрока и перезагрузку сцены.
- `GrappleAnchor` - специальная `Area3D`-точка в группе `grapple_anchor`, за которую разрешено цепляться slingshot grapple-модулю.
- `TargetHitbox` - отвечает за обработку попаданий по мишеням.
- `CrosshairUI` - отвечает за отображение и состояние прицела.

## Правила архитектуры

- `PlayerController` не должен превращаться в монолит и не должен содержать детальную логику отдельных систем.
- `PlayerController` может хранить ссылку на `PlayerAbilityStateModule`, но не должен сам решать priority/lock rules или превращаться в God-object.
- Каждый модуль отвечает за одну область поведения.
- Новые механики должны запрашивать locks/authority через `PlayerAbilityStateModule`, а не напрямую ломать чужие состояния.
- Логика конкретных интерактивных объектов не должна жить в `PlayerController`: игрок выражает намерение, а объект сам реализует своё поведение через общий контракт взаимодействия.
- Enemies own their own AI and shooting behavior; `PlayerController` does not know how enemies patrol, aim or fire.
- `EnemyProjectile` owns its own hit behavior; player death in this prototype is a scene reload triggered by projectile contact with the `player` group.
- Crouch и Slide живут в `PlayerCrouchSlideModule`; `PlayerMovementModule` только учитывает `CurrentSpeedMultiplier` и не перезаписывает X/Z velocity во время `IsSliding`.
- Slide jump разделён по ответственности: `PlayerCrouchSlideModule` завершает slide и готовит горизонтальный boost, а `PlayerJumpModule` остаётся владельцем вертикального jump impulse, coyote time и double jump counters.
- Slingshot grapple живёт в `PlayerSlingshotGrappleModule`; когда модуль активен, обычные movement/jump/slide-модули должны уважать его флаги блокировки и не перетирать внешнюю `Velocity`.
- Slingshot grapple выбирает anchor и может запросить camera snap, но не поворачивает `Camera3D` напрямую. Все yaw/pitch изменения должны проходить через `PlayerLookModule`.
- `PlayerSlingshotGrappleModule` определяет текущий доступный anchor, но визуал жёлтого available-highlight принадлежит `GrappleAnchor`.
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

## ViewModel Aim Stabilization Rule

Aim-stabilized sway lives inside `PlayerViewModelSwayModule` and is only a visual correction for `ViewModelSwayRoot`. It may use `ViewModelCamera3D` and `ArrowTipMarker` to keep the visual arrow tip near the center ray, but it must not move gameplay `Camera3D`, `ViewModelCamera3D`, `ShootPoint`, crosshair, `PlayerBowShootModule`, `ArrowProjectile`, or projectile direction.

`ArrowTipMarker` is a scene marker for visual alignment only. It is not an aiming source for gameplay code.

## Precision Shot Rule

- Precision Shot активируется только как instant `Alt + ЛКМ press` через `PlayerBowShootModule`.
- Удержание Alt включает Precision Ready: `PlayerBowVisualModule` ставит лук в вертикальную precision-позу, а `PlayerCameraFovModule` сужает FOV до `PrecisionFov`.
- Долгое удержание ЛКМ не должно переводить лук в Precision Shot.
- `precision_modifier` должен быть зажат до нового нажатия ЛКМ. Если игрок уже держит ЛКМ и потом нажимает Alt, текущий charged shot не меняет тип.
- Precision projectile использует `ArrowFlightMode.Straight`, не применяет gravity и не наследует скорость игрока.
- При Precision Ready итоговый FOV выбирает только `PlayerCameraFovModule`; `PlayerSpeedFovModule` может отключать speed bonus через `DisableSpeedFovDuringPrecisionAim`.
- ПКМ остаётся свободным под будущий parry.

Новые `[Export]`-поля должны быть понятны в Inspector через названия, `ExportGroup` / `ExportSubgroup`, безопасные `Range` и suffix для единиц измерения. XML summary нужен только для неочевидных архитектурных контрактов, gameplay-правил и fallback-логики; не добавлять его над каждым очевидным полем ради формальности.
