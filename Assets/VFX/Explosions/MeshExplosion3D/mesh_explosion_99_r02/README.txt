MESH_EXPLOSION_3D: six layers of real triangle meshes; no billboard or flipbook.
Open review.tscn. Drag to orbit, wheel to zoom; R restarts, Space pauses.
Reusable effect: explosion.tscn. Call restart(); seek(seconds) supports scrubbing. finished marks one-shot completion.
OBJ files are generated outputs. Editable source is *.meshvfx.json plus Tools/Art/VFXFactory/mesh_*.py.
Per-layer ShaderMaterials: alpha, additive, or Bayer dither/scissor. Instance uniforms isolate playback.
Forward+ renderer (Godot 4.6). Transparent mesh overlaps can show alpha sorting artifacts; DITHER writes depth when enabled.
No gameplay, collision, lights, camera-facing sprites, particle solver or character dependencies.
