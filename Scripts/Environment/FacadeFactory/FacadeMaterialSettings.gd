extends Resource
## Reusable standard ORM setup. Settings apply to a private material duplicate.
## Original .tres resources are never mutated by review controls.

@export_range(0.0, 8.0, 0.05) var emission_strength: float = 1.0
@export var uv_scale: Vector2 = Vector2.ONE
@export var macro_tint: Color = Color.WHITE

func make_material(source: ORMMaterial3D) -> ORMMaterial3D:
	var material := source.duplicate() as ORMMaterial3D
	material.emission_energy_multiplier = source.emission_energy_multiplier * emission_strength
	material.uv1_scale = Vector3(uv_scale.x, uv_scale.y, 1.0)
	material.albedo_color = macro_tint
	return material
