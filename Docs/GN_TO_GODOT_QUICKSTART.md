# V06 → Godot: ручной snapshot

## Следующая итерация

1. В Blender открыть `Assets/Levels/Level_Freestyle_01/Source/Level_Freestyle_01.blend`, изменить Proxy / Seed обычным способом. Завершить операцию и выйти в Object Mode. Debug Placement Volumes должен быть выключен.
2. В Text Editor один раз открыть `Tools/Blender/GodotSnapshot/export_current.py`. Запустить **Run Script / Alt+P**. Скрипт сохраняет текущий `.blend` и перезаписывает два файла Current, без накопления архивов. Сам Proxy, модификаторы и граф не изменяются.
3. Вернуться в Godot, дождаться автоматического reimport. Открыть `Scenes/Levels/Level_Freestyle_01.tscn`, нажать **F6**. F5 по-прежнему запускает основной Level_01 проекта; main scene не переназначен.

Выходы: `Assets/Levels/Level_Freestyle_01/Generated/GN_Blockout_Current.glb` и одноимённый `.json`.

## Человеческая сессия

- **F3** — показать/скрыть coverage-маркеры. Посещённые скрываются. Обычные cyan grapple anchors сохраняют собственную каноническую подсветку.
- **Shift+F3** — сохранить предыдущий журнал и начать coverage заново.
- **F1** — штатный reset сцены/Player; накопленная coverage сохраняется в текущем процессе. Падение ниже нижней границы снимка на 35 м вызывает тот же reset.
- **Esc** — отпустить мышь; ЛКМ — вернуть захват. Все movement-клавиши Player сохраняются, **E** — штатный grapple.
- Учёт стартует с первого движения/jump/grapple ввода человека. Простое ожидание на spawn ничего не засчитывает. Новое открытие игры начинает новую сессию с нуля.
- Запись раз в секунду: `.godot/traversal-coverage/latest.json`. При закрытии окна, выходе/перезагрузке сцены — timestamped файл той же сессии; F1 продолжает эту же сессию и при следующем выходе обновляет её архив. Shift+F3 начинает новый ID. Принудительное завершение процесса может оставить только последний `latest.json`.

Закончить игру обычным закрытием окна и отдельно сообщить, что тест закончен. До этого никакого анализа непосещённых точек не выполняется. Подготовленный `Tools/Levels/GNSnapshot/unreached.py --human-test-finished` создаёт отчёт только по отдельному ручному запуску.

## Что проверяется

`LANDING`: Player действительно IsOnFloor, ноги рядом по высоте, в радиусе 2.5 м и луч под ногами попадает в коллизию снимка. Опора для размещения точки проверена на финальной геометрии Blender в радиусе 0.6 м.

`PASS_THROUGH`: ноги физически в радиусе 2.5 м от точки; пролёт рядом также считается посещением области.

`WALLRUN`: канонический wallrun активен, центр капсулы в радиусе 2.2 м, нормаль текущей стены совпадает с целевой. Это локальный маркер использования, не измерение всей длины стены; отдельные тела для каждой стены не создаются.

`GRAPPLE`: активный канонический Pulling/Launching направлен на координату данного anchor. Подсветка доступности, прицеливание или близость не засчитываются. Два новых read-only свойства partial-классов только открывают существующие point/normal для наблюдателя; состояние и механика не изменяются.

Arena и Vertical — дополнительные теги к основным типам, их счётчики пересекаются с LANDING/WALLRUN. Цель — посещение representative targets человеком, а не доказательство полной проходимости или пригодности всех поверхностей.

## Текущий снимок и проверка

Seed 17, Proxy 162 вершины / 159 граней, 1 106 треугольников. 141 цель: 60 LANDING, 50 PASS_THROUGH, 11 WALLRUN, 20 GRAPPLE. Дополнительные теги: 10 VERTICAL и 20 ARENA. Все 20 anchors — реальные экземпляры `Scenes/GrappleAnchor.tscn`; в данном снимке все optional, GRAPPLE_REQUIRED отсутствует. Только геометрия `LEVEL_GENERATED_OUTPUT` входит в GLB.

Ветка `GN_Blockout_Current` содержит Visual / Collision / GrappleAnchors / CoverageDebug. Статическая `ConcavePolygonShape3D` строится из всех импортированных visual triangles на layer/mask 1. Старые SourceGeometry и DEV kit исключены из этой сцены, чтобы их коллизии не накладывались; их ассеты и старые отдельные сцены сохранены.

Исходный spawn `(0, 0.05, 0)` находился вне геометрии. По отдельному разрешению пользователя он перенесён на нижнюю дорожку `(140, 0.05, 5.40)`; геометрия не сдвигалась. Будущий экспорт только проверяет текущий marker и записывает опору под ним, ничего не перемещая.

Проверка: сборка C# без ошибок/предупреждений; headless Godot импорт; совпадение world bounds и числа треугольников; grounded spawn; 121/121 raycast к поверхностным целям; 20 canonical anchors; один canonical Player, V4 presentation. Human traversal не выполнялся. Есть предупреждение существующего legacy `PlayerViewModelSwayModule` об отсутствующем ArrowTipMarker/ViewModelCamera3D; оно не менялось этим pass, V4 загружается.

Автоматическая проверка (не играет и не пишет human session):

```powershell
godot --headless --editor --path . --import --quit --log-file .godot/gn-snapshot-import.log
godot --headless --path . --log-file .godot/gn-snapshot-check.log --script Tools/Levels/GNSnapshot/verify.gd -- --coverage-check
```

Результат — `Docs/Reviews/GNSnapshot/verification.json`. Collision не оптимизирована. Свободной камеры в исходной Freestyle не было; сохранены стандартные presentation/debug клавиши Player, новая freecam не добавлялась.
