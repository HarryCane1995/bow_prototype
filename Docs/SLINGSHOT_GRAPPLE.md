# Slingshot Grapple

`Slingshot Grapple` - это механика рогатки для игрока, а не классический grappling hook. Игрок не просто подтягивается к точке и останавливается: он запоминает стартовую позицию, быстро летит к специальной точке зацепа, а затем выстреливает дальше по направлению от стартовой позиции через эту точку.

## Главное правило

Направление вылета считается в момент старта grapple:

```csharp
launchDirection = (grapplePointPosition - initialPlayerPosition).Normalized();
```

Камера нужна только для выбора `GrappleAnchor`. После зацепа траектория задаётся геометрией: где игрок был относительно точки, туда через точку он и вылетает.

## Выбор точки

`PlayerSlingshotGrappleModule` при нажатии `slingshot_grapple` делает raycast из основной камеры на `MaxGrappleDistance`. Зацеп разрешён только по специальным объектам:

- `GrappleAnchor`;
- или любой `Node3D` в группе `grapple_anchor`.

Если прямой raycast не попал, модуль может найти ближайший anchor в небольшом конусе перед камерой. Это сделано для удобства прототипирования, но всё равно работает только со специальными anchor-точками, не с произвольной геометрией.

## Pulling

При старте Pulling модуль сохраняет:

- `initialPlayerPosition = player.GlobalPosition`;
- `grapplePointPosition = anchor.GlobalPosition`;
- `storedLaunchDirection = (grapplePointPosition - initialPlayerPosition).Normalized()`.

Во время Pulling модуль каждый physics tick ускоряет `Velocity` игрока к anchor-точке:

```csharp
velocity += pullDirection * PullAcceleration * delta;
```

Скорость ограничивается `MaxPullSpeed`. Pulling завершается, когда игрок находится ближе `GrappleArriveDistance` или перелетел anchor-точку при включённом `StopPullWhenPassedAnchor`.

## Launch

Launch использует сохранённое направление, а не текущий взгляд камеры. Наследование скорости берётся только вдоль направления вылета, чтобы случайная боковая скорость не ломала рогатку:

```csharp
float inheritedAlongDirection = currentVelocity.Dot(storedLaunchDirection);
Vector3 inheritedDirectionalVelocity = storedLaunchDirection * Mathf.Max(0f, inheritedAlongDirection) * InheritPullVelocityFactor;
Vector3 launchVelocity = storedLaunchDirection * LaunchSpeed + inheritedDirectionalVelocity;
```

Итоговая скорость ограничивается `MinLaunchVelocity` и `MaxLaunchVelocity`, затем применяется к `player.Velocity`.

## Grapple -> Air Jump Reset

При успешном старте grapple, когда anchor уже найден и модуль переходит в `Pulling`, `PlayerSlingshotGrappleModule` просит `PlayerJumpModule` восстановить один air jump charge.

Это не ground reset:

- grounded-состояние не меняется;
- coyote time не включается и не сбрасывается;
- jump impulse не применяется в момент зацепа;
- следующий прыжок в воздухе считается second jump / air jump.

Если игрок уже потратил double jump до grapple, после slingshot launch он снова может сделать один air jump. Если double jump ещё не был потрачен, grapple не выдаёт два air jump подряд: доступен максимум один воздушный прыжок до следующего приземления или нового успешного grapple.

## Inspector

Основные группы настроек:

- `Grapple Detection`: включение механики, дистанция, группа anchor, physics mask, line of sight и fallback cone.
- `Pull`: ускорение притяжения, максимум скорости, дистанция прибытия и проверка пролёта через точку.
- `Launch`: скорость рогатки, множитель силы, наследование pull velocity и лимиты итоговой скорости.
- `Control`: блокировка обычного movement/slide во время Pulling, задержка возврата air control и cooldown.
- `Debug`: debug-линии и печать переходов состояния в Godot Output.

## Связь с movement/jump/slide

`PlayerController` вызывает `PlayerSlingshotGrappleModule` в physics-пайплайне рядом с другими модулями. Во время Pulling модуль полностью управляет `Velocity`, поэтому:

- `PlayerJumpModule` временно не применяет прыжок/гравитацию;
- `PlayerCrouchSlideModule` отменяет текущий slide и не запускает новый;
- `PlayerMovementModule` не перезаписывает горизонтальную velocity.

После Launch обычная гравитация снова работает сразу, но horizontal movement получает короткую задержку `PostLaunchControlDelay`, чтобы air control не погасил вылет в тот же кадр. После задержки игрок возвращается к обычному управлению, double jump и air control продолжают жить в своих модулях.

## GrappleAnchor

`GrappleAnchor` - это `Area3D`, который добавляет себя в группу `grapple_anchor`. В прототипной сцене используется `Scenes/GrappleAnchor.tscn`: у неё есть sphere collision для raycast и маленькая светящаяся debug-сфера.
