import copy
import json
import math
from pathlib import Path
import tempfile
import unittest
from bsa.bim import run as author
from bsa.water_binding import derive,run
from bsa.engine import ProjectError

ROOT=Path(__file__).resolve().parents[1]
EX=ROOT/'examples/epanet-elbow'


class FiniteElbowWaterTests(unittest.TestCase):
    def test_saved_finite_elbow_length_loss_and_rejections(self):
        with tempfile.TemporaryDirectory(dir=ROOT/'runs') as tmp:
            root=Path(tmp);author(EX/'model.json',root/'model');ifc=root/'model/model.ifc'
            result=run(EX/'project.json',ifc,EX/'binding.json',root/'bound')
            self.assertTrue(result['calculated_checks_pass'])
            network=json.loads((root/'bound/network-input.json').read_text())
            self.assertAlmostEqual(network['pipes'][0]['length_m'],3+math.pi*.3/2,places=9)
            self.assertAlmostEqual(network['pipes'][0]['diameter_m'],.08)
            self.assertEqual(network['pipes'][0]['minor_k'],.4)
            p=json.loads((EX/'project.json').read_text());b=json.loads((EX/'binding.json').read_text())
            for change in ('aggregate','missing','loss','radius'):
                project=copy.deepcopy(p);binding=copy.deepcopy(b)
                if change=='aggregate':project['pipes'][0]['minor_k']=.4
                elif change=='missing':binding['fitting_sources']={}
                elif change=='loss':next(iter(binding['piece_losses'].values()))['value']=1
                else:next(iter(binding['fitting_sources'].values()))['properties']['CenterlineRadius_m']=.4
                with self.subTest(change=change),self.assertRaises(ProjectError):derive(ifc,project,binding)
