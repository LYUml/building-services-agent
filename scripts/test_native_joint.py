"""Reproducible original CAD fixtures for native rigid placement and Boolean checks."""
import argparse
import itertools
import json
import math
from pathlib import Path
import ezdxf
import numpy as np
from bsa.cad_joint import native, run
from bsa.native_cad import DEFAULT_EXE, lisp_string as q
from bsa.cli import digest


def main(out, exe=DEFAULT_EXE):
    out=Path(out).resolve();exe=Path(exe).resolve()
    if out.exists() or not out.is_relative_to(Path(__file__).resolve().parents[1]):
        raise ValueError('new repository output required')
    out.mkdir(parents=True)
    for name,corner,height,base in [('fixed','4,6,0',8,[0,0,0]),('moving','2,3,0',4,[1,2,3])]:
        folder=out/name;folder.mkdir();seed=folder/'seed.dxf'
        doc=ezdxf.new('R2018');doc.units=4;doc.saveas(seed)
        target=folder/'source.dwg'
        body=f'(command "_.BOX" "0,0,0" {q(corner)} {q(height)}) '
        body+='(setvar "INSBASE" (list '+ ' '.join(str(v) for v in base)+')) '
        body+=f'(command "_.SAVEAS" "2018" {q(target)})'
        native(exe,seed,folder/'create.scr',body)
        if not target.is_file():raise AssertionError('native fixture missing')
    ax,az=np.radians([37,23])
    rx=np.array([[1,0,0],[0,np.cos(ax),-np.sin(ax)],[0,np.sin(ax),np.cos(ax)]])
    rz=np.array([[np.cos(az),-np.sin(az),0],[np.sin(az),np.cos(az),0],[0,0,1]])
    tilted=rx@rz
    corners=np.array(list(itertools.product([0,2],[0,3],[0,4])))@tilted.T+[2,3,1]
    # Independent containment oracle: every vertex lies inside the convex fixed box.
    assert np.all(corners>0) and np.all(corners<[4,6,8])
    permutation=np.array([[0.,0,1],[1,0,0],[0,1,0]])
    cases=[('separated',tilted,[20,30,40],0),
           ('contained',tilted,[2,3,1],24),
           ('partial',permutation,[1,1,1],18)]
    fixed=out/'fixed/source.dwg';moving=out/'moving/source.dwg';results=[]
    for name,rotation,translation,expected_mm3 in cases:
        basis={'source':'Original synthetic boxes: fixed 4x6x8 mm, moving 2x3x4 mm; software verification only',
               'fixed_sha256':digest(fixed),'moving_sha256':digest(moving),'insunits':4,
               'translation_drawing_units':translation,'rotation':rotation.tolist()}
        path=out/(name+'.json');path.write_text(json.dumps(basis,indent=2),encoding='utf-8')
        report=run(fixed,moving,path,out/name,exe)
        assert report['native_clear']==(expected_mm3==0)
        if expected_mm3:
            assert math.isclose(report['intersection_volume_m3'],expected_mm3*1e-9,rel_tol=1e-7,abs_tol=1e-16)
        else:assert report['intersection_volume_m3'] is None
        assert all(digest(out/name/p)==h for p,h in report['artifacts'].items())
        results.append({'case':name,'expected_intersection_mm3':expected_mm3,
                        'observed_intersection_m3':report['intersection_volume_m3'],
                        'native_clear':report['native_clear'],'oracle_match':True,
                        'report_sha256':digest(out/name/'joint.json')})
    result={'original_fixtures':True,'units':'mm','moving_INSBASE':[1,2,3],
            'cases':results,'design_accepted':False,'scope':'Executable native geometry controls; not a building-services design'}
    (out/'controls.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    print(json.dumps(result,indent=2))


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--out',required=True);p.add_argument('--autocad',default=str(DEFAULT_EXE))
    a=p.parse_args();main(a.out,a.autocad)
