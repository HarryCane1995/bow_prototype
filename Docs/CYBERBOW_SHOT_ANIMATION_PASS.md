# CyberBow — первый WARDOGS-inspired shot pass

2026-09-06. Viewmodel only. GOOD ENOUGH, без commit / push.

Реализована grammar из `WARDOGS_BOW_ANIMATION_RESEARCH.md` для нашего горизонтального лука. Новые модели, Blender-ассеты и gameplay-правила не добавлялись.

- **Draw:** рука отходит назад за 0,24 с; дополнительный pull 4 см, небольшая сборка корпуса −2° pitch / −1,5° yaw / +1° roll. Gameplay charge timing прежний. Draw lock входит по прежнему правилу 0,12 с, остаток gait при full draw — 2,5%.
- **Release:** отдельный триггер `ShotVisualSequence`. Стрела исчезает на shot, тетива распрямляется за 45 мс. Torque достигает пика за 55 мс и заканчивается примерно за 220 мс.
- **Torque:** компонент +6° pitch / +9° yaw / −8° roll вокруг grip, с меньшим дополнительным follow-through. Горизонтальная базовая композиция сохраняется. Мировая камера и projectile direction не участвуют в этом преобразовании.
- **Support:** кисть и корпус используют один grip transform. Предплечье продолжает движение вперёд на 3,8 см и вправо на 2,2 см; пик через 120 мс, затухание к 340 мс.
- **Drawing hand:** первые 90 мс продолжает движение после выпуска; затем уходит вниз за край, с 190 до 340 мс возвращается к рабочей области. Тайминг отличается от support arm.
- **Next arrow:** появляется на возвращающемся пути руки примерно с 230 мс, занимает рабочее положение к 340 мс. При переносе вся стрела следует руке снизу, её tip не целится сквозь grip в центр экрана.
- **Cancel:** спокойно возвращает натяг за 180 мс, без shot torque, скрытия стрелы и retrieval loop.
- **Recovery:** shot удерживает подавление locomotion, после готовности стрелы плавно отпускает его до 460 мс; gait дополнительно использует своё сглаживание. Новый допустимый draw сразу начинает вытеснять recovery за 75 мс. Ввода, cooldown и fire rate анимация не контролирует. Удержанный Alt после precision shot не считается новым draw.

Параметры доступны в Inspector: `PlayerViewModelSwayModule / MotionPrototype / ShotMotion`: draw/pull, grip pivot, torque и его времена, support continuation, задержка/траектория руки, arrow return/ready, recovery и interrupt. Предыдущие поля и legacy A сохранены.

## Короткая проверка

Два визуальных pass по кадрам Godot runtime: неподвижный full draw/shot, W, strafe, jump, cancel, precision и четыре быстрых последовательных shot. Между pass исправлены траектория возвращаемой стрелы и преждевременный interrupt от удержанного precision. Один маршрут с выстрелом на стене и после grapple launch: 46,45 с, 0 recovery. Сборка успешна, ошибок C# нет; `git diff --check` проходит.

Первый внешний pose run закончил все случаи, затем при закрытии Godot выдал native `0xC0000005` в `godotsharp_variant_destroy` / finalizer. Причина не установлена; следующий pose run и traversal завершились с exit code 0. Сохраняется прежнее предупреждение legacy aim stabilization о `ArrowTipMarker`; новый B draw lock от него не зависит. Это не exhaustive QA, финальная оценка ощущения — ручная.

Внешние drivers и кадры: `C:\Users\harry\Documents\Codex\2026-09-06\files-pasted-by-the-user-gameplay\work\cyberbow-shot-pass\`.

## Изменённые файлы

- `Scripts/Player/ViewModel/CyberBowShotMotion.cs` и `.cs.uid` — общий визуальный clock/pose generator.
- `Scripts/Player/ViewModel/FirstPersonHands.cs` — bow pivot, связанная support hand, отдельные string/hand/arrow paths.
- `Scripts/Player/ViewModel/ViewModelMotionPrototype.cs` — приоритет release над locomotion/gait.
- `Scripts/Player/Modules/PlayerBowVisualModule.cs` — передача владения видимостью декоративной стрелы procedural hands; legacy timer сохранён.
- `Scenes/Player.tscn` — нода ShotMotion.
- `Docs/CYBERBOW_SHOT_ANIMATION_PASS.md` — эта заметка.

Movement, Parkour Mode, wallrun, slide, grapple, gait module, projectile physics/speed/damage, charge time, fire rate, camera sensitivity/world FOV, geometry и model sources сохранены без изменений этого pass.
