#!/usr/bin/env python3
"""BowPrototype procedural sound bank. Python 3 stdlib only; no input samples.

Run from any directory: python Tools/Audio/generate_audio.py [--check]
48 kHz mono PCM16. Fixed per-file seeds, deterministic asset manifest.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path
import random
import struct
import wave
import zlib

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "Assets/Audio/Procedural"
RATE = 48000
SEED = 0xB07A2026
TAU = 2 * math.pi
# duration, low resonator, upper resonator, noise/body mix, pitch sweep, variants
FAMILIES = {
    "jump": (.15, 330, 1120, .44, 1.7, 3),
    "air_jump": (.17, 460, 1720, .40, 2.2, 3),
    "landing_light": (.095, 310, 890, .58, -.4, 3),
    "landing_medium": (.15, 220, 690, .54, -.6, 3),
    "landing_heavy": (.23, 140, 440, .58, -.7, 3),
    "wall_enter": (.12, 420, 1860, .65, -.2, 2),
    "wall_exit": (.09, 560, 1260, .60, 1.1, 2),
    "wall_jump": (.18, 310, 1430, .52, 1.8, 3),
    "slide_enter": (.16, 240, 1040, .83, -.5, 3),
    "slide_exit": (.10, 380, 1730, .74, .8, 2),
    "grapple_fire": (.14, 640, 2480, .52, -1.5, 3),
    "grapple_attach": (.12, 720, 1890, .40, -.3, 3),
    "grapple_release": (.20, 380, 1580, .59, 1.3, 3),
    "checkpoint": (.25, 830, 1245, .10, .0, 2),
    "reset": (.22, 625, 938, .17, -.3, 2),
}


def one_shot(name, variant, params):
    duration, base, upper, mix, sweep, _ = params
    rng = random.Random(SEED + zlib.crc32(f"{name}/{variant}".encode()))
    detune = rng.uniform(.97, 1.03)
    count = round(duration * RATE)
    lp, last_lp, phase, upper_phase = 0., 0., 0., 0.
    samples = []
    for i in range(count):
        t = i / RATE
        u = i / (count - 1)
        lp += .31 * (rng.uniform(-1, 1) - lp)
        noise = lp - .48 * last_lp
        last_lp = lp
        env = min(1., t / .0025) * math.exp(-6.0 * u) * min(1., (1-u) / .055)
        phase += TAU * base * detune * (1 + sweep * .22 * (1-u)) / RATE
        upper_phase += TAU * upper * detune * (1 + sweep * .15 * (1-u)) / RATE
        body = .62 * math.sin(phase) + .25 * math.sin(upper_phase) * math.exp(-4*u)
        if name == "checkpoint":
            body = .55 * math.sin(phase) + .3 * math.sin(TAU * upper * t) * min(1., t / .065)
        click = noise * math.exp(-34*u) * .55
        samples.append(env * ((1-mix) * body + mix * noise * 1.8) + click * min(1., t/.001))
    return samples


def loop(name, low, high, duration=2.):
    """Periodic noise: integer-bin additive synthesis, exact seam continuity."""
    rng = random.Random(SEED + zlib.crc32(name.encode()))
    count = round(duration * RATE)
    samples = [0.] * count
    bins = rng.sample(range(math.ceil(low * duration), math.floor(high * duration)), 180)
    for bin_no in bins:
        step = TAU * bin_no / count
        phase = rng.uniform(0, TAU)
        amplitude = rng.uniform(.45, 1.) / math.sqrt(bin_no)
        # Recurrence avoids millions of sin calls; fixed reset bounds drift.
        c, s = math.cos(step), math.sin(step)
        x, y = math.cos(phase), math.sin(phase)
        for i in range(count):
            samples[i] += y * amplitude
            x, y = x*c-y*s, y*c+x*s
    return samples


def pcm(samples, peak=.58):
    mean = sum(samples) / len(samples)
    samples = [x - mean for x in samples]
    scale = peak / max(abs(x) for x in samples)
    return b"".join(struct.pack("<h", round(x * scale * 32767)) for x in samples)


def write_wav(path, payload):
    with wave.open(str(path), "wb") as f:
        f.setnchannels(1)
        f.setsampwidth(2)
        f.setframerate(RATE)
        f.writeframes(payload)


def generate():
    for name, params in FAMILIES.items():
        for variant in range(params[-1]):
            yield f"{name}_{variant}.wav", pcm(one_shot(name, variant, params)), False
    for name, low, high in [("wind_low", 170, 1600), ("wind_high", 1000, 7000),
                            ("slide_loop", 420, 4100), ("wall_loop", 250, 2800),
                            ("grapple_loop", 600, 3800)]:
        yield name + ".wav", pcm(loop(name, low, high), .40), True


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="Regenerate in memory; verify exact PCM against assets.")
    args = parser.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    manifest = {"schema": 1, "generator": "Tools/Audio/generate_audio.py", "seed": SEED,
                "sample_rate": RATE, "format": "mono PCM16", "source_samples": "none", "assets": []}
    for name, payload, looping in generate():
        path = OUT / name
        if args.check:
            with wave.open(str(path), "rb") as f:
                assert f.getframerate() == RATE and f.getnchannels() == 1
                assert f.readframes(f.getnframes()) == payload, name
        else:
            write_wav(path, payload)
        values = struct.unpack(f"<{len(payload)//2}h", payload)
        manifest["assets"].append({"file": name, "loop": looping, "frames": len(values),
            "seconds": len(values)/RATE, "pcm_sha256": hashlib.sha256(payload).hexdigest(),
            "peak_dbfs": round(20*math.log10(max(abs(v) for v in values)/32768), 3),
            "rms_dbfs": round(20*math.log10(math.sqrt(sum(v*v for v in values)/len(values))/32768), 3)})
    serialized = json.dumps(manifest, indent=2) + "\n"
    if args.check:
        assert (OUT / "manifest.json").read_text() == serialized
    else:
        (OUT / "manifest.json").write_text(serialized)
    print(f"{'VERIFIED' if args.check else 'GENERATED'} {len(manifest['assets'])} reproducible assets")


if __name__ == "__main__":
    main()
