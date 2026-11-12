"""Compose existing recognition,HK LPD and independent electrical adapters.

All project facts here are explicit synthetic software controls. Official PDF
bytes may be copied from a host-selected cache;no missing source is fabricated.
"""
import argparse
import json
from pathlib import Path
import shutil
from bsa.cli import digest
from bsa.documents import extract

ROOT=Path(__file__).resolve().parents[2]


def build(out, sources=None):
    out=Path(out).resolve()
    if out.exists():raise ValueError('New workflow input directory required')
    out.mkdir(parents=True);(out/'sources').mkdir()
    for name in ('l-shaped-room.geo','l-shaped-room.expected.json','l-shaped-room.request.json'):
        shutil.copyfile(ROOT/'examples/moosas-transform'/name,out/name)
    pack=ROOT/'regulations/hk/lighting-2026.11.08/pack.json'
    shutil.copyfile(pack,out/'lighting-pack.json')
    definition=json.loads(pack.read_text())
    if sources is not None:
        source=Path(sources)/definition['sources']['emsd_bec_2024']['cache_filename']
        if digest(source)!=definition['sources']['emsd_bec_2024']['sha256']:raise ValueError('Exact existing pinned official BEC source required')
        shutil.copyfile(source,out/'sources'/source.name)
    basis=json.loads((ROOT/'examples/regulations-hk-lighting/project.json').read_text())
    basis['lighting_space'].pop('internal_floor_area')
    (out/'lighting-basis.json').write_text(json.dumps({'l-shaped-room':basis},indent=2))
    shutil.copyfile(ROOT/'examples/office-electrical/project.json',out/'electrical.json')
    brief=out/'brief.md'
    brief.write_text('# Synthetic source-recognition and lighting integration\n\n'
        'Recognize the declared concave room from its surface geometry and preserve its source identity and boundary.\n\n'
        'Inherit its recognized floor area into the existing selected Hong Kong office LPD check using the explicit synthetic luminaire inventory and applicability assertions.\n\n'
        'Review downstream engineering applicability only after geometry and selected rules pass; no physical or complete compliance claim follows from numerical checks.\n\n'
        'Execute the independent synthetic single-phase electrical calculation even when the recognition provider is unavailable.\n',encoding='utf-8')
    passages=extract(brief)['passages']
    ids=['recognition','lighting-rules','review','independent-electrical']
    plan=dict(version=1,brief=brief.name,brief_sha256=digest(brief),
        passage_dispositions={r['id']:'context' if i==0 else 'requirement' for i,r in enumerate(passages)},
        tasks=[dict(id='recognition',kind='module_exchange',provider='moosas.surface-room-recognition',request='l-shaped-room.request.json'),
            dict(id='lighting-rules',kind='spatial_lighting_rules',depends_on='recognition',basis='lighting-basis.json',pack='lighting-pack.json',sources='sources'),
            dict(id='review',kind='manual',requires_pass=['recognition','lighting-rules'],description='Actual source interpretation,installation,photometry and full acceptance remain pending'),
            dict(id='independent-electrical',kind='electrical',project='electrical.json')],
        requirements=[dict(id='R'+str(i),passage=row['id'],quote=row['text'],task=task,acceptance=row['text']) for i,(row,task) in enumerate(zip(passages[1:],ids),1)])
    if len(passages)!=5:raise ValueError('Exact public fixture passage coverage required')
    path=out/'plan.json';path.write_text(json.dumps(plan,indent=2));return path


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--out',required=True,type=Path);parser.add_argument('--sources',type=Path)
    args=parser.parse_args();print(build(args.out,args.sources))
