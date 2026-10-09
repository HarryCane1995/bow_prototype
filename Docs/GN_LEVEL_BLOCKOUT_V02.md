# Geometry Nodes V02 — объёмный blockout и Godot preview

**Текущее состояние после следующей правки:** [V02_GAMEPLAY_SPACE_CORRECTION.md](V02_GAMEPLAY_SPACE_CORRECTION.md). Автоматические опоры и доступ на каждый этаж убраны, стены изолированы, плиты смещены. Ниже сохранён отчёт первого V02 до этой корректировки; его прежние числа и изображения относятся к историческому snapshot. Актуальный Blender и Godot export используют исправленную grammar.

20 сентября 2026. Source: `Assets/Levels/Level_Freestyle_01/Source/Level_Freestyle_01.blend`.
Выбран **Seed 17**, Volume **220 × 176 × 50 m**, Verticality **0.84**.
Последующее явное разрешение пользователя расширило Blender-only задачу: текущий результат импортирован в отдельную игровую сцену с коллизиями.

## Blender: модель и управление

1. **Архитектура.** `GN_LevelBlockout_Generator_v02` читает обычные ручные `LEVEL_VOLUME` и `LEVEL_CUTTER` через Object Info и формирует один `LEVEL_GENERATED_OUTPUT`. Обновление делает native Geometry Nodes, без Python handlers, Apply или Bake. Python нужен только для первоначального построения, QA и экспорта снимка.
2. **Границы.** Используется реальный evaluated AABB Volume по XYZ; исходный диапазон X ±110, Y ±88, Z −8…42 m. Object scale и Edit Mode изменения влияют на результат. Это осевой прямоугольный domain: произвольная вогнутая форма и поворот не означают точное clipping по её поверхности.
3. **Макроструктура.** Seed задаёт ориентацию и неравные разбиения объёма на 4–6 крупных зон, объединения соседних областей и связи. Фиксированной сетки 44 m нет. Геометрия ортогональная, с повторяющейся строительной грамматикой.
4. **Вертикальные уровни.** Над нижними площадками повторяются широкие плиты с согласованным шагом высоты около 6–7 m. Verticality меняет число занятых уровней и глубину части нижних площадок. Максимум шесть основных верхних bands; увеличение высоты не обязано линейно заполнять весь объём этажами.
5. **Стены.** Длинные наружные несущие стены, перпендикулярные сегменты, опоры свободных краёв и парные стены дают пространственную структуру и surfaces для текущих wall mechanics.
6. **Площадки и связи.** Широкие этажные плиты, внешние чередующиеся рампы шириной 4.8 m, поворотные площадки 6 × 13 m, часть нижних лестничных пролётов, межзональные мосты и отдельные высокие площадки. Seed меняет выбранные высоты и связи.
7. **Пустоты.** Сквозные шахты прорезают основные плиты; нижние recovery floors находятся около нижней границы. Cutter может удалять пол и оставлять падение. Автоматического ремонта разрывов нет.
8. **Movement metrics.** Использован текущий `Reviews/LevelFreestyle01/metrics_snapshot.json`, совпали SHA-256 всех десяти входных файлов. Running jump 12.505 m, air chain 23.035 m / +5.603 m, slide jump 14.741 m, wallrun trajectory 44.320 m, wall-jump rise 10.507 m / lateral transfer 9.530 m, acquisition grapple 50 m от камеры в 3D. Это измеренные случаи, не гарантированные максимумы. Traversal Difficulty использует запас; подход, LOS и полная проходимость маршрутов автоматически не решаются.
9. **Spawn.** Пол на Z=0 у origin добавляется после Cutter; вертикальная колонна очищается от геометрии. Радиус по умолчанию 8 m. Volume должен содержать эту область и пол Z=0. При изменении высоты удобнее двигать верхнюю грань; Edit Mode масштабирование всех вершин относительно медианы может поднять нижнюю границу выше spawn.
10. **Cutter.** Один обычный закрытый mesh, в том числе несколько несвязанных закрытых islands. Boolean действует в 3D на стены, плиты, мосты и пол. Пустой mesh явно обходит Boolean. Открытые, самопересекающиеся поверхности не входят в проверенный контракт Manifold.
11. **Открытый верх.** Пересечение с bounds обрезает существующие solids, общей верхней плиты не создаёт. Локальные этажи и высокие landing platforms остаются. Над spawn проверен свободный проход до неба.

Основные controls: Seed, Density, Verticality, Openness, Route Complexity, Traversal Difficulty, Grapple Presence, Spawn Safe Radius, Use Cutter, Preview Quality. Debug Spatial Roles показывает только floor / wall / platform / connection / grapple / void edge. Height Range удалён. Preview Quality 0 — Manifold; 1 — более дорогой Exact для последнего Cutter Boolean.

## Проверки и три Seed

12. **Сравнение.** Одинаковый внешний ракурс; числа ниже относятся к контрольному output без пользовательского Cutter.

| Seed | Вершины / грани | Основные верхние отметки Z, m | Вид |
|---|---:|---|---|
| 17 | 2823 / 2000 | 6.36, 12.72, 19.08, 25.44, 31.80 | [seed_17](Reviews/GNLevelBlockoutV02/seed_17.png) |
| 41 | 1369 / 949 | 6.65, 13.29, 19.94, 26.59 | [seed_41](Reviews/GNLevelBlockoutV02/seed_41.png) |
| 109 | 2968 / 2048 | 7.10, 14.20, 21.29, 28.39 | [seed_109](Reviews/GNLevelBlockoutV02/seed_109.png) |

13. **Техническая QA.** [technical_qa.json](Reviews/GNLevelBlockoutV02/technical_qa.json): 32/32 PASS на disposable copies. Проверены детерминизм, XYZ bounds, отсутствие общей крышки, 13 spawn rays, реальные размеры репрезентативных элементов, Volume XYZ и object scale, Verticality, difficulty, Cutter toggle / scale / extrusion / несколько islands / перекрытие spawn / пустой mesh, depsgraph и сохранность ручных meshes. Preview для трёх обновлений Seed: 26.4–47.0 ms, среднее 36.0 ms; это не измерение игрового FPS.

14. **UX и ограничения.** Реальным UI подтверждены Volume Edit Mode S Z 2 → live output, Seed 17 → 18 и Verticality 0.83 → 0.25 (output уменьшился с 1714/1215 до 1092/748 vertices/faces). Последний CU тест Cutter был остановлен Esc; повторное подключение вернуло тот же stop-сигнал. Поэтому V02 Cutter UI smoke test не считается завершённым. API-проверки Cutter прошли. [ux_states.json](Reviews/GNLevelBlockoutV02/ux_states.json) содержит исходные наблюдения; запись `ui_cutter_edit_scale2` относится к отменённой операции, output в ней не изменился.

Это blockout, а не solver полной проходимости. Не гарантированы все wall-jump chains, взаимные пересечения мостов и лестниц, достижимость после произвольных Cutter edits, LOS, безопасное возвращение из углублённого вручную domain. Grapple Presence создаёт геометрию потенциальных посадок; runtime anchors ещё не расставлены.

## Godot: импорт текущего результата с коллизиями

- Игровая сцена: **`Scenes/Levels/Level_Freestyle_GN_V02.tscn`**.
- Generated snapshot: `Assets/Levels/Level_Freestyle_01/Exports/Level_Freestyle_01_GN_V02.glb`.
- Exporter: `Tools/Blender/LevelBlockoutV02/export_godot.py`.
- В GLB ровно два authored nodes: `GN_V02_Level-col` и `PlayerSpawn_V02`. Cutter, Volume, старые версии и guides исключены. Суффикс `-col` создаёт один StaticBody3D с ConcavePolygonShape3D по итоговому мешу; [документация Godot](https://docs.godotengine.org/en/stable/tutorials/assets_pipeline/importing_3d_scenes/node_type_customization.html).
- Exporter получает evaluated mesh, создаёт временную копию в отдельной сцене и после экспорта удаляет только свои временные datablocks. Ручные meshes и GN-модификатор не применяются. Для glTF временные Principled-материалы получают цвет существующего Blender viewport; исходные материалы не меняются.
- Source сохраняется, предыдущая дисковая версия копируется в timestamped `Source/Backups/*-before-v02-godot/`. GLB — снимок на момент экспорта, live-связи открытой игры с Blender нет.
- Wrapper использует текущий `Scenes/Player.tscn`, существующий marker binder, Crosshair и Speedometer, свет/environment из Freestyle. Небольшой `GNBlockoutPreview.gd` задаёт только заголовок и подпись. Player/tuning/mechanics не изменялись. Spawn (0, 0.05, 0), F1 перезапускает уровень.

**Проверено в Godot 4.6.3 Mono / Jolt, включая обычный графический запуск:** build 0 errors / 0 warnings, import успешен, **27/27 runtime checks PASS**. 4718 visual triangles и 4718 collision triangles; полное взаимно-однозначное сопоставление с максимальным отклонением вершины **0.080 mm**. При сравнении используется расстояние, поскольку округление координат в ключи давало ложный mismatch на границе округления.

120/120 physics rays проверили полы, стены и рампы. Текущая капсула Player блокируется стеной. Через настоящий InputEvent выполнен прыжок и возврат на spawn; пик 2.423 m. Начальное размещение над верхними площадками проверило физические посадки на Y=6.36 / 12.72 / 25.44 m, также посадку на рампу. Масштаб и смена осей совпадают с Blender; над spawn нет коллизии потолка, в пустом крае domain нет скрытого safety floor. Это автоматизированная проверка, не полный ручной parkour playtest.

Доказательства: [godot_export.json](Reviews/GNLevelBlockoutV02/godot_export.json), [godot_qa.json](Reviews/GNLevelBlockoutV02/godot_qa.json), [вид от Player](Reviews/GNLevelBlockoutV02/godot_spawn.png), [общий вид](Reviews/GNLevelBlockoutV02/godot_overview.png).

Старое предупреждение canonical Player о legacy ArrowTipMarker остаётся; новые ошибки импорта/физики не обнаружены. Runtime grapple anchors, enemies, navigation и checkpoint system в этот импорт не добавлялись.

### Повторный экспорт и запуск

Сначала сохранить свои правки Blender и выйти из Edit Mode. Старый Freestyle `Save + Export` использует прежний whitelist и **не экспортирует V02**. Для V02 использовать отдельный exporter:

```powershell
blender --background Assets/Levels/Level_Freestyle_01/Source/Level_Freestyle_01.blend --python Tools/Blender/LevelBlockoutV02/export_godot.py
godot --headless --editor --path . --import --quit
godot --path . res://Scenes/Levels/Level_Freestyle_GN_V02.tscn
```

Exporter также можно выполнить в уже открытом Blender через Python API; он использует текущий live result. Не выполнять build.py/rebuild_graph.py ради обычных ручных изменений. В Godot открыть новую `.tscn` и нажать F6; main scene проекта оставлена прежней.

### Сохранность и изменённые файлы

[preservation.json](Reviews/GNLevelBlockoutV02/preservation.json): все 212 прежних object fingerprints сохранены, POC и V01 node/link counts совпадают; SHA-256 92 protected files не изменились, включая Player/tuning, старые уровни, project.godot и прежние Freestyle GLB. Три старых generic names получили префикс V01, их data и ссылки сохранились. Рабочая V02 `.blend` сохранена с Seed 17; editable source остаётся источником истины.

В этой итерации добавлены V02 GLB и generated import sidecar, новая игровая `.tscn`, `GNBlockoutPreview.gd` (+ UID), `export_godot.py`, `verify_godot.gd` (+ UID), этот отчёт и review evidence; сохранён существующий Freestyle `.blend`, дополнен `blender_pipeline.md`. Ранее созданные V02 build/QA scripts и Blender collections остаются. Commit/push не выполнялись.
