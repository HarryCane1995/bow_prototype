@tool
extends RefCounted
## Exact source-name mapping, restricted to Level_01 by the caller.
const PREFIX := "M_Level01_Art_"
const DIRECTORY := "res://Assets/Materials/Environment/Level01Art/"

static func resolve(source_name: String) -> Material:
	if not source_name.begins_with(PREFIX):
		return null
	var key := source_name.trim_prefix(PREFIX)
	if not key.is_valid_identifier():
		push_error("Invalid Level_01 art material key: " + key)
		return null
	var path := DIRECTORY + key + ".tres"
	if not ResourceLoader.exists(path):
		push_error("Missing Level_01 art material: " + path)
		return null
	return load(path) as Material
