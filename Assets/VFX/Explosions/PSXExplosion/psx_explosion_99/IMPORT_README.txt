Open review.tscn in Godot 4.6. R / RESTART replays; Space / PAUSE pauses.
Reusable effect: explosion.tscn. Call restart(); finished signal marks one-shot end.
Every instance duplicates its ShaderMaterial. No gameplay nodes or input map changes.
Straight alpha, sRGB color/emission, row-major frames with 2 px transparent gutters.
Shader forces nearest filtering and no repeat. Use lossless texture import; disable mipmaps.
No normal/ORM: this is a baked, unlit 2D billboard, not a physical volume.
Preview emission is local sprite radiance; it does not light nearby geometry.
Keep the generated directory in its exported res:// path (or update its resource links).
