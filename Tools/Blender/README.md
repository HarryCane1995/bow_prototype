# Blender Tools

## Grapple Anchor Markers

Use `create_grapple_anchor_marker.py` to create/update the first Level_01 grapple marker in `Level_01_Blockout.blend`.

Run from the repository root:

```powershell
& "C:\Program Files\Blender Foundation\Blender 5.1\blender.exe" Level_01_Blockout.blend --background --python Tools/Blender/create_grapple_anchor_marker.py
```

Or open `Level_01_Blockout.blend` in Blender, open `Tools/Blender/create_grapple_anchor_marker.py` in the Scripting workspace, and press Run Script.

Markers must:

- live in the `30_GAMEPLAY_MARKERS` collection;
- be named `GrappleAnchor`, `GrappleAnchor_01`, `GrappleAnchor_02`, or another `GrappleAnchor_*` / `GrappleAnchor.*` variant;
- avoid `-noimp`, `-col`, and `-colonly` suffixes;
- stay as marker objects only, with no gameplay logic or collision authored in Blender.

At runtime, `ImportedLevelMarkerBinder` finds these marker names and instances `res://Scenes/GrappleAnchor.tscn` under `Gameplay/GrappleAnchors`.
