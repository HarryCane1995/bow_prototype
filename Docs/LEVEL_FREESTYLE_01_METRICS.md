# Level_Freestyle_01 — current authoring snapshot

Дата: **2026-09-20**. Это чистый authoring canvas, без концепции, маршрута и переноса старого level design. Player/tuning/movement/combat в рамках этой задачи не изменялись. Main scene проекта не переназначена.

## Файлы и ownership

- Blender source: `Assets/Levels/Level_Freestyle_01/Source/Level_Freestyle_01.blend`.
- Рабочая геометрия: `Assets/Levels/Level_Freestyle_01/Exports/Level_Freestyle_01.glb`.
- Отдельный отключаемый kit: `Assets/Levels/Level_Freestyle_01/Exports/Level_Freestyle_01_DEV.glb`.
- Игровая сцена: `Scenes/Levels/Level_Freestyle_01.tscn`.
- Проверяемый снимок конфигурации, траектории и результаты: [metrics_snapshot.json](Reviews/LevelFreestyle01/metrics_snapshot.json).

Это явно запрошенный отдельный GLB workflow нового уровня. Старый `Level_01_Blockout.blend` продолжает использовать прямой импорт `.blend`; его pipeline, wrapper и Movement Gym не менялись. `Source/.gdignore` исключает двойной импорт authoring-файла. Generated GLB не редактировать вручную.

## Source of truth и метод

1. Реальный `Scenes/Player.tscn`, его `ActiveTuningProfile`, `Resources/Tuning/DefaultPlayerTuningProfile.tres` и defaults `Scripts/Player/Tuning/PlayerTuningProfile.cs`.
2. `PlayerJumpModule`, `PlayerCrouchSlideModule` + `InputGesture`, `PlayerWallRunModule`, `PlayerParkourIntentModule`, `PlayerSlingshotGrappleModule`.
3. Повторное измерение **в Level_Freestyle_01**, Godot 4.6.3 Mono / D3D12 Forward+ / Jolt / 60 physics ticks/s. Драйвер: `Tools/Levels/Freestyle01/verify_and_measure.gd`.
4. Для сравнения: `ASTRA_MOVEMENT_GYM_NOTES.md` от 2026-09-06, исходный внешний `measure_driver.gd` и `measure-plan.json` Gym.

Тест задаёт только начальную позицию/ориентацию case; далее физические InputEventKey / InputEventMouseButton проходят через настоящий Player и MoveAndSlide. Это автоматизированная проверка с кадрами, **не ручной playtest**. Дистанция считается от старта прыжка до первого `IsOnFloor`, а не до раннего `IsGrounded` от GroundCheck. Высота — подъём основания Player относительно старта. Выборка 60 Hz; поиск абсолютного максимума, всех FPS, углов и моментов второго прыжка не выполнялся.

Измерения зависят от timing и input. Для перечисленных jump/chain case W удерживается до посадки. Run-up — 30 ticks; slide перед прыжком — 5 ticks; air jump — после 18 ticks первого прыжка. Wall case: run-up 12 ticks, Shift удерживается, wall jump после 18 ticks, последующий air jump через 27 ticks. После grapple W не удерживается; anchor +10 m, по центру камеры. Пол ровный, landing на исходной высоте.

## Измерено в текущей сборке

Все строки ниже — **measured, 2026-09-20**, source: `metrics_snapshot.json / measurements` и указанный runtime-driver.

| Metric | Текущая выборка | Как использовать при blockout |
|---|---|---|
| Jump с места + W | **8.53 m**, пик **+2.42 m**, 0.683 s | Начинать с gap 5 m; 5–6 m требует проверки approach и ширины landing. Это не чисто вертикальный jump без W. |
| Running jump | **12.51 m**, пик **+2.42 m**, 0.683 s | Gap около 6 m оставляет большой запас. 12.51 m не гарантированная дистанция. |
| Running jump → air jump | **23.04 m**, пик **+5.60 m**, 1.20 s | Для начала 16–18 m с широкой посадкой; timing и redirect могут менять результат. |
| Slide → jump | **14.74 m**, пик **+2.42 m**, 0.683 s | Начинать с 10 m, затем пробовать 10–11 m. Не переносить старый measured maximum автоматически. |
| Canonical wallrun, обе стороны | **44.32 m** до пола, пик **+4.21 m**; 80 активных wall ticks | Для первого authored gap 20–24 m; стена должна заходить на approach/exit. Дуга снижается, постоянной высоты нет. |
| Jump → wallrun → wall jump | Полная chain **36.72 m**, пик **+10.51 m** | От самого wall-jump: ΔX≈−9.53, ΔZ≈−26.13 m, 1.217 s. Не путать длину chain с шириной разрыва между стенами. |
| Jump → wallrun → wall jump → air jump | Полная chain **42.64 m**, пик **+13.38 m** | После wall-jump: ΔX≈−7.77, ΔZ≈−32.59 m, 1.55 s. W-redirect уменьшает боковой перенос; широкая landing обязательна. |
| Grapple station 15 m по горизонтали | Camera→anchor **17.10 m**, pull 30 ticks; exit **39.77 m/s**; landing **55.47 m** от старта | Близкий высокий anchor даёт длинный перелёт. Оставлять большую площадку после точки. |
| Grapple station 30 m | Camera→anchor **30.94 m**, pull 46 ticks; exit **39.87 m/s**; landing **64.96 m** | Практичная средняя станция, не граница acquisition range. |
| Grapple station 45 m | Camera→anchor **45.52 m**, pull 64 ticks; exit **39.91 m/s**; landing **77.66 m** | Пример дальнего acquisition. Для обязательного перехода закладывать меньшую дистанцию и запас под LOS. |
| Grapple station 52 m | Camera→anchor **52.40 m**: acquisition отклонён | Радиус проверяется от камеры в 3D, а не только по горизонтали. |

Wallrun JSON keys `wallrun_left/right` обозначают сторону стартовой полосы относительно стены. Lane x=63.5 видит стену **справа**, x=66.5 — **слева**; `wall_side` записан в каждом sample.

Рекомендованные gaps — стартовые авторские ориентиры, а не сертифицированные safe distances. Нужно учитывать размер капсулы, floor snap, скорость подхода, высоту и ширину landing и выполнять собственные игровые проходы.

## Configured, не измеренная гарантированная дальность

Все строки: **configured, 2026-09-20**. Значения считаны из live Player; source property и применимые defaults сохранены в `metrics_snapshot.json / config`.

| Параметр | Значение | Source / интерпретация |
|---|---|---|
| Blender units / Godot scale | 1 unit = 1 m; unit scale 1 | Source units, identity ImportedLevel transform, Godot floor AABB 200 × 0.5 × 200 m проверен. |
| Human reference / standing capsule | 1.80 m; capsule diameter 0.90 m | `Scenes/Player.tscn`, CrouchSlide height. Нейтральный манекен высотой ровно 1.80 m, без копии character pipeline. |
| Crouched/slide capsule | 1.10 m | `PlayerCrouchSlideModule.CrouchingColliderHeight`; reference opening 1.25 m, запас 0.15 m. |
| Gravity | 9.8 × 5 = 49 m/s² | Project gravity × `PlayerJumpModule.GravityMultiplier`; jump 15 m/s. |
| Ground run | 18.3 m/s | `MoveSpeed`; Shift — contextual parkour intent, не sprint multiplier. |
| Air redirect | 27 m/s, vertical multiplier 1.15 | `DoubleJumpRedirectSpeed`, `DoubleJumpVelocityMultiplier`. |
| Slide entry / duration | 40 m/s / 0.98 s | `SlideInitialSpeed`, `SlideDuration`; скорость меняется после переходов. |
| Slide-jump horizontal cap | 35 m/s | `SlideJumpMaxHorizontalSpeed`; не постоянная скорость всей дуги. |
| Wallrun target / max timer | 33 m/s / 1.4 s | Target может сохранять более быстрый вход; canonical entry up 9.75 m/s, blend 0.10 s. |
| Wall jump impulse | away 24.4, up 27.1, forward 28.2 m/s | Tuning; общий clamp 55.5 m/s. |
| Grapple acquisition | 50 m | `MaxGrappleDistance`; вместе с camera aim, LOS и screen assist, не свободная сфера захвата. |
| Grapple pull / launch caps | 50 / 40 m/s | `MaxPullSpeed`, `MaxLaunchVelocity`. Launch измеряется при Launching→Cooldown. |
| Post-launch control delay | 0.73 s | Scene override `PlayerSlingshotGrappleModule`; нельзя проектировать landing под немедленный полный air control. |

## Расхождения с Gym 2026-09-06

- Rest/run/double и высоты совпали в округлении. Grapple landing 55.5 / 64.9 / 77.6 m также воспроизведены близко к старой выборке.
- Slide-jump: старое **15.73 m**, сейчас **14.74 m**. Current guide использует 14.74 m. Старый driver подавал InputEventAction, новый — физический Ctrl; с тех пор изменились gesture semantics. Точная причинная доля каждого изменения здесь не исследовалась.
- Wallrun: старое около **44.9 m**, текущий полный jump→floor **44.32 m**. Пик +4.21 m и 80 wall ticks воспроизведены.
- Старые wall-jump X/Z приведены после wall jump и с иным отпусканием W. Новые полные chain ranges 36.72/42.64 m имеют другой endpoint origin; выше отдельно даны смещения после wall jump. Нельзя считать разницу доказанным изменением tuning.
- Current canonical wallrun требует Shift. Ctrl удерживается как один consumed gesture: новый slide требует RELEASE→PRESS. На текущем исходнике это проверено, старую логику в уровень не переносили.

## Guides и DEV reference

В `.blend`: `LEVEL_GEO`, `COLLISION_GUIDES`, `DEV_METRICS`, `GAMEPLAY_MARKERS`, `GRAPPLE_GUIDES`, `LIGHTING_GUIDES`, `NOTES_HELPERS`, `DEV_MECHANICS_REFERENCE`.

`DEV_METRICS`: rulers **1/2/5/10/20/50 m**, human 1.80 m и wire standing capsule; семь записанных movement arcs с endpoints; configured speed bars **18.3/27/33/35/40/50 m/s** (длина бара = путь за 1 s при постоянной скорости). `GRAPPLE_GUIDES`: три записанных grapple arcs, launch markers, 15/30/45 m stations и заметка о 50 m acquisition. Все guides — без collision/trigger, исключены export whitelist и дополнительно имеют `-noimp`. Они остаются только authoring reference в Blender.

Основной пол 200 × 200 m, top Z=0. Spawn (0,0,0.05) Blender → (0,0.05,0) Godot. DEV kit сбоку, на востоке: обычная стена 60 × 18 m, два поднятых на 3 m блока с gap 6 m (основной пол ловит падение), препятствие 0.8 m, slide-перемычка 1.25 m, window-like opening с sill 0.7 m и просветом 1.8 m, wedge 1:5 / 11.31°, три canonical anchors. Это независимые reference primitives, не Movement Gym route. Slope показывает обычную работу CharacterBody на наклоне; отдельного slope-specific slide acceleration в текущем модуле не найдено.

F3 отключает **видимость, collision layers/masks, Area monitoring и membership `grapple_anchor`** всего kit. Он не оставляет невидимые препятствия или доступные anchor targets. Toggle проверен в idle; выключение kit посреди активного grapple не является проверенным сценарием.

## Canonical Player, nodes и управление

Scene instances **`res://Scenes/Player.tscn`** без overrides tuning/logic. Он подтягивает ground/run/jump/air jump, slide/slide-jump и Ctrl gesture fix, Shift parkour, canonical wallrun/wall-jump, slingshot grapple, Bow/projectiles, RMB foundation, camera, audio и presentation toggles.

К моменту финальной проверки canonical Player уже содержит **MainCharacterV4 split** с `MainCharacter1POV.tscn` / `MainCharacter3POV.tscn`. Во время работы параллельный character pass обновлял эти shared dependencies; уровень получил их через ту же ссылку. Локальной копии Player или character branch здесь нет.

Level-specific nodes: `ImportedLevel/SourceGeometry`, отключаемый `DEV_MECHANICS_REFERENCE`, `PlayerSpawn`, существующий `ImportedLevelMarkerBinder` + контейнер canonical `GrappleAnchor.tscn`, нейтральные light/environment, существующие CrosshairUI/SpeedometerHud, небольшой `FreestyleAuthoring.gd` для F3/F5 и read-only state/coordinates/aim-distance. Дальность HUD берётся у anchor с canonical selection highlight, новый target-selection алгоритм не создавался. Environment повторяет sky/ambient/SSAO Level_01 без геометрии, art, fog planes или skyline.

| Hotkey | Действие |
|---|---|
| WASD / Space / Ctrl / Shift / E | Canonical movement, jump/air jump, crouch/slide, parkour, grapple |
| LMB / RMB tap / RMB hold | Shot / melee foundation / logical power-shot foundation |
| F1 | Existing current-scene reload; восстановление после падения с края |
| F3 / F5 | DEV kit полностью off/on / authoring readout off/on |
| F4 / F10 | Current FP drift / external 3POV |
| **F12** | Current V4 split ↔ V3 reference; используется exported `ToggleSplitKey` |
| F11 / F9 | В V3 reference: V2 / legacy fallback |
| F6 / F7 | Existing audio panel / mute; V4 split больше не занимает F6 |

RMB power shot остаётся текущим **logical stub**; этот level не добавляет projectile/damage реализацию. Enemy combat targets сюда не переносились.

## Blender → Godot iteration

1. Работать в `LEVEL_BLOCKOUT`. Новый static mesh помещать в `LEVEL_GEO`, visual+collision назвать `Name-col`. Для отдельного простого collider: `Name_COL-colonly` в **LEVEL_GEO**; `COLLISION_GUIDES` является неэкспортируемой reference collection. Новый gameplay marker `PlayerSpawn` или `GrappleAnchor_<name>` — empty в `GAMEPLAY_MARKERS`; не ставить `-noimp` на настоящие markers.
2. В Object Mode: **N → Freestyle → Save + Export to Godot**. Экспортируется только whitelist: LEVEL_GEO + GAMEPLAY_MARKERS в основной GLB и DEV_MECHANICS_REFERENCE во второй. Скрытые collections/objects временно включаются только на экспорт, visibility/selection восстанавливаются.
3. Вернуться в Godot, дождаться reimport, открыть `Level_Freestyle_01.tscn`, **F6** запускает текущую сцену из редактора. Main scene остаётся Level_01. Standalone runtime не hot-reloads mesh: остановить и запустить заново.

Панель — session-only Python registration, без установки add-on или изменения trust/security. При обычном повторном открытии `.blend` выполнить встроенный Text `FREESTYLE_TOOLS.py` через Alt+P, либо запустить Blender с `--python Tools/Levels/Freestyle01/session_tools.py`. Рабочие файлы и export destinations определяются относительно repository, пользовательских абсолютных asset paths нет.

```powershell
blender --background Assets/Levels/Level_Freestyle_01/Source/Level_Freestyle_01.blend --python Tools/Levels/Freestyle01/export_level.py
godot --headless --editor --path . --import --quit
godot --path . res://Scenes/Levels/Level_Freestyle_01.tscn
```

В Blender: metric units, grid presets **0.25/0.5/1 m**, increment snap + absolute grid, snapping изначально OFF. **Shift+Tab** включает snap, **Ctrl** временно включает при трансформации, **N** открывает sidebar. Perspective grid адаптируется к zoom; для гарантированного точного шага использовать **G → X/Y/Z → 0.25 / 0.5 / 1**, а не полагаться на крупность видимой сетки. Geometry к grid автоматически не принуждается. Outliner содержит eye/viewport/render toggles.

Обычные wallrun surfaces: imported static geometry на physics layer 1, Player wall mask all layers; специальных тегов/материалов не требуется. Геометрия всё равно проходит canonical normal/intent/speed/air-state checks. Не объявлять любую наклонную грань пригодной для wallrun только по mask.

## Проверка и границы

- Build: `dotnet build Bow_prototype.sln --no-restore`, 0 errors / 0 warnings. Import и scale/collision/marker checks выполнены в новой сцене. Production GLB содержит только floor + spawn; helpers не импортируются.
- Измерительные cases: rest/run/air/slide-jump, wallrun с двух сторон, wall-jump/air extension, 15/30/45 m grapple launch+landing и отказ за range.
- Финальный отдельный sanity run: **43 assertions PASS** — spawn, один Player, три anchors, отсутствие guides, scale, F3 collision/group toggle, F5, current 1POV/3POV, V4/V3/V2/legacy toggles, projectile, RMB parry window/tap/hold/release, slide→jump, удержанный consumed Ctrl без re-entry, намеренный RELEASE→PRESS, Shift acquisition/release.
- В раннем общем прогоне поздний Shift case после цепочки других cases не вошёл в wallrun. В отдельном sanity run он прошёл; raw history сохранена в snapshot. Это не доказательство отсутствия всех transition bugs. В ходе тестов исправлены только тестовые предположения о F6/F12 и точке измерения landing/launch, production gameplay не менялся.
- Повторное уничтожение presentation scenes в ранней версии harness вызывало Mono `gchandle.is_released`. Драйвер теперь переиспользует одну живую сцену и дожидается окончания timers перед новым setup. Финальный sanity завершился с code 0. Character/engine исправления вне scope.
- Existing warning про отсутствующий legacy ArrowTipMarker сохраняется. Audio входит через canonical Player, но субъективное прослушивание всех sounds и ручная оценка presentation/game feel не заявляются. Падение с края восстанавливается F1; новый death/checkpoint framework не создавался.
- При дальнейших изменениях tuning guides автоматически не пересчитываются: запустить verifier, проверить новый snapshot, обновить только metric-owned guides через `update_metric_guides.py`. Это осознанно датированный снимок.

## Изменённые файлы этой задачи

Только новые `Assets/Levels/Level_Freestyle_01/**`, `Scenes/Levels/Level_Freestyle_01.tscn`, `Scripts/Levels/FreestyleAuthoring.gd` (+ Godot UID), `Tools/Levels/Freestyle01/**`, этот документ и `Docs/Reviews/LevelFreestyle01/**`. Import sidecars генерирует Godot. `.blend1` — локальная backup-копия нового source. Старые Level_01/Movement Gym, project.godot и tuning совпадают с исходными SHA-256. Concurrent character changes не откатывались и не присваиваются этой задаче. Commit/push не выполнялись.
