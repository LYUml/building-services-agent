import copy
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import zipfile

import ezdxf
from bsa.engine import ProjectError
from bsa.ifc_route_drawing import draw
from bsa.route_drawing_qa import audit_saved, distance, enters, run

ROOT=Path(__file__).resolve().parents[1]


class SavedRouteAuditTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        (ROOT/'runs').mkdir(exist_ok=True)
        cls.folder=tempfile.TemporaryDirectory(dir=ROOT/'runs');cls.root=Path(cls.folder.name)
        with zipfile.ZipFile(ROOT/'docs/evidence/elbow-riser/workflow.zip') as z:
            cls.data=json.loads(z.read('drawing/drawing.json'))
            cls.layout=json.loads(z.read('drawing/annotation-layout.json'))
            cls.ifc=cls.root/'model.ifc';cls.ifc.write_bytes(z.read('model/bim/model.ifc'))
            cls.dxf=cls.root/'native.dxf';cls.dxf.write_bytes(z.read('native/native-reopen/source-export.dxf'))
        cls.rows=cls.data['pieces']

    @classmethod
    def tearDownClass(cls):cls.folder.cleanup()

    def test_actual_native_saved_geometry_passes_without_planner_or_boolean_claims(self):
        report=copy.deepcopy(self.layout)
        report.update(leader_body_checks_pass=False,leader_pair_checks_pass=False,saved_leader_paths_match=False)
        with patch('bsa.route_annotations.layout',side_effect=AssertionError('audit must not invoke planner')):
            result=audit_saved(self.dxf,self.rows,[0,2],.06,report)
        self.assertTrue(result['calculated_checks_pass'])
        self.assertTrue(result['saved_labels_match'])
        self.assertGreaterEqual(result['minimum_leader_pair_gap_m'],.03)

    def test_faulty_planner_claims_cannot_authorize_intrusion_or_crossing(self):
        for fault in ('body','pair'):
            report=copy.deepcopy(self.layout)
            name='TURN' if fault=='body' else 'RISER'
            guid=next(r['guid'] for r in self.rows if r['name']==name)
            p=next(p for p in report['pieces'] if p['guid']==guid)
            target=[p['label_position_m'][0]-.06,p['label_position_m'][1]]
            tail=[[4.5,2.74],target] if fault=='body' else [[5.30,1.6],[5.30,3.2],[5.36,3.2],[5.36,1.6],target]
            p['leader_points_m']=[p['anchor_m'],p['escape_m']]+tail
            out=self.root/fault;out.mkdir()
            with patch('bsa.route_annotations.layout',return_value=report),self.assertRaisesRegex(ProjectError,'route obstacle|leader pair'):
                draw(self.rows,self.data['settings'],out)
            self.assertFalse((out/'annotation-layout.json').exists())

    def test_changed_actual_labels_or_leader_coverage_are_rejected(self):
        for fault in ('text','position','width','extra','missing'):
            doc=ezdxf.readfile(self.dxf)
            text=next(e for e in doc.modelspace().query('TEXT') if e.has_xdata('BSA_IFC'))
            leaders=doc.modelspace().query('LINE[layer=="BSA_LEADER"]')
            if fault=='text':text.dxf.text='Wrong bore and radius'
            elif fault=='position':text.dxf.insert=(0,0,0)
            elif fault=='width':text.dxf.width=.5
            elif fault=='extra':doc.modelspace().add_line((0,0),(1,1),dxfattribs={'layer':'BSA_LEADER'})
            else:doc.modelspace().delete_entity(leaders[0])
            target=self.root/(fault+'.dxf');doc.saveas(target)
            with self.subTest(fault=fault),self.assertRaises(ProjectError):audit_saved(target,self.rows,[0,2],.06,self.layout)

    def test_saved_line_endpoint_reversal_is_geometrically_equivalent(self):
        doc=ezdxf.readfile(self.dxf)
        for line in doc.modelspace().query('LINE[layer=="BSA_LEADER"]'):
            a,b=line.dxf.start,line.dxf.end;line.dxf.start=b;line.dxf.end=a
        target=self.root/'reversed.dxf';doc.saveas(target)
        self.assertTrue(audit_saved(target,self.rows,[0,2],.06,self.layout)['calculated_checks_pass'])

    def test_hidden_or_nonplotting_linked_annotations_are_rejected(self):
        for kind in ('label','leader'):
            for fault in ('invisible','paperspace','off','frozen','nonplot'):
                doc=ezdxf.readfile(self.dxf)
                entity=next(e for e in doc.modelspace() if e.dxf.layer==('BSA_LABEL' if kind=='label' else 'BSA_LEADER') and e.has_xdata('BSA_IFC'))
                layer=doc.layers.get(entity.dxf.layer)
                if fault=='invisible':entity.dxf.invisible=1
                elif fault=='paperspace':entity.dxf.paperspace=1
                elif fault=='off':layer.off()
                elif fault=='frozen':layer.freeze()
                else:layer.dxf.plot=0
                path=self.root/(kind+'-'+fault+'.dxf');doc.saveas(path)
                if fault=='paperspace':
                    # Both save and load repair this field. Inject into actual
                    # serialized tags, then prove the bad raw marker survives.
                    from ezdxf.lldxf.tagger import ascii_tags_loader
                    from ezdxf.lldxf.types import DXFTag
                    from bsa.route_drawing_qa import raw_space_markers
                    with path.open(encoding='utf-8') as stream:tags=list(ascii_tags_loader(stream))
                    start=next(i for i,t in enumerate(tags) if t.code==5 and t.value==entity.dxf.handle)
                    end=next(i for i in range(start+1,len(tags)) if tags[i].code==0)
                    index=next((i for i in range(start,end) if tags[i].code==67),None)
                    if index is None:tags.insert(start+1,DXFTag(67,'1'))
                    else:tags[index]=DXFTag(67,'1')
                    path.write_text(''.join(f'{t.code:3}\n{t.value}\n' for t in tags),encoding='utf-8')
                    self.assertEqual(raw_space_markers(path)[entity.dxf.handle],[['1']])
                with self.subTest(kind=kind,fault=fault),self.assertRaises(ProjectError):
                    audit_saved(path,self.rows,[0,2],.06,self.layout)

    def test_locked_visible_annotation_layers_are_accepted(self):
        doc=ezdxf.readfile(self.dxf)
        for name in ('BSA_LABEL','BSA_LEADER'):doc.layers.get(name).lock()
        path=self.root/'locked.dxf';doc.saveas(path)
        result=audit_saved(path,self.rows,[0,2],.06,self.layout)
        self.assertTrue(result['linked_annotation_visibility_flags_pass'])

    def test_unrelated_paper_space_and_binary_serialization_are_accepted(self):
        doc=ezdxf.readfile(self.dxf)
        doc.layout().add_text('Unlinked paper-space legend')
        for fmt in ('asc','bin'):
            path=self.root/('paper-'+fmt+'.dxf');doc.saveas(path,fmt=fmt)
            with self.subTest(fmt=fmt):
                self.assertTrue(audit_saved(path,self.rows,[0,2],.06,self.layout)['calculated_checks_pass'])

    def test_source_anchor_and_complete_layout_coverage_cannot_be_forged(self):
        for fault in ('anchor','coverage','nonfinite'):
            report=copy.deepcopy(self.layout)
            if fault=='anchor':report['pieces'][0]['leader_points_m'][0][0]+=.01
            elif fault=='coverage':report['pieces'].pop()
            else:report['pieces'][0]['label_position_m'][1]=float('nan')
            with self.subTest(fault=fault),self.assertRaises(ProjectError):audit_saved(self.dxf,self.rows,[0,2],.06,report)

    def test_segment_distance_detects_crossing_overlap_and_clear_gap(self):
        self.assertEqual(distance([0,0],[2,2],[0,2],[2,0]),0)
        self.assertEqual(distance([0,0],[2,0],[1,0],[3,0]),0)
        self.assertAlmostEqual(distance([0,0],[2,0],[0,.04],[2,.04]),.04)

    def test_small_physical_overlap_on_long_segment_is_not_lost_to_parameter_cutoff(self):
        self.assertTrue(enters([0,0],[20000000,0],[4,-.001,4.001,.001]))
        self.assertFalse(enters([0,.001],[20000000,.001],[4,-.001,4.001,.001]))
        with self.assertRaisesRegex(ProjectError,'precision'):
            enters([0,0],[1e12,0],[4,-.001,4.001,.001])

    def test_self_crossing_tail_is_rejected_before_saved_path_matching(self):
        report=copy.deepcopy(self.layout)
        guid=next(r['guid'] for r in self.rows if r['name']=='RISER')
        p=next(p for p in report['pieces'] if p['guid']==guid)
        target=[p['label_position_m'][0]-.06,p['label_position_m'][1]]
        p['leader_points_m']=[p['anchor_m'],p['escape_m'],[5.30,1.6],[5.30,3.2],[5.36,3.2],[5.36,1.8],[5.27,1.8],[5.27,3.1],[5.38,3.1],target]
        with self.assertRaisesRegex(ProjectError,'crosses itself'):
            audit_saved(self.dxf,self.rows,[0,2],.06,report)

    def test_adjacent_tail_overlap_is_rejected_without_nonadjacent_crossing(self):
        report=copy.deepcopy(self.layout)
        guid=next(r['guid'] for r in self.rows if r['name']=='RISER')
        p=next(p for p in report['pieces'] if p['guid']==guid)
        target=[p['label_position_m'][0]-.06,p['label_position_m'][1]]
        p['leader_points_m']=[p['anchor_m'],p['escape_m'],[target[0]+.1,target[1]],target]
        with self.assertRaisesRegex(ProjectError,'doubles back'):
            audit_saved(self.dxf,self.rows,[0,2],.06,report)

    @unittest.skipUnless(importlib.util.find_spec('ifcopenshell'),'requires native IFC reader')
    def test_standalone_audit_reopens_actual_ifc_and_native_export(self):
        layout=self.root/'layout.json';layout.write_text(json.dumps(self.layout))
        with patch('bsa.route_annotations.layout',side_effect=AssertionError('must not replan')):
            result=run(self.ifc,ROOT/'examples/elbow-riser/project.json',ROOT/'examples/elbow-riser/drawing-settings.json',self.dxf,layout,self.root/'audit')
        self.assertTrue(result['inputs_unchanged'])
        self.assertFalse(result['design_accepted'])


if __name__=='__main__':unittest.main()
