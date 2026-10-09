"""Favorite persistence and legacy compatibility; uses temporary files only."""
import base64
import io
import json
from pathlib import Path
import tempfile
import unittest

from PIL import Image
from lab_backend import Lab, load_recipe, normalized_request


def thumbnail(size=(256, 160)):
    output = io.BytesIO()
    Image.new('RGB', size, '#56736a').save(output, format='PNG')
    return 'data:image/png;base64,' + base64.b64encode(output.getvalue()).decode()


class FavoritePersistence(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.lab = Lab(cache=self.root / 'cache', favorites=self.root / 'favorites')

    def tearDown(self):
        self.temp.cleanup()

    def test_three_modes_survive_restart_and_reload(self):
        for mode, preset in [('UNIQUE_FACADE', 'INDUSTRIAL_TOWER'),
                             ('TILEABLE_SURFACE', 'INDUSTRIAL_FLOOR'),
                             ('CYLINDER_WRAP', 'REACTOR_CORE_WRAP')]:
            with self.subTest(mode=mode):
                _, recipe = normalized_request(dict(surface_mode=mode, preset=preset, seed=99))
                result = self.lab.favorite({'recipe': recipe, 'thumbnail_data_url': thumbnail()})
                doc = result['recipe']
                self.assertEqual(load_recipe(doc), recipe)
                self.assertNotIn('data:image', json.dumps(doc))
                with Image.open(self.lab.favorites / doc['thumbnail']) as image:
                    self.assertEqual((image.format, image.size), ('WEBP', (256, 160)))
        restarted = Lab(cache=self.lab.cache, favorites=self.lab.favorites)
        entries = restarted.list_favorites()
        self.assertEqual(len(entries), 3)
        self.assertTrue(all(e['thumbnail_url'].endswith('.thumb.webp') for e in entries))
        for entry in entries:
            self.assertEqual(load_recipe(entry['recipe'])['seed'], 99)

    def test_legacy_and_missing_thumbnail_are_loadable(self):
        old = self.lab.favorite({'preset': 'INDUSTRIAL_TOWER', 'seed': 99})
        self.assertNotIn('thumbnail', old['recipe'])
        self.assertIsNone(self.lab.list_favorites()[0]['thumbnail_url'])
        new = self.lab.favorite({'recipe': old['recipe'], 'thumbnail_data_url': thumbnail()})
        (self.lab.favorites / new['recipe']['thumbnail']).unlink()
        self.assertTrue(all(e['thumbnail_url'] is None for e in self.lab.list_favorites()))
        self.assertEqual(load_recipe(old['recipe']), load_recipe(new['recipe']))

    def test_invalid_images_leave_no_partial_favorite(self):
        for invalid in [thumbnail((512, 512)), 'data:image/png;base64,bm90LWFuLWltYWdl',
                        '../../project.godot', 'x' * 250001]:
            with self.assertRaises(ValueError):
                self.lab.favorite({'recipe': {'preset': 'INDUSTRIAL_TOWER'}, 'thumbnail_data_url': invalid})
        self.assertEqual(list(self.lab.favorites.iterdir()), [])
        for path in ['../project.godot', '../outside.thumb.webp', 'recipe.facade.json', None]:
            self.assertIsNone(self.lab.thumbnail_path(path))


if __name__ == '__main__':
    unittest.main()
