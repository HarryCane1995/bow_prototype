"""Rebuild final presentation boards and source-grounded handoff report."""
from pathlib import Path
import json,sys,shutil,hashlib,collections
from PIL import Image,ImageDraw,ImageFont
ROOT=Path(__file__).resolve().parents[3];OUT=ROOT/'Art/Environment/Highrise100'
sys.path.insert(0,str(Path(__file__).parent));from catalog import board
data=json.loads((OUT/'manifest.json').read_text());rs=data['buildings'];materials=json.loads((OUT/'materials.json').read_text())
best=[dict(next(r for r in rs if r['id']==i),previews=[f'Previews/{i}_mood.png']) for i in data['curated_best']]
board(best,OUT/'Mood/Best12.jpg','BOW / 12 CANDIDATES / DUSK',4,280)
used={k for r in rs for k in r['material_slots'].values() if k in {m['key'] for m in materials}}
materialboard=Image.new('RGB',(1280,6*190+60),(17,24,30));draw=ImageDraw.Draw(materialboard);font=ImageFont.truetype('C:/Windows/Fonts/consola.ttf',12)
draw.text((16,18),f'46 PROCEDURAL RECIPES / {len(used)} ASSIGNED / 5 RETAINED OPTIONS',font=font,fill='white')
for i,m in enumerate(materials):
    x=i%8*160;y=60+i//8*190;im=Image.open(OUT/'Textures'/m['key']/'albedo.png').convert('RGB');im.thumbnail((146,154));materialboard.paste(im,(x+(160-im.width)//2,y))
    draw.text((x+4,y+158),m['key'][:24],font=font,fill=(192,212,211));draw.text((x+4,y+174),'ASSIGNED' if m['key'] in used else 'OPTION',font=font,fill=(111,170,177))
materialboard.save(OUT/'Materials.jpg',quality=92)
source=json.loads((OUT/'QA/source_validation.json').read_text());runtime=json.loads((OUT/'GodotSanity/runtime_validation.json').read_text());cleanup=json.loads((OUT/'QA/cleanup.json').read_text())
roles=collections.Counter(r['role'] for r in rs);triangles=sum(r['metrics']['triangles'] for r in rs);h=[r['bounds_m'][2] for r in rs]
preview_paths=[p for r in rs for p in r['previews']];assert len(preview_paths)==145 and all((OUT/p).is_file() for p in preview_paths)
assert source['passed'] and runtime['passed']
families='\n'.join(f"| {i*5+1:03}–{i*5+5:03} | {family} | 5 |" for i,family in enumerate(data['families']))
tools='\n'.join('- `'+p.relative_to(ROOT).as_posix()+'`' for p in sorted((ROOT/'Tools/Environment/Highrise100').glob('*')) if p.is_file())
size=sum(p.stat().st_size for p in OUT.rglob('*') if p.is_file());free=shutil.disk_usage(ROOT).free
report=f'''# Bow Prototype — Highrise 100

Завершён самостоятельный exploratory pass: **100 высоток**, 20 семейств по 5 конструктивных подтипов.
Роли: **{roles['background']} background / {roles['midground']} midground / {roles['hero']} hero**.
Высоты с крышным оборудованием: **{min(h):.1f}–{max(h):.1f} м**. Совокупная геометрия: **{triangles:,} треугольников**,
на одно здание **{min(r['metrics']['triangles'] for r in rs)}–{max(r['metrics']['triangles'] for r in rs)}**. Это намеренно очень лёгкие формы для skyline и дальнейшего kitbashing.

## Просмотр и исходник

- [index.html](index.html) — автономный каталог: поиск ID/признака, семейство, роль, сортировка по высоте/полигонам.
- [Highrise100.blend](Highrise100.blend) — общий редактируемый источник; 100 asset-marked коллекций `HR001…HR100`.
- [ContactSheet_All.jpg](ContactSheet_All.jpg) — все 100 индивидуально вписанных силуэтов.
- [CommonScale.jpg](CommonScale.jpg) — все 100 фронтальных видов в **одном физическом масштабе**, вертикальный кадр 600 м.
- `ContactSheets/` — 4 листа по 25 и 20 листов по семействам.
- `Previews/` — 100 основных нейтральных кадров, 33 дополнительных ракурса, 12 атмосферных = **145 превью**; у здания 1–3 кадра.
- [Mood/Best12.jpg](Mood/Best12.jpg), [Mood/Skyline.png](Mood/Skyline.png) — дополнительные презентации настоящих мешей.
- [manifest.json](manifest.json), `Cards/HRxxx.json` — размеры, subtype, role, seed identity, mesh metrics, geometry hashes, material slots/recipes/seeds, 10 diagnostic axes.
- [References/CATALOG.html](References/CATALOG.html) и [References/GAME_REFERENCES.html](References/GAME_REFERENCES.html) — исследование.

Открыть `index.html` можно непосредственно в браузере без сервера. Сейчас также доступен просмотр на `http://127.0.0.1:8768/index.html`.
Для переноса в другой Blender-файл: **File → Append → Highrise100.blend → Collection → нужный HRxxx**.
Коллекция содержит root в локальном основании `(0,0,0)` и отдельные группы мешей: масса, каркас, сервис, крыша, реклама.
Сцена `Library_100` показывает экземпляры этих коллекций сеткой; её display offsets не записаны в исходные коллекции.
Сцены `Neutral_Preview` и `Atmosphere_Review` — презентационные. Их свет, камеры, ground и fog не входят в отдельные building assets.
Папка исключена из автоматического импорта основного проекта через `.gdignore`.

## Покрытие

| ID | Семейство | Количество |
|---|---|---:|
{families}

OLD+NEW — пять maintenance-вариантов с отдельными наружными лифтами, steel frames, трубами, сменными модулями и оборудованием.
В HR056 и HR059 старые корпуса преимущественно бетонные; окна — отдельные объёмные полосы, новая техника геометрически отделена.

## Материалы и параметры

Подготовлено **46 рецептов / 230 карт**, из них **{len(used)} рецептов реально назначены зданиям**.
24 фасадных листа получены существующим FacadeFactory: 6 грамматик × 4 конфигурации, 512×1024.
16 SurfaceFactory-рецептов взяты из существующей библиотеки проекта с сохранёнными картами и provenance.
Ещё 6 панелей сделаны существующим BillboardFactory. 5 неиспользованных вариантов оставлены как небольшие готовые опции.
Все производственные карты детерминированные; ни референсные фото, ни приложенная картинка не использованы как textures.

Channels: albedo/emission sRGB, normal/ORM/height data; ORM = AO/roughness/metallic. В blend назначены albedo, normal, roughness/metallic, emission и glTF occlusion.
Height сохранён как исходный канал, displacement не включён. Карты общие, не размножены по одному комплекту на здание; пути `//Textures/...`.

Фасадные параметры: emission_density 0.12/0.30/0.54/0.73, design floor_height 22/28/36/44 px,
window_aspect 0.55/0.85/1.45/2.1, grime_amount 0.12/0.26/0.43/0.59; выбор материал-семейства зависит от назначения здания.
Facade sheets использованы как отдельные UV-области/crops с clamp, не обещаны бесшовными.
На мелких hardware-деталях используются surface maps. Номинальный floor pitch 3.3/4.1/4.8/3.6/5.4 м;
на высоких/сужающихся массах crop/stretch делает реальный оконный ритм приблизительным — это не проект этажных планов.

Geometry recipes — 100 явно заданных конструкций и размеров. Поле `seed` фиксирует identity рецепта;
геометрия не получена случайным jitter одного меша. Материальные seeds реально используются фабриками и сохранены отдельно.
Десять art-direction axes — геометрические/материальные proxies, `old_new` — авторская оценка. Это не area-weighted perceptual measurements.

## QA и выполненные корректировки

- Все 100 сохранённых коллекций повторно открыты из `.blend`: UV есть, карты разрешаются по относительным путям, локальные основания корректны.
- **100/100 geometry-only signatures уникальны**, хеш исключает material/part names. Визуальный QA выполнен по всем основным кадрам и 33 обратным ракурсам.
- Независимый QA проверял партии 25/50/75/100, coverage, похожие группы, крышное оборудование, материалы и диск.
- Исправлены подиумный зазор и roof-over-courtyard, расширена развилка HR037, HR040 переработан в сервисный ствол с крупными pods,
  HR050 — в полый industrial court, рекламные поверхности получили оригинальные BillboardFactory sheets и mounts.
- По референсам усилены широкие transit/civic/mixed_use массы и два concrete-majority retrofit.
- Godot **4.6.3**, прямой `.blend` import: **6 образцов**, {runtime['mesh_instances']} mesh instances, {runtime['uv_surfaces']} UV surfaces,
  {runtime['textured_surfaces']} textured/normal/emission surfaces, {runtime['triangles']} треугольников; реальный runtime кадр — [GodotSanity/Godot_Six_Samples.png](GodotSanity/Godot_Six_Samples.png).
  Образцы: HR007, HR029, HR047, HR057, HR064, HR097. Это ограниченная sanity-проверка, не импорт всех 100 и не QA паркура.
- Каталог открыт в браузере: 100 карточек; поиск HR059 даёт 1, maintenance — 5, hero — 12.
- Контрольные SHA-256 существующих Level_01, CyberCity, Player, wrapper, project.godot и прежнего Skyscraper_Kit совпали с началом задачи.

## Кандидаты для следующего отбора

HR007 Inhabited Gate — большая сквозная пустота; HR012 Service Spine — функциональные сервисные ярусы;
HR026 Screen Sail — крупная реклама; HR037 Bifurcated Needle — раздвоенная skyline-игла;
HR047 Cooling Hourglass — глухая индустриальная форма; HR055 Octagon Regency — ретро-гранёный профиль;
HR060 Plant Cathedral — OLD+NEW; HR064 Splayed Cage — открытый каркас;
HR070 Tripod Lantern — поднятый landmark; HR073 Platform Funnel — инфраструктурная масса;
HR089 Stacked Districts — разные строительные слои; HR099 Helix Citadel — вращающиеся объёмы.
Это выбор для показа диапазона библиотеки, не утверждение объективного рейтинга.

## Исследование

49 curated entries: **40 разных реальных architecture/urbanism sources + 9 отобранных официальных игровых кадров**.
Реальные refs: 33 локальных Commons изображения с автором/лицензией, 5 remote-image карточек и 2 source-link-only.
Все локальные принятые фото и 9 игровых кадров просмотрены; полный визуальный QA 5 удалённых изображений не заявляется.
10 тематических contact sheets, принципы Ghostrunner/Deus Ex HR и feedback по партиям лежат в `References/RESEARCH_BRIEF.md`.
Production использует только формальные правила; конкретные здания не трассировались 1:1.

## Ограничения

Это exploration и база для kitbashing. Нет интерьеров, LOD, световых развёрток, игровых коллизий, навигации, проверенных traversal routes,
финальной инженерной логики всех опор или интеграции в текущий Level_01. Очень простые формы намеренно опираются на материал и силуэт.
Близкие родственники остаются (например ступенчатые HR006/031, rounded transit HR073/075); QA признал их конструктивно различными.
Общий тёмный оконный язык и несколько HVAC/tank/exhaust helpers заметно повторяются. Это известный предел текущей поверхности, а не скрытые дубли.
Hero здесь означает силуэтную роль, не высокую детализацию. Нельзя считать весь набор production-polished.
MCP был недоступен: использован Blender Python в отдельных background-процессах. Активная пользовательская Blender-сцена не переключалась.
Godot subset находится в отдельном тестовом проекте; производство и gameplay не менялись.

## Диск и очистка

На момент отчёта весь пакет со справочными материалами, превью и Godot sanity-кэшем: **{size/1024**2:.1f} MiB** (около {size/10**9:.3f} GB).
Свободно **{free/1024**3:.2f} GiB**. Исходник `.blend`: {(OUT/'Highrise100.blend').stat().st_size/1024**2:.2f} MiB.
Это существенно ниже заданного консервативного бюджета ~60 GB. Генераторы останавливаются при свободном остатке <30 GiB.
Удалены только собственные промежуточные данные: scratch-output фабрики после каждого рецепта и **100 common-scale PNG tiles, {cleanup['removed_bytes']/1024**2:.2f} MiB**,
после успешной сборки обзорного листа. Итоговые исходники, превью и ранее существовавшие кэши не чистились.
Неудачные атмосферные кадры были перерендерены на тех же именах; итоговый mood использует конечный объём тумана.

## Созданные файлы и повторение

Все записи задачи находятся только в `Art/Environment/Highrise100/` и `Tools/Environment/Highrise100/`.
Точный перечень/размеры — [file_manifest.json](file_manifest.json). Изменены новые scene/assets/tools/docs внутри этих папок; существующие production-файлы не редактировались.

Новые инструменты:
{tools}

Пересборка **заменяет процедурную библиотеку**, поэтому не запускайте её поверх ручной доводки без сохранения копии.
Из корня проекта:

```powershell
python Tools/Environment/Highrise100/prepare.py
python Tools/Environment/Highrise100/prepare_signs.py
blender --background --factory-startup --python Tools/Environment/Highrise100/build_library.py -- --to 100 --rerender
blender --background --factory-startup --python Tools/Environment/Highrise100/additional_previews.py
blender --background --factory-startup --python Tools/Environment/Highrise100/render_mood.py
python Tools/Environment/Highrise100/finish_boards.py
blender --background --factory-startup --python Tools/Environment/Highrise100/verify_and_stage.py
Copy-Item Tools/Environment/Highrise100/godot_sanity.gd Art/Environment/Highrise100/GodotSanity/godot_sanity.gd
godot --headless --editor --path Art/Environment/Highrise100/GodotSanity --import --quit
godot --path Art/Environment/Highrise100/GodotSanity --script res://godot_sanity.gd
python Tools/Environment/Highrise100/catalog.py
python Tools/Environment/Highrise100/package_report.py
```

`--factory-startup` здесь относится только к новым изолированным background-процессам, не к MCP-сессии пользователя.
Commit / push не выполнялись. После передачи пакета работа остановлена.
'''
(OUT/'REPORT.md').write_text(report,encoding='utf-8')
(OUT/'README.md').write_text('# Highrise 100\n\nОткройте [index.html](index.html) для просмотра и выбора по ID.\n\n[Полный отчёт](REPORT.md) · [100 силуэтов](ContactSheet_All.jpg) · [Общий масштаб](CommonScale.jpg) · [Blender source](Highrise100.blend)\n',encoding='utf-8')
inventory=[dict(path=p.relative_to(OUT).as_posix(),bytes=p.stat().st_size) for p in sorted(OUT.rglob('*')) if p.is_file() and p.name!='file_manifest.json']
(OUT/'file_manifest.json').write_text(json.dumps(dict(files=inventory,total_bytes_excluding_this_manifest=sum(p['bytes'] for p in inventory),free_bytes=shutil.disk_usage(ROOT).free),indent=2))
print(json.dumps(dict(buildings=100,triangles=triangles,previews=len(preview_paths),assigned_recipes=len(used),package_mib=size/1024**2,free_gib=free/1024**3)))
