"""Package unchanged reference/game captures into a standalone comparison page."""
import base64,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
src=ROOT/'.godot/humanoid-base/v2-camera'
results=json.loads((src/'results.json').read_text())
assert results['status']=='PASS'
html=['''<!doctype html><html lang="ru"><meta charset="utf-8"><title>V2 — PoseLab camera comparison</title>
<style>body{margin:24px;background:#171d24;color:#e3eaf2;font:16px system-ui}h1{font-size:26px}h2{margin-top:32px}
.grid{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:16px}figure{margin:0}img{width:100%;display:block}figcaption{padding:10px 0;color:#b7c9da}p{max-width:1100px;line-height:1.5}code{color:#83d2dc}@media(max-width:1000px){.grid{grid-template-columns:1fr}}</style>
<h1>BH_01 / camera calibration</h1><p>Слева — Blender WORLD, в центре — реальный Godot V2 WORLD. Справа — Blender VIEWMODEL для справки: его калибровка сохранена, отдельный viewmodel render в V2 выключен. Все кадры 1280×720.</p>
<p>Позиция камер следует <code>chest → FP_CAMERA_SOCKET</code> плюс общий offset в осях Male_Rig. WORLD: 98° vertical; VIEWMODEL: 65° vertical. Source poses и attachment лука не изменены; Slide сохранила прежнюю матрицу камеры.</p>''']
for pose in ['BH01_IDLE','BH01_SLIDE']:
    record=next(r for r in results['evidence'] if r['pose']==pose)
    html.append(f'<h2>{pose}</h2><p>Высота камеры над origin персонажа: {record["camera_height"]:.3f} м. Ошибка проекций joints: {record["max_bone_projection_error_px"]:.4f} px; ошибка позиции bow: {record["bow_origin_error_m"]*1000:.4f} мм.</p><div class="grid">')
    for filename,label in [(f'blender_{pose}_CAM_FP_WORLD.png','Blender · CAM_FP_WORLD · 98°'),
                           (f'godot_{pose}_CAM_FP_WORLD.png','Godot · existing WORLD Camera3D · 98°'),
                           (f'blender_{pose}_CAM_FP_VIEWMODEL.png','Blender · CAM_FP_VIEWMODEL · 65° (data only)')]:
        encoded=base64.b64encode((src/filename).read_bytes()).decode()
        html.append(f'<figure><img alt="{pose} {label}" src="data:image/png;base64,{encoded}"><figcaption>{label}</figcaption></figure>')
    html.append('</div>')
html.append(f'<p>В Idle камера автоматически выше на {results["idle_camera_rise_m"]*100:.2f} см. Проверено {len(results["socket_frames"])} кадров, включая {results["blend_intermediate_frames"]} промежуточных высот crossfade: камера использует текущую позу без задержки. Высоты по Actions не задаются. Различия стрелы/тетивы остаются от существующей gameplay weapon presentation; дополнительная постановка не выполнялась.</p></html>')
out=ROOT/'Assets/Characters/BaseHumanoid/Review/v2_camera_comparison.html'
out.write_text('\n'.join(html),encoding='utf-8')
print(out)
