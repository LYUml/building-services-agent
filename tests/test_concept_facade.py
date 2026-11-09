import json
from pathlib import Path
import runpy
import tempfile
import unittest
import ifcopenshell
from bsa.concept_facade import run,inspect,settings
from bsa.concept_layout import geometry_handoff
from bsa.engine import ProjectError
ROOT=Path(__file__).resolve().parents[1]

class ConceptFacadeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp=tempfile.TemporaryDirectory(dir=ROOT/'runs');cls.addClassCleanup(cls.temp.cleanup);cls.root=Path(cls.temp.name)
        runpy.run_path(str(ROOT/'scripts/run_public_massing.py'))['run'](cls.root/'source')
        cls.basis=dict(source='Explicit synthetic 0.2 m wall and 0.04 m window envelope decisions; no product rating',wall_thickness_m=.2,window_envelope_thickness_m=.04)
        cls.layout=dict(source='Course comparison target with unapproved centered rectangle design',window_wall_ratio=.4,layout='centered-equal-fraction')
        for name,data in [('basis',cls.basis),('layout',cls.layout)]: (cls.root/(name+'.json')).write_text(json.dumps(data),encoding='utf-8')
        cls.results={label:run(cls.root/'source'/label/'model.ifc',cls.root/'source'/(label+'.json'),cls.root/'layout.json',cls.root/'basis.json',cls.root/label) for label in ('compact','slender','stacked')}

    def test_actual_three_variants_have_saved_native_voids_and_preserved_sources(self):
        for label,count,area in [('compact',8,476),('slender',8,532),('stacked',16,672)]:
            r=self.results[label]
            self.assertEqual(len(r['records']),count)
            self.assertAlmostEqual(sum(x['opening_area_m2'] for x in r['records']),area)
            self.assertTrue(r['native_geometry_checks_pass']);self.assertTrue(r['original_records_preserved'])
            self.assertTrue(all(x['through_opening_euler']==0 for x in r['records']))
            self.assertFalse(r['thermal_model_ready']);self.assertFalse(r['design_accepted'])
        a=self.results['compact']['records'];b=self.results['slender']['records']
        self.assertEqual([r['window_guid'] for r in a],[r['window_guid'] for r in b])

    def test_changed_saved_void_window_identity_and_source_reject(self):
        source=json.loads((self.root/'source/compact.json').read_text(encoding='utf-8'))
        handoff=geometry_handoff(self.root/'source/compact/model.ifc',source,.4)
        for mode in ('void','fill','window','identity','source'):
            m=ifcopenshell.open(str(self.root/'compact/facade.ifc'))
            if mode=='void':m.remove(m.by_type('IfcRelVoidsElement')[0])
            if mode=='fill':m.remove(m.by_type('IfcRelFillsElement')[0])
            if mode=='window':m.by_type('IfcWindow')[0].OverallWidth+=1
            if mode=='identity':m.by_type('IfcWindow')[0].GlobalId=ifcopenshell.guid.new()
            if mode=='source':
                import ifcopenshell.util.element as element
                ps=element.get_psets(m.by_type('IfcWall')[0])['BSA_ConceptFacade']
                next(p for p in m.by_id(ps['id']).HasProperties if p.Name=='Source').NominalValue.wrappedValue='wrong'
            with self.subTest(mode=mode),self.assertRaises(ProjectError):inspect(m,source,handoff,self.basis)

    def test_unknown_or_invalid_thickness_is_not_inferred(self):
        for key,value in [('source',''),('wall_thickness_m',True),('wall_thickness_m',0),('window_envelope_thickness_m',.3)]:
            row=dict(self.basis);row[key]=value
            with self.subTest(key=key),self.assertRaises(ProjectError):settings(row)
