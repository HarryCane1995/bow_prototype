# V04 — editable local proxy volume

Состояние: Blender implementation + automated API QA, 21 сентября 2026.
Human Edit Mode / хоткеи пользователь проверяет самостоятельно. CU не использовался.
Godot не запускался, экспорт, collisions, runtime anchors и `.tscn` не менялись.

## Файл и авторский mesh

- Файл: `Assets/Levels/Level_Freestyle_01/Source/Level_Freestyle_01.blend`.
- Новый native GN group: **GN_LevelProxyGenerator_v04**, 681 nodes, **0 Bounding Box nodes**.
- **LEVEL_PROXY** — обычный Mesh без modifiers. Все изменения формы — ручные.
- **LEVEL_GENERATED_OUTPUT** — отдельный procedural host, solid.
- **GRAPPLE_CANDIDATES** — отдельный procedural helper host; без постоянных anchor objects.
- **LEVEL_CUTTER** — существующий secondary cutter; `Use Cutter` по умолчанию false.
- **PLAYER_SPAWN** оставлен прежним world-origin reference. Логика whole-level route к нему не привязана.

LEVEL_PROXY изначально создан независимой копией редактированного UX_TEST_V04_PROXY
(36 vertices / 34 faces). Последующие правки, появившиеся в сеансе, сохранены:
в итоговом файле **52 vertices / 50 faces**. Python генератор и QA не переписывают
этот авторский mesh. Исходный UX_TEST_V04_PROXY сохранён hidden/reference.

Сверка перед сохранением: сохранены meshes, transforms и modifier stacks всех
228 ранее существовавших объектов. Только прежнее имя объекта вывода V02 изменено
на `V02_GENERATED_OUTPUT_REFERENCE`, чтобы новый output получил требуемое имя.
V02 node group и объект как datablock сохранены, как и POC/v01/v03/старый V04.
Старые scripts, обращающиеся к буквальному имени LEVEL_GENERATED_OUTPUT для V02,
перед повторным использованием потребуют выбора reference-объекта. Их не запускать
поверх новой authoring сцены. Backup до новой реализации находится в
`Docs/Reviews/LocalProxyV04/before_local_proxy_20260921_020350.blend`.

## Исправленная причина растягивания

Предыдущий `GN_ProxyChunk_Generator_v04` в
`Tools/Blender/ProxyChunksV04/generator.py` вычислял один `GeometryNodeBoundBox`
для всего mesh. Общие W/L/H управляли положением, длиной, шириной и высотой
всех primitives. Последний Intersect также использовал bounding box.
Поэтому вертикальное/широкое extrusion меняло размеры прежнего наполнения,
а повороты и пустоты реального mesh не ограничивали результат корректно.

Новая группа не читает global bounds даже для placement limits.

## Локальные участки и направление

Это stateless разбор существующей topology, а не восстановление истории Extrude.
Пользователь не размечает segment IDs.

1. Object Info читает реальный proxy в его локальной системе. На отдельной
   evaluation-ветке удаляются нулевые грани и объединяются совпадающие rings
   в пределах 0.1 mm. Mesh пользователя не меняется.
2. Нижние/наклонные face patches задают горизонтальные секции. Две пары
   противоположных рёбер дают локальные length/width и tangent direction.
   `up = -normal`, `side = up × forward`, origin — центр patch.
   Локальный raycast вверх измеряет доступную высоту.
3. Длинные patches получают несколько beats примерно до 18 m каждый;
   каждый beat содержит landing/floor, gap и вариативные traversal surfaces.
   Новый extrusion создаёт новые faces, а значит новые patches, не меняя старые.
4. Для вертикального пространства выбираются ориентированные боковые patches.
   Внутренний raycast поперёк измеряет ширину; вниз — основание shaft.
   Фиксированная решётка высот с шагом **3.1–4.8 m** создаёт intermediate levels.
   Новая верхняя cap добавляет уровни, не распределяя старые по новой общей высоте.
   Совпадающие уровни соседних боковых patches дедуплицируются в пределах 2 mm;
   координаты level points округляются до 0.1 mm для числовой стабильности.
5. Широкие patches дают более широкие landings и дополнительные боковые площадки.
   Предыдущая narrow section сохраняет собственные локальные размеры.

Frames хранятся как `lp_forward`, `lp_side`, `lp_up`, `lp_center`; размеры —
`lp_length`, `lp_width`, `lp_height`, `lp_beat`. После Boolean новые cap vertices
могут иметь нулевые значения этих диагностических attributes.

Независимые closed islands проходят тот же локальный разбор. Они не получают
общего layout-box и не соединяются автоматически. Удаление одного island
оставляет прежний output другого идентичным в проверенном случае.

## Gameplay fill и метрики

Словарь: landings/floors, gaps, floating pads, wallrun strips, wall-jump contacts,
локальные ramp wedges, короткие slide passages. Supports и обязательные лестницы
не строятся. Платформы могут висеть в воздухе.

Десять source hashes существующего movement snapshot проверены перед сборкой.
Используются наблюдённые метрики: running jump 12.505 m, air-jump rise 5.603 m,
wallrun 44.320 m, lateral wall-jump 9.53 m, grapple acquisition 50 m.
Горизонтальный gap ограничен примерно 28–48% running-jump range; парные стены
расположены до 6 m друг от друга. Площадки имеют достаточную локальную площадь;
slide passage оставляет примерно 1.35 m clearance. Это локальные budgets,
не доказательство связности или проходимости каждого Seed.

Ramp Steepness меняет именно геометрический уклон unit wedge; API измерил
45°, 55° и 70°. 70° не запрещён, gameplay validation намеренно отложен.

Grapple helpers — процедурные amber icosphere instances, реализованные в одном
отдельном mesh host. Они располагаются над gap/landing и выше промежуточных
вертикальных уровней; смещения ограничены значительно ниже 50 m acquisition.
Grapple Bias = 0 даёт пустую helper geometry. Markers проходят тот же clip и Cutter.
Полезность каждой траектории, line of sight и runtime acquisition не проверялись.

## Seed и локальная стабильность

Random streams используют Global Seed и hash локальной позиции, округлённой
до сантиметра. Face/vertex indices, количество секций и общий размер mesh
не входят в random identity. Округление симметрично относительно нуля:
микропогрешность raycast не переносит point в соседнюю ячейку Seed.

При append новой секции нетронутые patches сохраняют frames и random placement.
В трёх основных regressions old-region geometry/vertex hashes, bounds и локальные
dimensions совпали. При удлинении отдельной 48 m шахты на 22 m old-region hash
также совпал. Hash геометрии канонизирует face vertex coordinates до 0.00001 m.

Это не persistent-ID система: изменение самого patch, его перемещение в Edit Mode,
subdivide или dissolve меняют локальную интерпретацию и могут сменить его Seed.
Параметры также намеренно перестраивают наполнение. Whole-object G/R сохраняет
локальный Seed, потому что оба output hosts следуют за parent LEVEL_PROXY.

## Strict containment

Realize Instances → **Intersect с очищенным реальным proxy mesh** → optional
Cutter Difference → закрытость guard. Helpers проходят аналогичную ветку.

- Preview Quality 0: Manifold solver.
- Preview Quality 1: Exact solver с self-intersection/hole-tolerant flags.
- Пустой набор primitives явно остаётся пустым. Это важно: Blender multi-input
  Intersect иначе игнорирует empty input и может вернуть целый proxy.
- Для объёма с boundary/nonmanifold edges output пуст, пока mesh не закрыт.
- Разрешённого exterior overhang нет: **0 m**. Отдельный Junction Tolerance
  control не нужен в этой версии. Внутренние пересечения primitives допустимы;
  они всё равно отсекаются final envelope. 2 mm dedup и 0.1 mm cleanup —
  технические допуски внутри алгоритма, не разрешение выступать наружу.

Containment QA использует вершины и четыре внутренних samples каждого треугольника,
double-precision generalized winding number относительно настоящего closed mesh,
плюс независимый Exact Boolean `output minus proxy`. Допуск boundary samples:
**0.3 mm**. В актуальной авторской форме проверено 3,716 samples поверхностей
и 2,392 samples helpers; внешних samples нет.

На coplanar/overlapping surfaces независимый Exact Difference иногда оставляет
числовые плоские фрагменты внутри/на границе, с residual volume порядка
5e-7 m³. Поэтому отчёт не заявляет буквально пустой Difference во всех случаях:
дополнительно проверяются его vertices, ненулевой внешний остаток не найден.
Preview 0 и 1 прошли эту проверку на авторской форме.

## Automated QA

Все topology operations выполнялись на `TEST_LPV04_*` disposable meshes.
После QA они удалены. Production source не использовался как mutable fixture.

| Проверка | Результат |
|---|---|
| Horizontal extension | Новый output; old-region hash/bounds сохранены |
| Horizontal → vertical (+26 m) | Новые верхние surfaces; old geometry/dimensions/bounds стабильны |
| Angled extension (12,20,0), cap rotation −32° | Old region стабилен; forward совпадает с ожидаемой осью, dot = 1 |
| Narrow → wide, cap width ×2.5 | Новая локальная композиция; old narrow region неизменён |
| Shaft 48 → 70 m | Новые верхние levels; старый hash сохранён |
| Наклонный descent | Новое наклонное наполнение, containment pass |
| Seed 17 → 42 → 17 | Изменение и детерминированный возврат |
| Seeds 17 / 42 / 73, текущая форма | Containment surfaces/helpers pass для каждого |
| Verticality / Platform Density | Изменяют слои и количество площадок |
| Grapple Bias 0 / 1 | 0 / 120 helper faces на fixture |
| Ramp 45 / 55 / 70 | Измеренные slopes совпадают |
| Cutter | Evaluated geometry изменяется, containment сохранён |
| Mesh scale / rotation / vertex move | Output изменяется, containment pass |
| Object transforms | Локальный hash сохранён, output matrix следует source |
| Disconnected islands / удаление island | Независимое наполнение, исходный island неизменён |
| Delete face → open volume | Output пуст до восстановления cap |
| Subdivide / inset / bevel / dissolve | Input/output меняются, output nonempty, containment pass |
| Merge by distance | Проверен на disposable coincident extrusion ring |
| Source Custom Properties → SUM drivers | Изменяют output; возврат Seed детерминирован; 15 valid drivers |
| API Edit Mode extrusion | Измерение при EDIT_MESH: output 47 → 71 faces без Apply/Bake |
| Node modifier warnings | Пусто |
| Saved file, background load, autoexec OFF | Оба outputs и native drivers работают; hashes совпали с live |

Замер не читает cached evaluated mesh: перед каждой итерацией вершина QA-копии
слегка перемещается, затем измеряется depsgraph update + оба output hosts.
8 измерений: Preview median **6.22 ms**, max **6.50 ms**; Exact median
**141.33 ms**, max **147.54 ms**. Это время evaluation, не измерение FPS,
задержки UI или производительности больших production meshes.

## Известные ограничения

1. Closed manifold, outward consistent normals и отсутствие self-intersections
   обязательны. Перевёрнутые normals, внутренние caps и пересекающиеся islands
   не являются поддержанным envelope. В этих случаях или при экстремальных
   координатах/почти нулевой толщине строгая Boolean containment не гарантирована.
   Открытый mesh обнаруживается и даёт пустой output целиком.
2. Quad extrusion — основной случай. Для сложных triangles/n-gons frame берётся
   из первых четырёх циклических corners: возможны underfill, неверный tangent
   или неудачные локальные пропорции. Final clip остаётся обязательным.
3. Это face-patch decomposition, не полноценный medial skeleton / semantic
   segmentation. Изменение topology самого старого patch может перестроить его.
4. Canonical side-patch выбор для shaft зависит от ориентации faces относительно
   локальных осей proxy. При сильном повороте mesh topology в Edit Mode выбор
   боковой patch и её наполнение могут измениться.
5. Рабочая метрическая настройка — Object Scale = (1,1,1). Неединичный scale
   сохраняет containment, но масштабирует физические clearance/distances.
6. Нет гарантии globally traversable route. Разрежённые Seeds, острые сужения,
   clipping и большой authored gap могут требовать ручной коррекции.
7. Human Edit Mode и gameplay тесты не объявляются пройденными. API Edit Mode
   проверяет зависимость depsgraph, а не удобство работы мышью/горячими клавишами.

## Передача и файлы

В Blender выбран **LEVEL_PROXY**, Object Mode, Seed **17**, Preview **0**,
Use Cutter **false**. В текущем сеансе N → **V04 Local** показывает controls.
После повторного открытия они всегда доступны через Object Properties →
Custom Properties; необязательный Text `V04_CONTROLS_PANEL.py` восстанавливает
удобную панель. Auto Run Python не нужен для самой генерации.

Тексты внутри `.blend`: **V04_QUICKSTART**, **V04_MANUAL_TEST_CHECKLIST** (14 тестов).
Их копии и JSON evidence находятся в `Docs/Reviews/LocalProxyV04/`.

Изменён `.blend`; добавлены `Tools/Blender/LocalProxyV04/` (native graph builder,
one-time setup, rebuild, QA, optional panel, handoff и read-only saved-file check),
эта документация и `Docs/Reviews/LocalProxyV04/`.
Сверены SHA-256 268 существующих Godot scene/code/export файлов: без изменений.
Commit и push не выполнялись.
