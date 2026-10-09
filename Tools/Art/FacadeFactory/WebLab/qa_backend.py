"""Bounded WebLab QA; writes its temporary test assets only under WebLab/review."""
import hashlib
import json
from pathlib import Path
import statistics
import subprocess
import sys
import tempfile

from lab_backend import HERE, ROOT, FACTORY, Lab, PRESETS, CHANNELS, config, load_recipe, normalized_request


def main():
    before = {f: hashlib.sha256((FACTORY / f).read_bytes()).hexdigest() for f in
              ("facade_factory.py", "facade_presets.py", "facade_stylizer.py")}
    report = {"presets": [], "checks": {}}
    review = HERE / "review"; review.mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="qa_", dir=review) as tmp:
        work = Path(tmp)
        lab = Lab(work / "cache", work / "favorites", work / "exports", work / "materials")
        for preset in PRESETS:
            preview = lab.preview({"preset": preset, "seed": 9123})
            again = lab.preview({"preset": preset, "seed": 9123})
            assert again["cached"] and again["sha256"] == preview["sha256"]
            assert set(preview["maps"]) == set(CHANNELS)
            report["presets"].append({"preset": preset, "generation_ms": preview["generation_ms"], "cache_ms": again["elapsed_ms"]})
        recipe = {"preset": "INDUSTRIAL_TOWER", "seed": 99,
                  "parameters": {"window_density": .14, "grime_amount": .65},
                  "style": {"posterization": 32}, "palette": "concrete"}
        result = lab.preview(recipe)
        different = lab.preview({**recipe, "seed": 100})
        assert result["sha256"] != different["sha256"]
        favorite = lab.favorite(recipe)
        assert len(lab.list_favorites()) == 1
        restored_favorite = load_recipe(favorite["recipe"])
        assert lab.preview(restored_favorite)["sha256"] == result["sha256"]
        exports = []
        for resolution in ([512, 1024], [1024, 2048]):
            exported = lab.export({**recipe, "name": "qa_industrial", "resolution": resolution})
            exports.append(exported)
            document = json.loads((lab.exports / f'{exported["name"]}.facade.json').read_text())
            restored = load_recipe(document)
            replay = lab.export({**restored, "name": "replay_" + str(resolution[0])})
            assert replay["recipe"]["sha256"] == exported["recipe"]["sha256"]
            for channel in CHANNELS:
                path = lab.exports / document["outputs"][channel]
                assert hashlib.sha256(path.read_bytes()).hexdigest() == document["sha256"][channel]
            text = (lab.materials / f'{exported["name"]}.tres').read_text()
            assert 'type="ORMMaterial3D"' in text and exported["name"] + "_orm.png" in text
        assert exports[0]["name"] == "qa_industrial"
        assert exports[1]["name"] == "qa_industrial_r02" and exports[1]["revisioned"]
        for channel in CHANNELS:
            original = lab.exports / exports[0]["recipe"]["outputs"][channel]
            assert hashlib.sha256(original.read_bytes()).hexdigest() == exports[0]["recipe"]["sha256"][channel]
        # Numeric validation, unsafe filenames, unknown controls and version drift fail closed.
        bad = [dict(recipe, seed=-1), dict(recipe, parameters={"window_density": float("nan")}),
               dict(recipe, style={"posterization": 3}), dict(recipe, parameters={"unrecognized": 1})]
        for payload in bad:
            try:
                normalized_request(payload)
                raise AssertionError("Accepted invalid request")
            except ValueError:
                pass
        for name in ("../outside", "a/b", "CON", "NUL"):
            try:
                lab.export({**recipe, "name": name, "resolution": [512, 1024]})
                raise AssertionError("Accepted unsafe filename")
            except ValueError:
                pass
        try:
            load_recipe({**favorite["recipe"], "generator_fingerprint": "different"})
            raise AssertionError("Accepted generator mismatch")
        except ValueError:
            pass
        # Execute the existing CLI parser/main in a subprocess. Redirect only its
        # report/preview root in memory so the delivered 24-facade board is untouched.
        code = "import sys;from pathlib import Path;sys.path.insert(0,sys.argv[1]);import facade_factory as f;f.HERE=Path(sys.argv[2]);sys.argv=['facade_factory.py','--batch','--output',str(f.HERE/'maps'),'--no-material'];f.main()"
        cli = subprocess.run([sys.executable, "-c", code, str(FACTORY), str(work / "cli")], capture_output=True, text=True)
        assert cli.returncode == 0, cli.stderr
        manifest = json.loads((work / "cli/generated/batch_manifest.json").read_text())
        assert len(manifest["variants"]) == 24
        # Canonical CLI and adapter use exactly the same raster recipe.
        base = lab.preview({"preset": "INDUSTRIAL_TOWER", "seed": 42})
        from facade_factory import generate
        from facade_presets import get_preset
        direct = generate(get_preset("industrial"), 42, 256, 512, work / "direct", None)
        assert base["sha256"] == direct["sha256"]
        report["checks"] = dict(all_six_presets=True, cache_hit=True, seed_divergence=True,
            favorites_roundtrip=True, full_recipe_roundtrip_both_resolutions=True,
            canonical_maps_identical=True, revision_suffix_no_overwrite=True,
            godot_material=True, input_validation=True, batch_cli_24_variants=True,
            canonical_source_unchanged=True)
        report["cli_seconds"] = manifest["generation_seconds"]
    for path, digest in before.items():
        assert hashlib.sha256((FACTORY / path).read_bytes()).hexdigest() == digest
    report["average_preview_generation_ms"] = round(statistics.mean(p["generation_ms"] for p in report["presets"]), 1)
    report["passed"] = True
    (review / "backend_qa.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))


if __name__ == "__main__": main()
