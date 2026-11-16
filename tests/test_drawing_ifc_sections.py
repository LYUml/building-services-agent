import copy
import json
from pathlib import Path
import tempfile
import unittest

import ifcopenshell
from bsa import drawing_ifc_sections as sections
from bsa.cli import digest
from bsa.rectangular_transition import run as transition

ROOT=Path(__file__).resolve().parents[1]


class IFCSectionDrawingTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(dir=ROOT/'runs');self.addCleanup(self.temp.cleanup);self.root=Path(self.temp.name)
        p=self.root/'transition.json';p.write_bytes((ROOT/'examples/rectangular-transition/project.json').read_bytes());transition(p,self.root/'model')
        source=self.root/'model/transition.ifc';model=ifcopenshell.open(str(source));guid=model.by_type('IfcDuctFitting')[0].GlobalId
        ports={p.Name:p.GlobalId for p in model.by_type('IfcDistributionPort')}
        layout=json.loads((ROOT/'examples/drawing-layout.json').read_text())
        layout={k:v for k,v in layout.items() if k not in ('schema','views')};layout.update(units='m',sheet=dict(paper='A4',window=[0,0,2.9,2],scale=10,title='Synthetic section',number='TEST',reference_length=.5),content_window=[.1,.3,2.8,1.8])
        self.spec=dict(schema='bsa.drawing-ifc-sections/1',source='Synthetic transition fixture',ifc='model/transition.ifc',ifc_sha256=digest(source),layout=layout,views=[dict(id='side',guids=[guid],frame=[[0,0,-1,0],[0,1,0,0],[1,0,0,0],[0,0,0,1]],layer='GEOMETRY',annotations=[],port_dimensions=[dict(id='reach',ports=[ports['start'],ports['end']],layer='ANNOTATION',distance=-.3,text_height=.025)])])
        self.project=self.root/'sections.json'

    def save(self,spec=None):self.project.write_text(json.dumps(spec or self.spec))

    def test_native_sections_port_dimensions_and_tamper_rejection(self):
        self.save();layout,source=sections.compose(self.project)
        dim=next(e for e in layout['views'][0]['entities'] if e['kind']=='dimension')
        self.assertAlmostEqual(dim['p2'][0]-dim['p1'][0],.5732050807568877)
        self.assertGreater(sum(source['coverage']['side'].values()),0)
        result=sections.run(self.project,self.root/'drawing');self.assertFalse(result['native_reopen_pass'])
        self.assertTrue(sections.verify(self.project,self.root/'drawing')['integrity_pass'])
        p=self.root/'drawing/resolved-layout.json';data=json.loads(p.read_text());data['views'][0]['entities'][0]['start'][0]+=.01;p.write_text(json.dumps(data))
        with self.assertRaisesRegex(ValueError,'geometry changed'):sections.verify(self.project,self.root/'drawing')

    def test_changed_source_invalid_frames_and_nonintersecting_cut_rejected(self):
        for kind in ('hash','mirror','skew','no-cut','off-plane-ports'):
            s=copy.deepcopy(self.spec)
            if kind=='hash':s['ifc_sha256']='0'*64
            elif kind=='mirror':s['views'][0]['frame'][0][2]=1
            elif kind=='skew':s['views'][0]['frame'][0][0]=.5
            elif kind=='no-cut':s['views'][0]['frame'][0][3]=10
            else:s['views'][0]['frame'][0][3]=.01
            self.save(s)
            with self.subTest(kind=kind),self.assertRaises(ValueError):sections.compose(self.project)


if __name__=='__main__':unittest.main()
