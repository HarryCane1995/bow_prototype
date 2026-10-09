# Original FP drift → MainCharacter1POV

18 сентября 2026. Узкий runtime presentation pass; без Blender, новых анимаций, commit/push.

## 1. Фактический источник

Первая версия `Scripts/Player/Modules/PlayerViewModelSwayModule.cs` найдена через Git в **4a22f21 — Add slide upgrades and viewmodel sway (2026-06-07)**. Проверены сам файл, `Scenes/Player.tscn`, `Resources/Tuning/DefaultPlayerTuningProfile.tres` и добавления следующего коммита `c5ef2b3`.

Оригинал писал local Position/RotationDegrees узла `ViewModelSwayRoot` относительно сохранённого neutral transform. Под ним находился `BowViewModelHolder`. Позднее legacy FirstPersonHands использовали тот же root, поэтому эффект передавался рукам вместе с луком. Самая первая Git-версия ещё предшествовала этим рукам/CyberBow; в visual A/B использованы сохранившиеся legacy art/руки с исходной математикой.

Текущий fallback уже содержит поздний `ViewModelMotionPrototype`, draw lock, gait и shot motion. Они не использованы как baseline. Текущий tuning также имеет другие величины mouse lag `0.056 / 5.6`; здесь восстановлены именно первые `0.015 / 1.5`, подтверждённые исходным сериализованным профилем.

## 2. Компоненты эффекта

- Mouse position offset, pitch/yaw и небольшой roll.
- Инерция от изменения горизонтальной velocity, спроецированной на горизонтальные оси камеры.
- Landing position/pitch impulse при переходе air → grounded.
- Экспоненциальное следование/возврат: `1 - exp(-speed * dt)`.

Grounded bob, циклического gait, реакции непосредственно на WASD, общего drift от абсолютной camera orientation или нового spring solver в исходнике нет. Они не добавлены.

## 3. Исходные коэффициенты

| Параметр | Перенесённое значение |
|---|---:|
| Mouse position / rotation amount | 0.015 / 1.5° на pixel/frame |
| Mouse position / rotation clamp | 0.08 m / 5° |
| Mouse roll multiplier | 0.35 |
| Movement position / rotation amount | 0.004 / 0.35° |
| Forward inertia position multiplier | 0.4 |
| Movement position / rotation clamp | 0.10 m / 6° |
| Acceleration magnitude clamp (legacy name VelocityClamp) | 40 |
| Landing min / max impact speed | 4 / 24 m/s |
| Landing position / rotation amount | 0.025 / 2° |
| Landing position / rotation clamp | 0.12 m / 8° |
| Follow / return / impulse return speed | 12 / 10 / 14 |

Сохранён и исходный порядок: суммы mouse + inertia → follow/return smoothing; landing impulse отдельно затухает → складывается с результатом → общий clamp. Дополнительные mouse input/output filters 18/12 и rotation smoothing 14 появились позже и в этот port не включены. V3 параметры независимы от gameplay tuning profile.

## 4. Новый additive root и порядок обновления

`FPSpace → FPPresentationBase → FPDriftRoot → FPUpperBody → Skeleton3D → hand.L / CyberBow`.

`FPPresentationBase` и `FPDriftRoot` добавлены с identity transform; прежние FP root calibration, FOV 65°, torso/arms framing и bow scale 0.62 сохранены. Камера и свет остаются прямыми детьми FPSpace.

На render-frame в существующем V3 process priority 20:

1. Drift transform временно сбрасывается в identity.
2. Вычисляются FP animation и существующий neutral wrist stabilizer.
3. Из `PlayerLookModule.ConsumeLookDelta()` читается принятый за этот render-frame mouse input; world camera к этому моменту уже опубликована V2.
4. На общий FPDriftRoot накладываются position/rotation offsets.

Wrist не пытается компенсировать cosmetic drift. Torso/arms/bow наследуют один и тот же transform. Старый `FpBowAimErrorDegrees` остаётся диагностикой **neutral wrist до additive drift**, а не ошибки косметического bow относительно reticle после sway. Projectile aim не использует FP rig.

FPSpace/base/drift/body имеют interpolation OFF; настройки Player physics body не менялись. Ни одного camera writer или обратной связи из FP в camera не добавлено.

## 5. Input и FPS

Mouse delta берётся из существующего look accumulator после обработки input, без отдельного input owner. Во время F9 fallback его снова читает legacy module. При выключении drift/переходе из hybrid/освобождении мыши offsets сбрасываются; при новом включении stale delta отбрасывается.

Movement inertia читает текущую velocity и grounded state; camera basis — текущий render-frame, не предыдущий physics-camera transform. Автоматический grapple camera snap сам по себе не превращается в mouse input, как и в оригинале.

**Ограничение оригинала сохранено:** smoothing/возврат используют dt, но mouse amplitude зависит от pixels per render-frame. При одинаковой скорости мыши эффект слабее на 240 FPS, чем на 60. Нормализация по mouse speed стала бы изменением исходного поведения и здесь не вводилась.

## 6. Draw / aim

В `4a22f21` нет draw/full-draw attenuation и вообще нет aim stabilization в sway-модуле. Stabilization через ArrowTipMarker появилась лишь в следующем `c5ef2b3`, а draw lock — значительно позже. Поэтому новый port **не уменьшает drift при RMB hold/full draw** и не создаёт новой charge logic, согласно условию ТЗ «если её не было — не придумывать».

Нынешний V3 wrist stabilizer сохранён и вычисляется до root drift. Проверен RMB anticipation → ready/draw → full draw: общий FP transform не разрывает grip и не вызывает борьбы двух корректоров.

## 7. Slide / wallrun / grapple

Во время slide drift получает только FP torso/arms/bow. World LEGS, locked trajectory и pelvis не меняются. При wallrun L/R сохраняется исходный roll gameplay camera; дополнительная компенсация/инверсия не введена. Короткая проверка дала противоположные camera roll ±19.5°. Grapple acquisition/launch и camera assist остались рабочими.

Legacy CanvasLayer, FirstPersonHands, procedural slide legs, MotionPrototype и старый sway-модуль в обычном V3 остаются отключены. Для requested visual A/B они включались только во внешнем тестовом A-preview; это не часть нового runtime path.

## 8. A/B и Inspector

**F4 — DRIFT ON/OFF**, только в hybrid 1POV. F7 оставлен audio mute; F8 — старый fallback motion toggle; F9/F10/F11 не изменены.

Inspector у `Player/MainCharacterV3`:

- `FPDriftEnabled`, `FPDriftWeight` (0 = прежний neutral, 1 = original baseline).
- `MouseDriftWeight`, `MovementSwayWeight`, `LandingSwayWeight`, `RollWeight`.
- Исходные amount/clamp/follow/return настройки в отдельных FP Drift groups.

Debug readout показывает ON/OFF, F4 и общий weight. `FPDriftPosition`, `FPDriftRotationDegrees`, `FPDriftLookDelta` доступны для read-only наблюдения.

## 9. Файлы и проверка

Созданы `Scripts/Player/Presentation/MainCharacterV3.FPDrift.cs` и UID, этот отчёт.

Изменены `Scripts/Player/Presentation/MainCharacterV3.cs`, `MainCharacterV3.FP.cs`, `Scenes/Characters/MainCharacter1POV.tscn`, `Docs/HYBRID_PRESENTATION_SCENES.md`, `AGENTS.md`.

V2, MainCharacter3POV, MouseLook, gameplay camera, movement/slide/wallrun/grapple, RMB, projectile, FP slots, BH01 sources/animations, CyberBow art, Player scene и tuning не изменялись.

GOOD ENOUGH checks:

- Build: 0 ошибок/предупреждений.
- Slow yaw/pitch, circles, flick и stop/return; run + mouse; real slide; wallrun L/R; RMB full draw; grapple.
- Weight 0 даёт identity root и прежний neutral bow transform; F4 выключает сразу. FP wrist и bow-to-root transform не меняются из-за sway.
- В hybrid legacy canvas/processes отключены, world body visibility и slide trajectory сохранены.
- Прямой A/B: одинаковая 4-секундная последовательность synthetic mouse input; A — исходная math из Git на legacy art, B — новый FP root. Временный original reference class удалён после проверки.
- После одинакового сброса initial state исходная формула и port совпали в пределах float rounding: max position delta ≈ 6e-9 m, rotation ≈ 4e-7°. До сброса fixture сравнение ловило разные стартовые transient offsets; production code для этого не менялся.
- Capture runs при cap 60: фактически около 55–57 FPS с сохранением PNG; отдельный sanity при cap 240 — около 239 FPS. В обоих случаях stop возвращает нейтраль. Визуально просмотрены A/B frames, slide и оба wallrun.

Артефакты вне production: `.godot/fp-drift/ab_result.json`, `result.json`, logs, PNG; видео `.godot/fp-drift/legacy_vs_hybrid.mp4` (**A слева, B справа**). В `result.json` первый общий smoke сохраняет initial-state parity failure; остальные gameplay/visibility/zero-weight assertions там прошли. `ab_result.json` — успешное повторное сравнение с исправленной инициализацией fixture. Внешний replay и snapshot reference source также сохранены в этой папке, не подключены к production.

Остались прежнее startup warning legacy ArrowTipMarker и renderer cleanup `indexing did not unpair geometries from light` на завершении отдельных тестов. Новых C# / scene-load ошибок нет.

## 10. Отличия от legacy и handoff

Другая геометрия рук/torso, размер и neutral placement лука, один новый FP skeleton, прежняя hybrid камера. Поэтому screen-space рисунок не pixel-perfect, при совпадающей sway-математике. Вся композиция дрейфует вместе; никаких новых Actions, gait или draw lock нет. Зависимость амплитуды от FPS сохранена и остаётся возможным отдельным design choice после просмотра.

Gym передаётся fullscreen: **V3 HYBRID / 1POV / DRIFT ON / weight 1**, настоящий input. Commit/push не выполнялись. STOP.
