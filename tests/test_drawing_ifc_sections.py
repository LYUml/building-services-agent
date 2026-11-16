import copy
import json
from pathlib import Path
import tempfile
import unittest

import ifcopenshell
from bsa import drawing_ifc_sections as sections
from bsa.cli import digest
from bsa.rectangular_transition import run as transition

ROOT=Path(__file__).resolve().parents[1]


class IFCSectionDrawingTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(dir=ROOT/'runs');self.addCleanup(self.temp.cleanup);self.root=Path(self.temp.name)
        p=self.root/'transition.json';p.write_bytes((ROOT/'examples/rectangular-transition/project.json').read_bytes());transition(p,self.root/'model')
        source=self.root/'model/transition.ifc';model=ifcopenshell.open(str(source));guid=model.by_type('IfcDuctFitting')[0].GlobalId
        ports={p.Name:p.GlobalId for p in model.by_type('IfcDistributionPort')}
        layout=json.loads((ROOT/'examples/drawing-layout.json').read_text())
        layout={k:v for k,v in layout.items() if k not in ('schema','views')};layout.update(units='m',sheet=dict(paper='A4',window=[0,0,2.9,2],scale=10,title='Synthetic section',number='TEST',reference_length=.5),content_window=[.1,.3,2.8,1.8])
        self.spec=dict(schema='bsa.drawing-ifc-sections/1',source='Synthetic transition fixture',ifc='model/transition.ifc',ifc_sha256=digest(source),layout=layout,views=[dict(id='side',guids=[guid],frame=[[0,0,-1,0],[0,1,0,0],[1,0,0,0],[0,0,0,1]],layer='GEOMETRY',annotations=[],port_dimensions=[dict(id='reach',ports=[ports['start'],ports['end']],layer='ANNOTATION',distance=-.3,text_height=.025)])])
        self.project=self.root/'sections.json'

    def save(self,spec=None):self.project.write_text(json.dumps(spec or self.spec))

    def test_native_sections_port_dimensions_and_tamper_rejection(self):
        self.save();layout,source=sections.compose(self.project)
        dim=next(e for e in layout['views'][0]['entities'] if e['kind']=='dimension')
        self.assertAlmostEqual(dim['p2'][0]-dim['p1'][0],.5732050807568877)
        self.assertGreater(sum(source['coverage']['side'].values()),0)
        result=sections.run(self.project,self.root/'drawing');self.assertFalse(result['native_reopen_pass'])
        self.assertTrue(sections.verify(self.project,self.root/'drawing')['integrity_pass'])
        p=self.root/'drawing/resolved-layout.json';data=json.loads(p.read_text());data['views'][0]['entities'][0]['start'][0]+=.01;p.write_text(json.dumps(data))
        with self.assertRaisesRegex(ValueError,'geometry changed'):sections.verify(self.project,self.root/'drawing')

    def test_changed_source_invalid_frames_and_nonintersecting_cut_rejected(self):
        for kind in ('hash','mirror','skew','no-cut','off-plane-ports'):
            s=copy.deepcopy(self.spec)
            if kind=='hash':s['ifc_sha256']='0'*64
            elif kind=='mirror':s['views'][0]['frame'][0][2]=1
            elif kind=='skew':s['views'][0]['frame'][0][0]=.5
            elif kind=='no-cut':s['views'][0]['frame'][0][3]=10
            else:s['views'][0]['frame'][0][3]=.01
            self.save(s)
            with self.subTest(kind=kind),self.assertRaises(ValueError):sections.compose(self.project)

    def test_projection_retains_closed_outlines_and_ignores_plane_elevation(self):
        s=copy.deepcopy(self.spec);view=s['views'][0];view['kind']='projection';view['port_dimensions']=[]
        self.save(s);layout,binding=sections.compose(self.project)
        self.assertEqual(binding['view_kinds'],{'side':'projection'})
        before=layout['views'][0]['entities'];self.assertTrue(before)
        self.assertTrue(all(e['kind']=='polyline' and e['closed'] for e in before))
        # Move only along the view normal: projected XY geometry stays identical.
        view['frame'][0][3]=10;self.save(s);after,_=sections.compose(self.project)
        self.assertEqual(before,after['views'][0]['entities'])
        view['kind']='unknown';self.save(s)
        with self.assertRaises(ValueError):sections.compose(self.project)


    def test_repeated_native_geometry_cache_preserves_rotated_world_projection(self):
        import numpy as np
        import ifcopenshell.api as api
        import ifcopenshell.geom as geom
        from ifcopenshell.util.element import copy_deep
        from unittest.mock import patch
        from shapely.geometry import Polygon
        from shapely import union_all
        from bsa.circular_geometry import configure
        from bsa.source_network_drawing import project
        path=self.root/'model/transition.ifc';model=ifcopenshell.open(str(path));original=model.by_type('IfcDuctFitting')[0]
        clone=api.run('root.create_entity',model,ifc_class='IfcDuctFitting',predefined_type='TRANSITION')
        clone.Representation=copy_deep(model,original.Representation)
        matrix=np.eye(4);matrix[:3,:3]=[[0,-1,0],[1,0,0],[0,0,1]];matrix[:3,3]=[0,.4,.8]
        api.run('geometry.edit_object_placement',model,product=clone,matrix=matrix,is_si=True);model.write(str(path))
        spec=copy.deepcopy(self.spec);spec['ifc_sha256']=digest(path);view=spec['views'][0];view.update(kind='projection',guids=[original.GlobalId,clone.GlobalId],port_dimensions=[],frame=np.eye(4).tolist());self.save(spec)
        native=geom.create_shape
        with patch.object(geom,'create_shape',wraps=native) as calls:
            layout,binding=sections.compose(self.project)
            self.assertEqual(calls.call_count,1);self.assertEqual(binding['native_mesh_builds'],1);self.assertEqual(binding['native_projection_builds'],1)
        frame=np.asarray(view['frame']);settings=geom.settings();settings.set(settings.USE_WORLD_COORDS,True);configure(settings)
        for obj in [original,clone]:
            shape=native(settings,obj);vertices=np.asarray(shape.geometry.verts).reshape(-1,3);faces=np.asarray(shape.geometry.faces).reshape(-1,3)
            reference=project((vertices-frame[:3,3])@frame[:3,:3],faces)
            actual=[Polygon(e['points']) for e in layout['views'][0]['entities'] if e['id'].startswith('side:'+obj.GlobalId+':')]
            expected=[Polygon(ring.coords) for poly in reference for ring in [poly.exterior,*poly.interiors]]
            a,b=union_all(actual),union_all(expected)
            self.assertTrue(a.buffer(2e-8).covers(b) and b.buffer(2e-8).covers(a))


    def test_failed_cleanup_keeps_raw_geometry_only_with_explicit_review(self):
        from unittest.mock import patch
        from shapely.geometry import Polygon
        from shapely.affinity import translate
        from bsa.source_network_drawing import project
        raw=Polygon([(0,0),(1,0),(0,1)]);bad=translate(raw,xoff=.1)
        args=([[0,0,0],[1,0,0],[0,1,0]],[[0,1,2]])
        with patch('bsa.source_network_drawing.union_all',side_effect=[raw,bad]):
            with self.assertRaisesRegex(ValueError,'cleanup exceeds'):project(*args)
        with patch('bsa.source_network_drawing.union_all',side_effect=[raw,bad]):
            with self.assertRaisesRegex(ValueError,'review record'):project(*args,retain_raw_on_cleanup_failure=True)
        review=[]
        with patch('bsa.source_network_drawing.union_all',side_effect=[raw,bad]):
            result=project(*args,retain_raw_on_cleanup_failure=True,review=review)
        self.assertTrue(result[0].equals(raw));self.assertTrue(review)


    def test_identical_representations_with_inverse_opening_do_not_share_mesh(self):
        import numpy as np
        import ifcopenshell.api as api
        import ifcopenshell.geom as geom
        from ifcopenshell.util.element import copy_deep
        from unittest.mock import patch
        path=self.root/'model/transition.ifc';model=ifcopenshell.open(str(path));original=model.by_type('IfcDuctFitting')[0]
        clone=api.run('root.create_entity',model,ifc_class='IfcDuctFitting',predefined_type='TRANSITION');clone.Representation=copy_deep(model,original.Representation)
        move=np.eye(4);move[0,3]=.8;api.run('geometry.edit_object_placement',model,product=clone,matrix=move,is_si=True)
        opening=api.run('root.create_entity',model,ifc_class='IfcOpeningElement',predefined_type='OPENING')
        context=original.Representation.Representations[0].ContextOfItems
        representation=api.run('geometry.add_wall_representation',model,context=context,length=.4,height=.1,thickness=.4)
        api.run('geometry.assign_representation',model,product=opening,representation=representation)
        position=np.eye(4);position[:3,3]=[.15,-.2,.15];api.run('geometry.edit_object_placement',model,product=opening,matrix=position,is_si=True)
        api.run('feature.add_feature',model,feature=opening,element=original);model.write(str(path))
        spec=copy.deepcopy(self.spec);spec['ifc_sha256']=digest(path);view=spec['views'][0];frame=np.eye(4);frame[2,3]=.2
        view.update(guids=[original.GlobalId,clone.GlobalId],frame=frame.tolist(),port_dimensions=[]);self.save(spec)
        with patch.object(geom,'create_shape',wraps=geom.create_shape) as calls:
            layout,binding=sections.compose(self.project)
        self.assertEqual(calls.call_count,2);self.assertEqual(binding['native_mesh_builds'],2)
        lengths={g:sum(np.linalg.norm(np.asarray(e['end'])-e['start']) for e in layout['views'][0]['entities'] if e['id'].startswith('side:'+g+':')) for g in view['guids']}
        self.assertGreater(abs(lengths[original.GlobalId]-lengths[clone.GlobalId]),.001)


    def test_explicit_drawing_mesh_quality_and_invalid_targets(self):
        quality=dict(source='Synthetic drawing target; no physical acceptance',classification='design_target',linear_deflection_m=.0001,angular_deflection_rad=.05)
        spec=copy.deepcopy(self.spec);spec['mesh_quality']=quality;self.save(spec)
        _,binding=sections.compose(self.project);self.assertEqual(binding['mesh_quality'],quality)
        for key in ('linear_deflection_m','angular_deflection_rad'):
            for bad in (0,-1,float('nan')):
                spec['mesh_quality']=dict(quality,**{key:bad});self.save(spec)
                with self.assertRaisesRegex(ValueError,'mesh targets'):sections.compose(self.project)


if __name__=='__main__':unittest.main()
