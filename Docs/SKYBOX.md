# Skybox / HDRI

Skybox в BowPrototype настраивается через существующую ноду `WorldEnvironment` и скрипт `TestSkyboxEnvironment.cs`.

## Как это работает

- В активной сцене должна быть одна `WorldEnvironment`.
- На эту ноду вешается `res://Scripts/Rendering/TestSkyboxEnvironment.cs`.
- Скрипт создаёт `Environment`, `Sky` и `PanoramaSkyMaterial` в коде.
- В `PanoramaSkyMaterial` назначается текстура из `SkyTexturePath`.

Не нужно создавать вторую `WorldEnvironment` в активной сцене.

## Формат текстуры

Ожидается equirectangular panorama 2:1.

Подходящие форматы:

- `.hdr`;
- `.exr`;
- для быстрых тестов допустимы `.png`, `.jpg`, `.jpeg`.

Локальная папка для skybox-файлов:

`res://Art/Skyboxes/`

## Git и локальные HDRI

HDRI/EXR-файлы могут быть тяжёлыми, поэтому они не коммитятся в репозиторий. В `.gitignore` добавлены:

- `Art/Skyboxes/*.hdr`;
- `Art/Skyboxes/*.hdr.import`;
- `Art/Skyboxes/*.exr`;
- `Art/Skyboxes/*.exr.import`.

После чистого клона проекта skybox может не загрузиться, пока вручную не положить файл по пути из `SkyTexturePath`.

Если файл отсутствует, сцена не должна падать. `TestSkyboxEnvironment` выводит warning в Output и оставляет сцену работать без panorama skybox.

## Blur

`GaussianBlurEnabled` включает CPU Gaussian blur перед назначением sky texture. Для больших HDRI это может быть дорого, поэтому blur ограничивается `GaussianBlurMaxSize`.

Если `GaussianBlurEnabled` включён, но `GaussianBlurRadius` равен `0`, blur не применяется и скрипт выводит warning.
