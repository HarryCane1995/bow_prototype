# Dev Workflow

## Startup Window Mode

При запуске `BowPrototypeScene` через Play игра может автоматически открываться на primary monitor и переходить в fullscreen. Это поведение включает root-node `StartupWindowModeController` в сцене `res://Scenes/BowPrototypeScene.tscn`.

Контроллер находится в:

`res://Scripts/System/StartupWindowModeController.cs`

По умолчанию:

- `EnableStartupWindowMode = true`;
- `ForcePrimaryScreen = true`;
- `StartFullscreen = true`;
- `UseExclusiveFullscreen = false`;
- `ApplyDeferredOnReady = true`.

Обычный `Fullscreen` предпочтителен для разработки: он менее агрессивен при Alt-Tab и удобнее, когда Godot/editor/runtime tuning panel остаются на другом мониторе. `ExclusiveFullscreen` можно включить вручную в Inspector через `UseExclusiveFullscreen`, если нужен настоящий эксклюзивный полноэкранный режим.

Если нужно временно вернуть обычный запуск окна, выключи `EnableStartupWindowMode` или отдельно отключи `ForcePrimaryScreen` / `StartFullscreen` в Inspector у `StartupWindowModeController`.
