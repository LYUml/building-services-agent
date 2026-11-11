"""Flexible-duct restrictions from individual sourced inventory assertions."""
import copy

from .engine import ProjectError

RESTRICTIONS={'main_distribution','fire_boundary','direct_damper'}


def findings(data,restriction):
    if restriction not in RESTRICTIONS:raise ProjectError('Supported flexible-duct restriction required')
    unknown=[];rows=[]
    if not isinstance(data,dict) or not isinstance(data.get('source'),str) or not data['source'].strip():
        return [],['sourced individual flexible-connection inventory missing']
    if data.get('complete') is not True:unknown.append('complete flexible-connection inventory not confirmed')
    connections=data.get('connections')
    if not isinstance(connections,list):return [],unknown+['explicit connection list missing']
    seen=set()
    for connection in connections:
        if not isinstance(connection,dict) or not isinstance(connection.get('id'),str) or not connection['id'].strip() or connection['id'] in seen:
            raise ProjectError('Unique nonempty flexible connection identities required')
        identity=connection['id'];seen.add(identity)
        if not isinstance(connection.get('source'),str) or not connection['source'].strip():
            unknown.append(identity+': sourced connection declaration missing');continue
        failures=[];missing=[]
        if restriction=='main_distribution':
            role=connection.get('role')
            if role not in (None,'main_distribution','connection','final_connection'):
                raise ProjectError('Explicit supported flexible-duct role or null required')
            if role is None:missing.append('connection role unknown')
            elif role=='main_distribution':failures.append('flexible duct declared as main distribution')
        elif restriction=='fire_boundary':
            if connection.get('penetrations_complete') is not True:missing.append('complete penetration inventory not confirmed')
            penetrations=connection.get('penetrations')
            if not isinstance(penetrations,list):missing.append('explicit penetration list missing')
            else:
                boundary_ids=set()
                for crossing in penetrations:
                    if not isinstance(crossing,dict) or not isinstance(crossing.get('id'),str) or not crossing['id'].strip() or crossing['id'] in boundary_ids:
                        raise ProjectError('Unique penetration identities required per connection')
                    boundary_ids.add(crossing['id'])
                    if crossing.get('kind') not in (None,'wall','floor','ceiling','partition') or type(crossing.get('fire_resisting')) not in (bool,type(None)):
                        raise ProjectError('Supported boundary kind and Boolean or null classification required')
                    if not isinstance(crossing.get('source'),str) or not crossing['source'].strip() or crossing.get('kind') is None or crossing.get('fire_resisting') is None:
                        missing.append(crossing['id']+': sourced boundary classification unknown')
                    elif crossing['fire_resisting']:
                        failures.append('fire-resisting '+crossing['kind']+' penetration: '+crossing['id'])
        else:
            ends=connection.get('ends')
            if not isinstance(ends,list) or len(ends)!=2:missing.append('exactly two sourced endpoint classifications required')
            else:
                for index,end in enumerate(ends):
                    if not isinstance(end,dict) or end.get('kind') not in (None,'fire_damper','fire_smoke_damper','other'):
                        raise ProjectError('Supported endpoint class or null required')
                    if not isinstance(end.get('source'),str) or not end['source'].strip() or end.get('kind') is None:
                        missing.append('endpoint '+str(index+1)+': sourced damper classification unknown')
                    elif end['kind']!='other':failures.append('direct '+end['kind']+' connection at endpoint '+str(index+1))
        unknown.extend(identity+': '+item for item in missing)
        rows.append(dict(connection_id=identity,source=connection['source'],forbidden_conditions=failures,
            unknown_conditions=missing,has_forbidden_condition=bool(failures)))
    return rows,unknown


def check(pack,rule,project,root):
    from .regulations import evaluate
    if rule.get('maximum')!=0 or rule.get('unit')!='connections':
        raise ProjectError('Zero forbidden-connection maximum in connections required')
    rows,unknown=findings(project.get('flexible_duct_inventory'),rule.get('restriction'))
    violations=sum(row['has_forbidden_condition'] for row in rows)
    derived=copy.deepcopy(project);derived['facts']=copy.deepcopy(project.get('facts',{}))
    # Caller-supplied aggregate counts cannot replace individual declarations.
    derived['facts'][rule['metric']]=dict(value=violations,unit='connections',
        source='Derived from individual sourced flexible-connection assertions;not native geometry or evidence authentication')
    simple=copy.deepcopy(rule);simple['method']='prescriptive_maximum'
    subpack=copy.deepcopy(pack);subpack['rules']=[simple]
    result=evaluate(subpack,derived,root)['checks'][0]
    if result['status'] not in ('pending','not_applicable'):
        if violations:result['status']='review_required'
        elif unknown:result.update(status='pending',reasons=unknown)
    result.update(connection_findings=rows,known_forbidden_connection_count=violations,
        unresolved_inventory_conditions=unknown,binding_status='sourced_inventory_assertions_only',
        pending_engineering_checks=['Source authenticity and complete inventory correspondence',
            'Native/installed fire-boundary and equipment identity',
            'Product testing,length requirements and remaining fire/HVAC obligations'])
    return result
