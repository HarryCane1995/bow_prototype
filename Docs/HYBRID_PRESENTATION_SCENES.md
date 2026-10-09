# Hybrid presentation — две сцены

**20 September 2026:** this document describes the preserved V3 reference. Current default is [V4 split](SPLIT_PRESENTATION_V4.md): arms-only 1POV, no world legs in Slide, independent indexed Actions/exports and skeleton-independent gameplay camera. The former FP scene is retained as `LegacyHybrid1POV.tscn`.

18 сентября 2026. Presentation restructuring, GOOD ENOUGH. Без commit/push.

## 1. Созданные и изменённые файлы

Созданы:

- `Scenes/Characters/MainCharacter1POV.tscn` — FP canvas, отдельный viewport/world, camera, свет, upper-body skeleton/mesh slots, grip, настоящий CyberBow.
- `Scenes/Characters/MainCharacter3POV.tscn` — тонкая inherited scene существующего `MainCharacterV2.tscn`, полное тело.
- `Scripts/Player/Presentation/FirstPersonBodySource.cs` и `.uid` — небольшой editor/runtime адаптер существующего BH01 import.
- Этот отчёт.

Изменены:

- `Scenes/Characters/MainCharacterV3.tscn` — instance отдельной 1POV вместо процедурной сборки всех узлов.
- `Scenes/Player.tscn` — world instance теперь указывает на 3POV scene. Имя узла `MainCharacterV2` сохранено для совместимости путей.
- `Scripts/Player/Presentation/MainCharacterV3.FP.cs` — связывает готовые узлы FP scene, сохраняет прежние Inspector-поля, FP slots, wrist stabilization и read-only bow state; обновлена только FP-композиция.
- `Tools/Character/verify_v3_hybrid.gd` — проверяет новую структуру, jump/fall/landing и настоящий grapple.
- `Docs/MAIN_CHARACTER_V3_HYBRID.md` — отметка исторического POC; `Docs/blender_pipeline.md`, `AGENTS.md` — актуальная схема.

`MainCharacterV3.cs`, все файлы V2, gameplay/controller/modules/tuning/combat, исходные `.blend`, BH01 GLB, CyberBow art и pipeline экспорта в этом pass не редактировались.

## 2. 1POV scene

`res://Scenes/Characters/MainCharacter1POV.tscn`

```text
MainCharacter1POV (CanvasLayer)
  FPContainer / FPViewport (own World3D, transparent, no input)
    FPSpace
      FPViewCamera / WorldEnvironment / FPKey / FPFill
      FPPresentationBase
        FPDriftRoot
          FPUpperBody (FirstPersonBodySource)
            Skeleton3D
              TORSO
              ARMS
              FP_LeftHandGrip (hand.L)
                FP_CyberBow / CyberBow_ViewModel
            AnimationPlayer
```

HEAD и LEGS mesh nodes отсутствуют. Совместимые 54 joints сохранены для Skin/клипов: наличие head/leg joint names не добавляет геометрии. Адаптер берёт данные TORSO/ARMS по именам из BH01, не дублирует mesh assets на диске и не привязывается к нестабильным ID импортированных subresources. У FP свои Skeleton3D, AnimationPlayer и AnimationLibrary container; исходные Animation/Mesh/Skin resources читаются без изменений.

Сцену можно открыть отдельно в Godot: tool-адаптер заполняет явные mesh slots. Финальная runtime-калибровка/wrist stabilization и выбор state выполняются companion-контроллером внутри Player; gameplay-preview делать через Player/Gym. После BH01 export нужна перезагрузка сцены, как в V2.

Последующий узкий pass добавил общий additive `FPDriftRoot` с исходной sway-математикой: [FP_LEGACY_DRIFT_PORT.md](FP_LEGACY_DRIFT_PORT.md). Нейтральная композиция не изменилась; F4 выключает drift, weight 0 даёт прежнюю V3 1:1. Камера/свет остаются вне drift-ветки.

## 3. 3POV scene

`res://Scenes/Characters/MainCharacter3POV.tscn`

Наследует прежнюю V2 сцену: `Body/Skeleton3D/{HEAD,TORSO,ARMS,LEGS}`, AnimationPlayer и ExternalCamera. Full-body source целиком сохранён, вместе с world locomotion и aim. В Player instance по-прежнему называется `MainCharacterV2`, чтобы не переписывать существующие зависимости. Эта сцена использует Player-контекст для runtime, не создаёт второго physics/input owner.

## 4. Visibility/state logic

Использован вариант с раздельными mesh-группами существующего full body. `MainCharacterV3` — прежний маленький routing/mask companion.

| Представление | Слой | Обычный FP | Реальный Slide | F10 external |
|---|---:|---|---|---|
| FP torso + arms + bow | 19, отдельный World3D | да | да | нет |
| World HEAD/TORSO/ARMS/bow | 17 | нет | нет | да |
| World LEGS | 18 | нет | да | да |
| Legacy viewmodel | 20 | нет | нет | нет |

Проверяется фактический `CrouchSlideModule.IsSliding`, не Ctrl сам по себе. При выходе из slide lower-body слой сразу убирается. Полное тело существует и анимируется постоянно; его верх не включается в gameplay camera. FP canvas выключается только при external/V2/legacy fallback. Синхронный visibility-change signal V2 сохранён.

## 5. Обычный first-person

Idle/run/jump/fall/landing/wallrun/grapple используют основной FP upper-body слой. Torso сохранён в составе сцены, но в текущем кадрировании находится преимущественно ниже экрана; голова, ноги и world bow в обычный FP не попадают. Центр кадра свободен.

Только FP-композиция: существующая Idle-поза целиком наклонена на 35° и развёрнута на −15° относительно прежней ориентации; это transform visual root, не новая Action/IK/physics. Смещение относительно собственного Idle camera socket `(0.003062, -0.141082, -0.388422)`, FOV 65°, прежний FP bow scale 0.62. Это убирает шею/torso из центра и сохраняет руки/лук снизу. Gameplay camera, её FOV, mouse look и pre-IK cadence не изменены.

## 6. Slide

Тот же FP upper body остаётся виден, world camera дополнительно рисует настоящие LEGS из full-body scene с существующим `BH01_SLIDE` и locked world slide direction. При взгляде вниз ноги особенно заметны. FP overlay может перекрывать часть ног; видимость ноги зависит от реального направления взгляда. Procedural legacy legs не включаются.

Прежнее правило V3 сохранено: world torso turret/Slide 360 не применяется в hybrid slide. F11 возвращает старый V2 вместе с его Slide 360; поведение V2 не изменено этим pass.

## 7. Подключение Bow

В 1POV scene сохранён настоящий instance `cyber_bow_preview.glb` под `FP_LeftHandGrip` → `FP_CyberBow`. Никаких PNG, sprites или второго оружейного gameplay-контроллера.

Существующий world CyberBow остаётся под V2 hand.L и сохраняет свой возврат в legacy при F9. FP получает его калиброванный локальный attachment и состояния дочерних деталей/видимость стрелы. Глобальные transforms world hand/bow не копируются. FP wrist stabilizer и библиотека остаются независимыми. Shot/charge/projectile/RMB имеют прежних единственных владельцев и целятся по gameplay camera.

## 8. Что осталось от V2

Сохранены V2 scene/controller, locomotion routing, авторские Actions, camera/socket calibration, pre-IK порядок, aim IK, world bow attachment. F9 — legacy fallback; F10 — external full body; F11 — V2 true body / hybrid. Заменены только способ сборки FP-представления и ресурс world scene в Player. FP теперь содержит TORSO вместе с ARMS, а не только руки.

Сверка 132 существующих файлов из Scripts/Player, tuning, character source/export и Blender tools выявила только разрешённое изменение `MainCharacterV3.FP.cs`. Отдельно Player scene отличается от снимка начала pass одной заменой пути scene resource.

## 9. Проверка и оставшиеся шероховатости

- `dotnet build --no-restore`: 0 ошибок, 0 предупреждений.
- Короткий rendered smoke PASS: idle/run, slide/locked yaw/exit, jump/fall/landing, canonical wallrun Left/Right, LMB draw/release, RMB anticipation/melee, F9/F10/F11, отдельные scenes/skeleton/library, только TORSO+ARMS в FP и полный body в external.
- Настоящий grapple через InputEvent и стандартную `GrappleAnchor.tscn`: acquisition → launch, Shift не требуется. Два предварительных отказа были ошибками тестовой fixture (неверное action name, затем точка без collision area), исправлен только driver.
- Дополнительный короткий ready/aim check PASS: FP_RMB_ANTICIPATION → FP_BOW_READY → FP_BOW_DRAW_START → FP_BOW_FULL_DRAW; RMB aim соответствует camera forward при повороте yaw/pitch.
- 587 кадров одного итогового smoke без утечки world upper/body/bow в FP; временный FP-only ключ не меняет world hand или gameplay camera. Это контроль одного короткого запуска, не exhaustive QA.
- Визуально просмотрены обычный FP, slide/взгляд вниз, external и grapple. Torso больше не закрывает bow/reticle.

Остаются грубые mannequin meshes и placeholder Idle в отсутствующих FP_* slots. Правая рука/хват и полноценный draw/release требуют будущего FP animation-authoring; новых анимаций здесь нет. Torso ниже кадра, отдельного torso motion/pose набора нет. Тени скрытого world body отдельно не перерабатывались.

В логе остаётся прежнее предупреждение legacy sway об ArrowTipMarker. При завершении smoke Godot может печатать прежнюю renderer cleanup ошибку `indexing did not unpair geometries from light`; новых C# / scene-loading ошибок нет.

Артефакты: `.godot/hybrid-scenes/smoke.json`, `smoke.log`, `aim_ready.json`, `01_idle.png`, `03_slide.png`, `04b_slide_down.png`, `06_external.png`, `14_grapple.png`, `16_ready_aim.png`. Тестовые fixtures, камеры, clips и synthetic input существуют только во внешних драйверах.

## 10. Следующий шаг

Ручной просмотр Gym и принятие композиции. После него — отдельный небольшой FP authoring pass для хвата/ready/draw на уже выделенной 1POV ветке, сохраняя world BH01 Actions. Сейчас дальнейшего animation/art/gameplay pass не запускать.

Gym запускается обычной production-сценой fullscreen с настоящим input, без тестового драйвера. Commit/push не выполнялись.
