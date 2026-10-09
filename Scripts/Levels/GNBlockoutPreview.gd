extends Node3D
## Scene-specific label only. Movement and reset remain owned by the canonical Player.

func _ready() -> void:
    var geometry := $ImportedLevel.find_child("GN_V02_Level", true, false)
    var seed_value = geometry.get_meta("extras", {}).get("seed", "?") if geometry != null else "?"
    if seed_value is float: seed_value = int(seed_value)
    get_window().title = "BowPrototype | GN Blockout V02 | Seed %s" % seed_value
    $CanvasLayer/PreviewLabel.text = "GN BLOCKOUT V02 · SEED %s\nF1 — restart" % seed_value
