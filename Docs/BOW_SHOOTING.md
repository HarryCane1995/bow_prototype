# Bow Shooting

BowPrototype сейчас поддерживает три режима стрельбы через удержание ЛКМ.

## State Machine

`PlayerBowShootModule` держит простую state machine:

- `Idle` - лук не натягивается.
- `Drawing` - ЛКМ удерживается, идёт обычное натяжение.
- `Charged` - удержание достигло `ChargeTime`.
- `PrecisionAiming` - удержание достигло `PrecisionChargeTime`.
- `Released` - ЛКМ отпущена, выбран тип выстрела и создаётся projectile.

Если игрок отпускает mouse capture через `Esc` во время удержания, draw/precision состояние сбрасывается, FOV возвращается к обычному.

## Light Shot

Быстрый клик ЛКМ выпускает light shot.

- Скорость: `LightShotSpeed`
- Урон: `LightShotDamage`
- Projectile flight mode: `Ballistic`

Light shot использует `ProjectileGravity`, поэтому летит быстро, но заметно уходит в дугу.

## Charged Ballistic Shot

Если удерживать ЛКМ дольше `ChargeTime`, но отпустить до `PrecisionChargeTime`, выпускается обычный charged shot.

- Скорость: `ChargedShotSpeed`
- Урон: `ChargedShotDamage`
- Projectile flight mode: `Ballistic`

Charged shot летит прямее light shot за счёт высокой скорости, но gravity всё равно действует.

## Precision Straight Shot

Если удерживать ЛКМ до `PrecisionChargeTime`, включается precision aiming.

В precision aiming:

- лук плавно поворачивается через `PlayerBowVisualModule`;
- основная камера плавно сужает FOV через `PlayerCameraFovModule`;
- после выстрела или отмены FOV возвращается к `PlayerCameraFovModule.PlayerFov`;
- при отпускании ЛКМ создаётся precision projectile.

Precision projectile:

- Скорость: `PrecisionShotSpeed`
- Урон: `PrecisionShotDamage`
- Armor-piercing метка: `PrecisionShotArmorPiercing`
- Projectile flight mode: `Straight`

В режиме `Straight` projectile не применяет gravity и летит строго по начальному velocity.

## Ответственность модулей

- `PlayerBowShootModule` отслеживает удержание ЛКМ, выбирает тип выстрела и создаёт projectile.
- `PlayerBowVisualModule` отвечает за Draw-анимацию, временное скрытие viewmodel-стрелы и precision-поворот лука.
- `PlayerCameraFovModule` отвечает только за плавный FOV переход при precision aiming.
- Базовый FOV игрока настраивается в Inspector через `PlayerFov`.
- `ArrowProjectile` отвечает за движение projectile: ballistic или straight.

Projectile-стрела не является частью FPS viewmodel. `Arrow_Visual` в луке остаётся только визуальной стрелой до выстрела.
