# Project Overview

`bow_prototype` - это FPS-прототип стрельбы из лука на Godot 4 C#.

Цель проекта - добиться приятного ощущения лука, движения и стрельбы: чтобы перемещение, наведение, натяжение тетивы, выстрел и попадание ощущались отзывчиво и понятно.

## Текущий статус

- Есть FPS-персонаж.
- Есть WASD movement.
- Есть jump.
- Есть mouse look.
- Есть crosshair.
- Есть projectile arrows.
- Есть light shot и charged shot.
- Есть bow viewmodel с Draw-анимацией.
- Есть target hitboxes.
- Есть modular blockout blocks.

## Главная сцена

Главная сцена проекта:

`res://Scenes/BowPrototypeScene.tscn`

Текущие удачные Inspector-настройки фиксируются в `Docs/TUNING_NOTES.md`.

## Архитектурные правила

- Общая модульная архитектура описана в `Docs/ARCHITECTURE.md`.
- Правило взаимодействий описано в `Docs/INTERACTION_ARCHITECTURE.md`: игрок выражает намерение, а объект сам владеет своим поведением, анимацией, звуком и состоянием.
