# Bow Shooting

BowPrototype поддерживает три режима стрельбы из лука:

- `ЛКМ click` - Light Shot;
- `ЛКМ hold/release` - Charged Ballistic Shot;
- `Alt held` - Precision Ready stance;
- `Alt + ЛКМ press` - instant Precision Straight Shot.

ПКМ не используется системой стрельбы и остаётся свободным под будущий parry.

## State Machine

`PlayerBowShootModule` держит простую state machine:

- `Idle` - лук не натягивается;
- `Drawing` - ЛКМ удерживается, идёт обычное натяжение;
- `Charged` - удержание достигло `ChargeTime`;
- `Released` - выбран тип выстрела и создаётся projectile.

Precision Shot больше не входит в state machine через долгое удержание ЛКМ. Precision Ready включается удержанием `precision_modifier`, а сам выстрел срабатывает только на новое нажатие `fire`, если в этот момент Alt уже зажат.

Если игрок уже держит ЛКМ для обычного charged shot, а потом нажимает Alt, текущий выстрел не превращается в Precision Shot.

## Light Shot

Быстрый клик ЛКМ без Alt выпускает light shot.

- Скорость: `LightShotSpeed`
- Урон: `LightShotDamage`
- Projectile flight mode: `Ballistic`

Light shot использует `ProjectileGravity`, поэтому летит быстро, но довольно скоро начинает уходить в дугу.

## Charged Ballistic Shot

Если удерживать ЛКМ без Alt дольше `ChargeTime`, при отпускании выпускается обычный charged shot.

- Скорость: `ChargedShotSpeed`
- Урон: `ChargedShotDamage`
- Projectile flight mode: `Ballistic`

Charged shot летит прямее light shot за счёт высокой скорости, но gravity всё равно действует.

## Precision Straight Shot

Precision Shot активируется мгновенно:

1. Игрок зажимает Alt.
2. `PlayerBowVisualModule` плавно переводит лук в вертикальную precision-позу.
3. `PlayerCameraFovModule` плавно сужает FOV до `PrecisionFov`.
4. Игрок нажимает ЛКМ.
5. `PlayerBowShootModule` сразу создаёт precision projectile.

Precision projectile:

- Скорость: `PrecisionShotSpeed`
- Урон: `PrecisionShotDamage`
- Armor-piercing метка: `PrecisionShotArmorPiercing`
- Projectile flight mode: `Straight`

В режиме `Straight` projectile не применяет gravity и летит строго по начальному velocity. Наконечник стрелы продолжает ориентироваться по направлению полёта.

`EnablePrecisionShot` отключает только instant Alt + ЛКМ shot. Обычные light/charged выстрелы от ЛКМ остаются рабочими.

При отпускании Alt precision stance выключается: лук плавно возвращается в обычное положение, а FOV возвращается к `PlayerFov + speedFovBonus`.

## Ответственность Модулей

- `PlayerBowShootModule` отслеживает ЛКМ, `precision_modifier`, выбирает тип выстрела и создаёт projectile.
- `PlayerBowVisualModule` отвечает за Draw-анимацию, короткий visual feedback после выстрела и vertical precision stance при зажатом Alt.
- `PlayerCameraFovModule` остаётся единственным владельцем `Camera3D.Fov`: при Alt held цель становится `PrecisionFov`, без Alt цель возвращается к обычному runtime FOV.
- `ArrowProjectile` отвечает за движение projectile: ballistic или straight.
- Projectile-стрела не является частью FPS viewmodel. `Arrow_Visual` в луке остаётся только визуальной стрелой до выстрела.
