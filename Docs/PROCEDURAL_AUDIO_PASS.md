# Procedural gameplay audio — первый pass

Дата: 2026-09-06. Статус: **реализовано и проверено технически; принято пользователем как прототип / GOOD ENOUGH для интеграции**.

Звуковая оценка агентом не выдается за выполненную: доступный интерфейс не поддерживает audio input. Сохранены настоящие записи Godot Master bus. После исходного handoff пользователь явно принял текущий audio pass как прототип и разрешил local commit и интеграцию без дополнительного слухового QA. Ниже сохранены результаты исходных технических тестов и их ограничения.

## 1. Starting snapshot и изоляция

- Starting HEAD: `c00ba64e29fd88b751d7752e740d622cc17e3f91`.
- Исходная ветка: `main`, рабочая копия: `C:\Users\harry\Documents\bow_prototype`.
- Audio branch: `audio/procedural-pass-20260906`.
- Audio worktree: `C:\Users\harry\Documents\bow_prototype_audio`.
- Исходный dirty status: изменены `PlayerSlingshotGrappleModule.cs`, `PlayerWallRunModule.cs`; untracked — три ASTRA audit/Gym отчета, Gym scene/layout, Gym scripts и `Tools/build_movement_gym.py`.
- Эти movement-изменения не перенесены. Audio использует ровно HEAD. Основная рабочая копия не изменялась, ручной fullscreen A/B не перехватывался.
- Gym scene/layout скопированы один раз как **inherited testing overlay**. Два Gym C# взяты из сохраненных `.before` snapshots. Их исходные SHA-256 проверены после работы: совпадают. Overlay исключен из audio diff/patch и будущего audio commit.

## 2. Что синтезировано

45 mono PCM16 WAV, 48 kHz: 40 коротких one-shots и 5 двухсекундных loops. Общий размер WAV — 1 571 100 байт. Ни samples, ни SFX packs, ни DAW, ни сторонние sound libraries не использованы.

One-shots: filtered noise, короткий transient, затухающие негармонические резонаторы, небольшие частотные sweep. Loops: периодический шум из 180 синусоид на целых частотных бинах. Направление — сухая механика и ранний industrial sci-fi; без музыки, большого sub-bass и длинного reverb. Это намерение синтеза, а не подтвержденная слуховая оценка результата.

## 3. Generator

`Tools/Audio/generate_audio.py` — Python 3 standard library: `wave`, `math`, `random`, `struct`, `hashlib`, `zlib`. Каждый файл получает фиксированный seed, независимый от порядка генерации.

```powershell
python Tools/Audio/generate_audio.py
python Tools/Audio/generate_audio.py --check
```

`--check` заново синтезирует весь банк в памяти и сравнивает PCM byte-for-byte и manifest. Проверка 45/45 прошла. В `.wav.import` используется `compress/mode=0`: PCM сохраняет исходную форму и loop seams.

## 4. Generated assets

`Assets/Audio/Procedural/`: WAV, Godot `.wav.import`, `manifest.json` с seed, длительностями, PCM SHA-256, peak/RMS. Семейства one-shots имеют 2–3 синтезированных варианта.

Loops: `wind_low.wav`, `wind_high.wav`, `slide_loop.wav`, `wall_loop.wav`, `grapple_loop.wav`.

## 5. Gameplay events

Озвучены jump, air jump, landing light/medium/heavy; wallrun enter/exit и wall jump; slide enter/exit; grapple fire/attach/release; checkpoint и run reset. Между переходами работают wallrun/slide/grapple loops и continuous speed audio.

Контроллер читает публичные states, velocity, input и существующий wallrun exit reason. Ни одного gameplay hook не добавлено. Jump определяется по input + наблюдаемому вертикальному импульсу; rejected input не создает отдельный звук. Checkpoint adapter читает `CurrentCheckpoint` у `MovementGymCourse` по существующему script path, без зависимости компиляции от Gym.

## 6. Speed Audio architecture

`PlayerAudioController` — autoload, physics priority 100, после `PlayerController.MoveAndSlide()`. Контроллер обнаруживает player group и не пишет в player, input или movement tuning.

Метрика: `sqrt(vx² + vz²)`. Pure vertical fall не превращается в sprint. По умолчанию wind почти отсутствует ниже 9 m/s и достигает полного диапазона при 44 m/s. Экспоненциальный smoothing — 8/s. Два слоя с нелинейным gain и плавным pitch дают больше верхних частот на скорости. Они одинаково реагируют на momentum от любых mechanics.

One-shots слегка приглушают wind на 0,13 s. Loop gain сглаживается отдельно; ниже практически неслышимого порога stream останавливается. В idle нет бесконечно работающего wind player. Master/mute/solo/volume также меняются с коротким gain smoothing.

Шины: `Master ← SFX ← Movement / Grapple / System / Speed`. Сохранены в `default_bus_layout.tres`, SFX baseline −3 dB.

## 7. Landing intensity

Используется последняя вертикальная скорость свободного падения перед контактом. Существующий GroundCheck может включить grounded snap раньше `IsOnFloor()` и подменить Vy на −3,2 m/s; audio сохраняет предшествующую скорость через этот proximity interval. Physics не меняется.

Порог слышимого impact — 2,5 m/s; light <8, medium <19, heavy ≥19. Gain и pitch меняются непрерывно внутри этих семейств. Короткий spawn/snap без полета не вызывает landing cue.

Контроль на настоящей Gym-геометрии после исправления: tiny drop 5,72 m/s → light; обычный jump 13,58 → medium; вертикальный fall 52,87 → heavy. Во всех этих вертикальных тестах wind был 0. После slide/air-jump цепочки impact 21,13, после wallrun/grapple комбинации — 36,39 m/s.

## 8. Slide / wallrun / grapple

- Slide: enter → friction loop → exit; gain/pitch зависят от горизонтальной скорости.
- Wallrun: enter → wall loop → exit; wall jump получает отдельный accent. Нет зависимости от tangent solver, canonical trajectory, вертикальной кривой или F2 A/B.
- Grapple: fire при принятом переходе в Pulling, короткий attach accent через ~45 ms, travel loop до выхода из Pulling, затем release. Pitch/gain travel зависят от velocity. Физическая tension не выдумывается и не вычисляется новой gameplay-системой.
- 12 фиксированных one-shot players и 5 loop players принадлежат autoload. R/F1 перепривязывают player; старые loops плавно уходят, pool не растет. Вариация: без immediate repeat, pitch ±3,5%, gain ±0,6 dB, короткий same-family debounce 55 ms.

## 9. Runtime tuning / debug

Существующий RuntimeTuningPanel просмотрен: он связан с PlayerTuningProfile и использует F2. Во избежание конфликта с wallrun A/B он не изменялся.

Новая компактная **F6 Audio panel**, **F7 mute**. SFX, Movement, Grapple, System, Speed, Landing, Slide, Wallrun; wind threshold/full-speed/response, pitch variance; solo по основным buses; meter horizontal speed/wind/voice count. F6/F7 работают и внутри собственного Window. UI не ставит gameplay на паузу.

Настройки сохраняются только по кнопке в `user://procedural_audio_settings.tres`. R/F1 сохраняют mix через autoload. `GameplayAudioSettings` также доступен в Inspector. Опциональный аргумент `--audio-trace=<absolute-path.jsonl>` пишет события и 10 Hz audio-state telemetry; по умолчанию никакого trace I/O нет.

## 10. Новые AUDIO-OWNED файлы

- `Tools/Audio/generate_audio.py`.
- `Assets/Audio/Procedural/`: 45 WAV, 45 `.import`, `manifest.json`.
- `Scripts/Audio/GameplayAudioSettings.cs` и `.uid`.
- `Scripts/Audio/PlayerAudioController.cs`, `.Playback.cs`, `.Panel.cs` и соответствующие `.uid`.
- `default_bus_layout.tres`.
- `Docs/PROCEDURAL_AUDIO_PASS.md`.

## 11. Измененные существующие файлы

Только `project.godot`: четыре добавленные строки, раздел autoload с `PlayerAudio`. Main scene, production display settings, Player.tscn, resources/tuning, camera, geometry и movement C# не менялись.

## 12. SHARED / POTENTIAL MERGE CONFLICTS

`project.godot` — единственный SHARED / POTENTIAL MERGE CONFLICT. Нужна одна autoload-запись. Movement files имеют нулевой diff относительно starting HEAD. `default_bus_layout.tres` новый; если позже появится другой bus layout, объединять его сознательно при интеграции.

Текущие untracked Gym scene/layout/scripts в audio worktree — inherited testing overlay, не часть audio pass. `.godot` — локальный generated cache. Соседнюю wallrun branch не догоняли и не сливались с ней.

## 13. Gameplay playtest и техническая проверка

Проводились настоящие headless Godot runs, synthetic InputEvent/held actions и обычный Player.MoveAndSlide на `Level_Movement_Gym`. В traversal driver нет записи player position/velocity. Для локальных коротких fixtures начальные position/velocity/view задавались только до добавления сцены в tree.

Покрыты idle, run, jump, air jump, три landing family, slide → jump, wallrun, wall jump, sustained speed, grapple → landing, slide → jump → wallrun → grapple → landing, checkpoint, R и F1. Максимальная зарегистрированная горизонтальная скорость — 47,44 m/s. В отдельной комбинации exit wallrun и grapple fire произошли в одном physics tick.

Длинный прогон достиг checkpoint 5 за 53,57 s, затем recovery на hook_air. **Полное прохождение Gym не заявляется.** У headless DisplayServer mouse mode остается Visible: обычный mouse-look driver не работает. Это ограничение теста обходилось фиксированным initial view в fixtures, без изменения Player, OS focus или текущей ручной сессии. Неудачные headless попытки не выдаются за gameplay/audio regression.

После audio fixes выполнены короткие retests: landing mapping, mixed wallrun/grapple, R/F1/F7, собственный viewport F6 panel. Build: 0 errors / 0 warnings. `git diff --check`: PASS. 45 PCM regeneration checks: PASS. Все пять loop seams имеют sample step ниже P99 обычных соседних sample steps. Это инструментальная проверка, не гарантия слуховой незаметности.

В записанных тестовых миксах: 0 clipped samples. После последней landing correction максимальный peak финальных записей — −12,90 dBFS; точные значения находятся в verification JSON. Никаких voice-budget drops или immediate variant repeats. Max одновременно наблюдавшихся one-shots — 3. R/F1 smoke: один player, 17 audio players, 0 playing после idle, autoload тот же.

Известные baseline warnings: отсутствующий ArrowTipMarker / aim stabilization, camera interpolation. Headless `PopupCentered` также сообщает invalid screen position из-за dummy screen; открытие/закрытие и window hotkeys проверены отдельно, визуальный layout на реальном экране не подтвержден.

**Прослушивание:** реальный Master bus записан в WAV через AudioEffectRecord с Dummy output, системный звук пользователя не перебивался. Попытка передать запись на аудиовход инструмента вернула `audio content omitted because you do not support audio input`. Поэтому тембр, субъективная громкость, masking и слышимость clicks не считаются проверенными на слух.

## 14. Слабые места / границы готовности

Ручное прослушивание комбинаций и визуальная оценка F6 оставлены для будущей итерации и не блокируют принятую пользователем интеграцию. Микс намеренно имеет запас по peak; субъективно он может оказаться слишком тихим. Три landing family имеют границы тембра при непрерывных gain/pitch. Очень ранний air jump, который понижает Vy вместо положительного импульса, может не распознаться observer-ом. Wall jump распознается по существующему `lastExit=wall_jump`; если формат debug reason изменится, adapter надо обновить. Checkpoint adapter пока Gym-specific.

Изначально audio-agent не создавал commit из-за недоступного прослушивания. По последующему прямому разрешению пользователя главный агент создаёт отдельный local commit `Add procedural gameplay audio pass`, исключая inherited Gym overlay, и интегрирует его поверх текущего gameplay. Canonical B и slide → wallrun handoff основного worktree остаются source of truth; audio адаптируется к их публичным состояниям.

## 15. Идеи второго pass

После ручного прослушивания: отстроить relative loudness wind/landings и яркость friction, проверить длину attach accent; добавить мягкую crossfade между landing families; при необходимости договориться о стабильных read-only event signals вместо inference/debug reason. Музыка, ambience, footsteps/material detection, occlusion и movement refactor сюда не входят.
