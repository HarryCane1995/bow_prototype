# Player Movement

Этот файл фиксирует текущее поведение движения игрока в BowPrototype. Документ короткий и рабочий: он нужен, чтобы не размыть модульную структуру при новых итерациях.

## Горизонтальное движение

- `PlayerMovementModule` отвечает за WASD movement.
- Направление движения считается относительно поворота игрока/камеры.
- Горизонтальная скорость разгоняется как единый `Vector3`, чтобы старт движения не уходил в сторону мировой оси.
- Обычный air control теперь настраивается через `AirAcceleration`, `AirDeceleration` и `AirDirectionChangeAcceleration`; старый `AirControlMultiplier` сохранён в коде только как legacy-поле для совместимости сцен.

## Прыжок

- `PlayerJumpModule` отвечает за вертикальную скорость, gravity, coyote time, ground snap и double jump.
- Первый прыжок с земли или из coyote window использует `JumpVelocity`.
- После приземления счётчик прыжков сбрасывается.

## Double Jump

- Double jump включается через `EnableDoubleJump`.
- `MaxJumpCount = 2` означает один прыжок с земли и один дополнительный прыжок в воздухе.
- `DoubleJumpVelocityMultiplier` меняет вертикальную силу второго прыжка относительно обычного `JumpVelocity`.
- Третий прыжок невозможен, пока игрок снова не коснётся земли.

## Double Jump Redirect

- Redirect применяется только на втором прыжке.
- Если игрок держит WASD, `PlayerJumpModule` вычисляет направление относительно камеры и заменяет текущую горизонтальную скорость на `desiredDirection * DoubleJumpRedirectSpeed`.
- Redirect не добавляется поверх старой скорости, чтобы не давать лишний диагональный импульс.
- Если WASD не нажат или input слабее `DoubleJumpRedirectMinInput`, второй прыжок остаётся обычным вертикальным double jump и не меняет горизонтальную скорость.
- `EnableDoubleJumpRedirect` позволяет быстро выключить механику из Inspector.
- `DoubleJumpRedirectKeepsVerticalVelocity` оставлен как настройка на случай, если нужно сохранять более высокий текущий вертикальный импульс вместо полной замены на double jump velocity.

## Crouch

- `PlayerCrouchSlideModule` отвечает за присед, подкат, высоту коллайдера и высоту камеры.
- `crouch_slide` удерживается через Ctrl или C; модуль гарантирует наличие этих bindings в InputMap при запуске.
- При crouch камера плавно опускается к `CrouchingCameraHeight`, а capsule collider уменьшается к `CrouchingColliderHeight`.
- `PlayerMovementModule` учитывает `CurrentSpeedMultiplier`, поэтому обычное WASD movement в приседе замедляется через `CrouchSpeedMultiplier`.
- При отпускании `crouch_slide` модуль пытается вернуть игрока в standing state.

## Ceiling Check

- Перед вставанием `PlayerCrouchSlideModule` проверяет свободное место в зоне будущей головы через physics shape query.
- Если над головой есть препятствие по `StandUpBlockedMask`, игрок остаётся в crouch.
- `StandUpCheckDistance` добавляет небольшой запас над стоячим коллайдером.
- `StandUpCheckRadius` позволяет настроить радиус проверки отдельно от текущей capsule shape.

## Slide

- Slide стартует только на земле, только по нажатию `crouch_slide`, если горизонтальная скорость не ниже `SlideMinStartSpeed`.
- При старте игрок переходит в низкое состояние, как crouch.
- Если есть WASD input и `SlideKeepsInputDirection = true`, направление slide считается относительно камеры.
- Если input нет, slide использует текущую горизонтальную скорость игрока.
- Во время slide `PlayerCrouchSlideModule` управляет X/Z velocity сам, а `PlayerMovementModule` не перезаписывает горизонтальную скорость.
- Slide короткий: длится `SlideDuration`, затухает через `SlideFriction` и ограничивается `SlideCooldown`.
- `SlideSteeringStrength` даёт лёгкую коррекцию направления, но не превращает slide в обычное свободное движение.

## Jump + Slide

- Прыжок из crouch разрешён обычной логикой `PlayerJumpModule`.
- Прыжок во время slide сейчас отменяет slide и выполняет обычный jump.
- В коде оставлен TODO для будущего slide jump с отдельной настройкой импульса.
- Double Jump Redirect не изменён: после прыжка из slide второй прыжок в воздухе работает по прежним правилам.

## Movement Response

- `PlayerMovementModule` теперь отдельно настраивает разгон, торможение и резкую смену направления.
- `GroundAcceleration` отвечает за обычный разгон по земле при WASD input.
- `GroundDeceleration` отвечает за торможение по земле, когда игрок отпустил WASD.
- `GroundDirectionChangeAcceleration` включается, когда текущая горизонтальная velocity сильно отличается от нового направления input.
- `DirectionChangeDotThreshold` задаёт порог dot product для определения резкой смены направления.
- `CounterStrafeBoost` дополнительно усиливает смену направления, когда input почти противоположен текущей скорости, например D -> A или W -> S.
- `AirAcceleration`, `AirDeceleration` и `AirDirectionChangeAcceleration` делают воздух менее резким, чем землю, чтобы double jump redirect оставался отдельной выразительной механикой.
- Slide не ломается: во время `IsSliding` обычный movement не перезаписывает X/Z velocity, а `PlayerCrouchSlideModule` продолжает управлять подкатом сам.
- Crouch не ломается: target speed умножается на `PlayerCrouchSlideModule.CurrentSpeedMultiplier`.
