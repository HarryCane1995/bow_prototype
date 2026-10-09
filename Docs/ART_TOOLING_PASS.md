# BowPrototype — ART / TOOLING PASS, 18.09.2026

Готовы 50 industrial materials, 10 mesh-based VFX и 12 signage archetypes.
Коммитов и push нет. Gameplay, movement, персонажи, уровни и project.godot
сохранены: контрольные SHA-256 существующих защищённых файлов совпадают.

## Открыть результат

- [Review-галерея](http://127.0.0.1:8765/review.html): 12 материалов, 4 tiles,
  4 wraps, 10 реальных Godot VFX-кадров, 8 representative вывесок.
- [Surface Factory](http://127.0.0.1:8765/?tab=surface): **INDUSTRIAL LIBRARY**
  вверху sidebar → семейство → миниатюра → обычные controls/favorite/export.
- [VFX Factory](http://127.0.0.1:8765/?tab=vfx): **3D MESH EFFECTS** → archetype.
- [Billboards](http://127.0.0.1:8765/?tab=billboard): 12 типов, палитры, A/B,
  библиотека, seed/variation, export и recipe load.
- Godot: `res://Scenes/Debug/ArtPassReview.tscn`. Сцена запущена для review.
  Выбор Materials/VFX/Billboards и recipe; drag вращает камеру, wheel — zoom,
  стрелки выбирают соседний ассет, R перезапускает эффект.

Оставлены две браузерные вкладки: генератор и review-галерея, а также отдельное
окно Godot review. Сервер работает на обычном 8765; временный 8766 остановлен.
Повторный запуск: `python Tools/Art/FacadeFactory/WebLab/server.py` из корня.
Сервер слушает только 127.0.0.1.

## Materials: 50 рецептов

| Семейство | Количество | Примеры конструкций |
| --- | ---: | --- |
| Wall / panel | 12 | service spine, maintenance, corporate, megablock, reactor housing, reinforced plate, vent bank |
| Floor / walkway | 12 | diamond deck, grating, access tiles, hazard crossing, damp concrete, cable trench, rooftop |
| Ceiling | 6 | tech panels, utilities, cable trays, hatches, ventilation, light baffles |
| Cylinder wrap | 10 | pipe, tank, reactor, exoskeleton, vent shaft, utility pillar, insulation, conduits, coolant, pressure column |
| Specialized / accent | 10 | hazard, emissive service, door, console, casing, shutter, billboard support, hatch cluster, data center, monolith |

Полный каталог: `Assets/ProceduralArt/Materials/manifest.json`. Source recipes:
`Tools/Art/Library/materials/*.facade.json`. Runtime:
`Assets/ProceduralArt/Materials/<id>/material.tres`.

250 PNG: albedo, normal, ORM, height, emission для каждого материала; 50 WebP.
Tiles — 512×512, wraps — 512×1024. У всех 50 разные структурные height-карты.
Сохранены исходные 6 фасадных и 12 surface presets. Референсная основа —
локальный PureRef BOW_ENVIRONMENT_DNA: крупные спокойные плоскости, сервисные
трассы, обслуживаемые узлы, нейтральные покрытия и локальная warning-покраска.
Записи каталога содержат ID опорных рефов; пиксели рефов не копировались.

## Управляемая структура, шум и палитра

Структура отделена от finish. CLEAN BASE обнуляет macro variation, grime,
micro grain и retro artifacts. Новые defaults сдержанные: grain 0.025,
retro artifacts выключены. Dither/pixel noise остаются отдельными controls.

| Control | Что меняет |
| --- | --- |
| Albedo palette influence | Подмешивает палитру по семантическим маскам |
| Emission palette influence | Цвет emission при сохранении intensity mask |
| Weather tint influence | Цвет существующей маски grime |
| Material variation influence | Вариацию окраски модулей |
| Accent color usage — новый | Долю цветовых акцентов |
| Neutral to colored balance — новый | Баланс нейтрального и насыщенного цвета |
| Structural color separation — новый | Разделение base/secondary конструкции |
| Palette material response / ORM — новый | AO/roughness/metallic через material masks |

Normal/height не получают RGB tint, grime или micro overlay. В shipped batch
finish запечён в albedo/ORM; отдельный detail export остаётся доступен.
Проверены plane, box, wall corner, cylinder и column cluster. Tiles замкнуты
по X/Y, wraps — по X; верхние/нижние coupling bands намеренные.
Подробности: `Docs/PROCEDURAL_MATERIAL_LIBRARY.md`.

## VFX: десять разных mesh-прототипов

| Effect | Конструкция |
| --- | --- |
| MESH_EXPLOSION_3D | Faceted core, curved petals, ring, shards, smoke |
| SHOCK_RING | Концентрические кольца и радиальные зубцы |
| SPARK_BURST | Тонкие направленные искры и streaks |
| DIRECTIONAL_LIGHTNING | Сегментированный bolt, ветви и impact ring |
| ARC_CLUSTER | Пространственные дуги с endpoint nodes |
| LASER_IMPACT | Входящий луч, flare, impact plate и искры |
| PROJECTILE_TRAIL | Конечный сужающийся след, strands и motes |
| ENERGY_ORB | Faceted orb, три орбитальные полосы и satellites |
| SMOKE_BURST | Low-poly puffs с ростом, задержками и затуханием |
| DEBRIS_SCATTER | Угловатые обломки, траектории, вращение, spark tails |

Index: `Assets/ProceduralArt/VFX/library.json`. Каждый каталог содержит
настоящие OBJ, ShaderMaterials, analytic player, manifest, recipe, `effect.tscn`
и `review.tscn`. Совместимый alias `explosion.tscn` сохранён. Старые эффекты,
которые использует gameplay, не изменены; их OBJ hashes воспроизводятся точно.
PNG-последовательности не создавались.

UI: shape/layer controls, play/pause/restart/scrub, loop, camera presets,
bounded variation, JSON load/save, export и thumbnails. VFX favorites — максимум
12 в local storage текущего браузера; для переноса используйте recipe JSON.
CPU-миниатюры иллюстративные; VFX sheet в review получен настоящим Godot GPU.

## Neon billboard generator

12 archetypes: vertical neon, transit billboard, service strip, warning panel,
abstract panel ad, stacked signage, hologram, pseudo-glyph monolith, numeric code,
clean corporate, worn lightbox и inactive billboard. Без официальных логотипов.

Controls: aspect, glyph/data density, пять палитр и роли neon/accent/back/ink,
emission strength, wear, grime, border, support frame, hazard stripes.
Primary glyph scale показывается только у двух использующих его glyph-типов.
Буквы — собственный переносимый 5×7 bitmap-алфавит; псевдоглифы декоративные.

Экспорт: `Assets/ProceduralArt/Billboards/<id>/sign.tscn`, ORMMaterial3D,
albedo/emission/ORM PNG, WebP и `recipe.billboard.json`. Меши — маленькая
подложка и отдельный quad; hologram использует alpha и отключает подложку.
Источник — JSON/Python, отдельного .blend нет. Map/character Blender pipeline
не менялся. Preview на свободной панели и стене; есть A/B и file-backed favorites.
Неизвестный fingerprint отклоняется при load; устаревшие favorites не загружаются
молча. Занятое export-имя получает `_r02`, `_r03` и т.д.

Визуальный Godot QA поймал белую пересветку от emission ADD. Экспортёр исправлен
на MULTIPLY, режим проверяется runtime-тестом, все 12 sign-сцен пересняты.

## Что проверено

- Все 50 material recipes, пять каналов seam QA, нормали, 50 разных structures;
  representative seeds, palette/clean-layer isolation и точный PNG replay.
- Surface regression: 62 surfaces и 6 исходных facade byte-baselines.
  Palette regression: все 68 presets, 8 palette presets, intensity/channel
  isolation, export/favorites. Загружаются все 16 старых favorites.
- 7 VFX geometry/export tests; controls меняют output, 10 recipe/hash reloads,
  старый explosion сохраняет OBJ hashes.
- 12 billboards: deterministic replay, seed variation, color/ORM isolation,
  clean overlays; min/max каждого параметра. Export replay, no-overwrite,
  stale favorite и небезопасные имена проверены.
- Godot 4.6.3 / D3D12 Forward+ / RTX 5060: загружены 50 материалов и 12 signs;
  GPU-снимки просмотрены, проверены 5 форм preview.
- Все 10 VFX: loading, playback, pause, seek, loop, завершение ровно один раз,
  camera-independent geometry, независимость экземпляров. GPU capture PASS.
- Web UI: 3 вкладки, catalog filtering/thumbnail load, wrap seam PASS, VFX
  archetype/variation/favorite, billboard A/B; ошибок в console не было.
  Исправлены CSP для library CSS и переполнение preview на узком окне.
- API: previews, thumbnails, recipe/export/favorite contracts, origin/token
  guards. Проверены пороги storage 25/15 GiB с имитацией свободного места.

Evidence: `Tools/Art/ArtPass/review/*_qa.json`, `godot_art.log`, `godot_vfx.log`,
`godot_import_final.log`, `final_scope_storage.json`. GPU source frames находятся
в ограниченных `.godot/art-pass-review/` и `.godot/art-pass-vfx-review/`;
компактные переносимые contact sheets — в `Tools/Art/ArtPass/review/`.

## Диск и cleanup

Точные финальные значения: `Tools/Art/ArtPass/review/final_scope_storage.json`.
Старт: **61.20 GiB свободно**, проект **3.308 GiB**, включая .git/.godot.
После pass: **59.194 GiB свободно**, проект **3.275 GiB**. Изменение
всего C: больше изменений проекта; сам проект стал меньше. Посторонние
потребители диска в этом pass не диагностировались.

Новая runtime library — **7.75 MiB** с import sidecars. Главный прирост:
Godot cache/import **60.67 MiB**, библиотека **7.75 MiB**, ArtPass review/QA
примерно **4.87 MiB** на момент инвентаризации.
Удалены **104,755,008 bytes / 99.90 MiB** из 338 подтверждённых hash-cache entries.
Mesh preview history дополнительно ограничен 24 записями / 8 при дефиците.
Итоговое сравнение выявило **110.414 MiB** удалённого прежнего art-cache
(3463 файла; все удалённые art-пути находятся внутри `.cache/`).
Старые production assets, рефы, Git, favorites и неизвестные captures сохранены.
Аудит нашёл 405 MiB `.godot/fog-sea-v3.avi` и крупные reference/Git файлы;
без доказательства их ненужности они не удалялись.

Каждая запись WebLab проверяет свободное место и резервирует 15 GiB. Ниже 25 GiB
уменьшается cache budget; ниже 15 GiB generation/export блокируется. Запросы
сериализованы. Каждые 24 previews воспроизводимый cache сокращается к 128 MiB,
при дефиците — к 64 MiB, с сохранением свежих записей. Recipes/favorites/production
в cleanup не входят. Временные тестовые экспорты удалены после QA.

## Изменённые файлы

- `Tools/Art/FacadeFactory/`: `surface_archetypes.py`, `surface_factory.py`,
  `material_library.py`, `palette_mixer.py`, `build_material_library.py`,
  `qa_material_library.py`.
- `WebLab/`: `lab_backend.py`, `mesh_vfx_backend.py`, `billboard_backend.py`,
  `server.py`, `README.md`.
- `WebLab/web/`: `app.js`, `index.html`, `vfx_app.js`, `mesh_vfx_app.js`,
  `mesh_vfx_viewer.js`, `mesh_vfx.css`, `material_library.js/.css`,
  `billboard_app.js`, `billboard_viewer.js`, `billboard.css`, `review.html/.css`.
- `Tools/Art/VFXFactory/`: mesh schema/geometry/export, новые archetypes/families,
  thumbnail/library builder и runtime review template.
- `Tools/Art/BillboardFactory/`: generator, library builder, QA, `.gdignore`.
- `Tools/Art/ArtPass/`: storage guard/inventory/cleanup, integration QA, review
  composition, final report tooling и evidence.
- `Tools/Rendering/`: `art_library_review.gd`, `verify_art_library.gd`,
  `verify_vfx_library.gd` и созданные Godot UID.
- `Scenes/Debug/ArtPassReview.tscn`, этот отчёт,
  `Docs/PROCEDURAL_MATERIAL_LIBRARY.md`, `Docs/VFX_FACTORY.md`.
- Новые recipes в `Tools/Art/Library/materials/`; runtime — `Assets/ProceduralArt/`.

Полный перечень новых/изменённых art-путей — в scope report. Проверены SHA-256
177 существующих защищённых файлов; изменений нет. Generated imports
созданы Godot и вручную не правились. Существующий dirty working tree сохранён.

## Ограничения и следующий полезный pass

Это готовая библиотека для прототипа, а не утверждённая отделка всего уровня.
Grilles/vents — непрозрачные material skins; height не создаёт displacement.
Для глубоких труб/раскосов и силуэта нужны отдельные меши. Wrap top/bottom
не обязаны замыкаться. Browser/Godot tonemapping и alpha sorting отличаются;
Mobile/Compatibility не проверялись. VFX без collision/audio/gameplay hookups,
динамических lights и bloom. Trail — конечный local −Z wake, не history recorder.
Вывески используют фиксированные процедурные layouts, без произвольного Unicode.

Следующий разумный шаг: выбрать 8–12 рецептов для конкретных зон Level_01 /
CyberCity, настроить UV density и свет в масштабе уровня, профилировать выбранные
VFX на игровой дистанции, затем подключать их к событиям. Размещение в уровнях
в этом проходе не начиналось. Работа остановлена на готовом review.
