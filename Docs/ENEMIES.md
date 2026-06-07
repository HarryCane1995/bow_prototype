# Enemies

Этот документ описывает временную primitive AI систему для BowPrototype. Цель простая: дать игроку движущиеся боевые цели для проверки стрельбы, mobility, slide, grapple и double jump.

## BasicPatrolShooterEnemy

- `BasicPatrolShooterEnemy` живёт в `Scenes/Enemies/BasicPatrolShooterEnemy.tscn`.
- Root сцены - `CharacterBody3D` примерно размера игрока.
- Враг сам хранит patrol state, shoot timer, ссылку на игрока, здоровье и смерть.
- Враг добавлен в группу `enemy`.
- Враг стоит на physics layer 3 (`collision_layer = 4`), а стрелы игрока смотрят в mask `1 + 4`, чтобы попадать и по миру/мишеням, и по врагам.
- Навигации, pathfinding, NavMesh, анимаций, ragdoll и UI здоровья нет.

## Patrol

- На старте враг сохраняет стартовую позицию.
- `PatrolAxis` задаёт одну ось движения.
- Враг ходит между `startPosition - PatrolAxis * PatrolDistance` и `startPosition + PatrolAxis * PatrolDistance`.
- На краю маршрута направление меняется.
- `WaitAtPatrolEnds` и `WaitTimeAtEnds` могут добавить короткую паузу на краях.

## Shooting

- Враг стреляет каждые `ShootInterval` секунд, если `CanShoot = true`.
- Цель берётся как `player.GlobalPosition + AimAtPlayerCenterOffset`.
- Предикта нет: projectile летит в текущую позицию игрока на момент выстрела.
- `RotateToFacePlayer` поворачивает врага к игроку по горизонтали.
- `EnemyProjectileScene` задаёт сцену projectile.

## EnemyProjectile

- `EnemyProjectile` живёт в `Scenes/Enemies/EnemyProjectile.tscn`.
- Root сцены - `Area3D` с маленькой sphere collision/debug mesh.
- Projectile летит прямо через ручное движение `GlobalPosition += velocity * delta`.
- `RigidBody3D` не используется.
- По истечении `Lifetime` projectile удаляется.
- Projectile добавлен в группу `enemy_projectile`.
- Enemy projectile смотрит в physics mask 1, поэтому видит игрока и мир, но не врагов на enemy layer.

## Player Hit

- Player root должен быть в группе `player`.
- Если `EnemyProjectile` попадает в объект группы `player` или объект с `PlayerController`, текущая сцена перезагружается через `GetTree().ReloadCurrentScene()`.
- Это временная death-модель для быстрого combat prototyping без health UI.

## Player Arrow Damage

- Для урона добавлен простой интерфейс `IDamageable`.
- `BasicPatrolShooterEnemy` реализует `IDamageable`.
- `ArrowProjectile` при попадании сначала ищет `IDamageable` вверх по иерархии hit node.
- Если damageable найден, стрела вызывает `ApplyDamage`.
- Если damageable не найден, старая логика `TargetHitbox` продолжает работать для тренировочных мишеней.
- При `Health <= 0` враг удаляется через `QueueFree`, если `DestroyOnDeath = true`.

## Architecture Notes

- Player не знает, как враги патрулируют или стреляют.
- Enemy owns its own AI and shooting behavior.
- EnemyProjectile owns its own hit behavior.
- Эта система намеренно примитивная и должна оставаться маленькой, пока не появится отдельная задача на полноценный AI.
