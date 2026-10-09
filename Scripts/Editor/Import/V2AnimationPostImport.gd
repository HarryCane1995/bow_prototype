@tool
extends EditorScenePostImport
## glTF has no standard loop flag. Read the exporter sidecar at import time.
func _post_import(scene: Node) -> Object:
	return apply_metadata(scene, get_source_file().get_basename() + ".animations.json")

static func apply_metadata(scene: Node, path: String) -> Object:
	if not FileAccess.file_exists(path):
		push_error("V2 animation metadata missing: " + path)
		return scene
	var metadata = JSON.parse_string(FileAccess.get_file_as_string(path))
	var player = scene.find_child("AnimationPlayer",true,false) as AnimationPlayer
	if player == null: return scene
	for clip in metadata.clips:
		if not player.has_animation(clip):
			push_error("V2 clip missing: " + clip)
			continue
		var animation = player.get_animation(clip)
		animation.loop_mode = Animation.LOOP_LINEAR if metadata.clips[clip].loop else Animation.LOOP_NONE
		animation.length = metadata.clips[clip].duration_seconds
	return scene
