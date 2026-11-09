import unittest
import numpy as np
import manifold3d as m
from bsa.cad_ifc import mesh_properties
from bsa.engine import ProjectError


class CADCavityTests(unittest.TestCase):
    contract={'source':'Independent synthetic nested cube controls','count':1,'containment_margin_m':.01,'volume_tolerance_m3':1e-9}

    def shells(self,inner,reverse=True):
        outer=m.Manifold.cube((3,3,3)).to_mesh64(); hole=inner.to_mesh64()
        v=np.concatenate([outer.vert_properties,hole.vert_properties])
        faces=np.array(hole.tri_verts)
        if reverse:faces=faces[:,::-1]
        f=np.concatenate([outer.tri_verts,faces+len(outer.vert_properties)])
        return v,f

    def test_known_cavity_volume_and_centroid(self):
        v,f=self.shells(m.Manifold.cube((1,1,1)).translate((1,1,1)))
        r=mesh_properties(v,f,self.contract)
        self.assertAlmostEqual(r['volume'],26)
        self.assertTrue(np.allclose(r['centroid'],[1.5]*3))
        self.assertEqual(len(r['nested_shells']['cavities']),1)

    def test_outside_crossing_touching_and_close_cavities_reject(self):
        for shift in ((4,1,1),(2.5,1,1),(0,1,1),(.005,1,1)):
            v,f=self.shells(m.Manifold.cube((1,1,1)).translate(shift))
            with self.assertRaises(ProjectError):mesh_properties(v,f,self.contract)

    def test_wrong_orientation_and_cavity_count_reject(self):
        cube=m.Manifold.cube((1,1,1)).translate((1,1,1))
        v,f=self.shells(cube,False)
        with self.assertRaises(ProjectError):mesh_properties(v,f,self.contract)
        v,f=self.shells(cube)
        with self.assertRaises(ProjectError):mesh_properties(v,f,{**self.contract,'count':2})

    def test_overlapping_cavity_shells_reject(self):
        v,f=self.shells(m.Manifold.cube((1,1,1)).translate((1,1,1)))
        other=m.Manifold.cube((1,1,1)).translate((1.5,1,1)).to_mesh64()
        faces=np.concatenate([f,np.array(other.tri_verts)[:,::-1]+len(v)])
        points=np.concatenate([v,other.vert_properties])
        with self.assertRaises(ProjectError):mesh_properties(points,faces,{**self.contract,'count':2})
