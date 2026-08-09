# Tuning Notes

Этот файл фиксирует не копии чисел, а источники истины и порядок сохранения tuning-настроек. Дублированные списки значений быстро устаревают и не должны использоваться как конфигурация проекта.

## Источники истины

- Общие gameplay-настройки: `res://Resources/Tuning/DefaultPlayerTuningProfile.tres`.
- Структура игрока, NodePath и локальные fallback-поля модулей: `res://Scenes/Player.tscn`.
- Runtime-интерфейс: `res://Scenes/Debug/RuntimeTuningPanel.tscn`.
- Временное runtime-сохранение: `user://player_tuning_runtime.json`.

`Scenes/BowPrototypeScene.tscn` является legacy playground. Его локальные overrides не переносятся автоматически в общий prefab и не считаются актуальными дефолтами.

## Порядок настройки

1. Запустить `Level_01` или `Level_CyberCity`.
2. Открыть Runtime Tuning Panel клавишей `F2`.
3. Проверить изменение параметров в gameplay.
4. Сохранить удачные значения в project defaults через панель.
5. Проверить diff `DefaultPlayerTuningProfile.tres` и убедиться, что не изменены посторонние сцены.

Gameplay feel нельзя переносить между сценами копированием отдельных scene overrides. Все level-wrapper сцены должны получать один и тот же `Scenes/Player.tscn` и общий tuning profile.
