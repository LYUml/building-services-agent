import copy
import json
from pathlib import Path
import tempfile
import unittest
import ifcopenshell
import ifcopenshell.geom
from bsa.bim import run,validate
from bsa.rectangular_geometry import specification,verify
from bsa.circular_geometry import configure
from bsa.engine import ProjectError

ROOT=Path(__file__).resolve().parents[1]
EX=ROOT/'examples/rectangular-air/straight-wall.json'


class RectangularGeometryTests(unittest.TestCase):
    def setUp(self):self.p=json.loads(EX.read_text())

    def test_invalid_envelope_wall_and_ports_rejected(self):
        changes=[lambda d:d['properties'].update(WallThickness_m=0),lambda d:d['size_m'].__setitem__(1,.6),
            lambda d:d['ports'][0]['offset_m'].__setitem__(1,0),lambda d:d.update(ifc_class='IfcPipeSegment')]
        for change in changes:
            p=copy.deepcopy(self.p);change(p['devices'][0])
            with self.assertRaises(ProjectError):validate(p)

    def test_all_three_axis_native_walls(self):
        with tempfile.TemporaryDirectory(dir=ROOT/'runs') as folder:
            root=Path(folder)
            for axis,size,offsets in [(0,[2,.502,.302],[[0,.251,.151],[2,.251,.151]]),
                (1,[.502,2,.302],[[.251,0,.151],[.251,2,.151]]),
                (2,[.502,.302,2],[[.251,.151,0],[.251,.151,2]])]:
                p=copy.deepcopy(self.p);d=p['devices'][0];d['size_m']=size
                for port,offset in zip(d['ports'],offsets):port['offset_m']=offset
                path=root/f'axis{axis}.json';path.write_text(json.dumps(p));result=run(path,root/f'axis{axis}')
                check=result['devices'][0]['rectangular_checks']
                self.assertTrue(result['model_checks_pass']);self.assertTrue(check['one_connected_wall'])
                self.assertAlmostEqual(check['mesh_wall_volume_m3'],.003208,places=10)
                self.assertEqual(check['euler_characteristic'],0);self.assertTrue(check['outward_port_axes_pass'])

    def test_saved_profile_and_metadata_mutations_rejected(self):
        with tempfile.TemporaryDirectory(dir=ROOT/'runs') as folder:
            root=Path(folder);run(EX,root/'model')
            for mutation in ('width','fillet','metadata','shift'):
                model=ifcopenshell.open(str(root/'model/model.ifc'));obj=model.by_type('IfcDuctSegment')[0]
                solid=obj.Representation.Representations[0].Items[0]
                if mutation=='width':solid.SweptArea.XDim+=.01
                elif mutation=='fillet':solid.SweptArea.InnerFilletRadius=.01
                elif mutation=='shift':solid.Position.Location.Coordinates=(.01,0.,0.)
                else:
                    import ifcopenshell.util.element as element
                    import ifcopenshell.api as api
                    ps=model.by_id(element.get_psets(obj)['BSA_DesignInputs']['id'])
                    api.run('pset.edit_pset',model,pset=ps,properties=dict(InternalWidth_m=.6))
                path=root/f'{mutation}.ifc';model.write(str(path));saved=ifcopenshell.open(str(path));obj=saved.by_type('IfcDuctSegment')[0]
                settings=ifcopenshell.geom.settings();settings.set(settings.USE_WORLD_COORDS,True);configure(settings)
                shape=ifcopenshell.geom.create_shape(settings,obj)
                with self.assertRaises(ProjectError):verify(obj,self.p['devices'][0],shape)

    def test_port_order_reversal_preserves_geometric_end_normals(self):
        d=self.p['devices'][0];d['ports'].reverse();s=specification(d)
        self.assertEqual(s['normals']['in'],[-1.,0.,0.]);self.assertEqual(s['normals']['out'],[1.,0.,0.])
