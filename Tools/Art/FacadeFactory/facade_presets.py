"""Art direction only. Dimensions are measured on a 512 x 1024 design sheet."""
from dataclasses import dataclass, replace


@dataclass(frozen=True)
class RetroStyle:
    posterization: int = 40
    dithering: float = .22
    color_quantization: int = 112
    micro_contrast: float = .12
    compression_artifacts: float = .08
    pixel_noise: float = .65
    edge_exaggeration: float = .20
    baked_ao_strength: float = .32


@dataclass(frozen=True)
class FacadePreset:
    name: str
    grammar: str
    palette: str = "cold"
    window_density: float = .82
    window_aspect: float = .8
    floor_height: float = 27
    structural_width: float = 10
    service_floor_frequency: float = .14
    dark_floor_frequency: float = .08
    emission_density: float = .42
    emission_strength: float = 1.35
    grime_amount: float = .22
    panel_density: float = .35
    signage_density: float = .20
    macro_contrast: float = .23
    retro_strength: float = .72
    style: RetroStyle = RetroStyle()


PALETTES = {
    "cold": dict(base=(72, 87, 91), concrete=(104, 114, 110), metal=(89, 110, 112),
                 recess=(17, 29, 35), glass=(31, 55, 63), accent=(88, 189, 168), warm=(198, 130, 64)),
    "concrete": dict(base=(98, 106, 102), concrete=(133, 133, 119), metal=(77, 97, 99),
                     recess=(25, 33, 35), glass=(40, 58, 60), accent=(104, 179, 156), warm=(197, 122, 64)),
    "industrial": dict(base=(80, 92, 88), concrete=(112, 120, 108), metal=(109, 123, 118),
                      recess=(23, 34, 34), glass=(37, 60, 60), accent=(102, 186, 155), warm=(204, 137, 66)),
}

PRESETS = {
    p.name: p for p in [
        FacadePreset("CORPORATE_MONOLITH", "corporate", window_aspect=.65, structural_width=14,
                     grime_amount=.10, panel_density=.16, signage_density=.10, emission_density=.32),
        FacadePreset("MEGABLOCK", "megablock", palette="concrete", window_density=.68,
                     window_aspect=1.40, floor_height=25, structural_width=17,
                     service_floor_frequency=.23, dark_floor_frequency=.13,
                     grime_amount=.40, panel_density=.45, signage_density=.34),
        FacadePreset("INDUSTRIAL_TOWER", "industrial", palette="industrial", window_density=.28,
                     window_aspect=1.65, floor_height=32, structural_width=18,
                     service_floor_frequency=.32, grime_amount=.48, panel_density=.88,
                     signage_density=.32, emission_density=.24, emission_strength=1.15),
        FacadePreset("EXOSKELETON_TOWER", "exoskeleton", window_density=.85,
                     window_aspect=.9, floor_height=26, structural_width=20,
                     panel_density=.24, grime_amount=.19, emission_density=.32),
        FacadePreset("OFFICE_GRID", "office", window_density=.96, window_aspect=.92,
                     floor_height=22, structural_width=5, panel_density=.13,
                     signage_density=.10, emission_density=.50, grime_amount=.16),
        FacadePreset("LANDMARK_TECH", "landmark", window_density=.58, window_aspect=.65,
                     floor_height=30, structural_width=14, panel_density=.44,
                     signage_density=.16, emission_density=.32, emission_strength=1.7,
                     grime_amount=.10, macro_contrast=.28),
    ]
}
ALIASES = {p.grammar: p.name for p in PRESETS.values()}


def get_preset(name, overrides=None, style_overrides=None):
    key = ALIASES.get(name.lower(), name.upper())
    if key not in PRESETS:
        raise ValueError(f"Unknown preset {name!r}; choose {', '.join(PRESETS)}")
    p = replace(PRESETS[key], **(overrides or {}))
    p = replace(p, style=replace(p.style, **(style_overrides or {})))
    for field in ("window_density", "service_floor_frequency", "dark_floor_frequency",
                  "emission_density", "grime_amount", "panel_density", "signage_density",
                  "macro_contrast", "retro_strength"):
        if not 0 <= getattr(p, field) <= 1:
            raise ValueError(f"{field} must be in [0, 1]")
    if not .2 <= p.window_aspect <= 3 or not 16 <= p.floor_height <= 60:
        raise ValueError("window_aspect: .2..3; floor_height: 16..60 design pixels")
    if not 2 <= p.structural_width <= 32 or not 0 <= p.emission_strength <= 8:
        raise ValueError("structural_width: 2..32; emission_strength: 0..8")
    s = p.style
    if not 4 <= s.posterization <= 256 or not 8 <= s.color_quantization <= 256:
        raise ValueError("posterization: 4..256; color_quantization: 8..256")
    for f in ("dithering", "micro_contrast", "compression_artifacts", "edge_exaggeration", "baked_ao_strength"):
        if not 0 <= getattr(s, f) <= 1:
            raise ValueError(f"style.{f} must be in [0, 1]")
    if not 0 <= s.pixel_noise <= 3:
        raise ValueError("style.pixel_noise must be in [0, 3]")
    return p
