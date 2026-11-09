import copy
import json
import math
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import numpy as np
import ifcopenshell
from bsa.rectangular_binding import run
from bsa.network_binding import _prepare
from bsa.circular_elbow import AXES
from bsa.engine import ProjectError
from bsa.workflow import execute
from bsa.workflow_status import diagnose

ROOT=Path(__file__).resolve().parents[1];EX=ROOT/'examples/rectangular-air'


class RectangularElbowBindingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp=tempfile.TemporaryDirectory(dir=ROOT/'runs');cls.addClassCleanup(cls.temp.cleanup);cls.root=Path(cls.temp.name)
        cls.result=run(EX/'elbow-chain-project.json',EX/'elbow-chain-model.json',EX/'elbow-chain-binding.json',cls.root/'positive')

    def inputs(self):return [json.loads((EX/name).read_text()) for name in ('elbow-chain-project.json','elbow-chain-model.json','elbow-chain-binding.json')]

    def test_actual_arc_length_and_independent_pressure_components(self):
        r=json.loads((self.root/'positive/analysis/network.json').read_text());s=r['segments'][0];length=2+math.pi*.8/2
        self.assertAlmostEqual(s['friction_pa'],s['darcy_friction_factor']*length/.375*1.2*(.5/.15)**2/2,places=10)
        self.assertAlmostEqual(s['minor_pa'],.3*1.2*(.5/.15)**2/2,places=10)
        p=json.loads((self.root/'positive/network-input.json').read_text());self.assertAlmostEqual(p['segments'][0]['length_m'],length)
        self.assertGreater(length,2+math.sqrt(2)*.8);self.assertTrue(self.result['calculated_checks_pass'])

    def test_aggregate_duplicate_and_missing_piece_basis_rejected(self):
        p,m,b=self.inputs();p['segments'][0]['minor_k']=.3
        with self.assertRaisesRegex(ProjectError,'double counting'):_prepare(p,m,b,rectangular=True)
        p,m,b=self.inputs();m['devices'][0]['properties'].pop('LocalLossBasis')
        with self.assertRaisesRegex(ProjectError,'excess K'):_prepare(p,m,b,rectangular=True)

    def test_coincident_but_wrong_section_roll_rejected(self):
        p,m,b=self.inputs();d=m['devices'][1];d['bend_axes']=['+Z','+Y'];d['arc_center_m']=[2.8,2,1.2]
        u,v=[np.array(AXES[a],dtype=float) for a in d['bend_axes']];n=np.cross(u,v);c=np.array(d['arc_center_m'])
        lo=c+np.minimum(0,u*1.051)+np.minimum(0,v*1.051)-abs(n)*.151
        hi=c+np.maximum(0,u*1.051)+np.maximum(0,v*1.051)+abs(n)*.151
        d['origin_m']=lo.tolist();d['size_m']=(hi-lo).tolist()
        for port,point in zip(d['ports'],(c+.8*u,c+.8*v)):port['offset_m']=(point-lo).tolist()
        with self.assertRaisesRegex(ProjectError,'section roll'):_prepare(p,m,b,rectangular=True)

    def test_saved_k_tamper_rejected_before_pressure_engine(self):
        from bsa.bim import run as author
        import ifcopenshell.api as api
        import ifcopenshell.util.element as element
        def changed(*args):
            r=author(*args);path=Path(args[1])/'model.ifc';model=ifcopenshell.open(str(path));obj=model.by_type('IfcDuctFitting')[0]
            ps=model.by_id(element.get_psets(obj)['BSA_DesignInputs']['id']);api.run('pset.edit_pset',model,pset=ps,properties=dict(LocalLossCoefficient=.6));model.write(str(path));return r
        with patch('bsa.bim.run',side_effect=changed),patch('bsa.rectangular_network.run') as engine:
            with self.assertRaisesRegex(ProjectError,'K/basis differs'):run(EX/'elbow-chain-project.json',EX/'elbow-chain-model.json',EX/'elbow-chain-binding.json',self.root/'bad-k')
            engine.assert_not_called()

    def test_native_low_pressure_workflow_blocks_review(self):
        root=self.root/'low';root.mkdir()
        for name in ('brief.md','elbow-chain-plan.json','elbow-chain-model.json','elbow-chain-binding.json'):(root/name).write_bytes((EX/name).read_bytes())
        p=self.inputs()[0];p['supply']['total_pressure_pa']=1.;(root/'elbow-chain-project.json').write_text(json.dumps(p))
        execute(root/'elbow-chain-plan.json',root/'workflow');rows=diagnose(root/'elbow-chain-plan.json',root/'workflow')['tasks']
        self.assertEqual([r['status'] for r in rows],['fail','pending']);self.assertEqual(rows[-1]['blocked_by'],['air'])

    def test_saved_port_normal_tamper_stops_before_pressure(self):
        from bsa.bim import run as author
        from bsa.circular_geometry import frame
        import ifcopenshell.api as api
        import ifcopenshell.util.system as system
        import ifcopenshell.util.placement as placement
        def changed(*args):
            r=author(*args);path=Path(args[1])/'model.ifc';model=ifcopenshell.open(str(path))
            port=system.get_ports(model.by_type('IfcDuctFitting')[0])[0];old=placement.get_local_placement(port.ObjectPlacement)
            new=frame(-old[:3,2]);new[:3,3]=old[:3,3];api.run('geometry.edit_object_placement',model,product=port,matrix=new,is_si=True);model.write(str(path));return r
        with patch('bsa.bim.run',side_effect=changed),patch('bsa.rectangular_network.run') as engine:
            with self.assertRaisesRegex(ProjectError,'normal differs'):run(EX/'elbow-chain-project.json',EX/'elbow-chain-model.json',EX/'elbow-chain-binding.json',self.root/'bad-normal')
            engine.assert_not_called()
