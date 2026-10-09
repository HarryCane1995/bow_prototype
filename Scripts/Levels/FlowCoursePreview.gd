extends Node3D
## Scene-specific readout. Canonical Player owns all movement and restart behavior.
func _ready() -> void:
    var section := $ImportedLevel.find_child("FLOW_00_ENTRY",true,false)
    var info: Dictionary = section.get_meta("extras",{}) if section else {}
    var seed_value := int(info.get("seed",17))
    var mode := int(info.get("layout_mode",0))
    get_window().title = "BowPrototype | Flow Course V03 | Seed %d" % seed_value
    $CanvasLayer/PreviewLabel.text = "FLOW V03 · %s · SEED %d\nFollow the lane · F1 restart" % [["BALANCED","VERTICAL","SPEED","ARENA MIX"][mode],seed_value]
