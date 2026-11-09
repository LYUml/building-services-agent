import copy
import json
from pathlib import Path
import runpy
import tempfile
import unittest
import ifcopenshell
from bsa.bim import run,validate
from bsa.concept_spaces import inspect_spaces
from bsa.engine import ProjectError
ROOT=Path(__file__).resolve().parents[1]

class ConceptSpaceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp=tempfile.TemporaryDirectory(dir=ROOT/'runs');cls.addClassCleanup(cls.temp.cleanup);cls.root=Path(cls.temp.name)
        cls.driver=runpy.run_path(str(ROOT/'scripts/run_public_massing.py'))
        cls.decisions=json.loads((ROOT/'benchmarks/mit-4401-2018/massing-decisions.json').read_text(encoding='utf-8'))
        cls.result=cls.driver['run'](cls.root/'concepts')

    def source(self,label='compact'):return json.loads((self.root/'concepts'/(label+'.json')).read_text(encoding='utf-8'))

    def test_actual_variants_have_native_area_storeys_and_no_fabricated_MEP(self):
        for label,row in self.result['variants'].items():
            model=ifcopenshell.open(str(self.root/'concepts'/label/'model.ifc'))
            spaces=inspect_spaces(model,self.source(label))
            self.assertEqual(sum(r['gross_footprint_area_m2'] for r in spaces),3500.)
            self.assertEqual(len(model.by_type('IfcBuildingStorey')),row['space_count'])
            self.assertEqual(len(model.by_type('IfcDistributionElement')),0);self.assertTrue(row['model_checks_pass'])
        self.assertFalse(self.result['design_accepted'])
        a=ifcopenshell.open(str(self.root/'concepts/compact/model.ifc'));b=ifcopenshell.open(str(self.root/'concepts/slender/model.ifc'))
        self.assertEqual({o.Name:o.GlobalId for o in a.by_type('IfcSpace')},{o.Name:o.GlobalId for o in b.by_type('IfcSpace')})

    def test_saved_geometry_and_storey_tampering_reject(self):
        for mode in ('geometry','level','source','storey_id','storey_source','storey_placement'):
            m=ifcopenshell.open(str(self.root/'concepts/compact/model.ifc'));obj=m.by_type('IfcSpace')[0]
            if mode=='geometry':obj.ObjectPlacement.RelativePlacement.Location.Coordinates=(1.,0.,0.)
            if mode=='level':m.by_type('IfcBuildingStorey')[0].Elevation=99.
            if mode=='storey_id':m.by_type('IfcBuildingStorey')[0].GlobalId=ifcopenshell.guid.new()
            if mode=='source':obj.GlobalId=ifcopenshell.guid.new()
            if mode=='storey_placement':m.by_type('IfcBuildingStorey')[0].ObjectPlacement.RelativePlacement.Location.Coordinates=(0.,0.,99.)
            if mode=='storey_source':
                data=__import__('ifcopenshell.util.element',fromlist=['get_psets']).get_psets(m.by_type('IfcBuildingStorey')[0])['BSA_DesignInputs']
                prop=next(p for p in m.by_id(data['id']).HasProperties if p.Name=='Source')
                prop.NominalValue.wrappedValue='fabricated source'
            with self.subTest(mode=mode),self.assertRaises(ProjectError):inspect_spaces(m,self.source())

    def test_source_overlap_mismatched_levels_and_fake_MEP_reject(self):
        for mode in ('overlap','height','mep','basis'):
            p=self.source()
            if mode=='overlap':p['spaces'].append(dict(p['spaces'][0],id='duplicate-volume'))
            if mode=='height':p['spaces'][0]['size_m'][2]=3.
            if mode=='mep':p['systems']=[dict(id='fake',predefined_type='AIRCONDITIONING',source='design')]
            if mode=='basis':p['floor_area_basis']='net usable'
            with self.subTest(mode=mode),self.assertRaises(ProjectError):validate(p)

    def test_old_MEP_scope_still_requires_real_system_device_inputs(self):
        p=self.source();p['geometry_scope']='axis-aligned bounding envelopes'
        with self.assertRaisesRegex(ProjectError,'nonempty'):validate(p)

    def test_saved_thermal_geometry_handoff_reconciles_contacts_and_targets(self):
        expected={'compact':(1190.,1750.,1),'slender':(1330.,1750.,1),'stacked':(1680.,875.,3)}
        for label,(walls,roof,count) in expected.items():
            r=json.loads((self.root/'concepts'/label/'geometry-handoff.json').read_text(encoding='utf-8'))
            self.assertEqual(r['exterior_vertical_face_area_m2'],walls)
            self.assertEqual(r['exposed_top_face_area_m2'],roof)
            self.assertEqual(r['exposed_bottom_face_area_m2'],roof)
            self.assertEqual(len(r['adjacency']),count)
            self.assertAlmostEqual(r['target_glazed_area_m2'],walls*.4)
            self.assertEqual(r['modeled_window_area_m2'],0)
            self.assertFalse(r['thermal_model_ready']);self.assertFalse(r['design_accepted'])
            self.assertEqual(r['ifc_sha256'],self.result['variants'][label]['ifc_sha256'])

    def test_handoff_rejects_changed_native_geometry(self):
        m=ifcopenshell.open(str(self.root/'concepts/compact/model.ifc'))
        m.by_type('IfcSpace')[0].ObjectPlacement.RelativePlacement.Location.Coordinates=(2.,0.,0.)
        path=self.root/'changed.ifc';m.write(str(path))
        with self.assertRaises(ProjectError):self.driver['geometry_handoff'](path,self.source(),.4)
