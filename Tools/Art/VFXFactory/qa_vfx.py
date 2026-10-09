"""Determinism, alpha, atlas/sequence parity and non-destructive export QA."""
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest
import numpy as np
from PIL import Image

HERE = Path(__file__).resolve().parent
LAB = HERE.parent / 'FacadeFactory/WebLab'
sys.path.insert(0, str(LAB))
from vfx_backend import VFXLab, load_recipe
from schema import normalize
from explosion import frames


class ExplosionQA(unittest.TestCase):
    def test_coherent_deterministic_frames_alpha_and_seed(self):
        recipe = normalize({})
        a, emission = frames(recipe); b, _ = frames(normalize(recipe))
        self.assertEqual([im.tobytes() for im in a], [im.tobytes() for im in b])
        other, _ = frames(normalize(dict(recipe, seed=100)))
        self.assertNotEqual(a[4].tobytes(), other[4].tobytes())
        self.assertFalse(np.array(a[-1])[:, :, 3].any())
        self.assertFalse(np.array(emission[-1])[:, :, 3].any())
        self.assertTrue(np.array(a[22])[:, :, 3].any())
        self.assertFalse(np.array(emission[22])[:, :, 3].any(), 'Late smoke should not emit')
        for image in a + emission:
            pixels = np.array(image)
            self.assertFalse(pixels[[0, -1], :, 3].any(), 'Top/bottom clipped')
            self.assertFalse(pixels[:, [0, -1], 3].any(), 'Left/right clipped')
            self.assertFalse(pixels[pixels[:, :, 3] == 0, :3].any(), 'Hidden RGB must stay clean')
            self.assertLessEqual(len(np.unique(pixels[pixels[:, :, 3] > 0, :3], axis=0)), recipe['parameters']['palette_color_count'])

    def test_frame_hold_and_color_edit(self):
        recipe = normalize({'parameters': {'frame_stepping': 2}})
        a, _ = frames(recipe)
        self.assertEqual(a[4].tobytes(), a[5].tobytes())
        recipe['colors']['primary'] = '#5588aa'
        b, _ = frames(recipe)
        self.assertNotEqual(a[4].tobytes(), b[4].tobytes())
        self.assertTrue(np.array_equal(np.array(a[4])[:, :, 3], np.array(b[4])[:, :, 3]))

    def test_export_reload_and_revision_preserve_files(self):
        parent = LAB / '.cache'; parent.mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(dir=parent, prefix='vfx_qa_') as tmp:
            lab = VFXLab(cache=Path(tmp) / 'cache', exports=Path(tmp) / 'exports')
            first = lab.export({'name': 'qa_effect', 'recipe': {}, 'format': 'BOTH'})
            folder = lab.exports / first['name']
            doc = json.loads((folder / 'qa_effect.vfx.json').read_text())
            self.assertEqual(load_recipe(doc), normalize({}))
            second = lab.export({'name': 'qa_effect', 'recipe': doc, 'format': 'BOTH'})
            self.assertEqual(second['name'], 'qa_effect_r02')
            self.assertEqual(doc['sha256'], second['recipe']['sha256'])
            for name, digest in doc['sha256'].items():
                self.assertEqual(hashlib.sha256((folder / name).read_bytes()).hexdigest(), digest)
            with Image.open(folder / 'color_sheet.png') as sheet:
                for i, (x, y, w, h) in enumerate(first['metadata']['rectangles']):
                    with Image.open(folder / 'color' / f'color_{i:04d}.png') as frame:
                        self.assertEqual(sheet.crop((x, y, x+w, y+h)).tobytes(), frame.tobytes())
            lean = lab.export({'name': 'no_emission', 'recipe': {}, 'format': 'FLIPBOOK', 'emission': False})
            self.assertFalse((lab.exports / lean['name'] / 'emission_sheet.png').exists())
            self.assertFalse((lab.exports / lean['name'] / 'color').exists())
            self.assertIn('shader_parameter/use_emission = false', (lab.exports / lean['name'] / 'explosion.tres').read_text())

    def test_invalid_recipes(self):
        for request in [dict(seed=-1), dict(seed=True), dict(resolution=1024), dict(effect='FIRE'),
                        dict(parameters={'fps': 60}), dict(parameters={'duration': float('nan')}),
                        dict(parameters={'unknown': 1}), dict(colors={'primary': 'red'})]:
            with self.assertRaises(ValueError):
                normalize(request)
        with self.assertRaises(ValueError):
            load_recipe(dict(normalize({}), generator_fingerprint='outdated'))


if __name__ == '__main__':
    unittest.main()
