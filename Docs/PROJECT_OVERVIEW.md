# Project Overview

`bow_prototype` - это FPS-прототип стрельбы из лука на Godot 4 C#.

Цель проекта - добиться приятного ощущения лука, движения и стрельбы: чтобы перемещение, наведение, натяжение тетивы, выстрел и попадание ощущались отзывчиво и понятно.

## Текущий статус

- Общий FPS-персонаж собран в `Scenes/Player.tscn` и используется level-wrapper сценами.
- Movement включает jump/double jump, crouch/slide, wall run и slingshot grapple.
- Лук поддерживает light, charged и precision shot; projectile остаётся отдельной сценой.
- Основной playable-уровень импортируется напрямую из `Level_01_Blockout.blend`.
- `Level_CyberCity` служит отдельным уровнем для rooftop/cybercity окружения.
- Runtime Tuning Panel меняет общий `PlayerTuningProfile` во время Play.

## Главная сцена

Главная сцена проекта:

`res://Scenes/Levels/Level_01/Level_01.tscn`

Дополнительный текущий уровень:

`res://Scenes/Levels/Level_CyberCity/Level_CyberCity.tscn`

Обе сцены остаются лёгкими wrapper-сценами: gameplay-контейнеры и Godot-окружение принадлежат wrapper, а редактируемая геометрия — соответствующему `.blend`-источнику. Старый `Scenes/BowPrototypeScene.tscn` сохранён только как legacy playground и не является источником истины для игрока или запуска проекта.

Текущие значения настройки хранятся в `Resources/Tuning/DefaultPlayerTuningProfile.tres` и `Scenes/Player.tscn`; `Docs/TUNING_NOTES.md` описывает порядок работы с ними без дублирования чисел.

## Архитектурные правила

- Общая модульная архитектура описана в `Docs/ARCHITECTURE.md`.
- Правило взаимодействий описано в `Docs/INTERACTION_ARCHITECTURE.md`: игрок выражает намерение, а объект сам владеет своим поведением, анимацией, звуком и состоянием.
- Blender/Godot asset workflow описан в `Docs/blender_pipeline.md`.
