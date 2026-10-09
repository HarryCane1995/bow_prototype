# MouseLook — почти полный вертикальный обзор

2026-09-07. Точечный pass, без commit / push.

Причина ограничения: `PlayerLookModule.MinPitch = -80`, `MaxPitch = 80`. Ни shared Player, ни другие сцены не переопределяли эти значения. Inspector также ограничивал доступный диапазон ±89°. Фактическая sensitivity в `Scenes/Player.tscn` — `0.0017`; она сохранена.

Изменены defaults и Inspector ranges на **−89,9° … +89,9°**. Это оставляет 0,1° до полюса: существующий `ArrowProjectile.AlignWithVelocity` вызывает `LookAt(..., Vector3.Up)`, поэтому точная вертикаль нежелательна без отдельной правки projectile presentation. Алгоритм input, sensitivity и сглаживание не менялись.

Фактическая иерархия:

`Player (yaw) → CameraPivot (local X pitch, Y/Z = 0) → CameraEffectsPivot → Camera3D → ShootPoint`.

Movement использует basis тела. Canonical wallrun B также сохраняет body/input tangent. Wallrun effects пишут локальный roll отдельного effects pivot: текущий профиль задаёт 19,5°; дополнительный pitch offset наследует −1,5°. Эти небольшие additive effects остаются поверх пользовательского pitch, поэтому суммарный угол камеры на wallrun может чуть пересекать вертикаль, но композиция basis непрерывна; скачка или смены знака roll в проверке не было. Механику и camera effects не меняли.

Grapple ray и bow shot берут `-Camera.GlobalTransform.Basis.Z.Normalized()`. Precision использует тот же camera forward. Grapple camera assist отдельно ограничен прежними 89°: при срабатывании тестового вертикального anchor он немного довёл 89,9° до ~89,25°. Это существующая краткая доводка, не новый предел свободного MouseLook; её tuning сохранён.

Viewmodel находится в отдельном SubViewport: камера и руки/лук живут в общей экранной системе координат с FOV 65°. Они не извлекают world Euler pitch и сохраняют композицию при взгляде вверх/вниз. Новых визуальных переворотов или clipping на просмотренных runtime-кадрах не обнаружено.

Короткая проверка через внешний Godot InputEvent driver: idle вверх/вниз; по одному полному 360° yaw на обоих пределах; movement/jump с Parkour Mode; wallrun при обоих крайних pitch; grapple почти вертикально вверх; charged и precision shots вверх/вниз. Пределы в runtime — ±89,9°, yaw шёл равномерно без reversal, camera basis оставался конечным с determinant ≈ 1. Оба wallrun состоялись; roll сохранял знак. Начальная ось всех четырёх projectile совпала с camera forward. Для grapple внешний driver разместил экземпляр существующего anchor над игроком; production geometry не менялась.

`dotnet build --no-restore`: 0 errors / 0 warnings. В runtime нет новых errors; сохранено прежнее предупреждение legacy viewmodel aim stabilization о `ArrowTipMarker`. GOOD ENOUGH, без полного regression audit.

Изменённые файлы:

- `Scripts/Player/Modules/PlayerLookModule.cs` — два defaults, два Inspector ranges и комментарий о полюсе.
- `Docs/MOUSELOOK_VERTICAL_RANGE_PASS.md` — эта заметка.

Внешние driver, JSONL и кадры: `C:\Users\harry\Documents\Codex\2026-09-07\bow-mouselook-pass\`. Для ручной проверки Gym запускается fullscreen обычной сценой, с реальным вводом и выбранным B.
