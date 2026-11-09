"""Synthetic selected-curve/class association against a pinned real manufacturer speed table."""
import argparse
import json
from pathlib import Path
import shutil
from bsa.cli import digest
from bsa.workflow import execute
ROOT=Path(__file__).resolve().parents[1]


def run(out,pdf):
    out=Path(out).resolve()
    if out.exists() or not out.is_relative_to(ROOT):raise ValueError('new repository-local output required')
    ex=ROOT/'examples/rectangular-air';out.mkdir(parents=True);results={}
    for label,speed,construction in [('within',1450,'Class_I'),('exceeded',3500,'Class_I'),('unknown',1450,None)]:
        root=out/label;root.mkdir()
        for p in ex.glob('*.json'):shutil.copyfile(p,root/p.name)
        shutil.copyfile(ex/'brief.md',root/'brief.md')
        shutil.copyfile(ROOT/'sources/products/tcf-bc-sw-122.json',root/'product.json')
        shutil.copyfile(pdf,root/'manufacturer.pdf')
        c=json.loads((root/'fan-catalogue.json').read_text())
        for candidate in c['candidates']:candidate['curve']['speed_rpm']=speed
        (root/'fan-catalogue.json').write_text(json.dumps(c,indent=2))
        basis=dict(product_reference='BC-SW 122',construction_class=construction,source='Explicit synthetic curve/product-class association for speed-gate test only; not manufacturer performance data or installed product identity')
        (root/'mechanical-basis.json').write_text(json.dumps(basis,indent=2))
        p=json.loads((root/'fan-selection-plan.json').read_text())
        p['tasks'].insert(2,dict(id='mechanical',kind='fan_mechanical_limits',depends_on='fan',record='product.json',pdf='manufacturer.pdf',basis='mechanical-basis.json'))
        p['tasks'][-1]['requires_pass'].append('mechanical')
        r=dict(p['requirements'][-1]);r.update(id='R-mechanical',task='mechanical',acceptance='Selected curve speed versus independently extracted pinned class maximum; product identity, curve applicability and full acceptance separate');p['requirements'].append(r)
        path=root/'plan.json';path.write_text(json.dumps(p,indent=2));report=execute(path,root/'workflow')
        results[label]={k:v['status'] for k,v in report['tasks'].items()}
        expected={'within':'pass','exceeded':'fail','unknown':'pending'}[label]
        if results[label]['mechanical']!=expected or results[label]['fan']!='pass' or results[label]['review']!='pending':raise ValueError('unexpected speed gate behavior')
    result=dict(cases=results,design_accepted=False,scope='Real pinned speed table with synthetic curve/product association; not real vendor performance/installation selection')
    (out/'demonstration.json').write_text(json.dumps(result,indent=2));return result

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--out',type=Path,required=True);p.add_argument('--pdf',type=Path,required=True)
    print(json.dumps(run(**vars(p.parse_args()))))
