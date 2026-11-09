import json
import math
from pathlib import Path
import tempfile
import unittest
import numpy as np
import ifcopenshell
import ifcopenshell.geom
from bsa.bim import validate,run
from bsa.rectangular_elbow import specification,verify
from bsa.circular_geometry import configure
from bsa.circular_elbow import AXES
from bsa.engine import ProjectError

ROOT=Path(__file__).resolve().parents[1];EX=ROOT/'examples/rectangular-air/elbow-wall.json'


class RectangularElbowTests(unittest.TestCase):
    def test_invalid_radius_or_offset_ports_rejected(self):
        p=json.loads(EX.read_text());p['devices'][0]['properties']['CenterlineRadius_m']=.2
        with self.assertRaises(ProjectError):validate(p)
        p=json.loads(EX.read_text());p['devices'][0]['ports'][0]['offset_m'][0]+=.01
        with self.assertRaises(ProjectError):validate(p)

    def test_native_signed_axis_planes_and_analytic_wall_volume(self):
        with tempfile.TemporaryDirectory(dir=ROOT/'runs') as folder:
            root=Path(folder)
            for i,axes in enumerate((['+X','+Y'],['-Y','+X'],['+X','+Z'],['-Z','-Y'])):
                p=json.loads(EX.read_text());d=p['devices'][0];d['bend_axes']=axes
                u,v=[np.array(AXES[a],dtype=float) for a in axes];n=np.cross(u,v);c=np.array([2.,2.,2.]);r=.8;extent=1.051
                lo=c+np.minimum(0,u*extent)+np.minimum(0,v*extent)-abs(n)*.151
                hi=c+np.maximum(0,u*extent)+np.maximum(0,v*extent)+abs(n)*.151
                d['origin_m']=lo.tolist();d['size_m']=(hi-lo).tolist()
                for port,point in zip(d['ports'],(c+r*u,c+r*v)):port['offset_m']=(point-lo).tolist()
                path=root/f'case{i}.json';path.write_text(json.dumps(p));report=run(path,root/f'case{i}')
                check=report['devices'][0]['rectangular_checks'];expected=(.502*.302-.5*.3)*math.pi*.8/2
                self.assertTrue(report['model_checks_pass']);self.assertTrue(check['one_connected_wall'])
                self.assertAlmostEqual(check['centreline_arc_length_m'],math.pi*.8/2)
                self.assertAlmostEqual(check['mesh_wall_volume_m3'],expected,delta=expected*.001)
                self.assertEqual(check['euler_characteristic'],0);self.assertTrue(check['outward_port_axes_pass'])

    def test_saved_profile_angle_axis_and_metadata_mutations_rejected(self):
        with tempfile.TemporaryDirectory(dir=ROOT/'runs') as folder:
            root=Path(folder);run(EX,root/'base');source=json.loads(EX.read_text())['devices'][0]
            for label in ('width','angle','axis-chord','metadata'):
                model=ifcopenshell.open(str(root/'base/model.ifc'));obj=model.by_type('IfcDuctFitting')[0]
                body=next(r for r in obj.Representation.Representations if r.RepresentationIdentifier=='Body').Items[0]
                if label=='width':body.SweptArea.XDim+=.01
                elif label=='angle':body.Angle=math.pi/3
                elif label=='axis-chord':
                    axis=next(r for r in obj.Representation.Representations if r.RepresentationIdentifier=='Axis').Items[0]
                    axis.Segments=[model.create_entity('IfcLineIndex',(1,3))]
                else:
                    import ifcopenshell.api as api
                    import ifcopenshell.util.element as element
                    ps=model.by_id(element.get_psets(obj)['BSA_DesignInputs']['id']);api.run('pset.edit_pset',model,pset=ps,properties=dict(CenterlineRadius_m=.9))
                path=root/(label+'.ifc');model.write(str(path));saved=ifcopenshell.open(str(path));obj=saved.by_type('IfcDuctFitting')[0]
                settings=ifcopenshell.geom.settings();settings.set(settings.USE_WORLD_COORDS,True);configure(settings)
                with self.assertRaises(ProjectError):verify(obj,source,ifcopenshell.geom.create_shape(settings,obj))
