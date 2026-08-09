# Technical Audit

Дата ревизии: 2026-08-09.

## Проверено

- структура сцен, C#/GDScript, shaders/materials, textures/models и editor tools;
- источники истины для Player, tuning и level-wrapper сцен;
- прямые пути ресурсов в текстовых файлах;
- текущие `.blend`-пути Level_01;
- build и headless import/run актуальных сцен.

## Исправлено

- удалены подтверждённые дубли Level_01 texture exports из корня;
- удалены неиспользуемые bow-preview wrapper/material/texture derivatives;
- удалён runtime preview-binder, который ссылался на уже отсутствующий `CITY_Building_02`;
- удалены автоматические `.blend1`, Python caches и случайные пустые директории;
- исправлен устаревший UID общего tuning profile в сценах игрока и legacy playground;
- обновлены README и документы, которые называли legacy playground главной сценой;
- добавлены ignore-правила для Python cache и случайных root texture exports.

## Осознанно оставлено

- `Scenes/BowPrototypeScene.tscn` и его blockout/test-зависимости: сцена имеет пользовательские незакоммиченные изменения, поэтому ревизия не удаляет её автоматически;
- крупные grapple/slide/wallrun модули: они объёмные, но сохраняют одну gameplay-ответственность; дробление без функциональной причины повысит риск;
- Blender-источники и editor preview/capture сцены без runtime-ссылок: это авторские и проверочные ассеты, а не доказанный мусор;
- `level_01_road_base_color.png`: импортируемого road mesh уже нет, но `.blend` сохраняет image datablock; удалять файл отдельно от Blender-источника нельзя;
- Aim Stabilization остаётся включённым в profile, но текущий bow GLB не содержит ожидаемый `ArrowTipMarker`; feature безопасно отключается модулем и пишет один warning. Маркер нельзя добавлять вслепую в рамках cleanup, потому что это изменит viewmodel feel;
- визуальные/environment изменения текущего CyberCity-этапа: они не смешиваются с архитектурной чисткой.

## Следующий безопасный долг

- после фиксации текущего dirty tree отдельно решить, нужен ли legacy `BowPrototypeScene`; если нет — удалить сцену одним атомарным изменением вместе с `Scenes/Blocks`, старым skybox helper и устаревшей документацией;
- отдельной Blender-задачей проверить и удалить неиспользуемый road image datablock, затем повторно проверить material import;
- при следующем функциональном изменении grapple/slide выносить только реально повторяющиеся расчёты, не меняя tuning defaults и physics order.
