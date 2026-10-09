extends Node3D
## Label for the preserved experimental chunk preview; Player owns gameplay.

func _ready() -> void:
    get_window().title = "BowPrototype | Proxy Chunks V04"
    $CanvasLayer/PreviewLabel.text = "PROXY CHUNKS V04 · EXPERIMENTAL\nF1 — restart"
