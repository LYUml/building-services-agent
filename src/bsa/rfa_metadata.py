"""Read saved RFA PartAtom text with olefile; never invokes Revit or verifies geometry."""
import argparse
import importlib.metadata
import json
from pathlib import Path
import xml.etree.ElementTree as ET
from .cli import digest
from .workspace import allowed

ATOM='http://www.w3.org/2005/Atom'
PART='urn:schemas-autodesk-com:partatom'
LIMIT=2*1024*1024


def partatom(data):
    if len(data)>LIMIT or b'<!DOCTYPE' in data.upper() or b'<!ENTITY' in data.upper():
        raise ValueError('Bounded PartAtom without DTD/entities required')
    try:root=ET.fromstring(data)
    except ET.ParseError as exc:raise ValueError('Malformed PartAtom XML') from exc
    if root.tag!='{'+ATOM+'}entry' or len(list(root.iter()))>10000:
        raise ValueError('Supported bounded PartAtom entry required')
    title=root.findtext('{'+ATOM+'}title')
    family=root.find('{'+PART+'}family')
    if not title or family is None or len(root.findall('{'+PART+'}family'))!=1 or len(root.findall('{'+ATOM+'}title'))!=1:raise ValueError('Unique PartAtom title and family required')
    types=[];seen=set()
    for part in family.findall('{'+PART+'}part'):
        name=part.findtext('{'+ATOM+'}title')
        if not name or name in seen:raise ValueError('Unique nonempty PartAtom type titles required')
        seen.add(name);parameters=[];names=set()
        for child in part:
            if child.tag=='{'+ATOM+'}title':continue
            if child.tag in names or len(child):raise ValueError('Unique scalar PartAtom parameters required')
            names.add(child.tag)
            parameters.append(dict(name=child.tag.split('}',1)[-1],qualified_name=child.tag,attributes=dict(child.attrib),raw_value=child.text or ''))
        types.append(dict(name=name,parameters=parameters))
    if not types:raise ValueError('At least one retained family type required')
    declared=family.findtext('{'+PART+'}variationCount')
    if declared is not None and (not declared.isdigit() or int(declared)!=len(types)):
        raise ValueError('PartAtom declared type count differs')
    return dict(family_title=title,types=types)


def inspect(source):
    import olefile
    source=Path(source).resolve()
    if not allowed(source) or source.suffix.lower()!='.rfa':raise ValueError('Selected RFA source required')
    if importlib.metadata.version('olefile')!='0.47':raise ValueError('Pinned olefile0.47 required')
    before=digest(source)
    with olefile.OleFileIO(source,write_mode=False,raise_defects=olefile.DEFECT_INCORRECT) as compound:
        if not compound.exists('PartAtom') or compound.get_size('PartAtom')>LIMIT:raise ValueError('Bounded saved PartAtom stream required')
        with compound.openstream('PartAtom') as stream:data=stream.read()
        inventory=[dict(path='/'.join(p),size=compound.get_size(p)) for p in compound.listdir()]
        issues=[dict(kind=kind.__name__,message=str(message)) for kind,message in compound.parsing_issues]
    metadata=partatom(data)
    paths=[source,Path(__file__).resolve(),Path(olefile.olefile.__file__).resolve()]
    pins={str(p):digest(p) for p in paths}
    if digest(source)!=before:raise ValueError('RFA changed during metadata read')
    result=dict(schema='bsa.rfa-metadata/1',source=str(source),inputs=pins,olefile_version='0.47',
        streams=inventory,parsing_issues=issues,metadata=metadata,
        parameter_semantics_verified=False,native_revit_executed=False,geometry_verified=False,
        connectors_verified=False,design_accepted=False,
        scope='Saved PartAtom scalar text only; no formula evaluation, type selection, unit conversion, native geometry or connector verification. Stored defaults are not project design inputs.')
    return result,data


def run(source,out):
    source,out=Path(source).resolve(),Path(out).resolve()
    if not allowed(out) or out.exists() or out==source or out in source.parents:raise ValueError('Fresh separate selected output required')
    result,data=inspect(source)
    out.mkdir(parents=True);(out/'PartAtom.xml').write_bytes(data)
    result['artifacts']={'PartAtom.xml':digest(out/'PartAtom.xml')}
    (out/'metadata.json').write_text(json.dumps(result,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
    return result


def verify(folder):
    folder=Path(folder).resolve()
    if not allowed(folder):raise ValueError('Selected metadata workspace required')
    def pairs(items):
        result={}
        for key,value in items:
            if key in result:raise ValueError('Duplicate metadata key')
            result[key]=value
        return result
    def invalid(value):raise ValueError('Nonfinite metadata number')
    result=json.loads((folder/'metadata.json').read_text(encoding='utf-8'),object_pairs_hook=pairs,parse_constant=invalid)
    replay,data=inspect(result['source'])
    replay['artifacts']={'PartAtom.xml':digest(folder/'PartAtom.xml')}
    if (folder/'PartAtom.xml').read_bytes()!=data or result!=replay:raise ValueError('Saved RFA metadata differs from source replay')
    return result


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('source',type=Path);parser.add_argument('--out',type=Path,required=True);args=parser.parse_args()
    result=run(args.source,args.out);print('Saved metadata types:',len(result['metadata']['types']),'native geometry unverified')

if __name__=='__main__':main()
