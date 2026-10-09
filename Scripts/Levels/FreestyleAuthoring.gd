extends Node3D
## Level-only authoring switches. Player remains the sole owner of gameplay.
@export var dev_reference_enabled := true
@export var readout_enabled := true
@export var reference_toggle_key: Key = KEY_F3
@export var readout_toggle_key: Key = KEY_F5
var _collision_settings: Dictionary = {}
var _anchor_groups: Array[Node] = []
@onready var _kit: Node3D = $ImportedLevel/DEV_MECHANICS_REFERENCE
@onready var _player = $Player

func _ready():
    get_window().title = 'BowPrototype | Level_Freestyle_01'
    # Existing marker binder populates the canonical anchors first.
    call_deferred('_prepare_reference')

func _prepare_reference():
    for node in _kit.find_children('*', '', true, false):
        if node is CollisionObject3D:
            _collision_settings[node] = Vector2i(node.collision_layer, node.collision_mask)
        if node.is_in_group('grapple_anchor'):
            _anchor_groups.append(node)
    set_reference_enabled(dev_reference_enabled)

func set_reference_enabled(enabled: bool):
    dev_reference_enabled = enabled
    _kit.visible = enabled
    _kit.process_mode = Node.PROCESS_MODE_INHERIT if enabled else Node.PROCESS_MODE_DISABLED
    for node in _collision_settings:
        var settings: Vector2i = _collision_settings[node]
        node.collision_layer = settings.x if enabled else 0
        node.collision_mask = settings.y if enabled else 0
        if node is Area3D:
            node.monitoring = enabled
            node.monitorable = enabled
    for node in _anchor_groups:
        if enabled:
            node.add_to_group('grapple_anchor')
        else:
            node.remove_from_group('grapple_anchor')

func _unhandled_key_input(event):
    if not event.pressed or event.echo:
        return
    if event.keycode == reference_toggle_key:
        set_reference_enabled(not dev_reference_enabled)
    elif event.keycode == readout_toggle_key:
        readout_enabled = not readout_enabled

func _process(_delta):
    $CanvasLayer/AuthoringReadout.visible = readout_enabled
    if not readout_enabled:
        return
    var state := 'GROUND' if _player.IsGrounded else 'AIR'
    if _player.CrouchSlideModule.IsSliding:
        state = 'SLIDE'
    elif _player.WallRunModule.IsWallRunning:
        state = 'WALLRUN ' + str(_player.WallRunModule.ActiveWallSide)
    elif _player.SlingshotGrappleModule.IsSlingshotActive:
        state = 'GRAPPLE'
    var aim := '—'
    # Observe the canonical selection highlight; do not implement another acquisition rule.
    for anchor in get_tree().get_nodes_in_group('grapple_anchor'):
        var highlight = anchor.get_node_or_null('AvailableHighlightSphere')
        if highlight != null and highlight.visible:
            aim = '%.1f m' % _player.Camera.global_position.distance_to(anchor.global_position)
            break
    $CanvasLayer/AuthoringReadout.text = ('FREESTYLE 01   |   F5 readout\n%s   |   Shift parkour %s\nAim anchor: %s\nXYZ  %.1f  %.1f  %.1f\nF1 reset   |   F3 DEV kit: %s' % [
        state, 'ON' if _player.ParkourIntentModule.IsActive else 'OFF', aim,
        _player.position.x, _player.position.y, _player.position.z,
        'ON' if dev_reference_enabled else 'OFF'])
