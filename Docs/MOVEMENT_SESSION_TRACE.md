# Movement session trace — log first

Диагностика sticky Slide. Первый pass добавил только trace; последующий разрешённый
fix ввёл семантику «один gesture — одно acquisition». См. `STICKY_SLIDE_GESTURE_FIX.md`.
Сцены, геометрия, collision, tuning, приоритеты и параметры звука не менялись.

## Запуск человеческой сессии

Запустить Godot Mono с корнем проекта и реальной сценой:

```text
godot --path . res://Scenes/Levels/Level_01/Level_01.tscn -- --movement-trace=human --movement-trace-capture
```

Без `--movement-trace` диагностический узел не создаётся. Никакой input не синтезируется.
Для повторного человеческого теста после fix используется `--movement-trace=human_fixed`:
`latest_human_fixed_session.jsonl` и `human_fixed_<UTC timestamp>_<unique id>.jsonl`.
Оригинальный `latest_human_session.jsonl` и его timestamped archive остаются нетронутыми.
`--movement-trace=regression` выделен для контролируемых тестов с InputEventKey;
в заголовке такого лога явно указано synthetic input.
`--movement-trace-capture` однократно сохраняет рендер с индикатором в
`.godot/movement-traces/handoff.png`; на игру и камеру он не воздействует.
В углу отображается `MOVEMENT TRACE: REC`. Ошибка записи меняет статус на `ERROR`.

- `.godot/movement-traces/latest_human_session.jsonl` — текущая сессия с чистого файла.
- `.godot/movement-traces/human_<UTC timestamp>_<unique id>.jsonl` — одновременно
  записываемый архив: он остаётся после остановки и при следующем запуске не перезаписывается.
- Root-owned observer сохраняет ту же сессию после reload/respawn; добавляет `PLAYER_REBIND`.
- Фоновый writer получает только сериализованные строки. Flush каждые 0.5 s и при stop/exit.
  При принудительном завершении процесса возможна потеря последнего не сброшенного хвоста.
  Переполнение ограниченной очереди или ошибка I/O явно переводят индикатор в `ERROR`.

## События и интерпретация

Каждая строка содержит UTC/monotonic timestamp, physics seconds, render/process frame,
engine physics tick, sequence, phase, from/to, reason и снимок состояния.

- `SLIDE_ENTER`, `SLIDE_EXIT`, `POSTURE_TRANSITION` — непосредственно в ветках изменения
  Standing/Crouching/Sliding. В `details.before` сохраняется состояние до изменения.
  Причины содержат имя метода и фактическую ветку: just-pressed entry, held buffered
  landing entry, timer/speed exit, slide jump, blocked jump, wallrun/grapple preemption.
- `ABILITY_BEGIN/END` — реальные requests арбитра с owner, priority, locks, предыдущим
  снимком и новой выбранной ability. Порядок событий сохраняет handoff внутри одного tick.
- `JUMP`, `AIR_JUMP`, `JUMP_REJECTED`, `WALL_JUMP`, `WALLRUN_TRANSITION`,
  `GRAPPLE_TRANSITION` — hooks в исполняемых ветках, включая grapple cooldown/idle.
- `LOCOMOTION_MODE_CHANGE` — **производная метка**, не новая state machine.
  Отдельного authoritative RUN в текущем motor нет: `GROUND_MOVE` обозначает обычное
  движение с настроенной MoveSpeed; `IDLE`, `AIR`, `CROUCH`, `SLIDE`, `WALLRUN`,
  `GRAPPLE_*` вычисляются из текущих модулей. Jump-события — реальные импульсы.
- `FLOOR_ACQUIRE/LOST` — изменения `CharacterBody3D.IsOnFloor`; `GROUNDED_ACQUIRE/LOST`
  отдельно наблюдает существующий `IsOnFloor || (Velocity.Y <= 0 && GroundCheck hit)`.
  Проверки до модулей, перед MoveAndSlide и после него; дополнительных physics queries нет.
  Пишутся текущий/предыдущий контакт, normal, position, collider ID/name/path и контакты
  последнего MoveAndSlide. Floor collider помечен **candidate** по совпадению normal;
  отсутствие кандидата остаётся null. GroundCheck collider явно отделён от него.
- `SLIDE_INPUT_DOWN/UP` имеют источник `raw_event` или `physics_poll`: это два наблюдения
  одного edge, не два нажатия. `SLIDE_INPUT_HELD` максимум 1 Hz. Каждый transition также
  содержит just_pressed/held/just_released, физические Ctrl/C/Shift, WASD vector и Parkour.
- В исходном логе schema 1: `SLIDE_AIR_BUFFER_ARM/REFRESH/CONSUMED`, refresh до 2 Hz.
  После fix (schema 2): buffer вооружается один раз новым airborne gesture, TTL убывает
  без refresh. `SLIDE_GESTURE_BEGIN/END/CONSUMED` показывают lifecycle ввода. Каждое
  acquisition имеет `details.before.slide.gesture_state=Available`; после старта —
  Consumed, buffer=0, airborne_intent_armed=false. В snapshots есть gesture_id,
  player_instance_id и jump_consumed_this_tick для проверки инварианта.
- `SLIDE_AUDIO_START/STOP`: отдельные `layer=one_shot` и `layer=loop` после реальных
  Play/Stop вызовов. STOP one-shot означает воспроизведение slide_exit; loop STOP означает
  остановку зацикленного player после существующего fade. Muted/gain фиксируются отдельно.
- `SLIDE_RAPID_REENTRY` — новый Slide ENTER менее чем через **0.5 s physics time** после EXIT.
  Содержит exit/enter reason, time_since_exit, текущий input/floor/speed и ring buffer
  последних **2 s** по physics ticks. Это только marker, никаких запретов на re-entry.
- `TELEMETRY` — 2 Hz, без непрерывных transform dumps на каждый tick. Ring хранится
  в памяти; попадает в файл только при rapid re-entry. В ring есть скорость до/после
  MoveAndSlide, позиция, floor/grounded, held input, Slide timer и airborne buffer.

Snapshot содержит реальный локальный `ref velocity`, когда hook срабатывает до присваивания
`Player.Velocity`; оба значения и `velocity_source` записаны. Slide snapshot включает raw
direction даже после exit, внутреннюю speed, cooldown, grace, buffer и действующие tuning
пороги. В schema 1 отдельного release-to-rearm состояния не было; schema 2 фиксирует
Released/Available/Consumed. Rapid marker остаётся диагностическим: намеренный быстрый
release+press может законно попасть под threshold, поэтому проверяется gesture_id.

## После сообщения игрока о воспроизведении

До такого сообщения запись не останавливать, лог не анализировать, баг не чинить.
После сообщения взять `details.stop_request_path` из `SESSION_START` и создать этот
пустой файл. Observer обработает запрос в течение 0.5 s, допишет `SESSION_END`, дождётся
writer и покажет `MOVEMENT TRACE: SAVED`; игра останется запущенной. Обычное закрытие
игры тоже закрывает writer. Следующий pass: timeline и доказанная цепочка по sequence/tick.

## Проверки и состав изменений

`dotnet build --no-restore`; отдельно headless smoke на Level_01 без синтетического input.
Smoke использует `--movement-trace=smoke`, свои latest/archive и не загрязняет human log.
Проверяются JSONL, floor contact, штатное завершение и совпадение latest/archive.
Это проверка trace infrastructure, не воспроизведение sticky-slide.

Проверено 2026-09-19: build — 0 ошибок / 0 предупреждений; idle smoke записал floor
и grounded acquire и завершился с `error=none`. Отдельная проверка stop-request дала
`SESSION_END` с reason `explicit session stop request file`; SHA-256 latest/archive
совпали. Runtime smoke имеет существующее предупреждение legacy aim stabilization
о ненайденных ViewModelCamera3D/ArrowTipMarker; связанных ошибок trace нет.

Изменены только код и этот документ:

- `Scripts/Debug/PlayerMovementTrace.cs` — session observer, marker, snapshots, ring.
- `Scripts/Debug/PlayerMovementTrace.Writer.cs` — фоновый writer.
- `Scripts/Player/Modules/PlayerCrouchSlideModule.Trace.cs` — read-only Slide telemetry.
- `Scripts/Player/PlayerController.cs` — opt-in attach и три точки наблюдения physics.
- `Scripts/Player/Modules/PlayerCrouchSlideModule.cs` — branch hooks.
- `Scripts/Player/Modules/PlayerAbilityStateModule.cs` — request hooks.
- `Scripts/Player/Modules/PlayerJumpModule.cs` — impulse/rejection hooks.
- `Scripts/Player/Modules/PlayerWallRunModule.cs` — transition/preemption hooks.
- `Scripts/Player/Modules/PlayerSlingshotGrappleModule.cs` — transition/preemption hooks.
- `Scripts/Audio/PlayerAudioController.Playback.cs` — наблюдение существующих Play/Stop.
- `Docs/MOVEMENT_SESSION_TRACE.md` — запуск и контракт логов.

Исходные версии семи изменяемых файлов перед инструментированием сохранены локально в
`.godot/movement-traces/instrumentation-baseline/` для сравнения с уже изменённым рабочим
деревом. Существовавшие изменения не откатывались. Commit/push не выполнялись.
