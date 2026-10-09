# Local Proxy V06 — composition, occupancy, arenas

Реализовано 21.09.2026 в Blender 5.1.2. Новая группа — **`GN_LevelProxyGenerator_v06`**.

Файл: [Level_Freestyle_01.blend](../Assets/Levels/Level_Freestyle_01/Source/Level_Freestyle_01.blend). Выберите `LEVEL_PROXY`, затем используйте обычные Edit Mode / Extrude / Move. Controls: **N → V06 Local**, либо Object Properties → Custom Properties. Необязательная панель восстанавливается из Text `V06_CONTROLS_PANEL.py`; сам генератор работает без Auto Run Python.

Проверенный сохранённый снимок Source содержит **150 вершин / 147 граней**, замкнут и не имеет modifiers. Ваши изменения во время разработки сохранены. Python строит только node graph и технические fixtures; production Source не переписывается.

## Active vocabulary

Все **42 формы V05 сохранены** в hidden/reference collection `V05_GAMEPLAY_MESH_LIBRARY`. V06 не использует их для наполнения: hexagon, clipped corners, boomerang, spear, L-like и составные экзотические формы исключены из active vocabulary.

Новая hidden collection `V06_SIMPLE_PRIMITIVES` содержит 11 простых прототипов:

| Active primitive | Форма / роль |
|---|---|
| PLATFORM_RECT | Обычная прямоугольная платформа |
| PLATFORM_WIDE | Широкий landing / крупная plate |
| PLATFORM_NARROW | Длинная беговая полоса |
| WALL_RECT | Прямоугольная traversal wall |
| WALL_LONG | Длинная wallrun wall |
| WALL_SHORT | Короткая стена |
| RAMP_WEDGE | Простой wedge |
| STEEP_RAMP | Крупный steep wedge / chute |
| BRIDGE_STRIP | Узкая прямоугольная connection strip |
| ARENA_SLAB | Одна крупная arena surface |
| VERTICAL_PAD | Простой pad для вертикальной композиции |

Геометрические размеры выбираются по роли, пространственному классу и доступному локальному объёму. Коробки задаются непосредственно в метрах; разнообразие не создаётся деформацией сложных силуэтов. У ramps отношение высоты к длине задаёт угол 45–70°. Их ориентированные bounding boxes намеренно консервативны.

Spatial classes: **SMALL** — технический/вертикальный pad; **MEDIUM** — обычная платформа; **LARGE** — runway, recovery, большая plate/ramp; **ARENA** — основной пол широкого section. Helpers имеют малый диагностический класс, но не считаются gameplay platforms.

## Placement patterns

Введены `LONG_RUN`, `SINGLE_CENTER`, `LEFT_RIGHT_ALTERNATE`, `STAGGERED`, `SIDE_BIASED`, `WALL_AND_PLATFORM`, `OPEN_CENTER`, `EDGE_WALLS`, `SLIDE_DESCENT`, `GRAPPLE_CROSSING`, `ARENA_EDGE`, `VERTICAL_ZIGZAG`.

Seed выбирает композицию и её параметры: сторону, поперечный/продольный offset, count, высоту, yaw, длину/ширину и пропуски. Pitch наследуется от локального наклонного frame. Density управляет вероятностями и бюджетом; Openness повышает вероятность свободных run sections. Наличие свободного места не заставляет генератор добавлять объект.

Run и receiving catch — отдельные читаемые поверхности. Walls размещаются снаружи центральной landing/run footprint с учётом их поворота. Крупный wedge появляется как один элемент подходящей композиции. Arena plates смещены к краям; центр остаётся свободным.

## Occupancy и clearance

Каждый кандидат сначала существует как point record: position, ортонормированные оси, размеры, роль, section ID, priority и budget. Mesh появляется только после принятия placement.

Порядок проверки:

1. Required crossing резервирует объём подхода, gap и принимающего landing.
2. Основные полы/run/catch получают высокий приоритет.
3. Helpers, затем вторичные walls/platforms/ramps рассматриваются в стабильном порядке.
4. Быстрый AABB broad phase выбирает только близкие ранее принятые объёмы.
5. Проверка по шести нормалям граней OBB отклоняет потенциальное пересечение.
6. Принятый объём добавляется в occupied set; конфликтующий или превышающий budget кандидат отклоняется.

Оба этапа выполняются в **native Geometry Nodes Repeat Zones**. Попарных Exact Boolean/physics simulation нет. Дополнительная проверка между соседними локальными sections предотвращает столкновения у junctions.

Шесть OBB face axes дают консервативную проверку: для boxes с общим up и yaw она достаточна; при сложном взаимном наклоне возможны дополнительные отказы. Отсутствующие девять edge-cross axes могут привести только к false rejection, не к принятию пересечения. Независимый Python QA проверяет все **15 SAT axes**.

**Primitive Clearance = 0.3 m**, одна треть диаметра player capsule 0.9 m. Для базовых соединяющихся route surfaces и ground contacts wall/ramp применяется отдельное разрешение контакта без зазора. Разрешение touching не разрешает объёмного проникновения. У required keepout уже есть запас: соседняя runway может встретить его границу. Поля `intentional_touch_group` и `primitive_role` позволяют отдельно проверить эти отношения.

Точность native contact comparison — 0.2 mm; независимого overlap QA — 0.4 mm. Это технические допуски floating-point расчёта, а не разрешённые заметные пересечения.

Local budgets:

| Section | Budget |
|---|---|
| Обычный run/gap/catch phrase | `floor(3 + 3*Density + min(2, run_length/35))`, максимум **8** |
| Arena patch | `5 + floor(4*Density)`, максимум **9** |
| Вертикальная колонка / фиксированный 24 m band | максимум **3** |

Helpers входят в budget; виртуальные required keepouts — нет. Большой authored extrusion может содержать несколько независимых rhythm sections. Budget относится к ним, а не к целому mesh из нескольких маршрутов.

## Arena score и scale

Используются **локальные** width `W` и length `L`, а также подтверждённая скорость бега `v = 18.3 m/s`:

`arena_score = min(1, W/(1.5*v), sqrt(W*L/(3*v*v)), 5*W/L)`.

Arena выбирается при score около 1: ширина не менее 27.45 m, площадь не менее 1004.67 m², aspect ratio не более 5. Эти пороги выражены через длину разбега за 1.5 s и площадь в единицах движения. Global proxy bounds в layout не участвуют.

Широкий patch получает **один основной slab**, вместо повторения маленьких плит по rhythm. Дополнения: до трёх LARGE raised plates, немного edge walls, максимум один крупный ramp и один optional helper, с дальнейшим occupancy rejection.

| Fixture | Результат Seeds 17 / 42 / 73 / 109 |
|---|---|
| **70 × 90 × 24 m** | score **1.0**; по **4** принятых элемента, включая helpers, где они выбраны |
| Основной arena floor | **89.2 × 69.2 m = 6172.64 m²**, одна непрерывная slab до clipping |
| Тот же arena fixture, Density/Verticality/Ramp/Wallrun = 1 | **7** элементов на каждом из трёх проверенных Seeds; budget 9; одна крупная ramp |
| **16 × 240 × 14 m** | score **0.333**; arena floor отсутствует; **11 / 18 / 13 / 20** элементов на всём длинном маршруте, включая helpers |
| **14 × 18 × 72 m** | **7 / 6 / 6 / 5** элементов, включая основной нижний run и helpers; sparse pads/walls вместо частой лестницы |

Для воспроизведения ramp в узкой секции: 20 × 240 × 16 m, Seed 1, Ramp Presence / Density / Slide Bias = 1. Проверен один принятый wedge размером около 5.52 × 7 × 7.88 m при 55°.

## Vertical rhythm и сохранённый фундамент

Сохранены authored `LEVEL_PROXY`, V04 local decomposition/frames и fixed-height lattice. V06 выбирает каждый третий кандидатный уровень, меняет сторону, добавляет небольшой height/longitudinal offset и пропускает часть beats. В зависимости от controls базовое расстояние между такими beats — 9.3–14.4 m; пропуски могут увеличивать интервалы. Walls и optional grapple hints дают другой тип опоры. Широкие arenas не получают дополнительный ковёр vertical pads.

Вертикальный режим выбирается для достаточно высокого и вытянутого вверх локального объёма. Stable 24 m bands ограничивают количество элементов без перераспределения всей шахты при extrusion.

`GN_LevelProxyGenerator_v05` осталась неизменной. Для V06 создана копия только зависимостей V05 rhythm; старое library filling в ней удалено. V04 foundation используется повторно. У V06 **2550 nodes**; runtime — native GN и SUM drivers, без Python handlers.

Стабильные spatial IDs и локальные ordinal IDs сохранены. Проверки vertical append, angled append и wide-after-narrow append сохранили hashes старой геометрии, bounds и placement records. Disconnected island также не изменил старый island. Изменение самого patch, пересекающее его новую геометрию или remesh/dissolve может изменить локальную композицию; это не гарантия неизменности junction.

## V05 spans и required grapple

Все 10 canonical Player/tuning hashes совпали с verified snapshot от 20.09.2026. **Observed horizontal air/double jump = 23.035152 m**, running jump = 12.505147 m, grapple acquisition = 50 m. Повторного Godot запуска не было.

| Span class | Сохранённый диапазон |
|---|---:|
| BASIC_JUMP | 5.627–8.754 m |
| AIR_JUMP | 13.360–17.967 m |
| NEAR_LIMIT | 19.350–21.653 m |
| GRAPPLE_REQUIRED | 25.339–33.401 m |

Length Variation сохранён отдельно от gap. На 480 m fixture при Seed 17: `0` даёт run 21.96 m; `0.82` — 11.58–70.21 m; `1` — 9.30–80.80 m. Длинный runway не становится длинным jump gap.

Required helper — крупный розовый marker; optional — маленький жёлтый. Required marker не отключается Grapple Bias. Для D проверяются range, proxy/cutter samples, approach/catch и occupied corridor. В этот corridor допускаются только собственные обязательные surface/helper records. Если резервирование D не удалось, span понижается до Basic с сокращением gap и расширением catch в прежнем phrase footprint.

На 20 × 480 × 12 m fixture, Seed 17: **gap 28.202 m**, helper **18.447 m** от подхода, catch **12 m**. При Bias 0 helper остаётся. Cutter на marker меняет D на **Basic 8.428 m**. Десять ray/BVH измерений по фактическому generated mesh совпали с declared gaps.

Горизонтальные bands применяются к почти горизонтальным frames (`abs(forward.z) <= 0.02`). Inclined patches сохраняют continuous fill. На текущем сохранённом Source, Seed 17, D spans не выбраны; правило проверено на длинных fixtures. Ни горизонтальная, ни вертикальная композиция не является полной гарантией gameplay reachability/LOS.

## API QA и performance

Проверены 16 сочетаний четырёх fixtures и четырёх Seeds, ещё девять сочетаний с Density/Verticality/Ramp/Wallrun = 1 и yaw до 25°, три append-сценария и текущий authored snapshot.

- **0 unintended primitive overlaps** и **0 clearance violations** на проверенных принятых records.
- Независимый QA использует 15-axis OBB SAT до final clipping/Boolean.
- Проверка реальных pre-Boolean mesh vertices/размеров против OBB прошла во всех девяти stress fixtures; дубликатов placement IDs нет.
- Wide arena имеет одну крупную floor, bounded count и score 1; narrow fixture не превращается в арену.
- Required helper, approach и catch присутствуют у всех проверенных D spans и остаются внутри acquisition range.
- Budget соблюдён; Seed меняет результат и детерминированно воспроизводит его при возврате.
- Source topology меняется на disposable mesh, evaluated output обновляется внутри API Edit Mode без Apply/Bake.
- Нет GN modifier warnings. Оба production host drivers valid.

**Сохранённый Source: 150 vertices / 147 faces.** Независимое фоновое открытие `.blend` с Auto Run Python disabled воспроизвело hashes обоих outputs. На этом снимке **90 принятых elements** на всём authored mesh, **0 overlaps**, **0 clearance violations**, 19 разрешённых boundary contacts.

Containment: 4266 surface samples и 1656 helper samples, **0 outside**. Дополнительный Exact `output minus proxy` не нашёл exterior vertices/face centers; у surfaces остаётся тонкий coplanar numerical residue с эквивалентной толщиной 0.000000299 m, helpers дают пустую разность. Допуск containment — 0.3 mm.

| Замер dirty edit → оба evaluated outputs | Preview 0 median / max | Exact 1 median / max |
|---|---:|---:|
| В подключённом Blender, копия Source 146v/143f | **65.98 / 69.46 ms** | **302.57 / 306.86 ms** |
| Независимо открытый сохранённый snapshot 150v/147f | **65.42 / 66.66 ms** | **309.20 / 315.48 ms** |

Это API timings, не измеренный human viewport FPS. Occupancy дороже V05 без проверки пересечений; число primitives и сложность объёма влияют на время. Упрощать текущий authored Proxy для этой проверки не понадобилось.

Сравнение с резервным `.blend` подтвердило неизменность V05 graph и всех 42 library meshes. Все **557** отслеживаемых Godot-related файлов и **11** файлов V05 builder остались неизменны. Из исходных 276 объектов ни один не удалён; изменены только два разрешённых output modifier stacks и Source mesh через ваши live edits. Предыдущие outputs сохранены в `V05_OUTPUT_REFERENCE`.

Фоновый Blender выводит предупреждения установленных InstaMAT plugins; процесс завершился успешно, GN warnings отсутствуют. Эти plugins не изменялись.

## Debug и handoff

`Debug Placement Volumes` показывает принятые OBB и D keepouts. Это диагностические wires, они могут выходить за уже clipped mesh. `Debug Span Colors` сохраняет V05 цвета. Оба режима выключены при handoff.

Доступные attributes: `placement_id`, `pattern_id`, `primitive_role`, `primitive_id`, `primitive_scale_class`, `primitive_budget`, `occ_size`, `occ_x/y/z`, `occ_aabb`, `intentional_touch_group`, `overlap_rejected_count`, прежние `section_id`, `local_seed`, `span_class`, `span_distance`, `required_traversal`, `grapple_required`, `local_forward`. Required helpers также несут `source_span`, `anchor_distance_from_approach`, `anchor_height`, `landing_distance`. Счётчик rejected включает отказы по occupancy и budget; это не число оставшихся пересечений.

Internal Output Mode: 0 surfaces, 1 helpers, 2 spans, 3 envelope, 4 raw surfaces, 5 helper records, 6 accepted records, 7 wires, 8 rejected records, 9 candidates. Production hosts используют 0/1.

Ручные тесты: [V06_MANUAL_TEST_CHECKLIST](Reviews/LocalProxyV06/V06_MANUAL_TEST_CHECKLIST.txt) — 11 проверок; [V06_QUICKSTART](Reviews/LocalProxyV06/V06_QUICKSTART.txt). Оба текста встроены в `.blend`.

Начните с **No Intersections → Placement Variety → Wide Arena → Narrow Flow → Vertical Rhythm → Grapple Required → Old Proxy Stability**. Human visual/playability test оставлен вам. CU, Godot, export, collisions, runtime anchors, commit и push не использовались.

Изменён asset `Assets/Levels/Level_Freestyle_01/Source/Level_Freestyle_01.blend`; добавлены `Tools/Blender/LocalProxyV06/`, этот отчёт и `Docs/Reviews/LocalProxyV06/`. Основные evidence: [wide](Reviews/LocalProxyV06/wide.json), [narrow](Reviews/LocalProxyV06/narrow.json), [vertical](Reviews/LocalProxyV06/vertical.json), [stress/controls](Reviews/LocalProxyV06/controls_and_meshes.json), [saved-file QA](Reviews/LocalProxyV06/saved_file_verification.json), [handoff audit](Reviews/LocalProxyV06/handoff.json). Резервная копия до V06: `Docs/Reviews/LocalProxyV06/before_v06_20260921_033005.blend`.
