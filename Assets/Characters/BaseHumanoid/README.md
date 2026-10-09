# BowPrototype Humanoid Base / BH_01

Оригинальная техническая база: Male 1,80 м + Female 1,70 м, две отдельные сетки и один стандарт скелета. Создана в Blender 5.1.2 через Blender Python API. Проверена в Godot 4.6.3 Mono / Forward+ / D3D12. UE/Manny/Quinn и сторонние body assets не использовались.

## Что открыть

- **Редактируемый исходник:** [Source/Humanoid_Base.blend](Source/Humanoid_Base.blend).
- **Тест в Godot:** [Humanoid_Base_Test.tscn](Humanoid_Base_Test.tscn), открыть и запустить F6. Главная сцена проекта не менялась этой задачей.
- **Экспорты:** [Male](Exports/Humanoid_Male.glb), [Female](Exports/Humanoid_Female.glb).
- **Ракурсы front / side / back / 3/4:** [Body_views.png](Review/Body_views.png).
- **Риги, wireframe и кисти:** [Topology_and_rig.png](Review/Topology_and_rig.png); отдельно [skeleton](Review/Skeleton_overlay.png), [wireframe](Review/Wireframe.png).
- **12 основных тестов деформации:** [Deformation_tests.png](Review/Deformation_tests.png).
- **Реальный Godot viewport:** [оба в rest pose](Review/Godot_pair.png), [временный skin probe](Review/Godot_skin_probe.png).
- Дополнительный сгиб шеи / запястий / пальцев: [Male](Review/Male_test_neck_wrist_flex.png), [Female](Review/Female_test_neck_wrist_flex.png), кисть крупно [Male](Review/Male_test_fingers_detail.png), [Female](Review/Female_test_fingers_detail.png).

## Исходник и ручная работа

В сцене ровно четыре объекта: `Male_Rig`, `Male_Body`, `Female_Rig`, `Female_Body`. Коллекции `10_Male`, `10_Female`. Никаких Geometry Nodes, внешних моделей, linked libraries, скрытых генераторов, reference meshes или helper-объектов. Встроенный Text `README_Humanoid_Base` объясняет основу при открытии файла.

Каждое тело — одна связная замкнутая сетка с настоящими соединениями у плеч, таза и пяти пальцев каждой кисти. Editable cage можно менять в Edit/Sculpt Mode, использовать как основу одежды или заменять части. Генератор нужен только как история создания; работа с `.blend` от него не зависит.

Стек модификаторов: **Subdivision Surface 1 → Armature**. Subdivision остаётся редактируемым, glTF получает вычисленную поверхность и интерполированные веса. Armature использует **линейную деформацию**, Preserve Volume выключен для соответствия glTF/Godot. Веса обычные vertex groups, до четырёх влияний; нормализованы.

Female отличается шириной плеч, грудной клетки, талии и таза, объёмом бедра, длиной рук, размером кистей/стоп и общим ростом. Это отдельная геометрия с той же топологией и skeletal convention, а не один scale/morph на мужском теле. Нет гениталий, secondary anatomy detail, лица, волос, одежды или character styling.

## Rig approach и иерархия

Простой собственный FK deform skeleton, **53 кости** у каждой модели. Имена и родители совпадают; rest positions соответствуют размерам каждого тела. Rigify не потребовался: для этих задач нет необходимости экспортировать его control/deform/helper слои.

```text
root
└─ pelvis
   ├─ spine_01
   │  └─ spine_02
   │     └─ chest
   │        ├─ neck → head
   │        ├─ clavicle.L → upper_arm.L → forearm.L → hand.L
   │        │  ├─ thumb_01.L  → thumb_02.L  → thumb_03.L
   │        │  ├─ index_01.L  → index_02.L  → index_03.L
   │        │  ├─ middle_01.L → middle_02.L → middle_03.L
   │        │  ├─ ring_01.L   → ring_02.L   → ring_03.L
   │        │  └─ pinky_01.L  → pinky_02.L  → pinky_03.L
   │        └─ clavicle.R → upper_arm.R → forearm.R → hand.R
   │           └─ те же пять цепочек пальцев с суффиксом .R
   ├─ thigh.L → calf.L → foot.L → toes.L
   └─ thigh.R → calf.R → foot.R → toes.R
```

Локальная Y кости направлена от head к tail; roll выровнен относительно Blender +Y, без случайных object rotations/scales. Bone Collections: Core, Arm.L/R, Leg.L/R, Fingers.L/R. `.L` / `.R` — стороны модели. Scale канал костей заблокирован от случайного изменения. `root` находится на уровне пола, `pelvis` — отдельная кость на высоте таза. Нет IK, twist/helper bones или facial rig.

Для ручной позы: выбрать rig → Pose Mode → нужную кость. `Alt+R`, `Alt+G`, `Alt+S` возвращают pose transforms; исходная A-pose хранится в rest skeleton. Варианты не являются готовым retarget profile: одинаковые naming/hierarchy подготовлены, но Godot BoneMap и анимационный retargeting здесь не создавались и не тестировались.

## Масштаб и ориентация

- 1 Blender unit = 1 метр; Blender **+Z up, −Y model front**.
- Экспорт glTF: **+Y up, +Z model front**, +X — левая сторона модели. Это стандарт модели Godot/glTF; −Z — направление камеры, не front персонажа. См. [Godot: model export considerations](https://docs.godotengine.org/en/4.4/tutorials/assets_pipeline/importing_3d_scenes/model_export_considerations.html).
- Объектные rotation = 0, scale = (1,1,1). В Blender риги расставлены по X на −0,68 / +0,68 м только для просмотра. Экспортёр сбрасывает эти display offsets в своей временной сцене, source не перезаписывает.
- В каждом GLB root имеет origin (0,0,0). Нижняя точка стоп после Godot import: Y=0. Измеренные высоты: Male 1,800000 м, Female 1,699998 м.
- В A-pose руки опущены примерно на 45° от горизонтали, локти и колени мягко согнуты, ноги на ширине таза. Никаких keyframes для rest pose.

## Геометрия и проверка

| Метрика | Male | Female |
|---|---:|---:|
| Editable cage vertices | 3 726 | 3 726 |
| Editable cage faces | 3 800 | 3 800 |
| В том числе quads | 3 648 | 3 648 |
| Остальные faces | 152 cap triangles | 152 cap triangles |
| Вычисленная поверхность: vertices | 15 050 | 15 050 |
| Вычисленная поверхность: quads | 15 048 | 15 048 |
| GLB / Godot triangles | 30 096 | 30 096 |
| Skeleton bones / skin binds | 53 / 53 | 53 / 53 |
| Связные компоненты тела | 1 | 1 |
| Boundary / nonmanifold edges | 0 / 0 | 0 / 0 |
| Непривязанные vertices | 0 | 0 |
| Object scale | 1,1,1 | 1,1,1 |
| Анимационные клипы | 0 | 0 |

Для **обеих** моделей проверены руки вперёд, сгиб локтя 90°, руки над головой, глубокий crouch, колено 115°, широкий шаг. Дополнительно проверены сгиб шеи 25°, кисти 35° и простое сгибание всех пальцев. Это только временные FK stress tests; foot planting и игровые pose silhouettes не настраивались. После теста все pose transforms сброшены, source и GLBs находятся в rest pose; Actions/NLA отсутствуют.

Проверки Godot подтверждают PackedScene, одну mesh/один Skeleton3D на asset, одинаковые родители/имена 53 костей, 53 skin binds, корректную привязку skeleton, normals/debug StandardMaterial3D, масштабы, ground и направление toes. Все 15 050 экспортных вершин имеют skin weights. Максимальное отклонение суммы весов после import/compression: 0,000046. В графическом Godot дополнительно выполнены временные bone rotations локтя и колена; GPU skin работает у обоих тел. В test scene только два экземпляра GLB, пол, свет, камера, подписи и линейка 1,8 м.

`Humanoid_Base_Test` запускается без ошибок; `dotnet build Bow_prototype.sln --no-restore` прошёл с 0 warnings / 0 errors. `git diff --check` прошёл. Дополнительный smoke run основной карты загрузил Level_01; при завершении основная карта вывела `ObjectDB instances leaked` / `1 resources still in use`. Причина в этой задаче не исследовалась; isolated humanoid test этого сообщения не выдаёт. Player и игровые сцены этой задачей не редактировались.

Машиночитаемые результаты: [Blender QA](Review/blender_qa.json), [Godot import QA](Review/godot_import_qa.json), [source/export SHA-256](Review/export_manifest.json).

## Что пока rough

- При крайнем overhead сжимается объём плеча/подмышки; в глубоком crouch видна складка и потеря объёма около таза. Сетки остаются цельными, но corrective shapes и ручной polishing weights нужны перед финальными игровыми позами.
- Переходы запястий, ладони, перепонки и thumb opposition — baseline. Пальцы раздельные и имеют три костных сегмента; хват лука и release не ставились.
- Шея, ступни, суставные объёмы и анонимная голова намеренно упрощены. Нет UV-развёртки, текстур, лицевых деталей, twist bones, IK или LOD. Это редактируемая test geometry, не финальный character asset.
- Skin stress tests не доказывают отсутствие self-intersection во всех возможных позах. Проверены перечисленные сгибы; анимаций нет.

## Повторный экспорт и тест

Из корня проекта, после ручного сохранения source:

```powershell
blender --background --python Tools/Blender/HumanoidBase/export_base.py
godot --headless --editor --path . --import --quit
godot --headless --path . --script res://Tools/Blender/HumanoidBase/verify_import.gd
godot --path . res://Assets/Characters/BaseHumanoid/Humanoid_Base_Test.tscn
```

`export_base.py` читает текущий `.blend`, не пересоздаёт геометрию. `verify_import.gd` заново создаёт только техническую `Humanoid_Base_Test.tscn` и JSON отчёт. `review_base.py` получает ракурсы и static skin tests без сохранения поз в source; `--supplement` проверяет шею/кисти/пальцы. `capture_godot.gd` сохраняет реальный кадр тестовой сцены; `-- --skin-probe` запускает временный GPU skin test. `compose_review.py` собирает контактные листы из этих кадров.

`build_base.py` — **одноразовый рецепт первоначального создания**, а не способ обновлять ручные правки. Он отказывается перезаписывать существующий исходник без явного `-- --rebuild-humanoid`; этот флаг заменит геометрию и ручные изменения. Для повседневной работы использовать Blender source и `export_base.py`.

## Изменённые / добавленные файлы этого pass

Новые файлы ограничены `Assets/Characters/BaseHumanoid/` и `Tools/Blender/HumanoidBase/`: source, два GLB, import metadata Godot, test scene, review PNG/JSON, README и шесть authoring/verification scripts. `Source/.gdignore` исключает параллельный auto-import рабочего `.blend`, `Review/.gdignore` исключает QA PNG из игровых ресурсов. `AGENTS.md` и `Docs/blender_pipeline.md` дополнены правилом именно этой базы и уточнением осей. Остальные существующие assets, Player и игровые системы не редактировались. Commit/push не выполнялись.
