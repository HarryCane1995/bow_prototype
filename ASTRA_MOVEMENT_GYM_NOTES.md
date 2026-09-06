# Movement Gym — practical envelopes

2026-09-06. Godot 4.6.3 Mono, Jolt, 60 physics ticks/s. Исходная рабочая версия включает несохранённые в Git исправления wallrun/grapple из Astra audit. Существовавшие 267 tracked files и ASTRA_GAMEPLAY_AUDIT.md защищены SHA-256 snapshot (268 файлов). PLAYER/TUNING CHANGES: **NONE**.

## Измерение перед построением трассы

Внешняя Calibration.tscn: исходный Scenes/Player.tscn, большой ровный пол, одна стена и исходный GrappleAnchor prefab. Каждый case начинает с новой копии сцены. Teleport применяется только для начальных условий измерения. После старта движение получается из реального Input и MoveAndSlide в графическом runtime. На полной трассе начальные условия — только штатный spawn; драйвер не пишет position, velocity, rotation или параметры игрока.

Расстояние до первого возврата на пол включает текущее floor snap поведение. Это практическая дальность при данных вводах, не точный баллистический максимум. Камера, gravity, air acceleration и профиль не подстраивались.

| Case | Измерено | Первоначальный запас для main route |
|---|---|---|
| Jump from rest + W | 8.53 m, пик 2.42 m, около 0.68 s до floor | Не требовать больше 5–6 m без разбега |
| Running jump | 12.51 m, пик 2.42 m | Основные обычные gaps 6 m |
| Run → jump → air jump через 18 ticks | 23.04 m, пик 5.60 m, около 1.20 s | Диагонали около 18–20 m с широкой landing area |
| Slide → jump, W удерживается | 15.73 m, пик 2.42 m | Gap 11 m; не ставить посадку на предельную дальность |
| Wallrun после обычного jump | Около 44.9 m до возвращения на пол, пик 4.21 m; 80 активных ticks | Простые wall gaps 24 m, стены заходят на approach/landing |
| Wallrun 18 ticks → wall jump | Пик 10.51 m; смещение до пола X=15.67, Z=28.18 m; 1.22 s после wall jump | Противоположные стены на расстоянии около 9 m между гранями |
| Wallrun → wall jump → air jump через 26 ticks | Пик 13.39 m; X=8.85, Z=32.55 m; 1.55 s | Вторую стену вводить раньше первого landing, не требовать same-wall exploit |
| Grapple, anchor на Y=10, 15 m по горизонтали | Pull 30 ticks; exit (0,22.06,-33.09), speed 39.77 m/s; первое landing примерно 55.5 m от старта pull | Большая площадка после anchor; высокий близкий anchor даёт длинный перелёт |
| Grapple, 30 m по горизонтали | Pull 46 ticks; exit (0,12.61,-37.83), speed 39.87 m/s; первое landing примерно 64.9 m от старта pull | Anchor 20–35 m впереди; landing начинается до расчётного касания |
| Grapple, 45 m по горизонтали | Pull 64 ticks; exit (0,8.66,-38.96), speed 39.91 m/s; первое landing около 77.6 m от старта pull | Не использовать край радиуса 50 m для обязательного main route |
| Grapple, 52 m по горизонтали | Не активирован; расстояние с высотой превышает MaxGrappleDistance=50 | Полный acquisition envelope ограничен range, направлением, screen assist и LOS |

Anchor всегда находился в центре камеры. Это измерение range, а не доказательство всех screen-space углов. В первом course build anchors стоят в открытом пространстве, над разрывом, с просматриваемой landing area. Стены не перекрывают sweep капсулы по pull-траектории.

## Переходы и ограничения

- Ground run 18.3 m/s; slide начинается с 40 m/s; slide-jump cap 35 m/s; wallrun 33 m/s; pull cap 50 m/s. Скорость после transition может затем уменьшаться обычным input response — это сохранено.
- Wallrun имеет вертикальную дугу, а не постоянную высоту: начальный подъём сменяется снижением. Для основной трассы нужен ранний выход и широкая посадка.
- Wall jump даёт Y=27.1 и lateral impulse=24.4; air jump после него меняет горизонтальную траекторию. Поэтому измерения с удержанным W и с диагональным вводом нельзя смешивать.
- Grapple запускается одним нажатием E. Его отпускание не прекращает pull. После launch действует существующий control lock примерно 0.73 s; landing нельзя рассчитывать исходя из немедленного полного air control.
- Wallrun → grapple проверяется на полной трассе в MIXED/MASTERY; camera ray не заменяет проверку проходимости капсулы.
- Same-wall cooldown 2 s сохранён. Основная chain использует противоположные world normals, а не разворот возле той же поверхности.

## Материалы измерения

Внешняя рабочая папка: `C:\Users\harry\Documents\Codex\2026-09-06\files-pasted-by-the-user-gameplay\work\gym`. `measure-plan.json`, `measure_driver.gd`, `trace-measure.jsonl`, `measure.log`. Итерации и результаты полных проходов зафиксированы в ASTRA_MOVEMENT_GYM_REPORT.md. Это достаточные ориентиры для первого graybox, а не попытка доказать максимальную дальность или все возможные углы наведения.
