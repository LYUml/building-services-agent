"""Source-bound property addition via official IfcMCP; writes only a new IFC."""
import argparse
import asyncio
import json
import importlib.metadata
from pathlib import Path
import sys
import ifcopenshell
import ifcopenshell.util.element
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from probe_ifcmcp import digest


async def run(model, patch, out):
    model,patch,out=[Path(p).resolve() for p in (model,patch,out)]
    root=Path(__file__).resolve().parents[1]
    if not out.is_relative_to(root) or out.exists() or any(out==p or out in p.parents for p in (model,patch)):
        raise ValueError('new repository output separate from inputs required')
    before={str(p):digest(p) for p in (model,patch)}
    spec=json.loads(patch.read_text(encoding='utf-8-sig'))
    if set(spec)!={'guid','pset','source','properties'} or any(not isinstance(spec[k],str) or not spec[k].strip() for k in ('guid','pset','source')):
        raise ValueError('explicit GUID, property-set name, source and properties required')
    props=spec['properties']
    if not isinstance(props,dict) or not props or any(not isinstance(k,str) or not k.strip() or not isinstance(v,str) or not v.strip() for k,v in props.items()) or 'Source' in props:
        raise ValueError('nonempty sourced text properties required; Source is reserved')
    native=ifcopenshell.open(str(model));target=native.by_guid(spec['guid'])
    if not target.is_a('IfcPump'):raise ValueError('this adapter requires an IfcPump target')
    if spec['pset'] in ifcopenshell.util.element.get_psets(target):raise ValueError('property set already exists; implicit overwrite forbidden')
    original={e.id():str(e) for e in native}
    props=dict(props,Source=spec['source'])
    out.mkdir(parents=True);saved=out/'model.ifc';records={}
    async def call(session,label,name,args):
        raw=(await session.call_tool(name,args)).model_dump(mode='json');records[label]=raw
        (out/'calls.json').write_text(json.dumps(records,indent=2),encoding='utf-8')
        data=raw.get('structuredContent')
        if data is None and len(raw.get('content',[]))==1 and raw['content'][0]['type']=='text':
            try:data=json.loads(raw['content'][0]['text'])
            except json.JSONDecodeError:pass
        if raw.get('isError') or isinstance(data,dict) and data.get('ok') is False:
            raise ValueError('upstream tool failed: '+label)
        return data
    params=StdioServerParameters(command=sys.executable,args=['-m','ifcmcp'])
    with (out/'server.log').open('w',encoding='utf-8') as errors:
        async with stdio_client(params,errlog=errors) as (read,write):
            async with ClientSession(read,write) as session:
                await session.initialize()
                await call(session,'load','ifc_load',{'path':str(model)})
                for function in ('pset.add_pset','pset.edit_pset'):
                    await call(session,'docs_'+function,'ifc_docs',{'function_path':function})
                added=await call(session,'add','ifc_edit',{'function_path':'pset.add_pset','params':json.dumps({'product':target.id(),'name':spec['pset']})})
                await call(session,'properties','ifc_edit',{'function_path':'pset.edit_pset','params':json.dumps({'pset':added['result']['id'],'properties':json.dumps(props)})})
                await call(session,'save','ifc_save',{'path':str(saved)})
                await call(session,'reset','ifc_reset',{})
                await call(session,'reload','ifc_load',{'path':str(saved)})
                await call(session,'inspect','ifc_info',{'element_id':target.id()})
    reopened=ifcopenshell.open(str(saved))
    actual=ifcopenshell.util.element.get_psets(reopened.by_guid(spec['guid']))[spec['pset']]
    actual.pop('id',None)
    current={e.id():str(e) for e in reopened}
    added_entities=[e for e in reopened if e.id() not in original]
    relations=[e for e in added_entities if e.is_a('IfcRelDefinesByProperties')]
    checks=dict(only_property_entities_added=all(e.is_a() in ('IfcPropertySet','IfcPropertySingleValue','IfcRelDefinesByProperties') for e in added_entities),
                only_target_assigned=len(relations)==1 and tuple(e.GlobalId for e in relations[0].RelatedObjects)==(spec['guid'],) and relations[0].RelatingPropertyDefinition.Name==spec['pset'],
                original_entities_unchanged=all(current.get(k)==v for k,v in original.items()),
                exact_properties=actual==props,inputs_unchanged=all(digest(Path(p))==h for p,h in before.items()),
                schema_unchanged=reopened.schema==native.schema)
    report=dict(runtime={n:importlib.metadata.version(n) for n in ('ifcopenshell-mcp','ifcopenshell','ifcquery','ifcedit','ifc5d','mcp')},inputs=before,checks=checks,property_edit_checks_pass=all(checks.values()),
                model_sha256=digest(saved),target_guid=spec['guid'],design_accepted=False,
                scope='New sourced text properties on one pump; original entity STEP records preserved. No new geometry or engineering approval.')
    (out/'edit-checks.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    return report


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('model','patch','out'):p.add_argument('--'+name,required=True)
    args=p.parse_args();r=asyncio.run(asyncio.wait_for(run(args.model,args.patch,args.out),60))
    print(json.dumps(r,indent=2));raise SystemExit(0 if r['property_edit_checks_pass'] else 2)
