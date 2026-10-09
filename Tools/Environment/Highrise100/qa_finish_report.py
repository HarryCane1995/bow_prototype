"""Current report, material board and final package inventory after verified promotion."""
from pathlib import Path
import json,hashlib,csv,shutil,math,re
from PIL import Image,ImageDraw,ImageFont
ROOT=Path(__file__).resolve().parents[3];OUT=ROOT/'Art/Environment/Highrise100';QA=OUT/'UV_Material_QA'
data=json.loads((OUT/'manifest.json').read_text());records=data['buildings'];materials=json.loads((OUT/'materials.json').read_text())
comparison=json.loads((QA/'Independent/comparison.json').read_text());godot=json.loads((QA/'GodotSanity/runtime_validation.json').read_text());validation=json.loads((OUT/'QA/source_validation.json').read_text());promotion=json.loads((QA/'PROMOTED.json').read_text())
used=set(k for r in records for k in r['material_face_counts']);textured=sorted(k for k in used if (OUT/'Textures'/k/'albedo.png').exists())
images=[]
for r in records:
    for p in r['previews']:
        imagepath=OUT/p;assert imagepath.is_file(),p
        with Image.open(imagepath) as im:im.verify()
        images.append(p)
assert len(images)==300
rows=list(csv.DictReader((QA/'Independent/before_surfaces.csv').open(encoding='utf-8-sig')))
ranked=sorted([r for r in rows if r['floor_pitch_max']],key=lambda r:float(r['relative_anisotropy_max']),reverse=True)
unique=[];seen=set()
for r in ranked:
    if r['building_id'] not in seen:unique.append(r);seen.add(r['building_id'])
    if len(unique)==8:break
worst='\n'.join(f'| {r["building_id"]} | `{r["mesh"]}` | {float(r["relative_anisotropy_max"]):.2f} | {float(r["floor_pitch_max"]):.2f} / {float(r["floor_pitch_nominal"]):.2f} м |' for r in unique)
report=f'''# Highrise100 — UV + material logic QA

**PASS в границах exploratory pass.** Проверены и сохранены все **100 зданий / 13 490 полигонов / 30 500 треугольников**. Геометрия, силуэты, имена коллекций, вершины, индексы граней, родители и трансформации не изменены. Не выявлено оставшихся P0/P1 UV/material дефектов в проведённых проверках. Commit/push не выполнялись.

## Что смотреть

- [Каталог QA](index.html): 100 зданий, три ракурса каждого, листы сравнения.
- [Все 100](UV_MATERIAL_QA_CONTACTSHEET.jpg), [001–025](ContactSheets/UV_MATERIAL_QA_001_025.jpg), [026–050](ContactSheets/UV_MATERIAL_QA_026_050.jpg), [051–075](ContactSheets/UV_MATERIAL_QA_051_075.jpg), [076–100](ContactSheets/UV_MATERIAL_QA_076_100.jpg).
- [Наиболее заметные исправления](OFFENDERS_BEFORE_AFTER.jpg), [направленный numbered checker](CHECKER_BEFORE_AFTER.jpg), [масштаб человека 1,8 м](PLAYER_SCALE_BEFORE_AFTER.jpg).
- [Независимый итоговый аудит](Independent/AFTER_INDEPENDENT.md), [baseline](Independent/BEFORE_INDEPENDENT.md).

## Результаты измерений

| Проверка поверхности | До | После |
|---|---:|---:|
| Максимальная нормализованная анизотропия фасада | 33,788 | 1,128 |
| Шаг этажей >150% номинала | 432 | 0 |
| Шаг этажей <67% номинала | 108 | 0 |
| Анизотропия >2 | 482 | 0 |
| Горизонтальный масштаб >150% | 128 | 0 |
| Реклама на нелицевых гранях | 60 | 0 |
| Roof material на нижних гранях | 321 | 0 |
| Фасад на верхней/нижней стороне | 6 / 6 | 0 / 0 |
| Стекло на верхней/нижней стороне | 15 / 15 | 0 / 0 |
| Инвертированная вертикальная UV-ось | 4 | 0 |

Предупреждения пересекаются, их нельзя складывать как число уникальных дефектов. Остались 34 диагностических предупреждения о наклоне V относительно касательной вертикали: это наклон самих поверхностей HR055/070/100. Gravity-Z UV сохраняет общие уровни этажей; анизотропия этих поверхностей 1,06–1,128. Это не боком повёрнутые окна.

Метод: world/UV area по треугольникам, сингулярные значения якобиана, нормализация на физический размер материала; дополнительно raw pixel anisotropy, плотность, направление V и номинальный floor pitch. Полные результаты всех поверхностей: [до](Independent/before_surfaces.csv), [после](Independent/after_surfaces.csv). `stretch_score` — нормализованная анизотропия; мировая площадь и UV-площадь приведены отдельно. UV area — сумма площади развёртки, она может быть >1 при repeat и не является процентом atlas packing.

Номинальный шаг этажей после исправления соответствует параметрам 3,3 / 4,1 / 4,8 / 3,6 / 5,4 м (максимальная численная ошибка 0,00032%). Эта метрика измеряет UV-масштаб design floor_height, а не каждый нарисованный этаж: service bands и authored window группировки имеют собственный ритм. Это не BIM-проверка.

## Offenders до исправлений

[Строгий TOP 20 поверхностей](Independent/top20_before.csv) и [те же поверхности после](Independent/top20_before_after.csv). Список ниже дополнительно разнесён по зданиям, чтобы не занимать всё сравнение фасетками одной иглы.

| ID | Mesh | Анизотропия до | Максимальный шаг / номинал до |
|---|---|---:|---:|
{worst}

Отдельно HR098 `cathedral_finger_2` имел номинальный визуальный шаг около16,56 м при параметре4,8 м; HR065 `tube_1` —15,51 м при5,4 м. У HR100 `inhabited_crown_bridge` общая box/beam-проекция давала окна на caps и неправильную ориентацию. Эти случаи устранены общими правилами, без изменения формы.

## Исправления и причины

**Системные P0/P1.** Удалён UV clamp `.96`, который растягивал единственный crop на высокие и широкие объёмы. Taper теперь получает настоящую трапециевидную UV-область: горизонтальная координата — касательная `Z × normal`, вертикальная — мировая Z. Ширина тайла фасада42 м; высота зависит от design floor_height и floor_pitch здания. Соседние массы сохраняют вертикальное направление и согласованный масштаб.

Из24 исходных unique facade sheets получены отдельные repeat-варианты: сохранён внутренний рисунок, удалены уникальные roof/base lips (crop Y36:992), добавлен узкий согласованный по всем PBR-каналам периодический structural seam. Исходные карты не изменены. Не используется бесконечное повторение исходного листа вместе с его крышей и цоколем.

Вывески назначены только лицевой плоскости с наружной нормалью -Y.12 оставшихся рекламных плоскостей имеют pixel anisotropy≈1,000. Thin edges/back/top/bottom — конструкционный металл. Полный рисунок вписан с сохранением пропорций: добавлена тёмная граница и clamp-letterbox. UV за пределами0..1 здесь намеренный: повторяется только матовая рамка, не растягивается рекламный рисунок.

**Системные P2.** Upward/downward/vertical классификация работает на каждой грани. Крыши основных масс и podium — rooftop; нижние поверхности — тёмный structural concrete; caps оборудования — metal deck. HVAC, roof access, tanks, exhaust и cabinets получают vent/maintenance/tank/pipe/service роли. Световые маяки сохраняют излучение на своих гранях.

| Поверхность | Физический тайл | Практический масштаб |
|---|---:|---|
| Roof | 5 м | Люк139×175px:1,36×1,71 м вместо3,26×4,10 м |
| Maintenance | 4 м | Люк170×123px:1,33×0,96 м вместо3,98×2,88 м |
| Service rack | 3 м | Панель154×148px:0,90×0,87 м вместо3,61×3,47 м |
| Metal deck / pipes | 3 м | Читаемые панели, без растяжки деталей на десятки метров |
| Vents / tank shell | 4 м | Согласованный масштаб оборудования |
| Broad concrete | 12 м | Крупные бетонные панели сохранены |

**Локальные случаи.** HR100 beam facade/caps исправлен той же per-face классификацией. У signage было несколько геометрических пропорций — единое aspect-fit правило покрывает все. Production asset overrides не потребовались. Только QA-фигуры HR098 и HR064 получили отдельный выбор открытой площадки, чтобы не скрываться за существующей геометрией.

## Material assignment / coverage

[Per-building coverage](Independent/building_coverage_before_after.csv) содержит100 записей до и100 после: slots, world area, UV area, facade, flat glass, emission, glass proxy, roof и service. [Per-material coverage](Independent/material_coverage_before_after.csv) — площадь каждой назначенной группы внутри здания.

Emission/glass оцениваются128 детерминированными выборками каждого треугольника с весом мировой площади. Emission: maxRGB × strength >0,02. Glass proxy: на фасадном ORM roughness<0,45 и metallic<0,18, плюс отдельный flat glass. Это эвристика: в одном facade sheet смешаны окна, бетон и металл. Площадь включает скрытые и пересекающиеся исходные грани. Не следует приравнивать число glass slots к проценту окон или выдавать coverage за видимую площадь.

Проверка не выявила общей аномалии corporate «почти без окон»: baseline facade area53–77%, sampled glass proxy около9,9–24,2%. У billboard assets рекламные поверхности присутствуют; industrial/service назначение не было глобально заменено на стекло.

## Крыши и player scale

Сохранены roof geometry, parapets и существующее оборудование. Крыши проверены сверху для100/100; подготовлены10 сопоставленных пар close-up с настоящим3D-маркером высотой1,8 м. Текстуры roof и service теперь читаются в более правдоподобном масштабе. Checker, фигура и QA-камерные изменения не сохранены в asset collections. Новые парапеты, лестницы, коллизии или traversal-геометрия не создавались.

## Godot sanity

Отдельный проект [GodotSanity](GodotSanity/project.godot), direct `.blend` import.12 образцов: HR003 corporate,007 megablock,013 industrial,018 residential,025 HVAC,027 billboard,036 needle,057 maintenance,064 exoskeleton,070 suspended,083 civic,100 hero.

[Runtime report](GodotSanity/runtime_validation.json): **PASS**, Godot4.6.3;128 meshes;250/250 surfaces сUV итангентами;248 textured surfaces сnormal, emission иroughness/metallic поG/B ORM;0 missing materials/textures.3 036 ожидаемых и фактических треугольников. Две оставшиеся поверхности используют flat material. [12 реальных кадров Godot](GODOT_12_CONTACTSHEET.jpg). Наличие и подключение карт проверены программно; точное фотометрическое совпадение Blender/Godot не обещается.

## Безопасность и воспроизводимость

До правок сохранены оригинальный [blend](Before/Highrise100.blend), manifest, materials, cards,145 previews и contact sheets. Исходный source SHA256: `{promotion['before_sha256']}`. Исправленный: `{promotion['source_sha256']}`.

Не выполнялся полный rebuild поверх сохранённого `.blend`: к его копии применены только material slots/indices и loop UV. Сначала12-asset subset, затем все100. [Строгий geometry check](candidate_geometry.json) сравнивает точные вершины/индексы/трансформации/родителей; независимый агент отдельно сравнил100 геометрических хешей.5 583 per-face material assignments изменены. Promotion разрешён только при неизменном исходном хеше; финальный файл побайтно равен проверенному кандидату. [Повторное открытие финального source](../QA/source_validation.json):100/100, без пропавших карт, все пути относительные,100 уникальных geometry signatures.

Общее правило реализовано в `Tools/Environment/Highrise100/uv_material_rules.py` и вызывается из `Tower.finish()`. `prepare_uv_tiles.py` детерминированно создаёт производные карты. [Тест воспроизводимости](reproducibility.json) пересоздал12 выбранных assets только в памяти: совпали вершины, индексы граней, material keys и UV с точностью5 десятичных знаков. Test process не сохранял source. Скрипты текущей миграции — одноразовый протокол этого pass; перед будущим rebuild снова требуется резервная копия ручных изменений.

Production Level_01, CyberCity, Player, project.godot и прежний Skyscraper_Kit проверены хешами: без изменений. Новые100 assets не импортировались в основной игровой проект. Runtime/movement/collision не менялись.

## Что остаётся

P3: на близких поверхностях видны повторение procedural тайлов, простота512px карт и низкополигональная геометрия. Небольшие фазовые швы между разными ориентациями фасадов допустимы; нет крупного скачка масштаба. Не выполнялись production bake/LOD, interiors, коллизии и человеческий gameplay traversal. Это рамки exploratory-библиотеки, а не незавершённый UV fix.

Активный каталог иmanifest ссылаются на300 новых neutral/front/back/roof кадров. Старые45 дополнительных файлов в`Previews`, `CommonScale.jpg`, `Mood/` и прежний6-asset `GodotSanity/` оставлены как историческая презентация доUV-pass; они не являются evidence исправленного состояния. [Исходный exploration report](Before/REPORT.md) сохранён отдельно.

## Изменённые группы файлов

- `Art/Environment/Highrise100/Highrise100.blend`, manifest/materials/cards,100 основных previews, contact sheets, Materials.jpg, index/README/REPORT/file_manifest.
- `Textures/*_uv/` и `Recipes/*_uv.uv.json`:30 производных наборов,150 карт;46 первоначальных наборов и230 карт сохранены без изменения.
- `UV_Material_QA/`:резервная копия, метрики, аудит,3-view/close-up/checker рендеры, сравнения, изолированный Godot sample, отчёты.
- `Tools/Environment/Highrise100/build_library.py`, `catalog.py`, новые `prepare_uv_tiles.py`, `uv_material_rules.py`, `qa_*.py`, `qa_godot.gd`.

STOP: UV/material QA и fixes завершены. Commit/push отсутствуют.
'''
report=re.sub(r'(?<=[А-Яа-яёЁ])(?=\d)|(?<=\d)(?=[А-Яа-яёЁ])',' ',report)
report=report.replace('Godot4.6.3','Godot 4.6.3').replace('UV итангентами','UV и тангентами')
(QA/'REPORT.md').write_text(report,encoding='utf-8')
rootreport=f'''# Bow Prototype — Highrise100

Текущая версия включает завершённый UV/material QA-pass. **100 высоток,20 семейств,30 500 треугольников**, геометрия сохранена. Роли:30 background /58 midground /12 hero.

- [Каталог библиотеки](index.html) · [Blender source](Highrise100.blend)
- [Каталог сравнений UV/material QA](UV_Material_QA/index.html) · [Полный отчёт](UV_Material_QA/REPORT.md)
- [Manifest](manifest.json) · [Материалы](Materials.jpg) · [100 силуэтов](ContactSheet_All.jpg)
- [Независимый аудит](UV_Material_QA/Independent/AFTER_INDEPENDENT.md) · [TOP20 до/после](UV_Material_QA/Independent/top20_before_after.csv)
- [Референсы архитектуры](References/CATALOG.html) · [Игровые референсы](References/GAME_REFERENCES.html)

Все100 asset-marked коллекций доступны через **File → Append → Highrise100.blend → Collection → HRxxx**. Root каждого asset находится в локальном основании0,0,0. Сцены Library_100/Neutral_Preview/Atmosphere_Review — презентационные; их cameras/lights/fog/ground не входят в building collections. Текстуры задаются относительными путями `//Textures/...`. Папка исключена из production autoimport через `.gdignore`.

Текущий manifest ссылается на300 проверенных кадров: front/back/roof каждого здания. Материалы:76 наборов /380 карт (46 первоначальных +30 производных), {len(textured)} текстурированных recipe keys реально назначены; также используются flat signal/warm/glass там, где применимо. Derived facade interiors повторяются в физическом масштабе, signs сохраняют aspect ratio, roof/service/underside назначаются по граням.

Подтверждено:100/100 загружаются, пропавших текстур0, исходная геометрия совпала; Godot12 sample PASS (250UV surfaces,248PBR textured surfaces). Это изолированная библиотека для kitbashing; коллизии, interiors, LOD и gameplay integration не добавлялись. Производственные карты и Player не изменены.

Максимальная нормализованная анизотропия фасадов33,788→1,128. Крупные нарушения шага этажей и назначения вывесок устранены; заметное повторение текстур остаётся exploratory-ограничением.

[Резервная копия и первоначальный exploration report](UV_Material_QA/Before/REPORT.md) сохранены. Старые CommonScale/Mood,45 дополнительных previews и6-asset GodotSanity отражают состояние доUV-pass. Они не являются текущей проверкой материалов.

Воспроизводимость: оригинальные prepare.py иprepare_signs.py → prepare_uv_tiles.py → build_library.py. **Полный rebuild заменяет procedural library; перед ним сохраните ручные изменения.** Текущий pass применён к сохранённой копии без rebuild; общий UV/material rule используется и будущим генератором.12-asset воспроизводимость проверена в памяти. Никаких commit/push.
'''
rootreport=re.sub(r'(?<=[А-Яа-яёЁ])(?=\d)|(?<=\d)(?=[А-Яа-яёЁ])',' ',rootreport)
(OUT/'REPORT.md').write_text(rootreport,encoding='utf-8')
(OUT/'README.md').write_text('# Highrise100\n\n[Библиотека](index.html) · [UV / material QA и сравнения](UV_Material_QA/index.html) · [Полный отчёт QA](UV_Material_QA/REPORT.md) · [Blender source](Highrise100.blend)\n\n100 assets. Геометрия сохранена. 300 актуальных front/back/roof кадров. Изолированный Godot sample:12 assets, PASS.\n',encoding='utf-8')
font=ImageFont.truetype('C:/Windows/Fonts/consola.ttf',15);title=ImageFont.truetype('C:/Windows/Fonts/consolab.ttf',26)
board=Image.new('RGB',(1600,math.ceil(len(textured)/10)*205+85),'#101c24');draw=ImageDraw.Draw(board);draw.text((20,18),f'HIGHRISE100 / {len(textured)} ASSIGNED TEXTURE RECIPES / UV PASS',font=title,fill='#dcebef')
for i,key in enumerate(textured):
    x=i%10*160;y=i//10*205+85;pic=Image.open(OUT/'Textures'/key/'albedo.png').convert('RGB');pic.thumbnail((150,175));board.paste(pic,(x+(160-pic.width)//2,y));draw.text((x+4,y+180),key[:19],font=font,fill='#a7c6cd')
board.save(OUT/'Materials.jpg',quality=94)
final=dict(status='PASS_EXPLORATORY_UV_MATERIAL_QA',count=100,geometry_exact_unchanged=True,triangles=30500,faces=13490,missing_textures=0,active_preview_count=len(images),godot_assets=12,godot_pass=godot['passed'],source_sha256=promotion['source_sha256'],original_maps_unchanged=True,protected_unchanged=validation['protected_unchanged'],production_integration=False,commit=False,push=False)
for rec in json.loads((QA/'Before/materials.json').read_text()):
    for channel,h in rec['sha256'].items():assert hashlib.sha256((OUT/'Textures'/rec['key']/(channel+'.png')).read_bytes()).hexdigest()==h
    # Make the bit-identical source backup independently openable with its
    # original relative image paths; only original, verified maps are copied.
    dest=QA/'Before/Textures'/rec['key']
    if not dest.exists():shutil.copytree(OUT/'Textures'/rec['key'],dest)
    recipe=OUT/rec['recipe'];backup_recipe=QA/'Before'/rec['recipe'];backup_recipe.parent.mkdir(parents=True,exist_ok=True)
    if not backup_recipe.exists():shutil.copy2(recipe,backup_recipe)
(QA/'final_validation.json').write_text(json.dumps(final,indent=2))
oldqa=OUT/'QA/qa_final.json';backupqa=QA/'Before/qa_final.json'
if not backupqa.exists():shutil.copy2(oldqa,backupqa)
oldqa.write_text(json.dumps(dict(schema='bow.highrise100.qa.v2',**final,report='UV_Material_QA/REPORT.md',independent='UV_Material_QA/Independent/AFTER_INDEPENDENT.md',previous_exploration_qa='UV_Material_QA/Before/qa_final.json'),indent=2))
files=[dict(path=p.relative_to(OUT).as_posix(),bytes=p.stat().st_size) for p in OUT.rglob('*') if p.is_file() and '.godot' not in p.parts and p.name!='file_manifest.json']
(OUT/'file_manifest.json').write_text(json.dumps(dict(files=files,total_bytes=sum(r['bytes'] for r in files),excludes=['generated .godot caches','self'],free_bytes=shutil.disk_usage(ROOT).free),indent=2))
print('FINAL_REPORT_PASS',len(textured),'assigned texture recipes',len(images),'active images',sum(r['bytes'] for r in files),'bytes excluding caches')
