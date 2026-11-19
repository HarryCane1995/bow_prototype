extends Node

@export_range(-30.0, 0.0, 0.5, "suffix:dB") var volume_db := -7.0

var _attach: AudioStreamPlayer
var _release: AudioStreamPlayer
var _resonance: AudioStreamPlayer
var _impact: AudioStreamPlayer


func _ready() -> void:
	_attach = _voice(_pluck(0.12, 520.0, 0.22, 0.30), -11.0)
	_release = _voice(_pluck(0.32, 185.0, 0.86, 0.85), 0.0)
	_resonance = _voice(_pluck(0.21, 790.0, 0.06, 0.18), -15.0)
	_impact = _voice(_pluck(0.19, 340.0, 0.52, 0.50), -3.0)


func nock() -> void:
	_attach.pitch_scale = 1.12
	_attach.play()


func settle() -> void:
	_attach.pitch_scale = 0.76
	_attach.play()


func full_draw() -> void:
	_resonance.play()


func fire(amount: float) -> void:
	_release.pitch_scale = lerpf(1.18, 0.90, amount)
	_release.volume_db = volume_db + lerpf(-4.5, 0.0, amount)
	_release.play()


func hit() -> void:
	_impact.play()


func _voice(stream: AudioStreamWAV, level: float) -> AudioStreamPlayer:
	var player := AudioStreamPlayer.new()
	player.stream = stream
	if AudioServer.get_bus_index(&"SFX") >= 0:
		player.bus = &"SFX"
	player.max_polyphony = 4
	player.volume_db = volume_db + level
	add_child(player)
	return player


func _pluck(duration: float, frequency: float, sweep: float, noise_level: float) -> AudioStreamWAV:
	const RATE := 22050
	var samples := ceili(RATE * duration)
	var pcm := PackedByteArray()
	pcm.resize(samples * 2)
	var noise := RandomNumberGenerator.new()
	noise.seed = roundi(frequency * 17)
	var filtered := 0.0
	var phase := 0.0
	for i in samples:
		var t := float(i) / RATE
		phase += TAU * frequency * (1.0 + sweep * exp(-t * 75.0)) / RATE
		filtered = lerpf(filtered, noise.randf_range(-1.0, 1.0), 0.53)
		var body := sin(phase) + 0.40 * sin(phase * 2.93) + 0.18 * sin(phase * 5.11)
		var signal_value := body * 0.37 * exp(-t * 7.8 / duration)
		signal_value += filtered * noise_level * exp(-t * 145.0)
		signal_value *= minf(t / 0.0015, 1.0)
		pcm.encode_s16(i * 2, roundi(clampf(signal_value, -1.0, 1.0) * 32767.0))
	var stream := AudioStreamWAV.new()
	stream.format = AudioStreamWAV.FORMAT_16_BITS
	stream.mix_rate = RATE
	stream.data = pcm
	return stream
