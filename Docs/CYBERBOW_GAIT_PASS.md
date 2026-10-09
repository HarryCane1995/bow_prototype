# CyberBow — procedural gait / step pass

2026-09-06. Прототип для ручной оценки; без commit / push.

К общему корню CyberBow и рук добавлен небольшой шаговый слой. Он накладывается на существующие W-drop и A/D-roll. World camera, movement, tuning, collision, shooting и audio в этом pass не менялись.

## Поведение

- Фаза интегрируется из фактической горизонтальной velocity игрока после movement; на месте цикл не идёт. `StepProgress` — непрерывное число шагов, целые пересечения чередуют ноги, два шага составляют полный цикл. Новые audio events не подключены.
- Вертикальный ритм содержит два шага на боковой цикл и небольшую асимметрию. Боковое смещение и roll слабее основного вертикального движения.
- Амплитуда насыщается при 18 м/с. На больших скоростях длина условного шага увеличивается, чтобы ограничить и cadence. Цикл остаётся связан со скоростью.
- В воздухе, slide, wallrun и grapple pull/launch фаза замораживается, остаток позы быстро затухает. После возвращения на землю фаза продолжается, амплитуда плавно нарастает.
- Draw использует существующий draw lock. При полном натяжении остаётся 2,5% gait. Фаза ног при этом продолжает идти по наземному движению.
- После отпускания draw амплитуда возвращается примерно за 0,25 с. Новая release-анимация не добавлена. В будущем release/recovery может удерживать передаваемый в `Evaluate` locomotion weight низким, не сбрасывая фазу.

## Настройки

Inspector: `PlayerViewModelSwayModule / MotionPrototype / Gait`.

| Параметр | Значение |
|---|---:|
| Step Distance | 5,5 м/шаг |
| Max Step Cadence | 4,2 шага/с |
| Minimum Speed | 0,2 м/с |
| Full Amplitude Speed | 18 м/с |
| Vertical Amount | 0,012 м |
| Lateral Amount | 0,006 м |
| Roll Degrees | 0,5° |
| Blend In / Out Speed | 12 / 24 с⁻¹ |
| Recovery Seconds | 0,24 с |

## Короткая проверка

`dotnet build --no-restore`: успешно, 0 warnings / 0 errors. `git diff --check`: без ошибок whitespace.

Просмотрены последовательности кадров из Godot runtime: idle, crouch walk как медленное движение, W, WA/WD, быстрый ground traversal, stop, jump/landing, slide/exit, движение с draw, full draw и release/recovery. Центр экрана остаётся свободным; ритм небольшой, directional roll читается отдельно. Оценка комфортности оставлена ручному прохождению.

Контрольные значения: медленное движение — 10,98 м/с; обычное — 18,3 м/с; быстрый случай — начальный импульс 36 м/с только во внешнем test driver. Амплитуда не превышала 1; при полном натяжении — 0,025; после остановки — 0. Slide удерживал одну фазу, после окончания шаги плавно возвращались. Первый slide-тест оказался длиннее стартовой площадки; его один раз повторили на существующем длинном landing у конца трассы. Геометрию не меняли.

Дополнительно один маршрут до первого grapple: 46,05 с, 0 recovery. На устойчивых кадрах wallrun, slide, grapple и свободного полёта cadence равен нулю. Это короткий visual smoke, не полный regression audit. Сохранилось ранее известное предупреждение legacy aim stabilization о пути `ArrowTipMarker`; этот pass его не исправляет и использует текущий B draw lock.

Внешние drivers, JSONL и runtime-кадры: `C:\Users\harry\Documents\Codex\2026-09-06\files-pasted-by-the-user-gameplay\work\viewmodel-gait\`.

## Изменённые файлы

- `Scripts/Player/ViewModel/ViewModelGait.cs` и автоматически созданный `.cs.uid`: отдельный генератор визуальной позы.
- `Scripts/Player/ViewModel/ViewModelMotionPrototype.cs`: подключение gait к существующей композиции B.
- `Scenes/Player.tscn`: дочерняя нода `Gait`, без изменения gameplay-параметров.
- `Docs/CYBERBOW_GAIT_PASS.md`: этот отчёт.

Сверка с 412 исходными файлами показала изменения только в двух перечисленных существующих файлах. Остальные исходные файлы сохранены побайтно.

Для ручной проверки выбран B. Gym запускается обычной сценой fullscreen, без synthetic driver; R / F1 и HUMAN RUN logger остаются штатными. F8 переключает весь существующий motion prototype B / legacy A, а не только gait. Для изолированного отключения gait есть `Enabled` на его ноде.
