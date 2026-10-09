# Main Character V3 — Hybrid FP + 3P POC

> Исторический отчёт первого POC. Следующий restructuring pass заменил процедурную FP-ветку двумя явными сценами и добавил TORSO. Актуальная структура, composition и проверка: [HYBRID_PRESENTATION_SCENES.md](HYBRID_PRESENTATION_SCENES.md). Указанные ниже arms-only состав и старое смещение относятся к предыдущему состоянию.

18 сентября 2026. Presentation-only pass, без commit/push.

## Что сделано

`MainCharacterV3` подключён отдельной сценой к Player. Он управляет FP-представлением и render masks. Существующий `MainCharacterV2` остаётся world character: тот же skeleton, authored Actions, routing и gameplay camera. F11 переключает V2 TRUE BODY ↔ V3 HYBRID; F10 сохраняет переключение 1POV ↔ external. F9 сохраняет старый fallback и при повторном включении возвращает выбранный V2/V3 режим.

В V3 создан отдельный SubViewport с собственным World3D, прозрачным фоном, камерой 65° и освещением. FP skeleton — независимый экземпляр существующего BH_01; в нём оставлен только mesh `ARMS`. HEAD/TORSO/LEGS удалены из FP-экземпляра до первого рендера. 54 совместимых joint names сохранены для существующего skin и возможности подключать baked clips. Это не второй player и не физическое тело.

Legacy CanvasLayer, FirstPersonHands, procedural slide legs, sway/gait не используются V3. Они остаются только в явном F9 fallback. Новый FP viewport не получает gameplay input.

## Render layers

| Объект | Слой по умолчанию | V3 gameplay camera, обычный 1POV | V3 gameplay camera, Slide | F10 external | FP camera |
|---|---:|---|---|---|---|
| Окружение / враги | существующие 1–16 | да | да | да | нет |
| World HEAD / TORSO / ARMS / CyberBow | 17 | нет | нет | да | нет |
| World LEGS | 18 | нет | да | да | нет |
| FP ARMS / CyberBow | 19, отдельный World3D | нет | нет | нет | да |
| Legacy viewmodel | 20 | нет | нет | нет | нет |

В normal 1POV world body продолжает анимироваться, но камера его не рисует. При настоящем `CrouchSlideModule.IsSliding` добавляется только lower-body layer. Это те же world LEGS, которые видны в external, с `BH01_SLIDE` и сохранённым `SlideDirection`. Pelvis/lower-torso geometry отдельно не добавлялась.

World body не переключается целиком через `Visible` на каждом Slide. Head оставлен доступным external-камере; обычную камеру защищает mask. Canvas FP выключается целиком только для external/V2/fallback. Сигнал V2 о переключении режима синхронно обновляет masks: это устраняет однокадровый flash при F9, пришедшем после `_Process`.

## Камера и aim

Gameplay camera продолжает получать pre-IK `FP_CAMERA_SOCKET` world character. `MainCharacterV2.Camera.cs`, порядок animation → socket cache → aim → camera publication и MouseLook не изменялись.

При V3 Slide world upper body остаётся authored: V2 aim/turret pass пропускается. Вместе с turret отключается его вращающийся composition offset; используется обычный shared socket offset в осях world skeleton. Camera yaw/pitch остаются свободными. В V2 тот же Slide 360 включается обратно; реализация не удалена.

FP rig находится в camera-local пространстве своего viewport. Его калибровка один раз берётся из собственного Idle reference; world hand/torso и FP socket не управляют gameplay camera. Для POC используется простой wrist stabilizer: FP bow направлен по FP camera forward. Это однонаправленная визуальная зависимость; дополнительного camera writer нет.

`FpCompositionOffset`, `FpFov`, `FpBowScale`, `FpBlendSeconds` и wrist stabilization доступны в Inspector. Текущие FP cheats: смещение рук `(0.18, 0.02, -0.45)` относительно исходной композиции и масштаб FP-лука 0.62 вокруг grip. World bow и исходный art не масштабировались.

## Один gameplay bow, два изображения

WORLD CyberBow остаётся существующим subtree под world `hand.L`. FP CyberBow — копия только art subtree, без scripts/signals/groups и второго gameplay owner; он прикреплён к FP `hand.L`.

В FP копируются локальные состояния частей лука и видимость стрелы; global transforms world hand/bow не копируются. Single `PlayerBowShootModule`, `PlayerBowVisualModule` и RMB state остаются источниками charge/shot/arrow state. Projectile direction по-прежнему вычисляется по gameplay camera. Визуальное положение FP bow не определяет spawn/aim/damage.

## FP slots и дальнейший authoring

Mapping resource: `Resources/Presentation/V3FpAnimationSlots.tres`.

Подготовлены все 14 имён:

```text
FP_IDLE, FP_RUN, FP_SLIDE, FP_WALLRUN_LEFT, FP_WALLRUN_RIGHT
FP_RMB_ANTICIPATION, FP_MELEE, FP_PARRY
FP_BOW_READY, FP_BOW_DRAW_START, FP_BOW_FULL_DRAW
FP_BOW_RELEASE, FP_BOW_FOLLOW_THROUGH, FP_BOW_RECOVERY
```

Слоты читают фактический locomotion state, RMB RequestedAnimation и LMB draw/shot state. Отсутствующий FP clip безопасно использует `BH01_IDLE`; ни один слот не меняет gameplay timing. Это placeholders, финальных FP Actions/анимаций не создавалось.

У FP отдельные AnimationPlayer и AnimationLibrary container. `FpAnimationLibrary` принимает отдельную библиотеку baked FP clips с совместимыми bone names и путями вида `Skeleton3D:hand.L`; имена из mapping заменяют fallback. Этот путь проверен временным FP_IDLE key, который изменял только FP руку. `FpModelScene` позволяет позднее назначить отдельный совместимый FP export; его калибровочный fallback должен содержать текущий socket и имена костей.

Минимально рискованное решение для этого POC — не менять PoseLab вообще. Существующий `Humanoid_Male_PoseLab.blend` и pipeline `BH01_*` остаются world-authoring source. Когда начнётся ручное FP-authoring, делать отдельную копию PoseLab/Actions и экспортировать FP_* в отдельную библиотеку/asset, назначаемую V3. Текущие `capture_v2.py`/`export_v2.py` по-прежнему обслуживают выбранные BH01_*; данный pass не добавляет туда FP-prefix и не выдаёт placeholders за подготовленный отдельный Blender FP production rig.

## Проверка GOOD ENOUGH

- Read-only Blender Python audit: 26 Actions, 89 authoring bones, обе FP камеры; source не сохранялся и не менялся. Blender MCP не был подключён, использован отдельный фоновый Blender.
- Build: 0 ошибок, 0 предупреждений компилятора.
- Короткий runtime smoke: Idle/Run, реальные canonical wallrun Left/Right, Slide, yaw 180°, взгляд вниз, Slide exit, F10, F11 и F9 прошли.
- Переключение V2/V3 прямо во время Slide сохраняет V2 Slide 360 и authored torso в V3.
- LMB draw/release вызывает один ShotVisualSequence; RMB anticipation/melee выбирают FP slots. Gameplay charge duration остаётся 0.4 s из текущей Player scene.
- Временный FP-only ключ проверил независимость FP library/skeleton и camera origin от FP-анимации; world hand не изменился.
- Проверка masks после каждого отрисованного кадра короткого run не обнаружила world arms/head/bow в FP, второго bow или исчезновения FP при Slide.
- Сравнение с baseline: из 57 отслеженных существующих code/tuning файлов изменены только два разрешённых presentation-файла V2. Camera foundation, locomotion routing, movement, grapple, bow/RMB/projectile logic сохранены.

Артефакты: `.godot/v3-hybrid/smoke.json`, `smoke.log`, `01_idle.png`, `03_slide.png`, `04b_slide_down.png`, `06_external.png`, `07_v2.png`. Скрипт: `Tools/Character/verify_v3_hybrid.gd`. Он создаёт временные fixtures/клип только в памяти.

## Известные ограничения

- Руки — грубый mannequin Idle placeholder. Верх руки/срезы и правый хват требуют будущего FP-authoring; полноценного draw/release/melee/parry motion пока нет.
- Руки/Bow стабильны в screen-space, без gait/sway. При Slide их overlay может перекрывать часть настоящих ног; при взгляде вниз ноги читаются лучше.
- Отдельная библиотека FP предусмотрена, но новый Blender FP source/риг и exporter для него не создавались.
- World shadow flags сохранены. Отдельный shadows-only pass для полного скрытого тела не добавлялся; тени не являются проверенным критерием этого POC.
- В запуске остаётся прежнее предупреждение legacy sway об ArrowTipMarker. В конце автоматического smoke Godot также печатает известные renderer cleanup `indexing did not unpair geometries from light`; gameplay/C# исключений в run нет.

## Изменённые файлы

- `Scripts/Player/Presentation/MainCharacterV3.cs` — режимы, masks, visual ownership, routing FP slots.
- `Scripts/Player/Presentation/MainCharacterV3.FP.cs` — отдельный viewport/skeleton/bow, калибровка, wrist stabilization.
- `Scripts/Player/Presentation/V3FpAnimationSlots.cs` — mapping resource.
- `Resources/Presentation/V3FpAnimationSlots.tres`.
- `Scenes/Characters/MainCharacterV3.tscn`.
- `Scenes/Player.tscn` — одна дополнительная V3 instance.
- `Scripts/Player/Presentation/MainCharacterV2.cs` — read-only integration hooks и visibility-change signal.
- `Scripts/Player/Presentation/MainCharacterV2.Aim.cs` — выключение turret/upper-body aim только для V3 Slide.
- `Tools/Character/verify_v3_hybrid.gd` и новые Godot UID sidecars.
- `Docs/MAIN_CHARACTER_V3_HYBRID.md`, `Docs/blender_pipeline.md`, `AGENTS.md`.

World GLB, `.blend`, authored Actions, CyberBow art, geometry и gameplay не редактировались.
