# RMB Combat Foundation — Main Character V2

ПКМ имеет одного владельца: `Player/PlayerRmbCombat`, отдельный Node без motor,
camera, bone или projectile writes. InputMap action — `rmb_combat` / Right Mouse.
Существующая ЛКМ и Alt precision остаются независимыми. Это логический foundation:
нового melee damage, отражения снарядов и power-projectile пока нет.

## Поведение и тайминги

- DOWN немедленно открывает parry и `RmbAnticipation`; melee на DOWN отсутствует.
- UP раньше **TapHoldThreshold = 0.17 s** → `Melee` → `Recovery` → `Idle`.
- Удержание после threshold → `PowerShotPrep`; ещё **PowerChargeTime = 0.75 s**
  до `PowerShotReady`. UP → один `PowerShotRelease` → `Recovery` → `Idle`.
- **ParryWindow = 0.14 s** от DOWN. Успех → `ParrySuccess` → recovery;
  весь жест потреблён, его UP и дальнейший hold не создают melee/power.
- Ранний UP в power prep выдаёт release request с `fullyCharged=false` и
  неполным charge. Будущий обработчик решит, выпускать ли такой выстрел.
- Нажатия во время melee/parry/release/recovery отбрасываются без буферизации.
  Нужен новый DOWN после recovery. Повторный UP ничего не делает.
- Escape/освобождение курсора, потеря focus и pause отменяют RMB-жест.

Все длительности экспортированы на `PlayerRmbCombat`. Melee: active delay 0.08 s,
active duration 0.12 s, общая длительность 0.30 s; recovery 0.18 s;
parry success 0.20 s; power release 0.20 s. Таймеры не зависят от длины клипа.
DOWN/UP используют события, поэтому сверхкороткий tap внутри одного кадра не теряется.
Распознавание жеста использует монотонное реальное время; при pause он отменяется.

## Хуки и подключение следующих passes

- **Melee:** `MeleeCommitted`, `MeleeActiveWindowChanged(bool)`.
  Будущий hit detector вызывает `TryReportMeleeHit(target, worldPosition)`;
  `MeleeHitReported` выдаётся только внутри active window, один раз на target за удар.
- **Parry:** `TryParryProjectile(projectile, eligible)` возвращает успех;
  collision/projectile owner сам определяет допустимость и дальнейшую физику.
  `ParrySucceeded` — hook на результат. `DebugTryParry()` — технический trigger
  через Remote Inspector/тестовый код; в release build отключён. Enemy code не менялся.
- **Power:** `PowerShotStarted`, `PowerReadyEntered`, `PowerChargeUpdated`,
  `PowerShotReleased(aimOrigin, aimDirection, charge, fullyCharged)`.
  Направление и origin берутся из gameplay camera, включая при включённом 3POV debug.
  Release payload публикуется один раз после V2 render pass, когда camera уже обновлена.
- **Nock/draw:** будущий изолированный presentation bridge читает `ChargeAmount`,
  `StateChanged` / `PowerChargeUpdated`, затем задаёт right-hand Nock target и string
  draw. Сейчас этот bridge не создан, writers обычной ЛКМ не перехвачены.

## Animation slots / Blender

Единая mapping-конфигурация: `Resources/Combat/RmbAnimationSlots.tres`.
V2 потребляет requested clip, если он существует в AnimationPlayer. Отсутствующие
клипы дают Idle fallback. Во время slide приоритет остаётся у `BH01_SLIDE`:
полная melee-поза не заменяет ноги/таз. Для будущей боевой анимации поверх slide
нужен отдельный upper-body blend pass; логика RMB уже работает.

В `Humanoid_Male_PoseLab.blend` созданы только четыре недостающих Actions:

- `BH01_RMB_ANTICIPATION`
- `BH01_MELEE`
- `BH01_PARRY`
- `BH01_MELEE_RECOVERY`

Каждый — независимая копия исходного `BH01_IDLE`, frame 1, Fake User, те же rig
channels. Финальная анимация не придумывалась. 21 существующий Action сохранён
с идентичными ключами/handles; rest/parent/deform-флаги 89 authoring bones совпали.
Backup: `.godot/rmb-foundation/PoseLab_before_RMB_20260912_171949_881328.blend`.

Без дублей переиспользованы Bow slots:
`BH01_BOW_READY`, `BH01_BOW_DRAW_START`, `BH01_BOW_FULL_DRAW`,
`BH01_BOW_RELEASE`, `BH01_BOW_FOLLOW_THROUGH`, `BH01_BOW_RECOVERY`.
Ready/DrawStart делят prep, FullDraw соответствует ready; Release/FollowThrough
делят release; затем BowRecovery. Эти Actions существуют в PoseLab, но текущий
production GLB пока по-прежнему содержит только Idle/Slide.

В capture добавлен явный `V2_EXTRA_ACTIONS` list, по умолчанию пустой. После ручного
позинга передать выбранные имена через `runpy.run_path(..., init_globals={
"V2_EXTRA_ACTIONS": [...]})`. Export и verifier теперь читают список из capture.
Это всё ещё capture **frame-1 poses**, а не bake полноценной многокадровой анимации.
Новые placeholders автоматически в runtime не экспортируются.

Файл сохранён для ручной работы: `BH01 PoseLab`, Male / Pose Mode,
`BH01_RMB_ANTICIPATION`, frame 1; controls видимы, DEF/MCH скрыты,
CyberBow видим, Action Editor открыт, обе FP cameras сохранены.

## Короткая проверка

- `dotnet build --no-restore`: 0 ошибок / предупреждений.
- Godot import и rendered smoke: `RMB_SMOKE_PASS`, failures=0.
- Проверены tap, tap в одном кадре, repeated taps, busy spam, hold/ready/release,
  immediate/invalid/expired parry, dedup hit callback и анимационный mapping.
- Проверены tap в движении, hold в slide, yaw 360 со slide body lock,
  F9/F10, cursor cancel и обычный projectile от ЛКМ.
- Ошибка V2 bow aim на контрольных samples: менее 0.000082°.
- Capture/export четырёх новых Actions проверен в **временный** GLB под `.godot/`:
  один skin / 54 joints; maximum surface bake error менее 0.007 мм.
  Production GLB и camera calibration не перезаписывались.
- Существующее предупреждение legacy sway про aim stabilization осталось.
  При завершении тестового процесса Godot также вывел два renderer teardown
  сообщения `indexing did not unpair geometries from light`; проверки до выхода
  прошли. Отдельный renderer audit не проводился.

Артефакты: `.godot/rmb-foundation/runtime_validation.json`, `runtime.png`,
`blender_slots.json`, `pipeline-check/`; обычный человеческий запуск — `human.log`.

## Изменённые файлы этого pass

- `Scripts/Player/Combat/PlayerRmbCombat.cs` + UID — input/state/hooks.
- `Scripts/Player/Combat/RmbCombatAnimationSlots.cs` + UID — тип конфигурации.
- `Resources/Combat/RmbAnimationSlots.tres` — mapping.
- `Scripts/Player/Presentation/MainCharacterV2.cs` — выбор доступного clip + readout.
- `Scenes/Player.tscn` — один RMB Node и его конфигурация.
- `project.godot` — один InputMap action.
- `Assets/Characters/BaseHumanoid/Source/Humanoid_Male_PoseLab.blend` — четыре Actions + authoring UI.
- `Tools/Blender/HumanoidBase/prepare_rmb_slots.py` — добавление только отсутствующих Actions с backup.
- `Tools/Blender/HumanoidBase/capture_v2.py`, `export_v2.py`, `verify_v2.gd` — явно выбранные дополнительные poses.
- `Tools/Character/verify_rmb_combat.gd` + UID — короткий внешний driver.
- `Docs/RMB_COMBAT_FOUNDATION.md` — этот отчёт.

Movement, wallrun, slide physics, grapple, MouseLook, camera foundation, IK
cadence, projectile aim и CyberBow art не менялись. Commit / push не выполнялись.
