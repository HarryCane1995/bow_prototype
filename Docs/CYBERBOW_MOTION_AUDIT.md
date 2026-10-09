# CyberBow — visual / kinematic audit + prototype B

2026-09-06. GOOD ENOUGH, до ручного просмотра. F8 переключает **A CURRENT / B NEW**. По умолчанию B. Canonical wallrun B — отдельная настройка, она сохранена.

1. **Текущая структура, перепроверенная в runtime.** Отдельный SubViewport → ViewModelRoot → ViewModelSwayRoot. Внутри последнего BowViewModelHolder и уже существующие FirstPersonHands. Holder содержит скрытый Bow_ViewModel с AnimationPlayer/Draw и видимый CyberBowViewModelOffset/CyberBow_ViewModel с Bow_Visual и Arrow_Visual. Draw имеет семь tracks, направленных только на старый BowRig/Skeleton3D. В новом CyberBow этого рига нет. Видимый корпус остаётся жёстким; рука, тетива и декоративная стрела уже двигаются отдельным FirstPersonHands. Поэтому прежний диагноз «видимый лук вообще не показывает charge» теперь неточен.

2. **Самое слабое в A.** Почти горизонтальная конструкция растянута по нижнему краю. Состояние натяжения показывает в основном правая рука, корпус не передаёт усилие. При быстром traversal предмет выглядит слишком независимым от тела.

3. **Недостающие движения.** Нет отдельного различия ascent/fall, отклика на вертикальное ускорение и общего release корпуса. Нет упругой деформации плеч CyberBow. Последнюю в этот pass не добавлял: для неё потребуется работа с исходной моделью.

4. **Избыточность и конфликты.** В A большой gain движения быстро упирается в clamps; горизонтальные translation/rotation от мыши частично взаимно компенсируются. Acceleration вычисляется между render frames при обновлении velocity в physics ticks. Посадочный сдвиг при текущем tuning 0.1 m на m/s быстро достигает лимита 0.12 m. Floor snap иногда стирает скорость падения до обнаружения посадки. Ограничитель aim stabilization сейчас не работает: отсутствует ArrowTipMarker; это существующее предупреждение, не новая ошибка.

5. **Camera turns.** В A slow yaw и разворот 180° дают менее различимую массу, чем ожидается от чисел sway; возврат дополнительно размазан несколькими фильтрами. B переводит mouse delta в angular rate, фильтрует и ограничивает её; translation/rotation направлены согласованно. В просмотренных сериях yaw, pitch, combined look и коротких коррекций лук отстаёт яснее и быстро возвращается без колебательного overshoot. Чувствительность камеры не менялась. Субъективную комфортность длительной игры оценивает ручной тест.

6. **Jump / fall / landing.** B опускает конструкцию при положительной vertical velocity/ускорении и слегка поднимает при падении. Посадка даёт короткую compression с плавным затуханием, сила зависит от падения. Скорость текущего спуска запоминается до контакта, чтобы floor snap не съедал отклик. Air jump и grapple launch используют тот же наблюдаемый velocity/acceleration; slide и wallrun добавляют небольшую позу. Camera wall roll не копируется целиком. Внешние контрольные падения, включая вход с 42 m/s horizontal speed, просмотрены в Gym.

7. **Draw / charged / release.** Старую Draw-анимацию и existing hand/string driver сохранил. B добавляет плавную tension-позу всей связки по существующему DrawAmount и короткий release по ShotVisualSequence. Full draw удерживается спокойно, без случайной дрожи; повторные выстрелы перезапускают один ограниченный импульс. Precision сохраняет существующий поворот holder на −65° и прежнее скрытие Arrow_Visual на 0.15 s. Projectile создаётся по gameplay Camera/ShootPoint; визуальная стрела и SwayRoot не определяют направление выстрела.

8. **Framing.** В Godot сравнены roll −6°, −10°, −18°. Выбран −10°: −18° слишком приближает левое плечо к рабочей зоне, −6° сохраняет почти плоский силуэт. Общая camera-space поправка B: (0.045, −0.020, −0.160) m, без изменения масштаба ассета. В precision базовый roll плавно исчезает по фактическому наклону holder, горизонтальный offset возвращается к нулю. Viewmodel FOV остаётся 65°; gameplay FOV не изменён.

9. **Архитектура.** Новый ViewModelMotionPrototype генерирует pose: base + look + physics-sampled body/speed/ability + draw + landing/release. Единственный владелец записи SwayRoot — существующий PlayerViewModelSwayModule, который выбирает A или B. A сохраняет прежний алгоритм. Суммарные динамические offsets B ограничены 0.085 m и 4.5°, отдельно от base/precision. В precision процедурное движение ослабляется до 35%. Тетива, руки и лук следуют общему pivot, без двух конкурирующих writers.

10. **Procedural / animation.** Camera и locomotion — процедурные фильтры с physics sampling. Draw — детерминированная smoothstep-кривая от готового состояния; release/landing — заданные короткие envelopes, без random shake и накопления recoil. Новых AnimationPlayer clips нет. Существующий скрытый Draw и минимальный rig рук сохранены. Для prototype это меньше работы и надёжнее, чем перенос старых bone tracks на несовместимую модель.

11. **Ограничения для рук.** Руки уже были добавлены предыдущим pass; здесь их mesh, rig и IK не менялись. Общая связка сохраняет grip и nock, оставляет место предплечьям. Это по-прежнему blocking: нет полноценной деформации плеч лука, тонкой работы пальцев или физического взаимодействия с окружением. Отдельный render layer предотвращает пересечение с геометрией мира визуально, но не моделирует контакт оружия со стеной. В precision верхнее плечо по-прежнему выходит за кадр, как и в A. В просмотренных B-позах near-plane clipping и скачков масштаба не заметил.

12. **Выбор после просмотра.** Предпочитаю B: диагональ лучше отделяет силуэт от горизонтального края кадра, turn response читается, jump/landing и shot имеют разные акценты. Центральная зона остаётся свободной. Это готовый кандидат для короткого ручного сравнения, не финальная анимация.

Проверки: build — 0 errors / 0 warnings; git diff --check — PASS. A прошёл Gym за **95.97 s**, 0 recovery. Первый B сорвался на grapple в cell 22; один повтор прошёл весь Gym за **95.92 s**, 0 recovery, 28 shots, включая 14 в воздухе, 13 launch frames. Это разные живые прогоны с небольшими различиями подачи input, не доказательство покадровой детерминированности и не новый speed benchmark. После локальной правки распознавания landing выполнены короткие A/B контрольные jump/air-jump, acceleration/brake, падения, rapid shots и heavy landing с charge/release. В B контрольном run общий dynamic peak: **0.0702 m / 2.74°**, внутри ограничителей. Визуально просмотрены кадры и последовательности реального Godot-render, а не только telemetry.

Изменённые файлы этого pass:

- `Scenes/Player.tscn` — ссылка на новый visual script и дочерний MotionPrototype; прежние правки prefab сохранены.
- `Scripts/Player/Modules/PlayerViewModelSwayModule.cs` — выбор одного A/B генератора позы.
- `Scripts/Player/ViewModel/ViewModelMotionPrototype.cs` и `.uid` — новый visual module.
- `Docs/CYBERBOW_MOTION_AUDIT.md` — этот отчёт.

Blender assets, руки, BowVisual/shooting, projectile, movement, wallrun, slide, grapple, tuning profile, project settings и геометрия не менялись в этом pass. Внешние scripts/captures находятся в `work/viewmodel-motion` соседнего audit workspace и не входят в production resources. Commit / push не выполнялись.
