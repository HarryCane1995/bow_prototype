# Bow Prototype

`bow_prototype` — FPS-прототип лука и скоростного перемещения на Godot C#.
Проект объединяет playable Movement Gym, модульного игрока, отдельные визуальные
ветки 1POV/3POV и экспериментальные инструменты создания уровней и окружения.
Это рабочий прототип; анимация, art и combat ещё развиваются.

## Открыть и запустить

Проверенный в проекте набор инструментов: **Godot 4.6.3 .NET / Forward+**,
**Blender 5.1.2**, **.NET SDK 9.0.200**. C# project использует
`Godot.NET.Sdk/4.6.3` и target framework `net8.0`.
Для Python art-tools нужны зависимости из
[`Tools/Art/FacadeFactory/requirements.txt`](Tools/Art/FacadeFactory/requirements.txt).

1. Клонировать репозиторий и открыть `project.godot` в Godot **.NET**.
2. Указать установленный Blender в настройках импорта Godot: основные карты
   импортируют `.blend` напрямую. Дождаться первого импорта.
3. Собрать C# project и нажать **F5**. Главная сцена —
   `res://Scenes/Levels/Level_01/Level_01.tscn`.
4. Для отдельного Freestyle открыть
   `res://Scenes/Levels/Level_Freestyle_01.tscn` и запустить текущую сцену
   (**F6 в редакторе**).

Из корня проекта, если `dotnet` и Godot Mono доступны в PATH:

```powershell
dotnet build Bow_prototype.sln
godot --headless --editor --path . --import --quit
godot --path . res://Scenes/Levels/Level_01/Level_01.tscn
```

Полный пайплайн и ограничения: [`Docs/blender_pipeline.md`](Docs/blender_pipeline.md).
Сгенерированные `.godot/`, `bin/`, `obj/` и локальные reference-пакеты в Git не входят.

## IMPLEMENTED — текущий runtime

- Общий игрок: `Scenes/Player.tscn`. WASD, jump/double jump с redirect,
  crouch/slide, airborne slide buffer, slide jump, canonical wallrun/wall jump
  и slingshot grapple. Slide использует правило «один жест — один вход»;
  wallrun требует parkour intent и повторно разрешает ту же поверхность после
  пространственного отделения или приземления.
- Лук: обычные light/charged shots и Alt precision shot, отдельный projectile,
  visual charge/release и существующее damage-взаимодействие. Gameplay aim
  принадлежит игровой камере; визуальные skeletons не управляют выстрелом.
- **V4 split — default presentation:** отдельные `MainCharacter1POV.tscn`
  (ARMS + FP CyberBow) и `MainCharacter3POV.tscn` (полное тело + world bow).
  Один read-only state observer маршрутизирует обе animation-ветки.
  Игровая камера независима от обоих skeletons; world body/legs не видны
  в обычном FP, включая Slide. V3, V2 и legacy сохранены для сравнения.
- Level_01: основной playable wrapper над `Level_01_Blockout.blend`.
  Отдельный Movement Gym —
  `Scenes/Levels/Level_Movement_Gym/Level_Movement_Gym.tscn`, маршрут для
  проверки traversal, wallrun и grapple с runtime review/tuning.
  `Level_CyberCity` остаётся дополнительной rooftop-сценой;
  `Scenes/BowPrototypeScene.tscn` — legacy playground.
- Процедурное аудио и runtime audio panel; opt-in movement trace для диагностики.
  Настройки игрока: `Resources/Tuning/DefaultPlayerTuningProfile.tres`,
  runtime tuning panel — F2.

Управление: **WASD** — движение, **Space** — прыжок, **Ctrl/C** — crouch/slide,
**Shift** — parkour intent, **E** — grapple, **ЛКМ** — натяжение/выстрел,
**Alt + ЛКМ** — precision, **ПКМ** — experimental combat gesture.
**Esc** освобождает курсор, **ЛКМ** захватывает его, **F1** перезапускает сцену.
**F10** — external review, **F12** — V4/V3, затем **F11** — V3/V2 и
**F9** — legacy; **F4** — FP drift, **F6 в игре** — audio panel, **F7** — mute.

## EXPERIMENTAL — authoring и незавершённые системы

- **RMB combat foundation:** tap/hold/parry windows, melee/recovery states,
  power-charge/release payload и animation hooks. Melee hit detection/damage,
  projectile reflection и отдельный power projectile ещё не подключены.
- **Character authoring:**
  `Assets/Characters/BaseHumanoid/Source/Humanoid_Male_PoseLab.blend` хранит
  независимые `BH01_1POV`/`BH01_3POV` rigs и indexed Actions. Capture/export
  scripts находятся в `Tools/Blender/HumanoidBase/`; runtime GLBs и sidecars —
  в `Assets/Characters/BaseHumanoid/Exports/`. Слоты и многие poses —
  placeholders, финального animation set нет. Humanoid base имеет отдельную
  `Humanoid_Base_Test.tscn`. Hero silhouette/mask studies и Hanzo research lab
  изолированы от Player; сторонние research assets остаются локальными.
- **Freestyle / Geometry Nodes:** текущий исходник —
  `Assets/Levels/Level_Freestyle_01/Source/Level_Freestyle_01.blend`, V06 graph.
  `Tools/Blender/GodotSnapshot/export_current.py` экспортирует evaluated graph
  в snapshot для Godot без перестроения ручных правок. Старые V02/V03 и
  LocalProxy V04/V05/V06 сохранены вместе с генераторами и manual test guidance.
  Coverage/metrics помогают review, но не доказывают полную проходимость.
- **Procedural environment lab:** Facade/Surface Factory, Material Intelligence,
  Billboard и VFX Factory. Библиотеки содержат 50 industrial material recipes,
  10 mesh VFX и 12 billboard archetypes. Запуск:
  `python Tools/Art/FacadeFactory/WebLab/server.py`, затем
  `http://127.0.0.1:8765/`. Godot review:
  `Scenes/Debug/ArtPassReview.tscn`. Это инструменты разработки и библиотеки
  прототипов; их наличие не означает завершённый art pass всех карт.
- **Highrise100:** exploratory kitbashing library — 100 building definitions
  в 20 families, генераторы, material recipes и переносимые textures.
  Blender source: `Art/Environment/Highrise100/Highrise100.blend`.
  Godot showcase: `Scenes/Environment/Highrise100_Showcase.tscn`.
  Interiors, collision, LOD и gameplay integration не реализованы.

## PLANNED — следующие этапы

Ручная анимация indexed 1POV/3POV Actions, дальнейшая доводка composition и
combat presentation, подключение RMB hit/parry/power consumers и человеческая
оценка movement/уровней. Эти этапы не входят в реализованный checkpoint.

## Документация и границы изменений

- [`Docs/CODEX_RULES.md`](Docs/CODEX_RULES.md),
  [`Docs/ARCHITECTURE.md`](Docs/ARCHITECTURE.md),
  [`Docs/INTERACTION_ARCHITECTURE.md`](Docs/INTERACTION_ARCHITECTURE.md).
- [`Docs/SPLIT_PRESENTATION_V4.md`](Docs/SPLIT_PRESENTATION_V4.md),
  [`Docs/RMB_COMBAT_FOUNDATION.md`](Docs/RMB_COMBAT_FOUNDATION.md),
  [`Docs/STICKY_SLIDE_GESTURE_FIX.md`](Docs/STICKY_SLIDE_GESTURE_FIX.md).
- [`Docs/GN_TO_GODOT_QUICKSTART.md`](Docs/GN_TO_GODOT_QUICKSTART.md),
  [`Docs/LOCAL_PROXY_V06.md`](Docs/LOCAL_PROXY_V06.md).
- [`Docs/ART_TOOLING_PASS.md`](Docs/ART_TOOLING_PASS.md),
  [`Docs/PROCEDURAL_MATERIAL_LIBRARY.md`](Docs/PROCEDURAL_MATERIAL_LIBRARY.md),
  [`Docs/VFX_FACTORY.md`](Docs/VFX_FACTORY.md),
  [`Docs/HIGHRISE100_SHOWCASE.md`](Docs/HIGHRISE100_SHOWCASE.md).

Отчёты отдельных passes описывают состояние на свою дату; для текущего runtime
приоритет имеют сцены, scripts и export sidecars. Геометрия/UV/material source
принадлежат Blender, gameplay и Godot wrapper logic — Godot. Не редактировать
`.godot/imported/` или generated GLB вместо его editable source. Object-specific
interaction logic остаётся у объекта и вызывается игроком через общий контракт.

Состав checkpoint, локальные исключения и ограничения воспроизводимости:
[`Docs/CHECKPOINT_2026-10-10.md`](Docs/CHECKPOINT_2026-10-10.md).
Источник и лицензия обязательного HDRI: [`THIRD_PARTY_ASSETS.md`](THIRD_PARTY_ASSETS.md).
