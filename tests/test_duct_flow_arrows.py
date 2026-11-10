import json
from pathlib import Path
import tempfile
import unittest
import ezdxf

from bsa.cli import digest
from bsa.duct_sheet import run
from bsa.duct_sheet_native import compare


class FlowArrowTests(unittest.TestCase):
    def fixture(self, root, units=6, reverse=False):
        factor=1000 if units==4 else 1
        doc=ezdxf.new();doc.units=units;space=doc.modelspace()
        a,b=(0,0,0),(3*factor,4*factor,0)
        if reverse:a,b=b,a
        line=space.add_line(a,b)
        cells=[space.add_text(t,dxfattribs={'insert':(i*factor,6*factor)}) for i,t in enumerate(['S','q','size','v','f'])]
        source=root/'source.dxf';doc.saveas(source)
        row=dict(id='S',inputs=dict(flow_m3_s=1,width_m=.8,height_m=.4),calculation=dict(actual_velocity_m_s=3.125,friction_Pa_m=.2),failures=[])
        data=dict(status='pass',sections=[row],flow_aggregation=dict(topology_pass=True,flow_conserved=True,
                  sections=[{'id':'S','from':'R','to':'L'}],section_flow_L_s={'S':1000}))
        schedule=root/'schedule.json';schedule.write_text(json.dumps(data))
        entry=dict(line_handle=line.dxf.handle,from_m=[v/factor for v in a],to_m=[v/factor for v in b],
                   from_node='L' if reverse else 'R',to_node='R' if reverse else 'L',
                   cells=[dict(handle=e.dxf.handle,expected_text=e.dxf.text) for e in cells])
        spec=dict(source_sha256=digest(source),schedule_sha256=digest(schedule),basis='Synthetic tree',sections={'S':entry},
                  flow_arrows=dict(layer='FLOW',length_m=.2,width_m=.1,fraction=.5))
        binding=root/'binding.json';binding.write_text(json.dumps(spec))
        return source,schedule,binding,spec,data

    def test_direction_units_and_preserved_source(self):
        for units,reverse in [(6,False),(4,True)]:
            with self.subTest(units=units),tempfile.TemporaryDirectory() as tmp:
                root=Path(tmp);source,schedule,binding,spec,data=self.fixture(root,units,reverse)
                before=digest(source);result=run(source,schedule,binding,root/'out')
                self.assertEqual(result['flow_arrow_count'],1)
                self.assertEqual(result['flow_arrows'][0]['from_node'],'R')
                self.assertEqual(result['flow_arrows'][0]['tip_m'],[1.5,2,0])
                for wing in result['flow_arrows'][0]['wings_m']:
                    self.assertAlmostEqual((1.5-wing[0])*.6+(2-wing[1])*.8,.2)
                self.assertEqual(digest(source),before)
                self.assertTrue(result['unchanged_unbound_modelspace'])
                saved=root/'out/Supply Air Distribution.dxf'
                self.assertEqual(len(ezdxf.readfile(saved).modelspace().query('LINE[layer=="FLOW"]')),2)
                self.assertTrue(compare(saved,saved,['0','FLOW'])['generated_native_correspondence'])
                doc=ezdxf.readfile(saved);doc.entitydb[result['flow_arrows'][0]['handles'][0]].dxf.end=(99,99,0)
                changed=root/'changed.dxf';doc.saveas(changed)
                with self.assertRaises(ValueError):compare(saved,changed,['0','FLOW'])

    def test_bad_size_unknown_tree_and_flow_do_not_generate_output(self):
        for case in ('size','topology','flow','layer'):
            with self.subTest(case=case),tempfile.TemporaryDirectory() as tmp:
                root=Path(tmp);source,schedule,binding,spec,data=self.fixture(root)
                if case=='size':spec['flow_arrows']['length_m']=3
                elif case=='topology':data['flow_aggregation']['topology_pass']=False
                elif case=='flow':data['flow_aggregation']['section_flow_L_s']['S']=500
                else:spec['flow_arrows']['layer']='0'
                schedule.write_text(json.dumps(data));spec['schedule_sha256']=digest(schedule)
                binding.write_text(json.dumps(spec))
                with self.assertRaises(ValueError):run(source,schedule,binding,root/'out')
                self.assertFalse((root/'out').exists())
