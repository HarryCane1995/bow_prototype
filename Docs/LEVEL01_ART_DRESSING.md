# Level_01 — размещение procedural art, 18.09.2026

В каноническом `Level_01_Blockout.blend` оформлены боевая трасса и тренировочный двор.
Новый декор — коллекция `70_LEVEL01_ART`, префикс `L01_ART_`, owner
`level01_industrial_dressing_v1`.

## Размещение

- 34 материала библиотеки: стены, настилы, потолки, корпуса и цилиндрические обёртки.
- 23 вывески из 10 archetypes: transit, service, warning, numeric, lightbox,
  offline, vertical neon, stacked, corporate, panel ad.
- 128 новых видимых meshes: пять сервисных станций, блок охлаждения,
  трубопровод с отводами и муфтами, щиты, шкафы, вентиляция, опоры вывесок.
- 46 отдельных коллайдеров новых твёрдых объектов.
- Два вентиляционных выброса и редкое искрение у электрощита — три экземпляра
  двух mesh-VFX библиотеки, без урона и взаимодействия с боем.
- Два сервисных светильника. Ambient переведён на цветовую подсветку
  (`source=2`, energy `0.85`) для читаемости PBR в тенях.

| Участок | Godot XYZ до смещения ImportedLevel |
| --- | --- |
| Вход | Transit-панель на укрытии; сервисный узел около `(78, 0, 35)` |
| Оконный переход | Numeric над проёмом; резервуар и щит около `(139, 0, -12)` |
| Высокая позиция | Lightbox на основании; вентиляция около `(141, 0, -49)` |
| Нижний обход | Панель над окном; резервуар около `(78, 0, -82)` |
| Финальная площадка | Offline-панель; сервисный узел около `(139, 0, -121)` |
| Внешняя полоса | Труба вдоль `x=146`, блок охлаждения около `(154, 0, -65)` |
| Тренировочный двор | Корпоративная панель, решётки, стояки, шкафы |

Крупный ранее оформленный пол, Atlas-пропы, робот, skyline, палитровые стенды,
игрок, враги, триггеры, точки grapple и боевые debug-надписи сохранены.
51 существующему архитектурному/боевому mesh назначены материалы и UV;
его геометрия и transform не менялись.

## Файлы

- Источник геометрии и UV: `Level_01_Blockout.blend`.
- Текстуры: `Assets/Textures/Levels/Level_01/ArtPass/`, 166 PNG с относительными
  Blender-путями; только используемые каналы, без height/displacement.
- Runtime ORM и список размещений: `Assets/Materials/Environment/Level01Art/`,
  `placement_manifest.json` содержит provenance и путь последней резервной копии.
- `Scripts/Editor/Import/Level01ArtMaterialLibrary.gd`: точная подмена материалов;
  существующий post-import hook вызывает её только для Level_01.
- `Scenes/Levels/Level_01/ArtAtmosphere.tscn`: VFX и свет, один инстанс в wrapper.
- `Tools/Environment/Level01Art/`: применение, настройки импорта, проверки.

`dress_level.py` сохраняет backup в `.godot/level01-art/` и проверяет отсутствие
параллельной записи исходника. Повторный запуск заменяет только декор с указанным
owner. Ручные изменения этого декора сначала перенести в script или сохранить
отдельной копией. Второй запуск проверен, дубликатов нет.

```powershell
blender --background --python Tools/Environment/Level01Art/dress_level.py
godot --headless --editor --path . --import --quit
python Tools/Environment/Level01Art/prepare_imports.py
godot --headless --editor --path . --import --quit
blender --background --python Tools/Environment/Level01Art/verify_source.py
godot --path . --script res://Tools/Environment/Level01Art/verify_runtime.gd -- --capture --player
```

`inspect_source.py` и `verify_runtime.gd -- --before --capture` создают исходные
контрольные снимки. Не перезаписывать before после внесения изменений.

## Проверка

- После повторного открытия `.blend`: 324 исходных объекта сохранили геометрию
  и transform; UV/материалы нетронутых объектов совпали. 166 изображений доступны
  по относительным путям и не упакованы внутрь `.blend`.
- Godot загрузил 44 ORM-ресурса (34 поверхности + 10 вывесок), 128 новых meshes
  и три VFX. D3D12 / Forward+, 1440×900.
- Все 155 исходных коллайдеров сохранили форму и положение. При разделении
  материалов importer меняет порядок треугольников боевых боксов: дополнительно
  проверены углы, плоскости, winding и площади граней.
- Новые коллайдеры не заходят на пять исходных боевых площадок; raycast
  в семи контрольных местах подтвердил пол.
- 178 защищённых соседних файлов совпали по SHA-256, включая gameplay,
  персонажей, второй уровень и `project.godot`.
- `dotnet build Bow_prototype.sln --no-restore`: 0 ошибок, 0 предупреждений.
- Реальный запуск wrapper и кадр от первого лица проверены. Полное ручное
  прохождение боевой трассы не выполнялось.
- Осталось прежнее предупреждение `PlayerViewModelSwayModule` об отсутствующих
  legacy aim references; оно было и в baseline.

Отчёты: `.godot/level01-art/source_validation.json`, `runtime_before.json`,
`runtime_after.json`, `after_final.log`, `build.log`. Текстуры с import-настройками
занимают около 2.34 MiB; `.blend` — 1.36 MiB. Свободно более 52 GiB.
Коммиты и push не выполнялись.

## Кадры из Godot

![Сервисный узел](Reviews/Level01Art/equipment.png)
![Блок охлаждения](Reviews/Level01Art/coolant.png)
![Первое лицо](Reviews/Level01Art/player.png)
![Общий вид](Reviews/Level01Art/overview.png)
