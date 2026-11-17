"""Source-linked connected-input and area-basis reconciliation."""
import math
from collections import Counter
from decimal import Decimal,ROUND_HALF_UP
from pathlib import Path

from ..engineering_data.model import validate_schema
from ..workspace import ROOT

PROJECT_SCHEMA=ROOT/'contracts/lighting-source-project-v1.json'


def number(value,*,zero=False):
    if type(value) not in (int,float) or not math.isfinite(value) or (value<0 if zero else value<=0):
        raise ValueError('Explicit finite positive source value required')
    return value


def pointer(data,path):
    if not isinstance(path,str) or not path.startswith('/'):
        raise ValueError('Exact JSON source pointer required')
    for part in path[1:].split('/'):
        part=part.replace('~1','/').replace('~0','~')
        data=data[int(part)] if isinstance(data,list) else data[part]
    return data


def validate_project(project):
    validate_schema(project,PROJECT_SCHEMA,'Lighting source-audit project')
    ids=[r['id'] for r in project['fixtures']]
    products=[r['id'] for r in project['products']]
    if len(ids)!=len(set(ids)) or len(products)!=len(set(products)) or set(products)!={r['product_id'] for r in project['fixtures']}:
        raise ValueError('Unique complete fixture/product source identities required')
    if project['fixture_count']['value']!=len(ids):raise ValueError('Declared fixture count differs from inventory')
    return project


def verify_sources(project,sources,hashes):
    """Bind normalized input facts to explicitly pinned original JSON roles."""
    validate_project(project)
    layout=sources['layout'];design=sources['design'];metrics=sources['native_metrics']
    if hashes['layout']!=design['bindings']['fixtures']['sha256'] or hashes['native_metrics']!=design['bindings']['core_results']['sha256'] or hashes['native_report']!=metrics['pdf_sha256']:
        raise ValueError('Lighting design/layout/native-report source bindings differ')
    expected=sorted((r['id'],r['product_order_code']) for r in layout['fixtures'])
    actual=sorted((r['id'],r['product_id']) for r in project['fixtures'])
    if expected!=actual or layout['fixture_count']!=len(actual) or project['fixture_count']['value']!=len(actual):
        raise ValueError('Lighting source inventory is missing, duplicated or changed')
    for fact in [project['fixture_count'],project['auxiliary_allowance'],project['annotation_area'],*[p['input_power'] for p in project['products']]]:
        origin=fact['source']
        if pointer(sources[origin['role']],origin['pointer'])!=fact['value']:
            raise ValueError('Normalized lighting value differs from its original source pointer')
    for product in project['products']:
        origin=product['source_product']
        if pointer(sources[origin['role']],origin['pointer'])!=product['id']:
            raise ValueError('Luminaire source product identity differs')


def calculate(project,summary):
    validate_project(project)
    if summary['room_scene_header']!=project['expected_header']:
        raise ValueError('Native lighting room/scene differs from explicit source selection')
    area=number(summary['area_m2'])
    metrics={}
    for row in summary['measurements']:
        if row['metric'] in metrics:raise ValueError('Ambiguous native lighting metric')
        metrics[row['metric']]=row
    native=metrics['lighting_power_density']
    if native['unit']!='W/m2' or native['calculation_surface']!='space':raise ValueError('Reported lighting density must be a space electrical input metric')
    reported=number(native['value'])
    counts=Counter(r['product_id'] for r in project['fixtures'])
    products=[]
    for p in project['products']:
        power=number(p['input_power']['value'])
        products.append(dict(id=p['id'],quantity=counts[p['id']],input_power_W=power,
            classification=p['input_power']['classification'],source=p['input_power']['source'],basis=p['input_power']['basis']))
    rates={p['id']:p['input_power_W'] for p in products}
    fixtures=[dict(id=r['id'],product_id=r['product_id'],input_power_W=rates[r['product_id']]) for r in project['fixtures']]
    connected=math.fsum(r['input_power_W'] for r in fixtures)
    allowance=number(project['auxiliary_allowance']['value'],zero=True)
    budget=connected+allowance
    annotation=number(project['annotation_area']['value'])
    density=connected/area
    precision=project['density_display_decimals']
    rounded=float(Decimal(str(density)).quantize(Decimal(1).scaleb(-precision),rounding=ROUND_HALF_UP))
    matched=rounded==reported
    totals=dict(fixture_count=len(fixtures),luminaire_input_W=connected,auxiliary_allowance_W=allowance,
        budget_input_W=budget,reported_floor_area_m2=area,annotation_area_m2=annotation,
        calculated_lpd_W_m2=density,budget_density_W_m2=budget/area,
        annotation_budget_density_W_m2=budget/annotation,native_reported_lpd_W_m2=reported)
    if not all(math.isfinite(v) for v in totals.values()):raise ValueError('Lighting audit outside numeric range')
    return dict(status='pass' if matched else 'fail',checks=dict(source_inventory_bound=True,native_lpd_display_matches=matched),
        room_id=project['room_id'],products=products,fixtures=fixtures,totals=totals,
        native_measurements=summary['measurements'],native_warnings=summary.get('warnings',[]),
        geometry_bound=False,native_calculation_executed=False,source_assertions_authenticated=False,
        regulatory_compliance='not_established',design_accepted=False,
        pending=['Recorded native report only; live state and new photometric calculation not verified',
                 'Source ratings/allowance are not measurements or authenticated manufacturer circuit watts',
                 'Reported gross area and annotation are separate; regulatory internal-area applicability not established',
                 'Workplane metrics are not desk task metrics; no room/task compliance inferred',
                 'Sparse-array coordinate/native geometry correspondence and full electrical design remain separate'])
