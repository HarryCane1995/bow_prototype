extends CanvasLayer

const INK := Color("10212cdb")
const TEXT := Color("f1f4f0")
const MUTED := Color("b1c5ca")
const AMBER := Color("ffad64")
const HIT := Color("aeffda")

@onready var _overlay: Control = $Overlay
@onready var _font: Font = _overlay.get_theme_default_font()
var _panel := StyleBoxFlat.new()
var _key := StyleBoxFlat.new()
var _equipped := true
var _captured := true
var _precision := false
var _percent := 0
var _shots := 0
var _hits := 0
var _hit_strength := 0.0
var _hit_tween: Tween


func _ready() -> void:
	_panel.bg_color = INK
	_panel.set_corner_radius_all(4)
	_key.bg_color = Color("354955")
	_key.set_corner_radius_all(3)
	_overlay.draw.connect(_draw_overlay)
	_overlay.resized.connect(_overlay.queue_redraw)
	_overlay.queue_redraw()


func update_status(equipped: bool, draw_amount: float, shots: int, hits: int, captured: bool, precision := false) -> void:
	var percent := 100 if equipped and precision else roundi(clampf(draw_amount, 0.0, 1.0) * 100.0)
	if _equipped == equipped and _percent == percent and _shots == shots and _hits == hits and _captured == captured and _precision == precision:
		return
	_equipped = equipped
	_percent = percent
	_shots = shots
	_hits = hits
	_captured = captured
	_precision = precision
	if is_node_ready():
		_overlay.queue_redraw()


func flash_hit() -> void:
	if _hit_tween:
		_hit_tween.kill()
	_set_hit_strength(1.0)
	_hit_tween = create_tween()
	_hit_tween.tween_method(_set_hit_strength, 1.0, 0.0, 0.23).set_trans(Tween.TRANS_QUAD).set_ease(Tween.EASE_IN)


func _set_hit_strength(value: float) -> void:
	_hit_strength = value
	_overlay.queue_redraw()


func _draw_overlay() -> void:
	var viewport_size := _overlay.size
	var s := clampf(viewport_size.y / 720.0, 0.84, 1.65)
	var margin := roundf(22.0 * s)
	_draw_reticle((viewport_size * 0.5).round(), s)
	_draw_score(Vector2(viewport_size.x - margin, margin), s)
	var controls := _draw_controls(Vector2(margin, viewport_size.y - margin), s, viewport_size.x < 630.0)
	if _equipped:
		var width := roundf(159.0 * s)
		var meter_pos := Vector2(viewport_size.x - margin - width, controls.position.y)
		if controls.end.x + margin > meter_pos.x:
			meter_pos.y -= 59.0 * s
		_draw_charge(Rect2(meter_pos, Vector2(width, controls.size.y)), s)


func _draw_reticle(center: Vector2, s: float) -> void:
	if not _captured:
		return
	var radius := maxf(1.5, 1.8 * s)
	_overlay.draw_circle(center, radius + s, Color(0.04, 0.08, 0.10, 0.78), true, -1.0, true)
	_overlay.draw_circle(center, radius, TEXT.lerp(HIT, _hit_strength), true, -1.0, true)
	if _hit_strength <= 0:
		return
	var tint := Color(HIT, _hit_strength)
	for angle in 4:
		var diagonal := Vector2.from_angle(PI * 0.25 + angle * PI * 0.5)
		var near := (6.0 + 2.0 * _hit_strength) * s
		_overlay.draw_line(center + diagonal * near, center + diagonal * (near + 5.0 * s), tint, 1.75 * s, true)


func _draw_score(top_right: Vector2, s: float) -> void:
	var heading_size := roundi(13.0 * s)
	var value_size := roundi(21.0 * s)
	var title := "Попадания / выстрелы"
	var value := "%d / %d" % [_hits, _shots]
	var width := maxf(_text_width(title, heading_size), _text_width(value, value_size)) + 23.0 * s
	var box := Rect2(top_right - Vector2(width, 0), Vector2(width, 55.0 * s))
	_overlay.draw_style_box(_panel, box)
	var start := box.position + Vector2(11, 18) * s
	_text(start, title, heading_size, MUTED)
	_text(start + Vector2(0, 25) * s, value, value_size, TEXT.lerp(HIT, _hit_strength))


func _draw_controls(bottom_left: Vector2, s: float, compact: bool) -> Rect2:
	var pairs: PackedStringArray
	if not _captured:
		pairs = ["ЛКМ", "Взять управление"]
	elif not _equipped:
		pairs = ["E", "Поднять лук"]
	elif _precision:
		pairs = ["ЛКМ", "Снайперский выстрел", "Alt ↑", "Обычная стойка"]
	elif _percent > 0:
		pairs = ["ЛКМ ↑", "Выстрел", "ПКМ", "Отменить"]
	else:
		pairs = ["ЛКМ", "Удерживать для натяжения", "Alt", "Прицелиться", "E", "Убрать"]
		if compact:
			pairs[1] = "Натянуть"
	var movement := "WASD  движение     Shift  бег     Пробел  прыжок     Esc  курсор"
	if compact:
		movement = "WASD · Shift бег · Пробел прыжок · Esc курсор"
	var small := roundi(13.0 * s)
	var regular := roundi(15.0 * s)
	var keys_width := 0.0
	for i in range(0, pairs.size(), 2):
		keys_width += _text_width(pairs[i], small) + 12.0 * s + 6.0 * s + _text_width(pairs[i + 1], regular)
		if i + 2 < pairs.size():
			keys_width += 16.0 * s
	var box_size := Vector2(maxf(keys_width, _text_width(movement, small)) + 24.0 * s, 55.0 * s)
	var box := Rect2(bottom_left - Vector2(0, box_size.y), box_size)
	_overlay.draw_style_box(_panel, box)
	var x := box.position.x + 12.0 * s
	for i in range(0, pairs.size(), 2):
		var key_width := _text_width(pairs[i], small) + 12.0 * s
		var cap := Rect2(Vector2(x, box.position.y + 7.0 * s), Vector2(key_width, 20.0 * s))
		_overlay.draw_style_box(_key, cap)
		_text(cap.position + Vector2(6.0, 14.2) * s, pairs[i], small, TEXT)
		x += key_width + 6.0 * s
		_text(Vector2(x, box.position.y + 22.0 * s), pairs[i + 1], regular, TEXT)
		x += _text_width(pairs[i + 1], regular) + 16.0 * s
	_text(box.position + Vector2(12, 44) * s, movement, small, MUTED)
	return box


func _draw_charge(box: Rect2, s: float) -> void:
	_overlay.draw_style_box(_panel, box)
	var start := box.position + Vector2(12, 23) * s
	var size := roundi(13.0 * s)
	_text(start, "Натяжение", size, MUTED)
	var value := "%d%%" % _percent
	var color := TEXT if _percent < 100 else AMBER
	_text(Vector2(box.end.x - 12.0 * s - _text_width(value, size), start.y), value, size, color)
	var track := Rect2(box.position + Vector2(12, 36) * s, Vector2(box.size.x - 24.0 * s, 4.0 * s))
	_overlay.draw_rect(track, Color("42545e"))
	if _percent > 0:
		_overlay.draw_rect(Rect2(track.position, Vector2(track.size.x * _percent / 100.0, track.size.y)), AMBER)


func _text(position: Vector2, label: String, font_size: int, color: Color) -> void:
	_overlay.draw_string(_font, position.round(), label, HORIZONTAL_ALIGNMENT_LEFT, -1.0, font_size, color)


func _text_width(label: String, font_size: int) -> float:
	return _font.get_string_size(label, HORIZONTAL_ALIGNMENT_LEFT, -1.0, font_size).x
