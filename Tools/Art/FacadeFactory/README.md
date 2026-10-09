# Facade Factory 0.1 — BowPrototype

Детерминированный procedural raster toolset: Python + Pillow + NumPy. Без ImageGen,
diffusion, сетевых API, скачанных изображений и внешних шрифтов. Это первый art pass,
не финальное оформление Level_01.

## Запуск

Из корня проекта, Python 3.11. Установленные/проверенные версии закреплены в
`requirements.txt` (Pillow 12.3.0, NumPy 2.4.6).

```powershell
python Tools/Art/FacadeFactory/facade_factory.py --batch
python Tools/Art/FacadeFactory/facade_factory.py --preset corporate --seed 42 --width 512 --height 1024
python Tools/Art/FacadeFactory/facade_factory.py --preset industrial --seed 99 --width 1024 --height 2048 --config Tools/Art/FacadeFactory/industrial_dirty.example.json
python Tools/Art/FacadeFactory/facade_factory.py --preset industrial --seed 99 --set grime_amount=0.65 --set window_density=0.14 --set emission_density=0.18
```

`--batch` создаёт 6 presets × seeds **17, 42, 103, 271**, затем контактный лист и
software box preview. Измеренный финальный batch 512×1024: **8.661 с** на генерацию
PNG/JSON/materials, **9.462 с** вместе с preview. Импорт Godot измеряется отдельно.

По умолчанию совпадающие preset/seed/resolution перезаписывают свой комплект.
Overrides сохраняются в JSON каждого листа; для хранения сравниваемых настроек
используйте другую папку `--output` и `--materials` либо другой seed.
`--no-material` разрешает сохранять растры вне проекта.

## Где лежит результат

- `Assets/Textures/Levels/Level_01/FacadeFactory/`: 24 основных комплекта 512×1024.
- Там же `resolution_tests/`: по одному seed 42 каждого пресета в 256×512 и 1024×2048.
- `Assets/Materials/Environment/FacadeFactory/`: 24 готовых `ORMMaterial3D` и 12
  тестовых в `resolution_tests/`, плюс `review_settings.tres`.
- `Tools/Art/FacadeFactory/review/FACADE_FACTORY_REVIEW.png`: 24 подписанных albedo.
- `Tools/Art/FacadeFactory/review/FACADE_BOX_REVIEW.png`: шесть вертикальных объёмов.
- `Tools/Art/FacadeFactory/generated/batch_manifest.json`: seeds, размеры, SHA-256, время.
- `Tools/Art/FacadeFactory/review/GODOT_*.png`: кадры настоящего Godot Forward+.

Каждый комплект: `_albedo.png`, `_emission.png`, `_normal.png`, `_orm.png`,
`_height.png` и JSON с полным preset, этажными группами, состояниями окон и SHA-256.
ORM = **R AO / G roughness / B metallic**. Normal = **OpenGL +X +Y +Z**.
Стекло неметаллическое; exposed metal, paint, concrete, recess и glass имеют
разные roughness/metallic/AO. Умеренная normal вычисляется из высоты после resize.

## Шесть грамматик

| Preset | Alias | Основная структура |
|---|---|---|
| CORPORATE_MONOLITH | corporate | Четыре строгих вертикальных пролёта, длинные стойки, редкие световые линии |
| MEGABLOCK | megablock | Тяжёлые горизонтальные пояса, оконные группы, глубокие пустоты, технические ярусы |
| INDUSTRIAL_TOWER | industrial | Асимметричные сервисные зоны, панели, вентиляция, непрерывные воздуховоды, hazard strips |
| EXOSKELETON_TOWER | exoskeleton | Крупные диагональные связи поверх вторичной оконной сетки |
| OFFICE_GRID | office | Плотная регулярная сетка, occupancy-кластеры, тёмные/сервисные этажи |
| LANDMARK_TECH | landmark | Асимметричный световой ствол, крупные разрывы, длинные вертикальные акценты |

Структура: macro layout → zones → 8–20 floor groups → modules/windows → details
→ signage → wear → stylizer. Иерархические RNG потоки имеют стабильные SHA-256
ключи; Python `hash()` и глобальный random не используются. Состояния окон:
OFF, DIM, ON, BRIGHT, BLOCKED, SERVICE, BROKEN/DARK. Occupancy задаётся группой,
затем зоной и соседним кластером. Grime начинается от кромок, а не заполняет лист шумом.

## Управление художественным направлением

Все 13 основных параметров в `facade_presets.py` отделены от рендера. Через CLI:

| Параметр | Эффект | Диапазон |
|---|---|---|
| `window_density` | Доля оконных модулей вместо непрозрачных панелей | 0–1 |
| `emission_density` | Базовая occupancy оконных кластеров | 0–1 |
| `structural_width` | Толщина стоек и диагоналей | 2–32 design pixels |
| `grime_amount` | Интенсивность и число локальных потёков | 0–1 |
| `retro_strength` | Общая сила ретро-обработки | 0–1 |

Остальные: `window_aspect`, `floor_height`, `service_floor_frequency`,
`dark_floor_frequency`, `emission_strength`, `panel_density`, `signage_density`,
`macro_contrast`. В MVP `panel_density` управляет техническим заполнением
неоконных модулей. `emission_density=0` не отключает аварийные лампы и signage;
для полного отключения используйте strength или кнопку E.

Восемь отдельных `--style FIELD=VALUE`: `posterization`, `dithering`,
`color_quantization`, `micro_contrast`, `compression_artifacts`, `pixel_noise`,
`edge_exaggeration`, `baked_ao_strength`. Например `--style posterization=28`.
Мягкие AO и macro lighting считаются художественной частью albedo; data maps
не проходят цветовую стилизацию.

## Godot review и reusable material

```powershell
godot --path . --scene res://Scenes/Debug/Level_Facade_Review.tscn
```

**0 / ALL** — все здания; **1–8** и стрелки — одно здание; правая кнопка мыши —
orbit; колесо — zoom; **E** — emission on/off; **N** — normal on/off.
Не требуется Player или изменение Input Map. Настройки приложения не сохраняются.

В `review_settings.tres` доступны `emission_strength` (множитель энергии пресета),
`uv_scale`, `macro_tint`. `FacadeMaterialSettings.gd.make_material(source)` создаёт
частную копию готового `ORMMaterial3D`. Его можно использовать вне viewer;
кастомного шейдера нет. UVScale меняет масштаб выборки, у уникальных листов clamp:
это не обещание seamless tiling. Освещение review — нейтральная собственная сцена.
Описание ORM и normal-конвенции сверено с
[официальной документацией Godot](https://docs.godotengine.org/en/4.6/tutorials/3d/standard_material_3d.html).

## Review-копия существующих зданий

`Assets/Models/Environment/FacadeReview/Facade_Review_Buildings.blend` получен
чтением актуального `Level_01_Blockout.blend`; это отдельный source для review,
который Godot импортирует напрямую. Выбраны исходные башни 01, 03, 04, 05, 06,
07, 08, 10. Все сохранённые mesh-координаты, полигоны и модификаторы совпали.

Только в копии добавлены UV и material slots, изменены root display transforms,
удалены collision-only объекты и старые WindowBands, чтобы растровые окна были
видны без наложения старых световых квадов. Геометрия несущих частей, braces,
силуэты и hardware сохранены. Полная высота UV общая для башни; ширина проецируется
по connected mass, чтобы не сжимать целый лист на каждый маленький этажный блок.
Крыши сохраняют исходные материалы. 21 фасадная поверхность получает все четыре
runtime maps через overrides. Пути карт в Blender относительные, без packed images.

Создание копии повторно (перезаписывает **только review source**, поэтому после
ручных правок этой копии запускать осознанно):

```powershell
blender --background --factory-startup --python Tools/Art/FacadeFactory/prepare_review_blend.py
godot --headless --editor --path . --import --quit
```

`--factory-startup` относится только к отдельному фоновому процессу и отключает
посторонние пользовательские addons; активный Blender/MCP этим не сбрасывается.
В исходном Level_01 отсутствовали UV на этих башнях. Основной `.blend`, wrapper,
Player, movement, персонажи V2/V3 и project settings этим проходом не менялись.
В рабочем дереве есть ранее существовавшие и параллельные правки; их не откатываем.

## Быстрая проверка

```powershell
python Tools/Art/FacadeFactory/quick_qa.py
godot --headless --path . --script res://Tools/Art/FacadeFactory/validate_godot.gd
godot --path . --scene res://Scenes/Debug/Level_Facade_Review.tscn -- --capture-and-exit
```

QA проверяет все шесть пресетов дважды при 256×512, 512×1024, 1024×2048,
побайтовую идентичность PNG, seed divergence, config override и нестандартные
333×777. Проверены направление normal на аналитических ramps, длина normal,
семантика ORM и ненулевой ограниченный emission. Godot загрузил **36 материалов**,
у 21 применённой поверхности есть UV/tangents; работают три material controls.
Настоящие кадры emission on/off отличаются ниже области интерфейса.

Evidence: `review/quick_qa.json`, `blender_review_validation.json`,
`godot_validation.json`, `emission_render_check.json`, `scope_validation.json`.
Точный перечень созданных файлов: `review/file_manifest.json`.

## Границы MVP

- Листы уникальные и имеют оформленные верх/низ; seamless tiling не реализован.
- Архитектурный design grid 512×1024 фиксирует ритм при смене разрешения.
  1024×2048 сохраняет пиксельную структуру, а не добавляет новые этажи или детали;
  это намеренный nearest resize для ретро-языка. Произвольный aspect поддерживается,
  но сильно вытянутые форматы растягивают пропорции дизайна.
- Обратная физически корректная засветка окружения от emission не запекается.
- UV review — автоматическая проекция; production unwrap и устранение повторов
  signage на соседних сторонах остаются отдельным art pass.
- Карты и runtime проверены в Godot 4.6.3 / D3D12 Forward+. Pixel replay гарантирован
  для данного tool version, config и закреплённого Python/Pillow/NumPy окружения.

Commit/push не выполнялись.
