# Facade Factory WebGL Lab

## ART / TOOLING PASS — September 2026

Current: **SURFACE / VFX / BILLBOARDS**, a 50-material industrial library,
ten 3D mesh effects and twelve signage archetypes. Open the
[review gallery](http://127.0.0.1:8765/review.html) or
[ART_TOOLING_PASS.md](../../../../Docs/ART_TOOLING_PASS.md) for results,
measured storage, validation and limits. Original notes below describe earlier
passes. Storage is now guarded at 25/15 GiB and cache is periodically bounded.
The INDUSTRIAL LIBRARY is at the top of the Surface sidebar.

VFX extension: **VFX → MESH_EXPLOSION_3D** opens a mesh-driven explosion
constructor with runtime Godot scene export. The separate PSX_EXPLOSION sprite
prototype remains available. See [VFX Factory](../../../../Docs/VFX_FACTORY.md)
for controls, generated files, review scenes and validation.

## Recipe Library thumbnails

`★ FAVORITE` сохраняет неизменяемый снимок recipe и отдельный **WebP 256×160**
в `WebLab/favorites/<preset>_<seed>_<id>.thumb.webp`. Поле `thumbnail` в соседнем
`.facade.json` содержит только имя файла. Карточка показывает картинку 120×75,
preset, seed, resolution и время; клик по любой её части загружает recipe.

Миниатюра использует тот же Three.js PBR renderer, свет и карты, включая
composited weather/detail, palette, ORM, normal и emission strength. Камера
фиксирована; UNIQUE_FACADE использует BOX, TILEABLE_SURFACE — FLOOR_PATCH
с 3×3 повтором (с учётом tile_scale), CYLINDER_WRAP — CYLINDER. Orbit, debug
map и временные preview toggles не меняют снимок сохранённого материала.
Рендер выполняется только при сохранении favorite; библиотека читает файлы.

Старые recipes и отсутствующие картинки показывают `NO PREVIEW`; загрузка
recipe работает независимо. Автоперегенерации и отдельной галереи нет.
Rename/delete UI в текущей библиотеке отсутствует. При ручном переносе
favorite сохраняйте JSON и указанный в нём thumbnail рядом.

Проверка хранения/совместимости: `python Tools/Art/FacadeFactory/WebLab/qa_favorite_thumbnails.py`.

Обновление 0.4: [Semantic Palette Mixer](PALETTE_MIXER.md) — восемь ролей,
locks, восемь палитр, сохранение recipes и сравнение A/B/C рядом.

Обновление 0.3: независимые weathering/detail layers, CLEAN BASE и отдельный
экспорт detail-карт. См. [SURFACE_BREAKUP.md](SURFACE_BREAKUP.md).

Обновление 0.2: три surface modes, 12 новых presets и глобальный BOW_BASE
ArtProfile. Актуальное описание расширения, seam QA, recipes и exports:
[SURFACE_FACTORY.md](SURFACE_FACTORY.md). Ниже — исходная инструкция v0.1;
её утверждение о неизменённом canonical generator относится к первому UI pass.

Локальная оболочка над существующим FacadeFactory. Растры создаёт только Python;
Three.js отображает полученные карты. Gameplay, Level_01 и character systems не
затрагиваются. Внешних API, AI, CDN и сетевых шрифтов нет.

## Запуск

Из корня BowPrototype, тем же Python, которым запускается FacadeFactory:

```powershell
python Tools/Art/FacadeFactory/WebLab/server.py --open
```

Адрес: **http://127.0.0.1:8765/**. Другой порт: `--port 8766`.
Остановить foreground server: Ctrl+C. Если сервер уже запущен, достаточно открыть
адрес. Listener всегда привязан к `127.0.0.1`, не к `0.0.0.0`.
Зависимости Python прежние: `../requirements.txt`. Node/npm для запуска не нужны.
Three.js 0.180.0 включён в `web/vendor/` вместе с MIT license и manifest/hash.

## Работа

- Стартовый вариант: `INDUSTRIAL_TOWER`, seed `99`.
- Шесть preset загружают свои defaults; seed сохраняется при переключении.
- Primary: window_density, emission_density, structural_width, grime_amount,
  retro_strength. Advanced: window_aspect, floor_height, service_floor_frequency,
  dark_floor_frequency, panel_density, signage_density, macro_contrast.
- Ещё доступны emission_strength и 8 существующих stylizer settings:
  posterization, dithering, color_quantization, micro_contrast,
  compression_artifacts, pixel_noise, edge_exaggeration, baked_ao_strength.
- Числовое поле и slider связаны. Reset icon / double click slider возвращает
  default; RESET ALL сбрасывает параметры/палитру, сохраняя seed.
- RANDOMIZE SEED меняет только seed. RANDOMIZE WITHIN PRESET использует
  ограниченные диапазоны относительно текущего preset default.
- Три существующие палитры: Neutral cold, Industrial green, Dirty concrete.
- LMB/RMB drag вращает камеру, wheel меняет дистанцию; FRAME возвращает кадр.
- BOX, TALL_TOWER, WIDE_MEGABLOCK, TAPERED_TOWER — тестовые примитивы.
  UV X/Y, FIT ONE SHEET и TILE ×2/×4 меняют только preview, не PNG.
- MATERIAL / ALBEDO / EMISSION / NORMAL / ROUGHNESS / ORM / HEIGHT.
  Emission toggle действует только на preview; strength также сохраняется в recipe
  и экспортируемом Godot material. Roof/bottom используют нейтральный материал.
- PIN AS A фиксирует вариант. Дальнейшие изменения создают B; SHOW A / SHOW B
  переключает их. Favorite и export сохраняют именно отображаемый вариант.
- PREVIEW PNG скачивает **кадр Three.js**, а не albedo, в загрузки браузера.

## Favorites, export и возврат

`☆ FAVORITE` сохраняет полный versioned recipe в `WebLab/favorites/`.
Кнопка favorite в RECIPE LIBRARY восстанавливает preset, seed и все параметры.

`EXPORT TO PROJECT` принимает ASCII-имя, разрешение **512×1024 / 1024×2048** и
опцию Godot material (включена по умолчанию). Создаются пять PNG и `.facade.json`:

- Текстуры и recipe: `Assets/Textures/Levels/Level_01/FacadeFactory/`.
- ORMMaterial3D: `Assets/Materials/Environment/FacadeFactory/Generated/`.
- Занятое имя получает `_r02`, `_r03` и т.д. Файлы записываются эксклюзивно,
  существующие ассеты не перезаписываются. Результат показывает фактическое имя.

`LOAD RECIPE` открывает `.facade.json` через файловый диалог. Полностью
восстанавливаются preset, seed, palette, effective parameters и stylizer settings;
preview пересчитывается в 256×512, export dialog помнит production resolution.
Для точного воспроизведения экспортируйте в разрешении исходного recipe.
JSON содержит schema/version, generator version + fingerprint, UTC timestamp,
effective settings, overrides, filenames, SHA-256 и canonical generation metadata.
Recipe от другой версии генератора отклоняется с объяснением, без тихой подмены
defaults. Камера, geometry, UV tiling и emission on/off — настройки просмотра,
в raster recipe не входят. Старые CLI `.json` не заменяют WebLab `.facade.json`.

## Производительность и ограничения

Preview **256×512**, debounce **120 ms**. Одновременно выполняется один запрос
этой вкладки; промежуточные изменения объединяются, устаревшие ответы/texture
loads отбрасываются. Все пять карт меняются одним комплектом. Disk cache `.cache/`
адресуется hash от generator fingerprint + полного recipe + resolution.
Возвращение к готовому варианту не запускает генератор повторно.

На этой машине средняя чистая генерация по 6 presets — **333.8 ms**, диапазон
277.2–409.8 ms; cache lookup 0.3–0.5 ms. Это backend time, без debounce и GPU upload.
Production export из UI: 379 ms (512×1024), 554 ms (1024×2048) в проверочном прогоне.
Cache можно удалить при остановленном сервере; он восстановится. Автоочистки cache
в v0.1 нет. Не редактировать canonical Python при работающем сервере — после
изменения генератора нужен restart. WebGL2 требуется для Three.js renderer.

## Проверки и файлы

```powershell
python Tools/Art/FacadeFactory/WebLab/qa_backend.py
godot --headless --path . --script res://Tools/Art/FacadeFactory/WebLab/verify_exports.gd
```

`qa_backend.py` использует временные каталоги; проверяет 6 presets, deterministic
maps, replay в обоих production resolutions, favorites, no-overwrite suffix,
canonical parity, validation и существующий `--batch` на 24 варианта.
Он не перезаписывает существующие production sets и review contact sheet.
Godot check загружает два handoff exports, уже импортированных редактором.

- `server.py`: loopback HTTP/static/API и request validation.
- `lab_backend.py`: canonical adapter, cache, favorites, recipe и export.
- `web/index.html`, `styles.css`: интерфейс.
- `web/app.js`, `controls.js`: state, debounce, controls и workflow.
- `web/facade_viewer.js`: Three.js materials, camera, primitives и screenshot.
- `web/vendor/`: локальные Three.js модули, license, provenance.
- `qa_backend.py`, `verify_exports.gd`, `review/`: проверки и evidence.
- `.gdignore`, `.gitignore`: tool isolation и исключение временных файлов.

Исходные `facade_factory.py`, `facade_presets.py`, `facade_stylizer.py` не изменены.
Godot review остаётся `res://Scenes/Debug/Level_Facade_Review.tscn`.

Официальные соглашения material channels:
[Three.js MeshStandardMaterial](https://threejs.org/docs/pages/MeshStandardMaterial.html),
[OrbitControls](https://threejs.org/docs/pages/OrbitControls.html).
