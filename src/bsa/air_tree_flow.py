"""Conservative terminal-to-leaf mapping for a prescribed-flow directed tree.

Identity/topology glue only; no pressure, geometry or equipment solver.
"""
import math


def aggregate(tree, terminals):
    if set(tree) != {'root', 'sections', 'leaf_terminals', 'basis'}:
        raise ValueError('Exact tree root, sections, leaf_terminals and basis required')
    if not isinstance(tree['basis'], str) or not tree['basis'].strip():
        raise ValueError('Explicit topology and grouping basis required')
    def name(value):
        if not isinstance(value, str) or not value.strip():
            raise ValueError('Nonempty string identities required')
        return value
    root=name(tree['root']);incoming={};outgoing={};sections={};nodes={root}
    for section in tree['sections']:
        if set(section)!={'id','from','to'}:raise ValueError('Tree section requires only id/from/to')
        sid,a,b=(name(section[k]) for k in ('id','from','to'))
        if sid in sections or a==b or b==root or b in incoming:
            raise ValueError('Unique sections and one parent per non-root node required')
        sections[sid]=section;incoming[b]=section;outgoing.setdefault(a,[]).append(b);nodes.update((a,b))
    if not sections or set(incoming)!=nodes-{root}:raise ValueError('Connected rooted tree required')
    order=[];stack=[root];seen=set()
    while stack:
        node=stack.pop()
        if node in seen:raise ValueError('Cycle in tree')
        seen.add(node);order.append(node);stack.extend(outgoing.get(node,[]))
    if seen!=nodes:raise ValueError('Disconnected tree or cycle')
    leaves=nodes-set(outgoing);groups=tree['leaf_terminals']
    if not isinstance(groups,dict) or set(groups)!=leaves:raise ValueError('Every leaf must have terminal membership')
    demands={}
    for terminal in terminals:
        tid=name(terminal['id']);flow=terminal['maximum_flow_L_s']
        if tid in demands or type(flow) not in (int,float) or not math.isfinite(flow) or flow<=0:
            raise ValueError('Unique terminals with positive finite flow required')
        demands[tid]=flow
    assigned=[];flow={n:0. for n in nodes}
    for leaf,members in groups.items():
        if not isinstance(members,list) or not members:raise ValueError('Nonempty terminal group required')
        for tid in members:
            if name(tid) not in demands:raise ValueError('Unknown terminal membership')
        assigned.extend(members);flow[leaf]=math.fsum(demands[t] for t in members)
    if len(set(assigned))!=len(assigned) or set(assigned)!=set(demands):
        raise ValueError('Every terminal must occur exactly once')
    for node in reversed(order):
        if node in outgoing:flow[node]=math.fsum(flow[child] for child in outgoing[node])
    total=math.fsum(demands.values())
    if not math.isfinite(total) or not math.isclose(flow[root],total,rel_tol=1e-12):
        raise ValueError('Tree flow not conserved')
    return dict(section_flow_L_s={sid:flow[s['to']] for sid,s in sections.items()},
                leaf_flow_L_s={n:flow[n] for n in sorted(leaves)},total_flow_L_s=total,
                topology_pass=True,flow_conserved=True,basis=tree['basis'],
                design_accepted=False)
