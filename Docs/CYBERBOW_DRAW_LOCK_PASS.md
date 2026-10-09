# CyberBow: neutral → locomotion → draw lock

2026-09-06. Короткий второй pass; заменяет motion B из `CYBERBOW_MOTION_AUDIT.md`.

**Оси исправлены до настройки движения.** Проверены `BlenderAssets/Bow.blend`, `Bow_Assembly.blend` и фактический `cyber_bow_preview.glb`. У mesh Bow_Visual длинная ось — local Y, толщина — local Z; постоянный authored transform внутри GLB переводит их в scene X и scene Y. Local +Y декоративной стрелы после её authored transform направлен в scene −Z. Таким образом, импортированная сцена уже имеет нужный контракт: +X вправо, +Y вверх, −Z вперёд.

В shared Player убраны ручные yaw/pitch/roll и неравномерный scale на CyberBow_ViewModel. Новый `CyberBowAxisCorrection` заменяет `CyberBowViewModelOffset`: uniform scale **0.056**, rotation **0**, translation **0**. Дополнительный corrective rotation не нужен. Imported instance имеет identity transform. `BowViewModelHolder` задаёт только положение **(0, −0.32, −0.86) m**, с единичным scale и neutral rotation 0. Его существующий precision roll остаётся намеренной aim-анимацией. `ViewModelSwayRoot` добавляет camera-space framing **(0, 0, −0.12) m** и motion; постоянного декоративного roll больше нет.

| Состояние B | Видимое поведение |
| --- | --- |
| Idle / backward | Горизонтальный neutral |
| W | Вся связка опускается на 0.085 m; pitch/yaw/roll от W равны 0 |
| A / D | Roll +6° / −6°, соответствующее плечо опускается в сторону движения |
| W+A / W+D | Те же drop и roll складываются |
| Отпускание / A→D | Exponential smoothing 18/s, без oscillation |
| Начало draw | За 0.12 s smoothstep-переход к aiming pose, приподнятой на 0.025 m |
| Draw / charged / precision | Остаётся 2.5% locomotion и вторичного camera sway: максимум 0.15° strafe roll и 2.125 mm W-drop |
| Release / cancel | Возврат за 0.16 s к актуальному locomotion input |

Больше нет дополнительных B-слоёв vertical velocity, acceleration, speed setback, slide, wallrun lean и landing/release kick. Camera sway вторичен: максимум 2 mm / 0.25° до подавления draw. Один генератор позы и один writer SwayRoot. Старые export-поля сохранены в отдельной группе совместимости, но не участвуют в новой схеме.

Draw lock начинается по реальному visual drawing state, а не по full charge и не по прямой проверке ЛКМ. `IsDrawing` — новая read-only проекция уже существующего состояния BowVisual; `ResetDraw` сразу снимает lock при release/cancel. Shooting logic и timings не менялись.

Существующие руки сохранены. Перепривязаны wrist guides после исправления asset transforms, тетива закреплена на фактических концах mesh. Натяжение идёт вдоль Z на 0.18 m, без прежнего бокового/вертикального увода. Blender meshes/rig не редактировались. Это всё ещё blocking рук, не финальная анимация пальцев.

**Quick runtime:** просмотрены idle, W, A, D, WA, WD, A→D, отпускание движения, movement/strafe/jump + draw, release/cancel и precision. Отдельный InputEvent-прогон Gym прошёл до grapple launch за 46.03 s без recovery; wallrun и grapple при удерживаемом draw сохраняли lock. Просмотрены реальные Godot screenshots и последовательности переходов. Полный маршрут заново не перепроходился. Build: 0 errors / 0 warnings. `git diff --check`: PASS. Существующие предупреждения об отсутствующем ArrowTipMarker и camera interpolation остались; новых runtime errors нет.

**Файлы pass:**

- `Scenes/Player.tscn` — чистые transforms и обновлённые NodePaths.
- `Scripts/Player/ViewModel/ViewModelMotionPrototype.cs` — простая motion grammar.
- `Scripts/Player/ViewModel/FirstPersonHands.cs` — привязки существующих кистей/тетивы к исправленным осям.
- `Scripts/Player/Modules/PlayerBowVisualModule.cs` — read-only `IsDrawing`.
- `Scripts/Player/Modules/PlayerViewModelSwayModule.cs` — default path к переименованному asset pivot.
- `Docs/CYBERBOW_DRAW_LOCK_PASS.md` — этот отчёт.

Movement, wallrun, slide, grapple, projectile, damage, charge timing, camera sensitivity, gameplay FOV, tuning и геометрия не менялись. F8 сохранён: **B — новая grammar; A — legacy sway на той же исправленной геометрии**. Human-run logger, R/F1 и canonical wallrun B сохранены. Commit / push не выполнялись.
