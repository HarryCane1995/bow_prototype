# Level Pipeline

Практичная шпаргалка по Blender -> Godot для `Level_01`.

## Основной поток

1. Править уровень в `Level_01_Blockout.blend`.
2. Держать Godot wrapper легким: `Scenes/Levels/Level_01/Level_01.tscn`.
3. Не редактировать импортированную Godot-сцену из `.blend` напрямую.
4. Godot импортирует `.blend` как `ImportedLevel`.
5. `ImportedLevelMarkerBinder` читает маркеры внутри `ImportedLevel` и создает runtime gameplay objects.

## Коллекции Blender

Рекомендуемая структура:

- `00_REF` - референсы, картинки, временные подсказки.
- `10_LEVEL_VISUAL` - видимый blockout/mesh.
- `20_COLLISION` - collision-only объекты для Godot.
- `30_GAMEPLAY_MARKERS` - gameplay markers: spawn, anchors, triggers.
- `40_ROUTE_NOTES` - стрелки/заметки маршрута, если нужны для дизайна.

## Видимые Объекты

Имена простые и читаемые:

- `Wall_RunHall_A`
- `Platform_Start`
- `Tower_Blockout_01`
- `Ramp_ToArena`

Не добавлять collision suffix к обычному visible mesh, если это не collision object.

## Collision Objects

Использовать Godot import suffix:

- `ObjectName_COL-colonly`
- пример: `Wall_RunHall_A_COL-colonly`

Правило: collision objects лежат в `20_COLLISION`, видимые объекты в `10_LEVEL_VISUAL`.

## Gameplay Markers

Маркеры лежат в `30_GAMEPLAY_MARKERS`.

Поддерживаемые имена:

- `PlayerSpawn` или `PlayerStart`
- `GrappleAnchor_01`, `GrappleAnchor_02`, ...
- `EnemySpawn_01`, `EnemySpawn_02`, ...
- `KillPlane`
- `FinishTrigger`

Binder распознает точное имя, `_suffix` и Blender-style `.001`.

Важно:

- Не использовать `-noimp`.
- Не использовать `-col` или `-colonly`.
- Это marker objects, не gameplay logic.
- Для grapple anchor можно использовать helper: `Tools/Blender/create_grapple_anchor_marker.py`.

## Grapple Anchors

Blender marker: `GrappleAnchor_01`

Runtime scene: `res://Scenes/GrappleAnchor.tscn`

`ImportedLevelMarkerBinder` создает runtime anchor под `Gameplay/GrappleAnchors` и копирует transform маркера.

## Lighting

Предпочтительно держать финальный playable lighting в Godot wrapper:

- `World/DirectionalLight3D`
- `World/WorldEnvironment`

Blender lights могут импортироваться в `ImportedLevel`. Binder имеет настройку:

- `DisableImportedLights = true` - старый flat-wrapper режим, импортированные lights отключаются.
- `DisableImportedLights = false` - Blender lights сохраняются в Play.

В `Level_01.tscn` сейчас imported lights сохранены. Binder трогает только lights внутри `ImportedLevel`, не `World`.

## Что Не Делать

- Не встраивать gameplay scenes в `.blend`.
- Не переносить C# logic в Blender.
- Не превращать `Level_01.tscn` в тяжелую сцену с level geometry.
- Не править generated imported scene вместо `.blend`.

## Быстрая Проверка

- В `.blend` есть `30_GAMEPLAY_MARKERS`.
- `GrappleAnchor_01` виден и лежит в этой коллекции.
- Collision objects имеют `-colonly`.
- В `Level_01.tscn` `Gameplay` содержит `ImportedLevelMarkerBinder`.
- `dotnet build Bow_prototype.sln` проходит.
