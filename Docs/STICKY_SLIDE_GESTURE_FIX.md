# Sticky Slide — one input gesture, one acquisition

Исправлено 2026-09-19 по подтверждённой человеческой сессии
`human_20260919_144944_224Z_d1828465b9a7466a9e11470c7862f191.jsonl` и её сохранённому
report.md. Исходный лог и latest_human_session сохранены без изменения SHA-256.

## Причина и изменение

`ProcessCrouchSlide` вызывал `UpdateAirborneSlideBuffer` до проверки активного Slide.
Удерживаемый Ctrl заново заполнял буфер в воздухе, даже когда Slide уже был активен.
После timer exit буфер разрешал новый вход без нового DOWN. При slide-jump это могло
произойти в том же tick: Jump обрабатывается раньше Slide и раньше MoveAndSlide,
поэтому `IsOnFloor` ещё true. В человеческом логе были 30 ENTER на 3 Ctrl DOWN.

Семантика сосредоточена в `PlayerCrouchSlideModule.InputGesture.cs`:

- DOWN: Released → Available, новый gesture_id. Raw input events сохраняют быстрый
  RELEASE → PRESS между physics ticks; keyboard echo не создаёт gesture.
- `UpdateAirborneSlideBuffer`: только свежий Available gesture, отсутствие активного
  Slide, airborne intent и существующий speed threshold вооружают buffer один раз.
  TTL продолжает убывать; held никогда его не обновляет.
- `StartSlide`: окончательная проверка Available; успешный старт вызывает
  `ConsumeSlideGesture`, переводит gesture в Consumed и очищает airborne intent/buffer.
- RELEASE: завершает gesture и очищает ожидающий intent. Следующий DOWN снова доступен.
- Дополнительный локальный guard `PlayerJumpModule.JumpConsumedThisTick` выставляется
  только после успешного ground/air jump. `CanStartSlide` и `StartSlide` отвергают
  acquisition в этот tick. Это семантическая отметка реального прыжка, а не debounce.
  Одновременные Jump+Ctrl сохраняют airborne intent для последующего приземления.

Основная защита — Consumed gesture и отсутствие повторно вооружённого буфера.
GroundCheck/IsGrounded, порядок PlayerController, окно/collision, Slide speed=40,
duration=0.98, cooldown=0.35, остальные tuning и audio logic не изменены. Существующий
cooldown сохранён; новые задержки или cooldown не добавлены. В G свежий DOWN сработал
на первом следующем physics tick после быстрой пары RELEASE → PRESS.

## Проверка

`dotnet build --no-restore`: PASS, 0 ошибок, 0 предупреждений.

Контролируемый integration run использовал настоящие Player modules и runtime tuning,
InputEventKey с PhysicalKeycode=Ctrl. A–C/E–J выполнялись на временном тестовом плоском
полу (production geometry не редактировалась). D загружал настоящую Level_01 и проходил
исходное окно с заданной начальной скоростью подхода, затем обычными Jump/Slide/MoveAndSlide.
Это автоматический regression, человеческий retest проводится отдельно.

| Проверка | Ctrl DOWN | Slide ENTER | Результат |
|---|---:|---:|---|
| A: обычный Slide | 1 | 1 | PASS |
| B: удержание после полного timer exit | 1 | 1 | PASS; нового входа нет |
| C: DOWN в воздухе → held → landing | 1 | 1 | PASS; одно buffered acquisition |
| D: настоящее окно/подоконник Level_01 | 1 | 1 | PASS; потеря контакта не вооружает buffer |
| E: slide-jump при held Ctrl, cooldown уже 0 | 1 | 1 | PASS; exit + jump, без входа в том же tick |
| F: четыре следующих Jump при том же held Ctrl | 0 новых | 0 | PASS |
| G: deliberate RELEASE → PRESS после exit | 2 | 2 | PASS; первый eligible tick, без задержки |
| H: новый airborne gesture после slide-jump | 2 | 2 | PASS; одно landing acquisition на второй gesture |
| I: одновременные Jump + Ctrl | 1 | 1 | PASS; вход только на приземлении |
| J: истечение buffer TTL до приземления | 1 | 0 | PASS; held не продлевает TTL |

Итого: **11 синтетических Ctrl DOWN, 10 Slide ENTER, 0 acquisitions из Consumed gesture,
0 jump acquisitions в том же tick, максимум 1 acquisition на gesture**.
Все buffered entries с just_pressed=false происходят из Available gesture.

`SLIDE_RAPID_REENTRY`: **1**, только в G — два разных жеста, новый just_pressed=true,
интервал 0.033333 s. Это ожидаемое быстрое chaining, не повтор consumed input.
Нежелательных rapid re-entry нет.

В D trace подтвердил тот же контакт `CB_CrossWindowSill/StaticBody3D` при IsOnFloor=false,
IsGrounded=true. После начала Slide контакт снова теряется, но buffer остаётся 0.
На RoutePad2 Slide выходит по таймеру с held Ctrl; нового входа нет.
События D: seq371 (ENTER), seq376 (ground lost while sliding), seq383 (timer EXIT).

Audio: 10 one-shot START / 10 STOP, соответствуют 10 реальным movement ENTER/EXIT.
Loop: 9 START / 9 STOP; при намеренном быстром chaining G существующий fade не успевает
полностью остановить loop. Audio implementation не изменялась.

Архив regression:
`.godot/movement-traces/regression_20260919_150646_793Z_500e9fd79c124d468204dd95ecb98904.jsonl`.
Доказательства: `.godot/movement-traces/slide-gesture-regression/runtime_assertions.json`
и `trace_verification.json`; 396 events, sequence без пропусков, latest/archive совпадают.
Хэши исходных human logs, Level_01.blend/wrapper, Player scene, tuning, PlayerController,
wallrun, grapple и audio совпали с состоянием перед fix.

## Повторяемые команды

```text
dotnet build --no-restore
godot --headless --path . --script res://Tools/Diagnostics/verify_slide_gesture.gd -- --movement-trace=regression
python Tools/Diagnostics/check_slide_gesture_trace.py
```

Человеческий retest у исходного окна, без synthetic input:

```text
godot --path . --script res://Tools/Diagnostics/slide_gesture_human_retest.gd -- --movement-trace=human_fixed --movement-trace-capture
```

Этот launcher только загружает настоящую сцену, после штатного startup ставит игрока
перед окном в `(116.96, -0.6763, -15.42)`, направляет взгляд вдоль -Z и отдаёт input.
Лог: `.godot/movement-traces/latest_human_fixed_session.jsonl`, timestamped copy рядом.
`MOVEMENT TRACE: REC` остаётся включённым; stop — через путь из session header после
сообщения пользователя или при закрытии игры. Исходный human log не перезаписывается.

## Файлы этого fix pass

- `Scripts/Player/Modules/PlayerCrouchSlideModule.InputGesture.cs` — новое состояние gesture.
- `Scripts/Player/Modules/PlayerCrouchSlideModule.cs` — одноразовый arm/acquisition invariant.
- `Scripts/Player/Modules/PlayerJumpModule.cs` — отметка успешного jump tick.
- `Scripts/Player/Modules/PlayerCrouchSlideModule.Trace.cs` — gesture telemetry.
- `Scripts/Debug/PlayerMovementTrace.cs` — schema 2, отдельные режимы логов и test markers.
- `Tools/Diagnostics/verify_slide_gesture.gd` — regression A–J.
- `Tools/Diagnostics/check_slide_gesture_trace.py` — проверка raw trace и protected hashes.
- `Tools/Diagnostics/slide_gesture_human_retest.gd` — launcher для человека.
- `Docs/MOVEMENT_SESSION_TRACE.md`, этот документ; Godot `.uid` metadata новых скриптов.

Изменены код и документация. Сохранённые сцены, ассеты, геометрия и tuning не редактировались.
Commit/push не выполнялись. Human retest — следующий этап подтверждения feel игроком.
