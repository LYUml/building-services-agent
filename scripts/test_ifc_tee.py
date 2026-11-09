import json
from pathlib import Path
import tempfile
import unittest
import ifcopenshell
from probe_ifc_tee import run,verify_geometry

ROOT=Path(__file__).resolve().parents[1]


class TeeTrialTests(unittest.TestCase):
    def test_bore_obstruction_rejected(self):
        with tempfile.TemporaryDirectory(dir=ROOT/'runs') as tmp:
            root=Path(tmp);spec=ROOT/'examples/tee-trial/spec.json'
            result=run(spec,root/'positive');self.assertTrue(result['geometry_trial_pass'])
            f=ifcopenshell.open(str(root/'positive/tee.ifc'));tee=f.by_type('IfcPipeFitting')[0]
            data=result['parameters'];L=data['main_half_length_m'];B=data['branch_length_m']
            positions={'main-a':([0,0,-L],[0,0,-1]),'main-b':([0,0,L],[0,0,1]),'branch':([B,0,0],[1,0,0])}
            ports=[(p.GlobalId,*positions[p.Name]) for p in f.by_type('IfcDistributionPort')]
            wall=tee.Representation.Representations[0].Items[0]
            # Remove the branch bore subtraction but preserve the outer shape and all ports.
            wall.SecondOperand=wall.SecondOperand.FirstOperand
            changed=root/'blocked.ifc';f.write(str(changed))
            checks,*_=verify_geometry(changed,data,tee.GlobalId,ports)
            self.assertFalse(checks['main_and_branch_bores_clear'])
            self.assertFalse(checks['volume_matches_analytic'])
            self.assertTrue(checks['ports_match'])


if __name__=='__main__':unittest.main()
