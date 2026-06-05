# Player Movement

Этот файл фиксирует текущее поведение движения игрока в BowPrototype. Документ короткий и рабочий: он нужен, чтобы не размыть модульную структуру при новых итерациях.

## Горизонтальное движение

- `PlayerMovementModule` отвечает за WASD movement.
- Направление движения считается относительно поворота игрока/камеры.
- Горизонтальная скорость разгоняется как единый `Vector3`, чтобы старт движения не уходил в сторону мировой оси.
- Обычный air control настраивается через `AirControlMultiplier`.

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
