import json
import math
from pathlib import Path
import tempfile
import unittest
import numpy as np
import ifcopenshell
import ifcopenshell.util.placement as placement
from bsa.tee_assembly import run,verify
from bsa.tee_losses import run as losses
ROOT=Path(__file__).resolve().parents[1]

class TeePlacementTests(unittest.TestCase):
    def test_rotated_translated_geometry_and_diagnostic(self):
        with tempfile.TemporaryDirectory(dir=ROOT/'runs') as tmp:
            root=Path(tmp);spec=json.loads((ROOT/'examples/tee-trial/spec.json').read_text())
            # Independent composed 30-degree Z then 40-degree X rotations.
            a,b=math.radians(30),math.radians(40)
            rz=np.array([[math.cos(a),-math.sin(a),0],[math.sin(a),math.cos(a),0],[0,0,1]])
            rx=np.array([[1,0,0],[0,math.cos(b),-math.sin(b)],[0,math.sin(b),math.cos(b)]])
            r=rx@rz;origin=np.array([12.3,-4.5,2.7])
            spec['placement']={'source':'Explicit synthetic project-coordinate scenario','origin_m':origin.tolist(),'rotation':r.tolist()}
            sp=root/'spec.json';sp.write_text(json.dumps(spec));assembly=ROOT/'examples/tee-trial/assembly.json'
            report=run(sp,assembly,root/'placed');self.assertTrue(report['assembly_checks_pass'])
            model=root/'placed/assembly.ifc';f=ifcopenshell.open(str(model))
            tee=f.by_type('IfcPipeFitting')[0];mat=placement.get_local_placement(tee.ObjectPlacement)
            np.testing.assert_allclose(mat[:3,3],origin,atol=1e-9)
            for pipe in f.by_type('IfcPipeSegment'):
                solid=pipe.Representation.Representations[0].Items[0]
                native=placement.get_local_placement(pipe.ObjectPlacement)@placement.get_axis2placement(solid.Position)
                xyz={'main-a':[0,0,-.1],'main-b':[0,0,.1],'branch':[.1,0,0]}[pipe.Name]
                np.testing.assert_allclose(native[:3,3],origin+r@xyz,atol=1e-9)
            diagnostic=losses(model,sp,assembly,ROOT/'examples/tee-trial/loss-basis.json',root/'losses')
            self.assertAlmostEqual(diagnostic['paths']['branch']['k_combined_velocity'],1.0378515625)
            # Move the tee body placement only; source coordinate mismatch must fail.
            point=tee.ObjectPlacement.RelativePlacement.Location
            coords=list(point.Coordinates);coords[0]+=.01;point.Coordinates=coords
            changed=root/'changed.ifc';f.write(str(changed))
            result=verify(changed,spec,json.loads(assembly.read_text(encoding='utf-8-sig'))['pipe_lengths_m'])
            self.assertFalse(result['checks']['tee_geometry']);self.assertFalse(result['assembly_checks_pass'])
            for label,rotation in [('scale',[[2,0,0],[0,1,0],[0,0,1]]),('reflection',[[-1,0,0],[0,1,0],[0,0,1]])]:
                spec['placement']['rotation']=rotation;sp.write_text(json.dumps(spec))
                with self.assertRaisesRegex(ValueError,'orthonormal'):run(sp,assembly,root/label)
                self.assertFalse((root/label).exists())

if __name__=='__main__':unittest.main()
