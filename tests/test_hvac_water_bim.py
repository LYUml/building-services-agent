import json
from pathlib import Path
import tempfile
import unittest
from bsa.bim import run,validate
from bsa.network_binding import prepare,reconcile

ROOT=Path(__file__).resolve().parents[1]


class HVACWaterBIMTests(unittest.TestCase):
    def test_native_branch_topology_and_hvac_system_types(self):
        import ifcopenshell
        example=ROOT/'examples/regulations-hk-water-branches'
        model=json.loads((example/'model.json').read_text())
        skeleton=json.loads((example/'skeleton.json').read_text())
        binding=json.loads((example/'binding.json').read_text())
        with tempfile.TemporaryDirectory(dir=ROOT/'runs') as folder:
            root=Path(folder)
            for system_type in ('CHILLEDWATER','CONDENSERWATER'):
                model['systems'][0]['predefined_type']=system_type;validate(model)
                derived,_=prepare(skeleton,model,binding)
                self.assertEqual({s['id']:s['length_m'] for s in derived['segments']},{'TRUNK':8,'BRANCH-A':6,'BRANCH-B':9})
                np=root/(system_type+'-network.json');np.write_text(json.dumps(derived))
                mp=root/(system_type+'.json');mp.write_text(json.dumps(model))
                out=root/system_type;run(mp,out)
                native=ifcopenshell.open(str(out/'model.ifc'))
                self.assertEqual(native.by_type('IfcDistributionSystem')[0].PredefinedType,system_type)
                self.assertEqual(len(native.by_type('IfcRelConnectsPorts')),6)
                self.assertTrue(reconcile(out/'model.ifc',np,binding,model))


if __name__=='__main__':unittest.main()
