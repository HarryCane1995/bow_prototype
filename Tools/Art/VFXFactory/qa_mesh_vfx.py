"""Geometry validity, seed stability, toggle isolation and runtime-export contracts."""
import copy
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest
import numpy as np

HERE=Path(__file__).resolve().parent
LAB=HERE.parent/'FacadeFactory/WebLab'
sys.path.insert(0,str(LAB))
from mesh_schema import normalize
from mesh_geometry import generate
from mesh_vfx_backend import MeshVFXLab,load_recipe
from mesh_archetypes import EFFECTS, defaults


class MeshQA(unittest.TestCase):
    def test_determinism_valid_triangle_meshes_and_real_depth(self):
        recipe=normalize({});a=generate(recipe);b=generate(normalize(recipe))
        self.assertEqual(a,b)
        other=generate(normalize(dict(recipe,seed=100)))
        self.assertNotEqual(a['meshes']['Petal_00'],other['meshes']['Petal_00'])
        for name,mesh in a['meshes'].items():
            xyz=np.array(mesh['positions']).reshape(-1,3);normals=np.array(mesh['normals']).reshape(-1,3)
            self.assertTrue(np.isfinite(xyz).all());self.assertEqual(len(xyz)%3,0)
            self.assertTrue(np.allclose(np.linalg.norm(normals,axis=1),1,atol=2e-6))
            self.assertEqual(len(mesh['uvs']),len(xyz)*2)
            if name!='ShockRing':self.assertTrue((np.ptp(xyz,axis=0)>.01).all(),name+' must have three-dimensional extent')
        for part in a['parts']:
            self.assertAlmostEqual(np.linalg.norm(part['rotation']),1)
            self.assertLessEqual(part['start']+part['life'],a['duration']+1e-6)

    def test_layers_and_materials_do_not_reshuffle_geometry(self):
        recipe=normalize({});base=generate(recipe)
        edited=copy.deepcopy(recipe);edited['layers']['smoke']['enabled']=False;edited['layers']['petals']['color']='#5588aa'
        changed=generate(normalize(edited))
        self.assertEqual(base['meshes'],changed['meshes']);self.assertEqual(base['parts'],changed['parts'])
        self.assertEqual(changed['stats']['mesh_count'],base['stats']['mesh_count']-recipe['parameters']['smoke_count'])
        edited['parameters']['petal_curl']=1.3
        self.assertNotEqual(base['meshes']['Petal_00'],generate(normalize(edited))['meshes']['Petal_00'])

    def test_export_reproduce_and_preserve(self):
        with tempfile.TemporaryDirectory(dir=LAB/'.cache',prefix='mesh_qa_') as tmp:
            lab=MeshVFXLab(cache=Path(tmp)/'cache',exports=Path(tmp)/'exports')
            a=lab.export({'name':'qa_mesh','recipe':{}});root=lab.exports/a['name']
            doc=json.loads((root/'qa_mesh.meshvfx.json').read_text())
            self.assertEqual(load_recipe(doc),normalize({}))
            b=lab.export({'name':'qa_mesh','recipe':doc})
            self.assertEqual(b['name'],'qa_mesh_r02');self.assertEqual(doc['mesh_sha256'],b['recipe']['mesh_sha256'])
            for name,digest in doc['mesh_sha256'].items():self.assertEqual(hashlib.sha256((root/name).read_bytes()).hexdigest(),digest)
            self.assertEqual([p.name for p in root.rglob('*.png')],['preview.png'],'Only one compact navigation thumbnail; no frame sequence')
            self.assertEqual(len(list((root/'materials').glob('*.tres'))),6)
            self.assertTrue((root/'explosion.tscn').is_file());self.assertTrue((root/'review.tscn').is_file())
            self.assertIn('instance uniform float life_alpha',(root/'materials/petals.gdshader').read_text())

    def test_all_archetypes_have_distinct_seeded_geometry_and_bounded_timing(self):
        signatures=set()
        for effect in EFFECTS:
            recipe=normalize(defaults(effect));a=generate(recipe)
            self.assertEqual(a,generate(normalize(recipe)),effect)
            signatures.add(hashlib.sha256(json.dumps(a['meshes'],sort_keys=True).encode()).hexdigest())
            other=generate(normalize(dict(recipe,seed=recipe['seed']+1)))
            self.assertNotEqual(a['parts'],other['parts'],effect)
            edited=copy.deepcopy(recipe);edited['layers']['core']['opacity']=.2;edited['layers']['shards']['enabled']=False
            changed=generate(normalize(edited));self.assertEqual(a['meshes'],changed['meshes']);self.assertEqual(a['parts'],changed['parts'])
            for name,mesh in a['meshes'].items():
                xyz=np.asarray(mesh['positions']).reshape(-1,3);normals=np.asarray(mesh['normals']).reshape(-1,3)
                self.assertTrue(np.isfinite(xyz).all(),effect+name)
                self.assertGreater(len(xyz),0);self.assertEqual(len(xyz)%3,0)
                self.assertTrue(np.allclose(np.linalg.norm(normals,axis=1),1,atol=2e-6),effect+name)
            for part in a['parts']:
                self.assertAlmostEqual(np.linalg.norm(part['rotation']),1,places=5)
                self.assertLessEqual(part['start']+part['life'],a['duration']+1e-6)
            self.assertLess(a['stats']['triangle_count'],15000)
        self.assertEqual(len(signatures),10,'Families must have genuinely distinct topology')

    def test_legacy_recipe_migrates_without_geometry_change(self):
        source=Path('Assets/VFX/Explosions/MeshExplosion3D/mesh_explosion_99/mesh_explosion_99.meshvfx.json')
        if not source.is_file():self.skipTest('Legacy export unavailable')
        data=json.loads(source.read_text());loaded=load_recipe(data)
        generated=generate(loaded)
        with tempfile.TemporaryDirectory() as tmp:
            from mesh_geometry import write_obj
            for name,mesh in generated['meshes'].items():
                path=Path(tmp)/(name+'.obj');write_obj(mesh,path)
                self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(),data['mesh_sha256']['meshes/'+name+'.obj'])

    def test_every_exposed_family_shape_control_changes_mesh_or_motion(self):
        for effect,meta in EFFECTS.items():
            recipe=normalize(defaults(effect));base=generate(recipe)
            for key in meta['shape_controls']:
                edited=copy.deepcopy(recipe);value=edited['parameters'][key]
                edited['parameters'][key]=value+1 if key in ('effect_count','effect_segments') else value*1.1
                changed=generate(normalize(edited))
                self.assertTrue(base['parts']!=changed['parts'] or base['meshes']!=changed['meshes'],effect+'/'+key)

    def test_invalid_input(self):
        for data in [{'seed':-1},{'parameters':{'petal_count':1000}}, {'parameters':{'vertex_wobble':float('nan')}},
                     {'layers':{'core':{'blend':'OPAQUE'}}},{'layers':{'core':{'enabled':1}}},{'effect':'PSX_EXPLOSION'}]:
            with self.assertRaises(ValueError):normalize(data)


if __name__=='__main__':unittest.main()
