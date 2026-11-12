import tempfile
from pathlib import Path
import unittest
import numpy as np
import ifcopenshell
import ifcopenshell.api as api
from bsa.ifc_preview import extract, run
from bsa.engine import ProjectError

ROOT=Path(__file__).resolve().parents[1]


class IFCPreviewTests(unittest.TestCase):
    def test_millimetre_rotated_body_and_port_use_world_metres(self):
        with tempfile.TemporaryDirectory(dir=ROOT/'runs') as tmp:
            f=ifcopenshell.file(schema='IFC4')
            api.run('root.create_entity',f,ifc_class='IfcProject')
            length=api.run('unit.add_si_unit',f,unit_type='LENGTHUNIT',prefix='MILLI')
            api.run('unit.assign_unit',f,units=[length])
            context=api.run('context.add_context',f,context_type='Model')
            body=api.run('context.add_context',f,context_type='Model',context_identifier='Body',target_view='MODEL_VIEW',parent=context)
            obj=api.run('root.create_entity',f,ifc_class='IfcPipeFitting')
            rep=api.run('geometry.add_wall_representation',f,context=body,length=2,height=1,thickness=.3)
            api.run('geometry.assign_representation',f,product=obj,representation=rep)
            matrix=np.array([[0.,-1,0,10],[1,0,0,20],[0,0,1,30],[0,0,0,1]])
            api.run('geometry.edit_object_placement',f,product=obj,matrix=matrix,is_si=True)
            p=api.run('system.add_port',f,element=obj);p.Name='Independent fixture'
            pm=matrix.copy();pm[:3,3]=[10,22,30.5]
            api.run('geometry.edit_object_placement',f,product=p,matrix=pm,is_si=True)
            other=api.run('root.create_entity',f,ifc_class='IfcPump')
            path=Path(tmp)/'model.ifc';f.write(str(path))
            v,faces,ports,omitted=extract(path,obj.GlobalId)
            self.assertTrue(np.allclose(v.min(axis=0),[9.7,20,30]))
            self.assertTrue(np.allclose(v.max(axis=0),[10,22,31]))
            self.assertTrue(np.allclose(ports[0]['position_m'],[10,22,30.5]))
            self.assertEqual(ports[0]['axis'],[0,0,1])
            self.assertEqual(ports[0]['owner_guid'],obj.GlobalId)
            self.assertEqual(omitted,[other.GlobalId])
            self.assertGreater(len(faces),0)
            # Two independently placed bodies must both contribute to world bounds.
            other_rep=api.run('geometry.add_wall_representation',f,context=body,length=1,height=1,thickness=.2)
            api.run('geometry.assign_representation',f,product=other,representation=other_rep)
            other_matrix=np.eye(4);other_matrix[:3,3]=[40,50,60]
            api.run('geometry.edit_object_placement',f,product=other,matrix=other_matrix,is_si=True)
            f.write(str(path))
            combined=run(path,obj.GlobalId,Path(tmp)/'preview',[other.GlobalId])
            self.assertTrue(np.allclose(combined['world_bounds_m'],[[9.7,20,30],[41,50.2,61]]))
            self.assertEqual(combined['omitted_element_guids'],[])
            self.assertEqual(len(combined['ports']),1)
            with self.assertRaisesRegex(ProjectError,'unique'):
                run(path,obj.GlobalId,Path(tmp)/'duplicate',[obj.GlobalId])
            other.Representation=None
            p.ObjectPlacement=None;f.write(str(path))
            with self.assertRaisesRegex(ProjectError,'placement missing'):extract(path,obj.GlobalId)
            with self.assertRaisesRegex(ProjectError,'represented'):extract(path,other.GlobalId)
