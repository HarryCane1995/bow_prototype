# Surface Factory 0.2 / BOW_BASE

0.3 adds a clean material stage and optional breakup layers. Current layer/export
contract and comparison: [SURFACE_BREAKUP.md](SURFACE_BREAKUP.md). The original
0.2 baked renderer described below remains selectable as Legacy.

Additive extension: исходные шесть UNIQUE_FACADE preset и их Legacy raster output
сохранены. `facade_presets.py` и `facade_stylizer.py` не изменены. Runtime сцены,
gameplay, Level_01, персонажи и movement systems этим инструментом не меняются.

## Открыть

```powershell
python Tools/Art/FacadeFactory/WebLab/server.py --open
```

Сервер остаётся локальным: `http://127.0.0.1:8765/`.

- [Tile example](http://127.0.0.1:8765/?mode=TILEABLE_SURFACE&preset=INDUSTRIAL_FLOOR)
- [Wrap example](http://127.0.0.1:8765/?mode=CYLINDER_WRAP&preset=REACTOR_CORE_WRAP)
- [Facade A/B](http://127.0.0.1:8765/) — INDUSTRIAL_TOWER / 99, кнопка
  **A LEGACY ↔ B BOW_BASE**, затем SHOW A / SHOW B. Структура, seed, camera и UV
  общие; меняется только art treatment.

## Режимы и пресеты

| Режим | Presets | Preview | Production |
|---|---|---|---|
| UNIQUE_FACADE | прежние CORPORATE_MONOLITH, MEGABLOCK, INDUSTRIAL_TOWER, EXOSKELETON_TOWER, OFFICE_GRID, LANDMARK_TECH | 256×512 | 512×1024, 1024×2048 |
| TILEABLE_SURFACE | TECH_WALL, INDUSTRIAL_FLOOR, SERVICE_PANEL, MEGABLOCK_WALL, ROOF_SURFACE, DARK_CONCRETE_TECH | 256×256 | 512×512, 1024×1024 |
| CYLINDER_WRAP | PIPE_HEAVY, COLUMN_TECH, TANK_WRAP, VENT_SHAFT, REACTOR_CORE_WRAP, EXOSKELETON_COLUMN | 256×512 | 512×1024, 1024×2048 |

Новые surface controls: tile_scale, panel_scale, grout_width, surface_wear,
macro_variation, seam_visibility, floor_markings_density, wall_module_density.
Cylinder controls: circumference_modules, vertical_band_count, ring_density,
vertical_seam_count, service_hatch_density, emission_band_density, pipe_grime_flow.
Они воздействуют на соответствующие детали выбранного preset: wall modules не
создают окна на полу, floor markings — редкая техническая маркировка.
`tile_scale` меняет повторение в preview и generated Godot material, не raster layout.

## Глобальный ArtProfile

Архитектура сначала строится прежними правилами. Sidecar buffers записывают
material ID, seam class, module ID и authored edges без обращений к architecture
RNG. Его namespace `STRUCTURE_RNG_VERSION = 0.1.0` закреплён отдельно от release
version. `BOW_ART:1.0` имеет независимый RNG. ArtProfile применяется после структуры.
`LEGACY` — точный bypass нового treatment, воспроизводящий старые пять карт.

Глобальные поля: panel_outline_strength, seam_contrast, material_variation,
macro_grime_strength, macro_grime_scale, saturation, baked_lighting_strength,
detail_contrast, module_irregularity. `macro_grime_scale` — количество крупных
областей поперёк листа: больше число означает меньший размер пятна.

**Illustration → Material** ослабляет authored outlines, edge exaggeration,
posterization/quantization severity, saturation и baked lighting; добавляет
медленную вариацию материала, macro grime и неодинаковые joins. Число уровней
posterization и число palette colors растут к 256: это уменьшает эффект квантования.

**Clean → Weathered** увеличивает macro grime, discoloration, variation между
панелями, долю replacement patches и вертикальные streaks. Meta sliders задают
согласованные глобальные значения и сбрасывают ручные art overrides; девять полей
ниже позволяют их уточнить. При переключении facade preset глобальный profile
сохраняется. `module_irregularity` меняет finish/repair variation, не координаты,
размеры или наличие структурных модулей.

| Класс шва | Назначение |
|---|---|
| DEEP_RECESS | реальные глубокие разрывы, окно/вентиляция, сильный локальный AO |
| NORMAL_SEAM | стык панели средней глубины и контраста |
| SUBTLE_JOIN | неглубокое соединение с небольшим тональным перепадом |

| Material class | Roughness base | Metallic base | Treatment |
|---|---:|---:|---|
| PAINTED_METAL | .76 | .035 | dielectric paint, broad variation, restrained edges |
| RAW_METAL | .49 | .82 | exposed metal, stronger edge response |
| GLASS | .23 | 0 | low variation, controlled reflections |
| CONCRETE | .94 | 0 | broad discoloration, soft edges |
| VENT | .82 | .38 | rough technical metal and recessed louvres |
| RECESSED_VOID | .98 | 0 | deep shadow, almost no surface variation |

Grime/edges дополнительно меняют roughness и metallic. Не каждый preset обязан
содержать все классы: у пола, например, нет стеклянных окон. Emission layout и
height структурного фасада при смене Legacy/BOW_BASE остаются прежними.

## Seamless и review

TILEABLE_SURFACE всегда использует FULL_2D_TILE. Примитивы рисуются на торе:
часть модуля, вышедшая за край, продолжается с другой стороны с тем же module ID
и finish. Поля вариации периодические; streaks и фильтры учитывают противоположные
края. У normal используются периодические центральные производные и wrap blur.
Выход — замкнутая область с продублированной конечной строкой/колонкой; пять карт
проходят отдельную проверку равенства граничных texels (max delta = 0).

CYLINDER_WRAP всегда периодичен по X. **HORIZONTAL_WRAP_ONLY** сохраняет
контролируемые верх/низ; **FULL_2D_TILE** включает повтор по Y. В первом режиме
держите UV Y = 1 для единой композиции: бесшовность по Y не заявляется.

Preview geometries: прежние четыре здания + Plane, Floor Patch, Wall Corner,
Cylinder и Column Cluster. Панель **SURFACE REVIEW** переключает Plane 3×3,
Wall Corner и Cylinder. **SEAM ZONE** отмечает оранжевым область U=0/1; это
диагностический overlay, в PNG material maps он не попадает. В режиме MATERIAL
цилиндр направлен стыком к камере, чтобы его было удобно проверять.

## Export / favorites / recipes

Папки прежние:

- `Assets/Textures/Levels/Level_01/FacadeFactory/`: 5 PNG (albedo, normal, ORM,
  emission, height), `.facade.json`, `_preview.png`, `_tiled_preview.png`,
  `_seam_debug.png` для новых режимов.
- `Assets/Materials/Environment/FacadeFactory/Generated/`: ORMMaterial3D `.tres`,
  включён repeat; checkbox экспорта material по умолчанию включён.
- `Tools/Art/FacadeFactory/WebLab/favorites/`: сохранённые recipes.

`_preview.png` нового режима — воспроизводимый CPU review (3×3 tile или cylinder),
`_tiled_preview.png` — раскладка 3×3, `_seam_debug.png` — она же с границами тайлов.
Кнопка **PREVIEW PNG** отдельно скачивает настоящий кадр текущего Three.js preview.
Базовые карты остаются без текста, рамок и seam overlays.

Recipe schema v2 хранит mode, preset, seed, tile mode, resolution, palette,
effective structural/style fields, ArtProfile, meta settings, overrides, resolved
global controls, generator fingerprint, output names/hashes и canonical metadata
с seam QA. `LOAD RECIPE` восстанавливает mode, preset, seed и controls; затем
генерирует быстрый preview. Для production replay используются прежние resolution
и настройки. Дубли имён получают `_r02`, `_r03`; исходные файлы не меняются.
Recipes schema v1 от исходного генератора распознаются и мигрируют в Legacy;
проверен побайтный replay исходного `industrial_99_weblab.facade.json`.

## QA и ограничения v0.2

```powershell
python Tools/Art/FacadeFactory/WebLab/qa_surfaces.py
python Tools/Art/FacadeFactory/WebLab/qa_backend.py
godot --headless --path . --script res://Tools/Art/FacadeFactory/WebLab/verify_surfaces.gd
```

Проверки: 6 Legacy outputs и raw structure buffers против baseline; 3 seam/6
material classes; 12 новых пресетов; deterministic cache; все 5 карт по X/Y;
cylinder full-2D option; production export/reload и no-overwrite; v1 migration;
старый CLI `--batch` на 24 вариантах. Evidence: `review/art_direction/`.

Новые previews тяжелее Legacy: примерно 0.6–1.2 с на этой машине, в зависимости
от режима; debounce 120 мс, latest-request wins и cache продолжают работать.
Процедурные рисунки повторяются с выбранным tile period — seamless не означает
отсутствия видимой повторяемости. В v0.2 нет displacement/parallax, true geometric
damage, автоматического LOD или индивидуального потолочного/cap texture atlas.
UV transforms и geometry — настройки просмотра, кроме сохранённого `tile_scale`.
Raw data maps не фильтруются color stylizer; normal остаётся OpenGL convention.
При изменении canonical Python нужен restart server; неизвестный fingerprint
recipe отклоняется, чтобы не выдавать изменённый raster за точный replay.

## Файлы этого расширения

Добавлены: `facade_semantics.py`, `facade_art_profiles.py`, `surface_factory.py`,
`WebLab/qa_surfaces.py`, `WebLab/verify_surfaces.gd`, этот документ и QA evidence.
Изменены: `facade_factory.py` (semantic sidecar + art dispatch, frozen RNG version,
опциональные CLI art flags), `WebLab/lab_backend.py` (mode dispatch, recipe v2 и
экспорт), `WebLab/web/{index.html,app.js,controls.js,facade_viewer.js,styles.css}`,
`WebLab/.gitignore`, `WebLab/README.md`.
Добавлены два review exports `surface_industrial_floor_99*` и
`surface_reactor_core_99*` и их generated materials. Старые outputs сохранены.
