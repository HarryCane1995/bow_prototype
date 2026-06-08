# Runtime Tuning

Runtime tuning нужен, чтобы во время Play менять основные параметры игрока и оружия без перезапуска сцены. Это удобно для настройки движения, прыжков, slide, slingshot grapple, скоростей лука, projectile gravity и FOV.

## PlayerTuningProfile

`PlayerTuningProfile` - это data-only `Resource` с числами и флагами настройки. Он не содержит gameplay logic и не решает, как игрок движется, стреляет или цепляется за anchor.

Default-профиль лежит здесь:

`res://Resources/Tuning/DefaultPlayerTuningProfile.tres`

`PlayerController` хранит ссылку на профиль через `TuningProfile` и флаг `UseTuningProfile`. Модули читают только свою часть профиля:

- `PlayerMovementModule` - movement-настройки;
- `PlayerJumpModule` - jump и double jump;
- `PlayerCrouchSlideModule` - crouch/slide;
- `PlayerSlingshotGrappleModule` - slingshot grapple;
- `PlayerBowShootModule` - скорости выстрелов и projectile gravity;
- `PlayerCameraFovModule` - базовый FOV, precision FOV и скорость перехода;
- `PlayerSpeedFovModule` - speed-based FOV bonus;
- `PlayerViewModelSwayModule` - procedural sway/inertia viewmodel.

Если профиль не назначен или `UseTuningProfile` выключен, модули используют свои локальные `[Export]`-поля как fallback.

## Runtime Tuning Panel

Панель находится в:

`res://Scenes/Debug/RuntimeTuningPanel.tscn`

В основной сцене `BowPrototypeScene` она добавлена как `Window`, поэтому её можно открыть, перетащить на второй монитор и продолжать играть в главном окне.

Клавиша:

- `F2` - показать или скрыть tuning panel.

Панель содержит группы:

- `Movement`;
- `Jump`;
- `Crouch / Slide`;
- `Slingshot Grapple`;
- `Bow / Projectiles`;
- `Camera`.
- `Camera / Speed FOV`.
- `ViewModel / Sway`.

`Crouch / Slide` содержит базовые параметры crouch/slide, выход из slide по скорости, airborne slide buffer и slide jump. Основные ручки: `SlideExitMinSpeed`, `AirborneSlideMinSpeed`, `AirborneSlideBufferTime`, `SlideJumpHorizontalBoost`, `SlideJumpVelocityCarryFactor` и `SlideJumpMaxHorizontalSpeed`.

`Jump` содержит обычную силу прыжка, double jump, redirect и флаг `RestoreDoubleJumpOnGrapple`, который включает восстановление одного air jump charge после успешного Slingshot Grapple.

`Slingshot Grapple` содержит базовые параметры дистанции, pull/launch, а также aim assist и camera assist. `GrappleScreenAssistRadiusPixels` отвечает за экранный радиус вокруг прицела, `GrappleAssistMaxAngleDegrees` ограничивает сектор перед камерой, веса `GrappleAssistDistanceWeight` и `GrappleAssistScreenDistanceWeight` выбирают лучший anchor. `EnableGrappleCameraSnap`, `GrappleCameraSnapDuration`, `GrappleCameraSnapStrength`, `GrappleCameraSnapSpeed` и `LockLookInputDuringGrappleSnap` настраивают короткую доводку камеры после успешного зацепа. `EnableGrappleAvailableHighlight` включает жёлтую debug-сферу только на anchor, который прямо сейчас доступен для grapple.

`Camera / Speed FOV` содержит главный ползунок силы эффекта `SpeedFovMultiplier`, порог `MinSpeedForFov`, ограничитель `MaxSpeedFovBonus`, smoothing для расширения/возврата и флаги `UseFullVelocityForSpeedFov` и `DisableSpeedFovDuringPrecisionAim`.

Для уменьшения укачивания от A/D там же есть осевые настройки speed FOV: `UseAxisBasedSpeedFov`, `StrafeSpeedFovMultiplier`, `MinStrafeSpeedForFov` и `IncludeBackwardSpeedInForwardFov`. При `StrafeSpeedFovMultiplier = 0` боковой strafe полностью перестаёт расширять FOV, а forward/back движение продолжает использовать `SpeedFovMultiplier`.

`ViewModel / Sway` содержит mouse lag, movement inertia, landing impulse и скорости сглаживания. Эти параметры меняют только визуальный `ViewModelSwayRoot` и не влияют на crosshair, gameplay camera или projectile direction.

`Bow / Projectiles` содержит скорости light/charged/precision shot, `EnablePrecisionShot`, `PrecisionShotDamage`, `PrecisionShotArmorPiercing` и `ProjectileGravity`. Precision Ready включается удержанием Alt, а Precision Shot является мгновенным `Alt + ЛКМ press`; `PrecisionChargeTime` больше не участвует в активной логике и не должен появляться в runtime tuning UI.

Изменение slider/spinbox сразу меняет значения в `PlayerTuningProfile`. Модули читают профиль во время расчёта поведения, поэтому изменения применяются live.

## Save / Load

Кнопки панели:

- `Reset To Defaults` - возвращает значения из `DefaultPlayerTuningProfile.tres`.
- `Save Runtime Values` - сохраняет текущие значения в `user://player_tuning_runtime.json`.
- `Save As Project Defaults` - явно записывает текущие значения в `res://Resources/Tuning/DefaultPlayerTuningProfile.tres`.
- `Load Saved Values` - загружает значения из `user://player_tuning_runtime.json`.

Панель не перезаписывает `DefaultPlayerTuningProfile.tres` автоматически. Project defaults меняются только при ручном нажатии `Save As Project Defaults`, а runtime-save живёт отдельно в `user://`.

## Архитектурная граница

Централизация разрешена только для данных настройки. `PlayerTuningProfile` не должен превращаться в god-object, не должен знать про состояние сцены и не должен вызывать gameplay-методы.

Правильная зависимость:

- профиль хранит данные;
- модуль читает свои данные;
- модуль сам реализует поведение.

Неправильно:

- профиль запускает прыжок;
- профиль открывает двери;
- profile/panel управляет combat logic;
- `PlayerController` начинает содержать всю механику только ради tuning.
