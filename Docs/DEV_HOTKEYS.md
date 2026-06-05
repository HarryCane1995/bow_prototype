# Dev Hotkeys

Проект поддерживает несколько dev-действий для удобства Play Mode.

## Управление мышью

- `Esc` - освобождает курсор и переключает `Input.MouseMode` в `Visible`.
- `ЛКМ` по игровому окну - снова захватывает курсор и переключает `Input.MouseMode` в `Captured`.

Mouse look обрабатывается только когда курсор захвачен.

## Перезапуск сцены

- `F1` - полностью перезапускает текущую сцену через `GetTree().ReloadCurrentScene()`.

## InputMap

`PlayerLookModule` гарантирует наличие runtime actions:

- `ui_cancel` -> `Esc`
- `reload_scene` -> `F1`

Это сделано в коде, чтобы hotkeys работали без ручной настройки `project.godot`.

