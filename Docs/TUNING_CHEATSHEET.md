# Tuning Cheatsheet

Открыть runtime tuning: `F2`.

## Movement

Главное:

- `Move Speed` - базовая скорость.
- `Ground Acceleration` - как быстро набирается скорость.
- `Ground Deceleration` - как быстро останавливается.
- `Ground Direction Change` / `Counter Strafe Boost` - резкость смены направления.

Хочется быстрее: поднять `Move Speed`, `Ground Acceleration`.

Хочется мягче: снизить `Ground Direction Change`, `Counter Strafe Boost`.

Хочется резче: поднять `Ground Direction Change`, `Counter Strafe Boost`.

## Jump

Главное:

- `Jump Velocity` - высота/сила прыжка.
- `Double Jump Multiplier` - сила второго прыжка.
- `Double Jump Redirect Speed` - насколько сильно второй прыжок меняет направление.
- `Restore Double Jump On Grapple` - вернуть air jump после grapple.

Хочется выше: поднять `Jump Velocity`.

Хочется сильнее air control через double jump: поднять `Double Jump Redirect Speed`.

## Crouch / Slide

Главное:

- `Slide Initial Speed` - стартовая скорость slide.
- `Slide Duration` - длительность.
- `Slide Friction` - как быстро гаснет.
- `Slide Steering` - управляемость.
- `Slide Jump Boost` / `Slide Jump Carry` / `Slide Jump Max Speed` - прыжок из slide.

Хочется быстрее: поднять `Slide Initial Speed`, снизить `Slide Friction`.

Хочется контролируемее: поднять `Slide Steering`.

Хочется сильный slide jump: поднять `Slide Jump Boost` и `Slide Jump Max Speed`.

## Wall Run

Скорость:

- `Wall Run Speed`
- `Wall Run Acceleration`
- `Entry Speed Retention`
- `Exit Speed Retention`

Удержание высоты:

- снизить `Wall Gravity`
- снизить `Arc Down Force`
- поднять/настроить `Vertical Damping`
- поднять `Fall Speed Clamp`, если нужно разрешить быстрее падать

Сила wall jump:

- `Jump Away Force`
- `Jump Up Force`
- `Jump Forward Force`
- `Jump Speed Clamp`
- `Jump Cooldown` / `Same Wall Cooldown` против мгновенного reattach

Camera feel:

- `Camera Roll Angle`
- `Camera Roll Enter`
- `Camera Roll Exit`
- `Camera Pitch Offset`
- `FOV Boost`
- `FOV Lerp Speed`

Если крен слишком сильный: снизить `Camera Roll Angle`.

Если крен слишком резкий: снизить `Camera Roll Enter`.

Если игрок быстро отваливается: поднять `Max Duration`, снизить `Wall Gravity`, проверить `Require Forward Input`.

## Slingshot Grapple

Range / выбор anchor:

- `Max Grapple Distance`
- `Enable Screen Assist`
- `Screen Assist Radius`
- `Assist Max Angle`
- `Assist Line Of Sight`
- `Assist Distance Weight`
- `Assist Screen Weight`

Pull:

- `Pull Acceleration`
- `Max Pull Speed`

Launch:

- `Launch Speed`
- `Inherit Pull Velocity`
- `Max Launch Velocity`

Camera assist:

- `Enable Camera Snap`
- `Camera Snap Duration`
- `Camera Snap Strength`
- `Camera Snap Speed`
- `Lock Look During Snap`

Хочется цепляться легче: поднять `Screen Assist Radius`, `Assist Max Angle`, `Max Grapple Distance`.

Хочется быстрее подтягиваться: поднять `Pull Acceleration`, `Max Pull Speed`.

Хочется сильнее вылет: поднять `Launch Speed`, `Max Launch Velocity`.

## Bow / Projectiles

Главное:

- `Light Shot Speed`
- `Charged Shot Speed`
- `Enable Precision Shot`
- `Precision Shot Speed`
- `Precision Shot Damage`
- `Precision Armor Piercing`
- `Projectile Gravity`

Хочется прямее стрелы: поднять speed или снизить `Projectile Gravity`.

Хочется мощнее precision shot: поднять `Precision Shot Damage` и `Precision Shot Speed`.

## Camera / FOV

Base:

- `Player FOV`
- `Precision FOV`
- `FOV Transition Speed`

Speed FOV:

- `Enable Speed FOV`
- `Speed FOV Multiplier`
- `Min Speed For FOV`
- `Max Speed FOV Bonus`
- `Speed FOV Smooth Up/Down`
- `Strafe Speed FOV Multiplier`

Хочется больше ощущения скорости: поднять `Speed FOV Multiplier`, `Max Speed FOV Bonus`.

Укачивает при strafe: держать `Strafe Speed FOV Multiplier` около `0`.

## ViewModel / Sway

Главное:

- `Enable ViewModel Sway`
- `Mouse Lag Position/Rotation`
- `Movement Inertia Position/Rotation`
- `Landing Position/Rotation`
- `Sway Follow/Return Speed`

Хочется спокойнее: снизить lag/inertia/landing amounts.

Хочется живее: поднять amounts, но проверять jitter.

## ViewModel / Aim Stabilization

Главное:

- `Enable Aim Stabilization`
- `Aim Stabilization Strength`
- `Aim Stabilization Smooth Speed`
- `Max Aim Correction Degrees`
- `Aim Stabilization Dead Zone`

Если наконечник стрелы слишком гуляет: поднять strength/smooth.

Если viewmodel выкручивает странно: снизить `Max Aim Correction Degrees`.

## Debug Sections

- `Speed FOV Debug` - текущая скорость/FOV.
- `Wall Run Debug` - состояние wallrun, normal, cooldowns, last exit.
- `Frame / Physics Debug` - FPS, physics ticks, interpolation, velocity.
