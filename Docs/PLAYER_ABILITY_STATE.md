# Player Ability State

`PlayerAbilityStateModule` - первый слой arbitration для player ability / motor authority. Он нужен, чтобы новые механики не ломали друг друга прямыми проверками вроде "если сейчас grapple, то выключи всё остальное" в каждом модуле.

Модуль работает как расписание и приоритеты задач: он решает, какая способность сейчас держит право на канал управления, но сам не выполняет работу. Slide остаётся в `PlayerCrouchSlideModule`, slingshot grapple остаётся в `PlayerSlingshotGrappleModule`, jump остаётся в `PlayerJumpModule`, shooting остаётся в `PlayerBowShootModule`.

## Зачем Это Нужно

Проект уже содержит slide, slide jump, double jump, slingshot grapple, precision stance и shooting. Дальше появятся wall run, parry, knockback, death state и, возможно, dash/air tricks. Без общего арбитража каждая новая механика начнёт знать слишком много о соседях.

`PlayerAbilityStateModule` даёт общий контракт:

- механика регистрирует активный request через `BeginAbility`;
- механика снимает request через `EndAbility`;
- другие модули спрашивают `CanStart`, `CanWrite` или `IsLocked`;
- приоритеты и locks остаются данными арбитража, а не gameplay-логикой.

## PlayerAbilityTag

- `None`
- `DefaultMovement`
- `Crouch`
- `Slide`
- `SlingshotGrapplePull`
- `SlingshotGrappleLaunch`
- `WallRun`
- `Parry`
- `PrecisionStance`
- `Knockback`
- `Death`

`WallRun`, `Parry`, `Knockback` и `Death` сейчас зарезервированы для будущих механик.

## PlayerAbilityLock

- `MovementInput`: обычное WASD-управление не должно применяться.
- `HorizontalVelocity`: обычный movement не должен перетирать X/Z velocity.
- `VerticalVelocity`: обычная вертикальная логика не должна перетирать Y velocity.
- `Jump`: обычный jump временно запрещён.
- `DoubleJump`: double jump временно запрещён.
- `Slide`: нельзя стартовать slide.
- `Grapple`: нельзя стартовать grapple.
- `Shooting`: нельзя стрелять.
- `LookInput`: нельзя или временно нельзя принимать mouse input.
- `FovControl`: модуль временно владеет FOV.

## Priorities

| Ability | Priority |
|---|---:|
| `DefaultMovement` | 0 |
| `Crouch` | 10 |
| `Slide` | 30 |
| `WallRun` | 40 |
| `SlingshotGrapplePull` | 60 |
| `SlingshotGrappleLaunch` | 65 |
| `Parry` | 70 |
| `Knockback` | 90 |
| `Death` | 100 |

## Current Integration

`Slide` регистрируется при реальном старте slide и держит `HorizontalVelocity`. Поэтому `PlayerMovementModule` не перезаписывает X/Z velocity, пока slide сам управляет скольжением.

`SlingshotGrapplePull` регистрируется при успешном старте grapple и держит `MovementInput`, `HorizontalVelocity`, `VerticalVelocity` и `Slide`. Это формализует старое правило: grapple pull перебивает обычное движение и slide.

`SlingshotGrappleLaunch` регистрируется на фазе launch с теми же locks и остаётся активным до конца `PostLaunchControlDelay`. Это защищает вылет от немедленного перетирания обычным horizontal movement.

`PlayerJumpModule` сейчас проверяет `Jump` перед обычным jump и `DoubleJump` перед air jump. Текущие механики эти locks не держат, поэтому slide jump и double jump после grapple продолжают работать по старым правилам.

`PlayerBowShootModule` проверяет `Shooting` перед выстрелом. Сейчас ни одна механика не блокирует shooting; это подготовка к будущим `Parry` и `Death`.

## Examples

Slide управляет `HorizontalVelocity`, но не блокирует shooting или look input.

SlingshotGrapplePull перебивает обычное движение и slide, потому что его приоритет выше и он держит velocity/slide locks.

Будущий WallRun сможет перебивать обычное движение через `HorizontalVelocity`, но не обязан блокировать `Shooting`.

Будущий Parry сможет на короткое окно держать `Shooting`, не блокируя movement.

Будущий Death сможет зарегистрировать priority `100` и держать все нужные locks: movement, velocity, jump, shooting, look input и FOV.

## Debug

`GetDebugState()` возвращает read-only строку с highest active ability, aggregate locks и активными requests. Runtime tuning panel пока не редактирует приоритеты; если нужен UI, его лучше добавлять как debug display, а не как gameplay tuning.
