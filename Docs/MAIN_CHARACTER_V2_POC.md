# Main Character V2 — первый POC

V2 показывает две ручные позы BH_01 в настоящем Player: `BH01_IDLE` и `BH01_SLIDE`. Один Skeleton3D с 53 исходными deform bones, одним non-deforming `FP_CAMERA_SOCKET` и один AnimationPlayer используются в 1POV и внешнем 3POV. Авторские позы сохранены. В PoseLab добавлен только socket с привязкой камер; current body-driven camera pass описан ниже.

## Запуск и управление

- Сцена: `Scenes/Levels/Level_Movement_Gym/Level_Movement_Gym.tscn`.
- V2 включён по умолчанию. **F9** переключает V2 / старую presentation.
- **F10** переключает 1POV / внешний 3POV. F8 сохранена для старого motion-прототипа.
- Обычный gameplay slide: двигаться + Ctrl. R возвращает к checkpoint Gym.

## Изоляция

`Scenes/Characters/MainCharacterV2.tscn` и `Scripts/Player/Presentation/MainCharacterV2.cs` подключены одной instance в `Scenes/Player.tscn`. Код PlayerController и movement/physics modules не менялся.

V2 читает существующие `IsSliding` и `SlideDirection`. На входе запоминается направление slide; yaw мыши больше не вращает тело до выхода из этого состояния. Между статическими позами — crossfade 0,12 с. Остальные gameplay states временно показывают Idle; отдельного locomotion graph нет.

Модель рендерится существующей WORLD-камерой с калибровкой из PoseLab (см. ниже). Viewmodel camera/FOV и прежний viewport сохранены для fallback, его Canvas и старые procedural hands/legs/sway выключаются при V2 ON. Внешняя камера смотрит на тот же объект Skeleton3D. Только HEAD скрыт в 1POV; TORSO, ARMS, LEGS остаются видимыми. Нет FP skeleton или FP clips. Последующий [runtime aim experiment](MAIN_CHARACTER_V2_AIM.md) добавляет ограниченный arm IK поверх того же скелета; нулевые веса возвращают source pose.

Существующий `CyberBowAxisCorrection` временно переносится в `V2_LeftHandGrip` на `hand.L`; отдельный игровой bow не создаётся. Offset откалиброван по PoseLab с учётом импортированных bone axes. При V2 OFF parent, transform, layers и прежние writers возвращаются. Стрельба/снаряды остаются прежними; runtime hand/nock IK и доводка weapon aim не входят в POC.

## Экспорт

`Assets/Characters/BaseHumanoid/Exports/BH01_Male_V2.glb`: один skin, 53 исходных deform bones с сохранёнными именами/rest/hierarchy плюс camera socket под chest, четыре части Male mesh и только Idle/Slide. Socket не имеет весов mesh. Два одинаковых endpoint-ключа держат каждый static clip 1 с без loop. До разделения mesh bake совпал с исходной поверхностью в пределах 0,007 мм. Сохранено до восьми влияний на вершину.

Аудит текущего source: Idle и Slide имеют разные ручные формы. Jump Air совпадает с Idle; остальные Actions не добавлены в runtime. Текущие Bow/Crouch/Landing визуально соответствовали нейтральным placeholders, поэтому изменение исходного файла не выполнялось.

Повторный экспорт после ручных правок:

1. В открытом PoseLab на frame 1 выполнить `Tools/Blender/HumanoidBase/capture_v2.py` через Blender Python/MCP. Это создаёт backup и evaluated capture в `.godot/humanoid-base/`, сохраняя активную авторскую позу.
2. Запустить Blender background с `--python Tools/Blender/HumanoidBase/export_v2.py -- .godot/humanoid-base/v2_source_capture.json`.
3. Godot import, затем `--script res://Tools/Blender/HumanoidBase/verify_v2.gd -- --write-grip-offset` для проверки bones/poses и обновления grip offset. Без последнего флага verifier не пишет сцену.

## Проверка и вывод

`dotnet build` — 0 ошибок/предупреждений. Godot import проверил оба клипа и позиции всех 53 joints: ошибка менее 0,005 мм. `Tools/Character/v2_playtest.gd` прогнал настоящий Player через input actions: Idle FP/external, slide FP/external, независимые yaw/pitch, выход в Idle, левое/правое направления и V2 OFF/ON. Данные и кадры: `.godot/humanoid-base/v2-playtest/`; результат `V2_PLAYTEST_PASS`. Reset в этом тестовом драйвере относится только к fixture; gameplay-настройки не изменяются. Старое предупреждение про отсутствующий ArrowTipMarker существует и в fallback.

- **A:** одна full-body Slide работает в 1POV и 3POV; при смене камер instance skeleton не меняется.
- **B:** для POC скрыта только голова, корпус дополнительно не скрывался.
- **C:** отдельная FP skeletal pose пока не нужна для проверки фундамента. Skeletal offsets не добавлялись.
- **D:** во время slide камера свободна; тело остаётся по траектории. На больших углах руки/лук закономерно уходят из кадра, head aim пока нет.
- **E:** первоначальный POC использовал старую высоту игровой камеры. Затем калибровка повторила статичную PoseLab-камеру на высоте Slide. Текущий socket pass сохраняет Slide и автоматически поднимает камеру в Idle на 50,95 см.
- **F:** в slide собственные ноги/торс видны как части одного тела; при взгляде вниз связь с телом убедительнее, чем отдельные slide legs.
- **G:** при сильном взгляде вниз торс, руки и лук заполняют нижнюю часть кадра. Общая гипотеза работает, окончательная 1POV-композиция требует отдельного approval pass.

Crossfade использует штатный [AnimationPlayer](https://docs.godotengine.org/en/4.6/classes/class_animationplayer.html); разделение камер остаётся на [presentation level](https://docs.godotengine.org/en/4.6/classes/class_camera3d.html).

F9/F10 дополнительно проверены через клавиатурный ввод в обычном запуске Gym: внешний вид, fallback и возврат в V2/1POV. Обработчик принимает logical/physical keycode и помечает своё событие обработанным.

## Файлы этого pass

- Новый asset: `Assets/Characters/BaseHumanoid/Exports/BH01_Male_V2.glb` и import descriptor; manifest — `Assets/Characters/BaseHumanoid/Review/v2_export_manifest.json`.
- Новые runtime files: `Scenes/Characters/MainCharacterV2.tscn`, `Scripts/Player/Presentation/MainCharacterV2.cs`.
- В `Scenes/Player.tscn` добавлена ссылка на V2 и один дочерний instance.
- Новые инструменты: `Tools/Blender/HumanoidBase/capture_v2.py`, `export_v2.py`, `verify_v2.gd`; `Tools/Character/v2_playtest.gd`.
- Документация: этот отчёт, дополнения к `Docs/blender_pipeline.md` и `AGENTS.md` о V2 export и обнаруженном ограничении `hide_select`.
- В первоначальном POC `.blend` source не перезаписывался. Последующий socket pass сохранил PoseLab с новым helper bone и camera anchor constraint после backup; Actions не изменены. Backup и тестовые кадры находятся в `.godot/humanoid-base/`. Остальные существовавшие изменения working tree сохранены.

## Body-driven camera socket (2026-09-12)

`FP_CAMERA_SOCKET` добавлен в `Male_Rig` у основания шеи, на конце chest. Иерархия: `root → pelvis → spine_01 → spine_02 → chest → FP_CAMERA_SOCKET`. Это disconnected helper, `use_deform=False`, без vertex groups/весов, в bone collection `Presentation`. Существующие rest transforms, Actions и control rig, включая пальцы, сохранены.

`FP_Camera_Anchor` имеет object parent `Male_Rig` и constraint `FP Socket Position Only`: Copy Location, target socket в POSE space, owner LOCAL, Offset включён. Его editable local Location — presentation offset в осях rig. Rotation груди не передаётся камерам. Существующие `CTRL_CAM_WORLD`/`CTRL_CAM_VIEWMODEL` и их камеры сохранены, обе selectable. При миграции anchor откалиброван по текущей Slide: матрицы обеих камер до/после совпали без сдвига.

`capture_v2.py` получает evaluated camera в осях `Male_Rig` и вычитает animated socket origin из translation. `export_v2.py` создаёт calibration JSON **version 2**, один набор `cameras` с `socket_offset_transform`, без таблицы `poses`. Offset проверяется на совпадение между захваченными Actions; несовпадение останавливает экспорт. Оси Blender `(x,y,z)` переводятся в Godot `(x,z,-y)`. В disposable export остаются 54 bones; socket сохраняет identity local pose под chest, без отдельных авторских ключей высоты.

`MainCharacterV2` обновляет body transform, вызывает manual `AnimationPlayer.Advance(delta)`, затем `ApplyCameraCalibration()`. `Skeleton3D.GetBoneGlobalPose` синхронно разрешает dirty parent transforms; позиция текущего кадра вычисляется как `Skeleton.GlobalTransform * (socket.Origin + sharedOffset)`. Через `parent.ToLocal` она применяется существующей Player Camera3D. Socket basis не используется для camera rotation: yaw/pitch/effects остаются у прежних MouseLook parents. Aim читает ту же камеру; presentation process priority -10 предшествует weapon modules. Отдельного camera-height crossfade больше нет: высота следует действительному animation blend.

FOV вычисляется через Blender `view_frame(scene=...)` с sensor fit и pixel aspect. WORLD = **98° vertical**, VIEWMODEL = **65° vertical**. Сохраняются fit, aspect, near/far и offsets обеих камер. Ненулевой lens shift пока отклоняется. WORLD использует calibration FOV/near; Far остаётся игровым. VIEWMODEL остаётся data-only, старые procedural руки/ноги не включаются. Legacy FOV writer временно выключен при V2 ON; OFF восстанавливает transform/FOV/near/aspect/interpolation/writer.

Workflow: переместить `FP_Camera_Anchor`/камеру или изменить pose в PoseLab → `capture_v2.py` → `export_v2.py` → Godot import и перезагрузка сцены. Числа вручную не переносятся. Для будущих экспортируемых Actions socket наследует движение chest; отдельных camera Y по состояниям не требуется. Runtime пока переключает только Idle/Slide. `add_fp_camera_socket.py` — одноразовая миграция, не routine export; повторный запуск блокируется.

Backup перед миграцией: `.godot/humanoid-base/PoseLab_before_camera_socket_20260912_030445.blend`. Проверка migration JSON: drift исходных body poses = 0, drift камер Slide = 0, fingerprint всех Action keyframes неизменен. Snapshot для экспорта: `PoseLab_V2_source_20260912_030549.blend`. Высота WORLD относительно origin персонажа: **Idle 1,182461 м; Slide 0,672914 м; подъём 0,509547 м**.

`verify_v2.gd` проверил оба клипа и 54 joints: максимальное отклонение < 0,005 мм. `verify_v2_camera.gd` прошёл в настоящем Gym: Idle → реальный Slide → Idle, свободные yaw/pitch, locked body direction, aim ray, F10 с тем же Skeleton instance и V2 OFF/ON. В 65 render frames, включая 12 промежуточных высот crossfade, camera origin сверялся с независимой композицией текущих local bone poses — без frame lag. Ошибка проекций при 1280×720: Idle **0,0284 px**, Slide **0,0055 px**. Attachment bow не менялся; ошибка его origin < 0,004 мм.

Контрольные кадры: [standalone comparison](../Assets/Characters/BaseHumanoid/Review/v2_camera_comparison.html). Генерация: `review_v2_camera.py` (disposable Blender snapshot), `verify_v2_camera.gd` (runtime), `compose_v2_camera.py` (упаковка исходных кадров). Сборка — 0 ошибок/предупреждений. Сохраняются прежнее предупреждение ArrowTipMarker и renderer teardown `indexing did not unpair geometries from light` при закрытии теста. Ошибок камеры в прошедшем тесте нет.

Runtime files socket pass: `MainCharacterV2.cs`, `MainCharacterV2.Camera.cs`. Source PoseLab сохранён с helper/constraint; обновлены capture/export/verifiers, GLB, camera JSON, manifest и review. PlayerController, MouseLook, movement/slide physics, CyberBow attachment и исходный Humanoid_Base.blend в этом pass не менялись. Коммитов/push нет.
