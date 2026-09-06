# ASTRA GAMEPLAY AUDIT — BowPrototype

Дата: 2026-09-06. Репозиторий: `C:\Users\harry\Documents\bow_prototype`, ветка `main`, исходный HEAD `c00ba64`. До работы `git status --short` был пустым. В открытом редакторе была несохранённая вкладка `[unsaved](*)`; она не сохранялась и не изменялась.

## Метод и границы доказательств

Изучены AGENTS.md, Docs/CODEX_RULES.md, документы движения, ability arbitration, grapple, стрельбы и viewmodel, shared Player.tscn, оба level wrapper, C# модули движения, прыжка, crouch/slide, wallrun, grapple, look/FOV, bow, projectile, marker binder и HUD/tuning UI.

Godot **4.6.3 Mono**, D3D12 / Forward+, Jolt, 60 physics ticks/s. Сначала выполнены `dotnet build --no-restore` и обычный запуск сохранённой main scene с изображением на экране. Дальнейшие проходы выполнены **в запущенной графической игре**, через внешний GDScript SceneTree-драйвер с InputEventAction/InputEventKey/InputEventMouseMotion, реальными C# модулями и MoveAndSlide. Это автоматизированный gameplay playtest с осмотром кадров и телеметрии, а не утверждение о ручной игре с непрерывным удержанием клавиш через Computer Use: его API даёт короткие нажатия, которых недостаточно для точных комбинаций.

Драйвер находится вне репозитория, в `C:\Users\harry\Documents\Codex\2026-09-06\files-pasted-by-the-user-gameplay\work`. Он записывает каждый physics tick: позицию, velocity, контакты, grounded, wallrun/cooldown, slide, grapple и ability locks. Для отдельных cases драйвер ставит игрока в явно указанную исходную точку и направляет взгляд; после этого механика запускается обычным вводом. Установка позиции — только подготовка теста, не доказательство достижимости маршрута. Геометрия, ресурсы и tuning при этом не меняются. Для удобства наблюдения только в этих процессах выключен startup fullscreen.

В trace запись на границе новой команды может ещё содержать состояние предыдущего physics tick; сравнения выполняются по последующим кадрам. Ошибка чтения частично заменённого command.json и один null CurrentScene во внешнем драйвере при F1 — ошибки инструмента ревизии, **не баги игры**. Перед проверкой исправлений драйвер защищён от null, команды заменяются атомарно.

Не проверен весь мировой объём CyberCity, все Blender mesh seams, все варианты коллизий потолка, бой с активным AI на legacy playground и поведение на всех FPS/physics rates. Нет основания называть проект полностью свободным от багов.

## Обнаруженные механики

- WASD: ground/air acceleration, deceleration, counter-strafe. Отдельного sprint action нет.
- Space: jump, coyote time, один air jump, camera/input redirect; grapple и wallrun восстанавливают air jump.
- Ctrl/C: crouch, slide, воздушный буфер входа на приземлении, slide jump с carry/boost и cap, проверка места над головой.
- Wallrun: автоматический вход по боковому raycast и скорости; wall jump, общий и same-wall cooldown, отдельный CameraEffectsPivot для roll/pitch.
- E: одно нажатие запускает slingshot pull, затем автоматический launch и cooldown. Отпускание E не является предусмотренной ручной отменой.
- ЛКМ: лёгкий и charged ballistic shot; Alt + новое нажатие ЛКМ: precision straight shot. Стрелы не наследуют скорость игрока.
- FOV: базовый, precision, speed bonus, wallrun bonus; независимый viewmodel viewport/sway.
- Esc освобождает курсор, ЛКМ захватывает его, F1 reload; F2 runtime tuning.
- Арбитраж: slide 30, wallrun 40, grapple pull 60 / launch 65. Обычное движение уступает владельцам каналов.
- Общего player health/death/OOB respawn нет. В `EnemyProjectile` есть отдельный `ReloadSceneOnPlayerHit`; это не обработчик падения за карту. `Death` в arbitration зарезервирован.

## Журнал проходов до исправления

| Pass | Содержание | Непосредственный результат |
|---|---|---|
| A — normal | Spawn, run, jump, double redirect, third jump, landing, slide → jump | Run 18.3 m/s; jump Y=15; air jump Y=17.25; третьего импульса нет. Slide начинается с 40 m/s. После приземления locks пусты. |
| B — movement | Wallrun, wall jump, восстановленный air jump; grapple с ближайшей к spawn точки, spam E/Space/C при pull, launch/landing | Wallrun ~33 m/s; wall jump Y=27.1; grapple достигает 50 m/s pull и завершает цикл. Повторная активация во время pull не перезапускает способность. |
| C — abuse | Разворот после wall jump; wallrun → hook; выход за границу пола | Обход same-wall cooldown подтверждён; grapple забирает управление, wallrun завершён с `arbitration`; за пределами пола продолжается падение. |
| D — reproduce / collision | Независимый повтор exploit после reload; нижний anchor рядом с геометрией; slide с прижимом к стене | Exploit повторён; нижний grapple завершён; slide не оставил stuck state после остановки. |
| E — bow / reload / CyberCity | Light/charged/precision, отмена draw через Esc, F1; запуск второго уровня и движение со spawn | Стрелы 50.5/100/177 m/s, damage 8/24/60, ballistic/ballistic/straight; после Esc новая стрела не создана; F1 восстановил main scene. CyberCity запускается отдельно, падение вне временной платформы не восстанавливает игрока. |
| F — CyberCity edges | Wallrun → hook на временной стене; закрытый стеной anchor; зацеп совсем близко | Переход выполнен, закрытый anchor не активируется, близкий grapple проходит Launch/Cooldown/Idle. Выход за платформу отдельно от успешного завершения grapple. |
| G — верхняя кромка | Зацеп над верхней гранью TEMP_WallRunWall с Y=7.9 | Капсула вышла через кромку, grapple завершился; stuck не подтверждён этим case. |
| H + H-repeat — blocked pull | Та же стена, старт Y=7.0; повтор после reload | Потеря управления и колебания у стены. H удерживал Pulling 2003 ticks / 33.38 s до самопроизвольного выхода; в повторе всё фиксированное окно 6 s осталось Pulling. Это длительный stuck, не доказательство бесконечного зависания. |

## A. CONFIRMED BUGS

### BP-001 — Same-wall cooldown обходится сменой стороны камеры

- **SEVERITY:** Medium.
- **CONFIDENCE:** Confirmed.
- **REPRODUCTION:** Level_01; исходная позиция `(-35.6,-0.70,-76)`, yaw 180°, рядом с восточной гранью `L01_Arena01_TestBuilding_04_COL`. Дать осесть 45 ticks; W 12 ticks; Space 1 tick и отпустить на 12 ticks; Space для wall jump, отпустить на 6 ticks; развернуться на 180° (yaw 0), W+A+Space 1 tick для redirect обратно к стене; отпустить Space, W+A 12 ticks; отпустить A, продолжить W 20 ticks. Точный ввод сохранён в `pass-c.json` и независимом повторе `pass-d.json`.
- **EXPECTED:** та же поверхность с normal `(1,0,0)` не допускает повторный wallrun до истечения `SameWallReattachCooldown=2.0`; обычный air control и air jump остаются доступны.
- **ACTUAL:** новый wallrun `side=Left` начинается через **12 ticks / 0.20 s** после wall jump; прежний был `side=Right`. В момент входа `sameCooldown=1.80`, горизонтальная скорость снова 33 m/s; вход восстанавливает air jump.
- **EVIDENCE:** `trace.jsonl`: pass C, wall jump frame 13068, повторный вход 13080; pass D: 16994 → 17006. Оба входа normal `(1,0,0)`. Кадры `C4_same_wall.png`, `D4_same_wall_repeat.png`; engine log содержит Right enter → wall_jump → Left enter.
- **LIKELY ROOT CAUSE (зафиксирована ДО изменения):** `IsSameWallOnCooldown` требует `hit.Side == _lastWallSide`. `Side` вычисляется относительно поворота игрока и меняется при yaw 180°, хотя мировая нормаль и поверхность остаются теми же. Поэтому ненулевой cooldown не применяется.
- **FILES / NODES INVOLVED:** `Scripts/Player/Modules/PlayerWallRunModule.cs`, `Player/PlayerWallRunModule`, `Resources/Tuning/DefaultPlayerTuningProfile.tres`, указанная импортированная стена Level_01.
- **FIX RECOMMENDATION:** убрать зависимость same-wall cooldown от camera-relative Side, сохранив текущую проверку normal, duration и все movement параметры. Это не меняет направление/скорость штатного wallrun или wall jump.
- **FIX RESULT:** FIXED + VERIFIED. В V1 и V3 в том же окне возврата C3/C4 — 0 wallrun ticks вместо 34 до правки. Обычный B2 wallrun, B3 wall jump и B6/B7 grapple сохранили покадровые position/velocity. Удалены только camera-relative Side из проверки cooldown и больше не нужное private поле; прежняя проверка world normal сохранена.

### BP-004 — Grapple удерживает игрока у преграды без восстановления управления

- **SEVERITY:** High.
- **CONFIDENCE:** Confirmed.
- **REPRODUCTION:** CyberCity, существующая `TEMP_WallRunWall_COL` (X=4.5..5.5, Y=0..8, Z=-11..3), anchor `(0,7,-8)`. Подготовить игрока в `(6.2,7.0,-5)`, взгляд точно на anchor; через 1 physics tick нажать E на 1 tick и отпустить. Ждать 240 ticks, попробовать Space/E/D, ждать ещё 240 ticks. Независимый H-repeat: та же подготовка после reload, E, ждать 360 ticks. Позиция задана отладочным драйвером; полный маршрут достижения этой точки с земли не был сыгран.
- **EXPECTED:** блокировка пути капсулы не должна десятки секунд отнимать движение/прыжок. Неуспешный pull должен использовать уже существующий CancelGrapple/cooldown и освободить ability locks.
- **ACTUAL:** камера видит anchor поверх стены, капсула упирается сбоку. Игрок колеблется примерно X=5.951, Y около 7, Z=-5..-11; остаётся Pulling, movement и jump блокируются. В H — 33.38 s; в независимом 6-секундном окне H-repeat — всё ещё Pulling. Пытаться выйти игровым вводом не помогло.
- **EVIDENCE:** `trace-baseline-extra.jsonl`, id=9, pull frames 22134..24136; контакт `/root/Level_CyberCity/ImportedLevel/TEMP_WallRunWall_COL`, normal `(1,0,0)`; все 360 ticks H-repeat остаются state=1 / SlingshotGrapplePull. `H4_escape_result.png`, `Hrepeat_stuck.png`.
- **LIKELY ROOT CAUSE (зафиксирована ДО изменения grapple):** выбор target проверяет ray из камеры, а движение использует капсулу и origin игрока. `UpdatePulling` выходит только при arrive distance или пересечении плоскости anchor, которые здесь недоступны из-за стены. Tangential velocity колеблется, таймера отсутствия продвижения при блокирующей коллизии нет; CancelGrapple не привязан к игровому вводу.
- **FILES / NODES INVOLVED:** `PlayerSlingshotGrappleModule.cs` (`TryFindGrappleAnchor`, `UpdatePulling`, `CancelGrapple`), `PlayerController._PhysicsProcess`, временная стена и anchor CyberCity.
- **FIX RECOMMENDATION:** локальная защита только для длительной блокирующей коллизии без нового сближения с целью. Использовать существующий CancelGrapple/cooldown; не менять pull acceleration, силы launch, camera snap, arrival distance или штатные переходы. Порог ожидания и минимального продвижения экспортировать в Inspector.
- **FIX RESULT:** FIXED + VERIFIED. После нового запуска V2 и независимого V3 исходный case держит Pulling 138 ticks / 2.30 s, затем Cancel → Cooldown с пустыми locks → Idle. Добавлены Inspector-поля BlockedPullTimeout=2 s и BlockedPullMinProgress=0.05 m; timeout=0 отключает защиту. Таймер идёт только при контакте, направленном против pull, без нового сближения; продвижение либо отсутствие препятствия его сбрасывают. Свободный pull, launch, arrival и camera snap не изменены.

## B. POSSIBLE BUGS / NEED HUMAN DESIGN DECISION

### BP-002 — Нет восстановления после падения за уровень

- **SEVERITY:** High.
- **CONFIDENCE:** Confirmed (поведение); статус «недостающая механика или дефект» требует решения дизайнера.
- **REPRODUCTION:** Level_01, точка `(165,-0.70,100)`, yaw -90°; W 150 ticks, отпустить, ждать 240 ticks. Пол оканчивается около X=172.67. В CyberCity достаточно сойти с TEMP_SpawnPlatform за Z=-12.
- **EXPECTED:** для игрового маршрута нужно определить смерть, checkpoint или reload; в существующем коде такого контракта нет.
- **ACTUAL:** Y падает ниже -880 уже к концу фиксированного case C6, движение вниз продолжается; способность не заблокирована, вернуть сцену можно F1.
- **EVIDENCE:** C6 trace и `C6_no_respawn.png`, проходы E/F по CyberCity, marker binder пишет отсутствие KillPlane, поиск player death/OOB handler не находит его.
- **LIKELY ROOT CAUSE:** отсутствуют OOB/death/checkpoint logic; KillPlane/FinishTrigger в binder только распознаются и логируются, триггеры не создаются.
- **FILES / NODES INVOLVED:** `PlayerController.cs`, `ImportedLevelMarkerBinder.cs`, `Gameplay/Triggers`, оба wrapper; `EnemyProjectile.cs` имеет отдельный reload-on-hit.
- **FIX RECOMMENDATION:** сначала определить границы каждого уровня и способ восстановления; затем отдельный scoped handler. Нельзя выбирать произвольный KillY для двух разных карт.
- **FIX RESULT:** NOT FIXED — новое правило игры не вводилось.

### BP-003 — Визуальный charged draw остаётся на скрытом старом луке

- **SEVERITY:** Low.
- **CONFIDENCE:** High confidence.
- **REPRODUCTION:** удерживать ЛКМ >0.4 s, наблюдать видимый CyberBow, отпустить; сравнить precision (Alt), где поворот holder виден.
- **EXPECTED:** если CyberBow должен поддерживать текущую Draw-анимацию, видимый лук должен показывать натяжение. Для статического preview ассета это может быть намеренной незавершённостью.
- **ACTUAL:** charged projectile создаётся (100 m/s, damage 24), видимый CyberBow не показывает старое натяжение; precision holder поворачивается.
- **EVIDENCE:** `E2_charged_draw.png`, `E3_precision.png`; runtime tree имеет AnimationPlayer только под `Bow_ViewModel`, а этот root `visible=false`; у CyberBow AnimationPlayer отсутствует.
- **LIKELY ROOT CAUSE:** `PlayerBowVisualModule.AnimationPlayerPath` указывает на старую скрытую модель, новая `cyber_bow_preview.glb` не содержит равнозначного animation rig.
- **FILES / NODES INVOLVED:** `Scenes/Player.tscn:107`, `PlayerBowVisualModule.cs`, обе модели в `Assets/Models/Bow`.
- **FIX RECOMMENDATION:** подтвердить назначение preview; если это финальный визуал, подготовить rig/animation в источнике. Не подменять это новым процедурным визуалом в рамках bug revision.
- **FIX RESULT:** NOT FIXED — нужен выбор визуального контракта.

## C. GAMEPLAY OBSERVATIONS

### OBS-001 — Высокие скорости и активное торможение

**SEVERITY:** Observation. **CONFIDENCE:** Confirmed. **REPRODUCTION:** A/B — бег, slide jump, отпускание ввода после launch. **EXPECTED / ACTUAL:** текущий профиль задаёт 18.3 run, 40 slide, 33 wallrun, air acceleration 33; `MoveToward` уменьшает повышенную скорость в сторону MoveSpeed. Поведение стабильно. **EVIDENCE:** trace + профиль. **LIKELY ROOT CAUSE:** намеренные tuning values и явная логика response. **FILES / NODES:** Movement/Jump/CrouchSlide/Grapple modules, default profile. **FIX RECOMMENDATION:** не менять без отдельной задачи на game feel. **FIX RESULT:** NOT FIXED (изменение не требуется).

### OBS-002 — Приоритет wallrun не означает автоматический вход из активного slide

**SEVERITY:** Observation. **CONFIDENCE:** High confidence. **REPRODUCTION:** предмет проверки — активный slide со сходом с края возле боковой стены; полный такой переход в текущих проходах не воспроизведён. **EXPECTED:** уточнить, должен ли wallrun прерывать slide. **ACTUAL / EVIDENCE:** `CanAttemptWallRun` требует свободный HorizontalVelocity, а slide его держит; документы одновременно описывают более высокий приоритет wallrun и требование свободных каналов. **LIKELY ROOT CAUSE:** CanStart проверяет занятость каналов, а не численный приоритет будущего request. **FILES / NODES:** WallRunModule, AbilityStateModule, Docs/PLAYER_MOVEMENT.md. **FIX RECOMMENDATION:** решить правило перехода и затем воспроизвести на маршруте; автоматическая правка могла бы изменить slide feel. **FIX RESULT:** NOT FIXED.

### OBS-003 — Отпускание E не отменяет pull

**SEVERITY:** Observation. **CONFIDENCE:** Confirmed. **REPRODUCTION:** B6: E на 1 tick, отпустить. **EXPECTED / ACTUAL:** pull → launch продолжается автоматически. **EVIDENCE:** B6/B7 trace; ввод проверяет только JustPressed. **LIKELY ROOT CAUSE:** slingshot по зафиксированной геометрии, не удерживаемая верёвка. **FILES / NODES:** SlingshotGrappleModule, Docs/SLINGSHOT_GRAPPLE.md. **FIX RECOMMENDATION:** сохранить; ручная отмена — отдельное design decision. **FIX RESULT:** NOT FIXED (изменение не требуется).

## D. POSSIBLE EXPLOITS

- **BP-001:** подтверждённый cooldown bypass с дополнительным air-jump reset; запись и root cause находятся в A. Бесконечный цикл набора высоты отдельно не доказан: не выдаётся за подтверждённый exploit.
- Rapid E во время pull не создаёт второго grapple в проверенном случае. Третий jump без landing/wallrun/grapple не сработал. Не обнаружены NaN, бесконечное горизонтальное ускорение или зависший Slide в выполненных проходах.

## E. TECHNICAL / GODOT ISSUES

### TECH-001 — Включённая aim stabilization не имеет ArrowTipMarker

- **SEVERITY:** Low.
- **CONFIDENCE:** Confirmed.
- **REPRODUCTION:** обычный запуск Level_01 или CyberCity с текущим Player.tscn.
- **EXPECTED:** при включённой AimStabilization найдены ViewModelCamera3D и marker наконечника.
- **ACTUAL:** предупреждение `aim stabilization is disabled because ViewModelCamera3D or ArrowTipMarker was not found`; слой не работает.
- **EVIDENCE:** предупреждение обычного запуска `baseline-native.log`, воспроизводится при reload и во второй карте; в runtime tree есть нужная камера и CyberBow/Arrow_Visual, но **нет ни одного ArrowTipMarker**.
- **LIKELY ROOT CAUSE:** `Scenes/Player.tscn:120` ссылается на отсутствующий child внутри preview-модели; fallback-поиск тоже не находит marker.
- **FILES / NODES INVOLVED:** `PlayerViewModelSwayModule.Initialize/ShouldApplyAimStabilization`, Player.tscn, `CyberBow_ViewModel/Arrow_Visual`, `cyber_bow_preview.glb`.
- **FIX RECOMMENDATION:** восстановить корректный marker на реальном кончике стрелы в утверждённом visual pipeline, затем отдельно проверить включившуюся стабилизацию. Это изменит текущее визуальное поведение, поэтому в данной ревизии правка не выбрана.
- **FIX RESULT:** NOT FIXED — подтверждённая техническая неисправность, оставлена явно.

### TECH-002 — Предупреждения Camera3D physics interpolation

**SEVERITY:** Low. **CONFIDENCE:** Suspected (влияние на gameplay). **REPRODUCTION:** двигаться / менять look в графическом runtime. **EXPECTED:** отсутствие нештатной интерполяции. **ACTUAL:** движок иногда печатает `Interpolated Camera3D triggered from outside physics process (possibly benign)`. **EVIDENCE:** есть и в обычном native run, и в driver run; ухудшение управления, NaN или измеренный jitter не установлены. **LIKELY ROOT CAUSE:** чтение/обновление interpolated камеры из render `_Process`; точный вызывающий участок не локализован. **FILES / NODES:** Camera3D, LookModule, FOV/ViewModel modules. **FIX RECOMMENDATION:** отдельное измерение cadence и visual jitter; не переносить камеру между processing loops на основании одного warning. **FIX RESULT:** NOT FIXED.

### TECH-003 — F2-панель обрезает числовые поля и кнопку Load Saved Values

- **SEVERITY:** Low.
- **CONFIDENCE:** Confirmed.
- **REPRODUCTION:** запустить Level_01, нажать F2 при окне игры 1280×720 или 2560×1440; посмотреть правую часть строк и toolbar.
- **EXPECTED:** все существующие поля и четыре кнопки доступны внутри панели или через прокрутку.
- **ACTUAL:** SpinBox и Load Saved Values находятся за правым краем, горизонтально добраться до них нельзя.
- **EVIDENCE:** `V2_UI_F2.png`, `V3_UI_2560.png`; runtime Window=520×760, ScrollContainer minimum width=677, Content/Toolbar=669; MoveSpeed SpinBox X=570, width=95, полностью за границей Window X=520.
- **LIKELY ROOT CAUSE (записана ДО правки UI):** `RuntimeTuningPanel._Ready` задаёт ширину 520, toolbar из четырёх кнопок расширяет Content до 669, а `BuildUi` запрещает HorizontalScrollMode. Контейнер не может сжать контент и выходит за Window.
- **FILES / NODES INVOLVED:** `Scripts/Debug/RuntimeTuningPanel.cs:80`, `RuntimeTuningPanel.Controls.cs`, `Debug/RuntimeTuningPanel/ScrollContainer`.
- **FIX RECOMMENDATION:** разрешить штатную горизонтальную прокрутку через `ScrollMode.Auto`. Не перестраивать форму, не менять настройки игрока.
- **FIX RESULT:** REVERTED. Экспериментальная замена Disabled → Auto дала ScrollContainer width=520, горизонтальную прокрутку 157 px и видимые SpinBox/Load Saved Values (`V4_UI_right.png`). Однако проверка полного цикла F2 не завершена: синтетический повторный F2 оставлял окно открытым и до, и после правки (`V3_UI_closed.png`, `V4_UI_closed.png`). Контроль обычной клавишей через Computer Use остановлен физической Escape пользователя. По условию задачи правка полностью откачена; итоговый RuntimeTuningPanel.cs совпадает с исходным. Это не утверждение, что scrollbar вызвал дефект закрытия.

## Решение перед правками

Первым выбран **BP-001**: два воспроизведения в текущей карте, точная причина, локальная проверка cooldown, без изменения tuning/геометрии/камеры. После дополнительных H/H-repeat вторым выбран **BP-004**, с локальным выходом из физически заблокированного pull через существующий cancel contract. Максимум три исправления — верхний предел, не квота. Остальные записи остаются отделены от субъективного game feel.

После V2/V3 третьим выбран **TECH-003**: два изображения при разных размерах окна и измеренные runtime-границы подтверждают clipping. Исправление одной настройки ScrollContainer не меняет форму или game feel.

## Проверка после правок

| Запуск | Код / сценарии | Результат |
|---|---|---|
| V1 | Только BP-001; точный C без OOB, затем B после reload | Same-wall exploit не повторился; штатный wallrun, wall jump, restored air jump, wallrun → hook и grapple/landing работают. |
| V2 | BP-001 + BP-004; H, G, F, K, B, A, F2 | H освобождает locks через 2.30 s. G проходит верхнюю кромку с нормальным launch; F wallrun → hook, закрытая цель и близкий launch работают. A jump Y=15, slide=40, по окончании locks пусты. |
| V3 | Те же два исправления; независимый H-repeat, C, F2 при 2560×1440 | H снова 138 Pulling ticks; повторного wallrun при cooldown нет. UI clipping подтверждён независимо от 1280×720. |
| V4 | Эксперимент TECH-003; A и F2 | Горизонтальная прокрутка исправила clipping, нормальный jump/slide сохранён. Закрытие F2 синтетическим вводом не подтверждено; утверждать полный PASS этого запуска нельзя. |
| V5, прерван | Контроль F2 обычным Windows-вводом | Игра запущена, но Computer Use остановлен физической Escape до действий. Не засчитывается завершённым gameplay pass. Процесс теста завершён, UI-правка откачена. |

**Точность сравнения:** B2_wallrun (15 ticks), B3_wall_jump_flight (12), B6_pull (22), B7_release (100) в V1/V2 имеют максимальное различие position/velocity с исходным B **0.0** в записанных данных. Это ограниченная проверка конкретного маршрута, а не доказательство всех траекторий. Для G2 расхождения порядка 0.00003 в velocity; цикл завершён. Близкий F4 launch произошёл на один physics tick позже, поэтому его траектория не объявляется покадрово идентичной; ветка arrive/launch срабатывает до новой защиты и заканчивается Idle.

**Hook → wallrun:** отдельная попытка K стартовала в CyberCity `(-5,8,-8)`, E на anchor `(0,7,-8)`, после 18 ticks поворот yaw 180° + W. Игрок дошёл до стены и приземлился; wallrun не включился в действовавшем post-launch control lock. Зависшего состояния нет, но успешный непосредственный переход hook → wallrun этим маршрутом не доказан. В C5 после hook позднее зарегистрирован wallrun с противоположной normal и последующее приземление. Нельзя переносить это на все углы/тайминги.

**Автоматические проверки телеметрии:** `verify_results.py` проверяет реальные captured traces. Полный экспериментальный набор: 25 PASS / 1 FAIL (ожидание закрытия F2, приведённое выше). Для оставленных исправлений отдельно сохранён `verification-retained.json`: все 22 проверки PASS. Экспериментальные результаты не скрыты и не подменены зелёным общим статусом.

**После отката UI:** повторная C# сборка — 0 warnings / 0 errors; `git diff --check` — PASS. Итоговые gameplay-модули соответствуют проверенным в V3. UI восстановлен к состоянию V3; новых правок после этого нет. В engine logs сохраняется известный TECH-001 и предупреждение TECH-002. Ошибки драйвера baseline отделены от runtime игры.

## Итог и изменения

- **8 исследовательских проходов A–H**, **1 независимый H-repeat**, **4 завершённых проверочных запуска V1–V4**; всего 13 сценарных последовательностей. V5 остановлен и в число завершённых не включён.
- **4 подтверждённых дефекта:** два gameplay (BP-001, BP-004), два технических (TECH-001, TECH-003). Из них **2 FIXED + VERIFIED**, **1 REVERTED**, **1 NOT FIXED**.
- **3 possible issues:** BP-002 (правило восстановления после OOB), BP-003 (визуальный контракт CyberBow), TECH-002 (неизмеренное влияние interpolation warning). Три OBS не включены в число багов. BP-001 одновременно считается одним exploit, а не вторым отдельным багом.
- Изменены только `C:\Users\harry\Documents\bow_prototype\Scripts\Player\Modules\PlayerWallRunModule.cs`, `C:\Users\harry\Documents\bow_prototype\Scripts\Player\Modules\PlayerSlingshotGrappleModule.cs` и этот отчёт `C:\Users\harry\Documents\bow_prototype\ASTRA_GAMEPLAY_AUDIT.md`.
- Сцены, `.blend`, GLB, геометрия, текстуры, default tuning, acceleration/gravity/jump/slide/wallrun/launch/FOV параметры не редактировались. Level_01 и CyberCity остаются раздельными. Commit/push не выполнялись. Несохранённая пользовательская вкладка редактора не сохранена; тестовые runtime-процессы остановлены.

## Решения человека и следующие три кандидата

1. **BP-002, High:** определить death/OOB/checkpoint contract отдельно для Level_01 и CyberCity. Сейчас F1 — ручной выход из падения.
2. **TECH-003, Low:** закончить проверку F2 с обычным вводом и восстановить доступность всех controls; минимальная scrollbar-правка и её проверенные визуальные результаты сохранены как эксперимент, в проекте она откачена.
3. **TECH-001, Low:** определить верный наконечник CyberBow и восстановить ArrowTipMarker, затем проверить реально включившуюся aim stabilization. Связанный вопрос BP-003: нужен ли видимому preview натягивающийся rig или пока допустима статическая модель.

Отдельные design decisions: может ли wallrun прерывать активный slide (OBS-002), нужна ли ручная отмена E (OBS-003). Их не следует смешивать с найденными техническими сбоями.

## Доказательства и повторное воспроизведение

Рабочие доказательства: `C:\Users\harry\Documents\Codex\2026-09-06\files-pasted-by-the-user-gameplay\work`. В архиве `ASTRA_GAMEPLAY_EVIDENCE.zip` — планы pass-*.json и verify-*.json, внешний `audit_driver.gd`, исходные и проверочные traces/logs, кадры, runtime tree, три снимка отчёта с root cause до соответствующей правки, исходные копии затронутых C# файлов, итоговый diff и результаты проверок. Файлы `*_closed.png` отражают **намерение теста**, не гарантируют, что панель закрылась; фактическое содержимое описано выше.

Для повторения настроить BASE внешнего драйвера на распакованную рабочую папку, собрать проект, атомарно скопировать нужный план в command.json и запустить Godot с `--path <repo> --script <driver> --log-file <log> -- <trace-suffix>`. План использует реальные InputEvent; debug position/look явно указаны в JSON. Драйвер не должен попадать в production scene. Для скриптов проверки нужны сохранённые имена trace-файлов.
