import copy
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from bsa.three_phase import prepare,build,audit,run
from bsa.cli import digest
from bsa.engine import ProjectError


@unittest.skipUnless(importlib.util.find_spec('pandapower'),'requires pinned isolated pandapower runtime')
class ThreePhaseTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(dir=ROOT/'runs');self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)
        self.p=json.loads((ROOT/'examples/three-phase-network/project.json').read_text(encoding='utf-8-sig'))
        self.project=self.root/'project.json';self.save()

    def save(self):
        basis=self.root/'basis.json'
        basis.write_text(json.dumps(dict(scope='Synthetic integration fixture',declared={k:v for k,v in self.p.items() if k!='sources'})),encoding='utf-8')
        for source in self.p['sources'].values():source.update(path=basis.name,sha256=digest(basis))
        self.project.write_text(json.dumps(self.p),encoding='utf-8')

    def test_branched_network_saved_roundtrip_and_nonzero_reactive_demands(self):
        result=run(self.project,self.root/'run')
        self.assertEqual(result['status'],'pass');self.assertFalse(result['design_accepted'])
        self.assertEqual(len(result['nodes']),3);self.assertEqual(len(result['lines']),2)
        self.assertLess(result['residuals']['total_power_balance_error_va'],1e-3)
        self.assertTrue((self.root/'run/network.json').is_file())
        self.assertEqual(result['network_sha256'],digest(self.root/'run/network.json'))

    def test_mesh_and_explicit_current_target_failure(self):
        extra=copy.deepcopy(self.p['lines'][0]);extra.update(id='parallel-route',to='load-B',length_m=60)
        self.p['lines'].append(extra);self.save()
        result=run(self.project,self.root/'mesh')
        self.assertEqual(result['status'],'pass')
        for line in self.p['lines']:line['max_current_a']=1
        self.save();result=run(self.project,self.root/'failed-target')
        self.assertTrue(result['verification_pass']);self.assertFalse(result['study_targets_pass'])
        self.assertEqual(result['status'],'fail')
        self.assertTrue(any(not l['current_target_pass'] for l in result['lines']))

    def test_corrupt_result_angles_power_and_currents_rejected(self):
        import pandapower as pp
        net=build(self.p);pp.runpp_3ph(net,numba=False,max_iteration=30,tolerance_mva=1e-10)
        for table,index,column in [('res_bus_3ph',1,'va_a_degree'),('res_line_3ph',0,'p_a_from_mw'),
            ('res_asymmetric_load_3ph',0,'q_a_mvar'),('res_line_3ph',1,'i_a_to_ka'),('res_ext_grid_3ph',0,'q_a_mvar')]:
            altered=copy.deepcopy(net);altered[table].loc[index,column]+=0.001
            with self.subTest(column=column):self.assertFalse(audit(self.p,altered)['verification_pass'])
        net.res_bus_3ph.loc[1,'vm_a_pu']=float('nan')
        with self.assertRaisesRegex(ProjectError,'nonfinite'):audit(self.p,net)

    def test_wrong_native_line_impedance_not_hidden_by_solver_convergence(self):
        import pandapower as pp
        net=build(self.p);net.line.loc[0,'r_ohm_per_km']*=2
        pp.runpp_3ph(net,numba=False,max_iteration=30,tolerance_mva=1e-10)
        result=audit(self.p,net)
        self.assertFalse(result['verification_checks']['max_line_voltage_error_v'])
        self.assertFalse(result['verification_checks']['native_input_correspondence'])

    def test_changed_source_sequence_parameters_and_load_type_are_detected(self):
        import pandapower as pp
        for change in ('sequence','type'):
            net=build(self.p)
            if change=='sequence':net.ext_grid.loc[0,'x0x_max']=1.2
            else:net.asymmetric_load.loc[0,'type']='delta'
            pp.runpp_3ph(net,numba=False,max_iteration=30,tolerance_mva=1e-10)
            result=audit(self.p,net)
            self.assertFalse(result['verification_checks']['native_input_correspondence'])
            self.assertFalse(result['verification_pass'])

    def test_source_invalid_inputs_and_unconnected_nodes_rejected(self):
        original=copy.deepcopy(self.p)
        mutations=[lambda: self.p['buses'].append(dict(id='isolated')),
            lambda: self.p['loads'][0].update(p_kw=[-1,2,3]),
            lambda: self.p['lines'][0].update(length_m=True),
            lambda: self.p['supply'].update(bus=[]),
            lambda: self.p['loads'][0].update(connection='delta')]
        for change in mutations:
            self.p=copy.deepcopy(original);change();self.save()
            with self.assertRaises(ProjectError):prepare(self.project)
        self.p=original;self.save();(self.root/'basis.json').write_text('changed',encoding='utf-8')
        with self.assertRaisesRegex(ProjectError,'hash mismatch'):prepare(self.project)

    def test_solver_failure_and_existing_directory_do_not_emit_success(self):
        import pandapower as pp
        with patch.object(pp,'runpp_3ph',side_effect=RuntimeError('controlled solver failure')):
            with self.assertRaisesRegex(RuntimeError,'controlled'):run(self.project,self.root/'run')
        self.assertTrue((self.root/'run/failure.json').is_file())
        self.assertFalse((self.root/'run/study.json').exists())
        with self.assertRaisesRegex(ProjectError,'overwrite'):run(self.project,self.root/'run')

    def test_source_change_during_solver_prevents_success_report(self):
        import pandapower as pp
        original=pp.runpp_3ph
        def changed(net,**kwargs):
            original(net,**kwargs)
            (self.root/'basis.json').write_text('changed during solve',encoding='utf-8')
        with patch.object(pp,'runpp_3ph',side_effect=changed):
            with self.assertRaisesRegex(ProjectError,'source changed'):run(self.project,self.root/'run')
        self.assertFalse((self.root/'run/study.json').exists())
        self.assertTrue((self.root/'run/failure.json').exists())


if __name__=='__main__':unittest.main()
