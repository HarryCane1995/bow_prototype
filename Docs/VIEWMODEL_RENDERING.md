# Viewmodel Rendering

FPS-лук рендерится через отдельный `SubViewport`, чтобы viewmodel не клипался стенами, блоками и другими объектами окружения.

## Схема

Основная камера игрока (`Player/CameraPivot/Camera3D`) рендерит мир, мишени, блоки и projectile-стрелы.

Viewmodel-камера (`ViewModelCamera3D`) находится внутри:

`CanvasLayer_ViewModel/ViewModelSubViewportContainer/ViewModelSubViewport/ViewModelRoot`

Она рендерит только лук и накладывается поверх основной картинки через `CanvasLayer` и `SubViewportContainer`.

## Viewmodel Light Rig

Лук освещается отдельным `ViewModelLightRig` внутри `ViewModelSubViewport`.

Сейчас light rig содержит:

- `MainLight` (`DirectionalLight3D`) - основной мягкий свет для формы лука.
- `FillLight` (`OmniLight3D`) - слабый дополнительный свет, который подсвечивает тени.

Это сделано намеренно: после переноса лука в `SubViewport` он больше не должен зависеть напрямую от освещения основной 3D-сцены. Отдельный light rig помогает луку не клиппиться об окружение, не темнеть рядом со стенами и сохранять читаемый FPS viewmodel-силуэт.

## Visual Layer

Для viewmodel используется visual layer `20`.

- Основная камера исключает layer `20` из `CullMask`.
- `ViewModelCamera3D` рендерит только layer `20`.
- `PlayerViewModelRenderModule` может рекурсивно назначать layer `20` всем `MeshInstance3D` внутри `Bow_ViewModel`.
- `PlayerViewModelRenderModule` также гарантирует, что lights внутри `ViewModelLightRig` светят только на layer `20`.
- Мир, блоки и мишени не должны использовать layer `20`.

## Модули

`PlayerViewModelRenderModule` отвечает только за рендер-настройки viewmodel:

- ссылки на основную камеру и viewmodel-камеру;
- cull mask камер;
- visual layer для mesh-нод viewmodel;
- отдельный FOV viewmodel-камеры или синхронизацию FOV с основной камерой.
- light rig viewmodel, включая `MainLightEnergy`, `FillLightEnergy` и `LightRigEnabled`.

`PlayerBowVisualModule` по-прежнему отвечает за Draw-анимацию, визуальную стрелу в луке и reset/release visual state.

`PlayerBowShootModule` по-прежнему создаёт projectile-стрелы из основной сцены через `Camera3D/ShootPoint`. Projectile-стрелы не являются частью viewmodel viewport.
