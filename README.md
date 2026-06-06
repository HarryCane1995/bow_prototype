# Bow Prototype

`bow_prototype` - FPS-прототип стрельбы из лука на Godot 4 C#.

Цель проекта - быстро настраивать и проверять ощущение движения, натяжения лука, выстрела и попадания.

## Project

- Engine: Godot 4 C#
- Main scene: `res://Scenes/BowPrototypeScene.tscn`
- Documentation: `Docs/`

## Docs

Подробности по текущему состоянию, архитектуре, правилам для Codex, пайплайну ассетов и ближайшим задачам лежат в папке `Docs/`.

Ключевое правило взаимодействий: не класть object-specific interaction logic в `PlayerController`. Player interaction code должен находить объект и вызывать общий контракт, а объект сам владеет своим поведением, анимацией, звуком и состоянием. Подробнее: `Docs/INTERACTION_ARCHITECTURE.md`.
