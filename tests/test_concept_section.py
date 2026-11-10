import json
import math
from pathlib import Path
import runpy
import tempfile
import unittest
import ezdxf
import ifcopenshell
from bsa.bim import run as author
from bsa.concept_facade import run as facade
from bsa.concept_section import run,section,audit
from bsa.engine import ProjectError
ROOT=Path(__file__).resolve().parents[1]

class ConceptSectionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp=tempfile.TemporaryDirectory(dir=ROOT/'runs');cls.addClassCleanup(cls.temp.cleanup);cls.root=Path(cls.temp.name)
        stage=runpy.run_path(str(ROOT/'scripts/run_public_massing.py'))['stage'];d=json.loads((ROOT/'benchmarks/mit-4401-2018/massing-decisions.json').read_text(encoding='utf-8'))
        source=stage(d,d['variants'][0]);data=dict(project=source,layout=dict(source='Explicit concept comparison',window_wall_ratio=.4,layout='centered-equal-fraction'),basis=json.loads((ROOT/'benchmarks/mit-4401-2018/facade-decisions.json').read_text(encoding='utf-8')),drawing=dict(source='Synthetic cut/drawing QA, not architectural acceptance',cut_height_above_storey_m=1.2,annotation_height_m=.6,scale_denominator=250))
        for name,row in data.items():(cls.root/(name+'.json')).write_text(json.dumps(row),encoding='utf-8')
        author(cls.root/'project.json',cls.root/'model');facade(cls.root/'model/model.ifc',cls.root/'project.json',cls.root/'layout.json',cls.root/'basis.json',cls.root/'facade')
        cls.result=run(cls.root/'facade/facade.ifc',cls.root/'project.json',cls.root/'layout.json',cls.root/'basis.json',cls.root/'drawing.json',cls.root/'sheets')
        cls.source=source;cls.basis=data['drawing']

    def test_actual_sections_follow_window_cut_and_all_storeys_without_DWG_claim(self):
        self.assertEqual(set(self.result['storeys']),{'Level1','Level2'})
        for row in self.result['storeys'].values():
            self.assertAlmostEqual(sum(r['area_m2'] for r in row['sections'] if r['ifc_class']=='IfcWall'),2*(50+35)*.2*(1-math.sqrt(.4)),places=6)
            self.assertAlmostEqual(sum(r['area_m2'] for r in row['sections'] if r['ifc_class']=='IfcWindow'),2*(50+35)*math.sqrt(.4)*.04,places=6)
            self.assertTrue(row['dxf_audit']['saved_geometry_notes_identity_pass'])
        self.assertFalse(self.result['native_reopen_pass']);self.assertFalse(self.result['design_accepted'])
        model=ifcopenshell.open(str(self.root/'facade/facade.ifc'));below=section(model,.2,'Level1')
        self.assertAlmostEqual(sum(r['area_m2'] for r in below if r['ifc_class']=='IfcWall'),34.)
        self.assertEqual(sum(r['area_m2'] for r in below if r['ifc_class']=='IfcWindow'),0)

    def test_saved_line_identity_visibility_and_notes_mutation_reject(self):
        model=ifcopenshell.open(str(self.root/'facade/facade.ifc'));level=self.source['storeys'][0];space=dict(self.source['spaces'][0],guid=model.by_type('IfcSpace')[0].GlobalId);rows=self.result['storeys']['Level1']['sections']
        for mode in ('missing','guid','hidden','text','white','mirror'):
            doc=ezdxf.readfile(self.root/'sheets/Level1/section.dxf');entity=next(iter(doc.modelspace()))
            if mode=='missing':doc.modelspace().delete_entity(entity)
            if mode=='guid':entity.set_xdata('BSA_IFC',[(1000,'wrong')])
            if mode=='hidden':doc.layers.get(entity.dxf.layer).dxf.plot=0
            if mode=='text':next(iter(doc.modelspace().query('TEXT'))).dxf.text='false source width'
            if mode=='white':entity.dxf.true_color=0xFFFFFF
            if mode=='mirror':next(iter(doc.modelspace().query('TEXT'))).dxf.text_generation_flag=2
            path=self.root/(mode+'.dxf');doc.saveas(path)
            with self.subTest(mode=mode),self.assertRaises(ProjectError):audit(path,rows,space,level,self.basis)

    def test_cut_outside_storey_rejects_before_drawing(self):
        p=self.root/'bad-cut.json';row=dict(self.basis,cut_height_above_storey_m=4);p.write_text(json.dumps(row),encoding='utf-8')
        out=self.root/'bad-cut'
        with self.assertRaises(ProjectError):run(self.root/'facade/facade.ifc',self.root/'project.json',self.root/'layout.json',self.root/'basis.json',p,out)
        self.assertFalse(out.exists())

    def test_source_storey_name_cannot_escape_output_directory(self):
        row=json.loads((self.root/'project.json').read_text(encoding='utf-8'));row['storeys'][0]['id']='../outside'
        path=self.root/'unsafe-source.json';path.write_text(json.dumps(row),encoding='utf-8');out=self.root/'unsafe-output'
        with self.assertRaisesRegex(ProjectError,'path-safe ASCII'):run(self.root/'facade/facade.ifc',path,self.root/'layout.json',self.root/'basis.json',self.root/'drawing.json',out)
        self.assertFalse(out.exists())
