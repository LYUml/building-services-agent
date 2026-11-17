"""Small auditable engineering report; no external scripts or copied coursework style."""
import html


def render(data):
    def e(v):return html.escape(str(v))
    labels={'luminaire_input_W':'Luminaire input (W electrical)','auxiliary_allowance_W':'Declared auxiliary allowance (W electrical)',
        'budget_input_W':'Input budget including allowance (W electrical)','reported_floor_area_m2':'Recorded native gross area (m²)',
        'annotation_area_m2':'Source annotation area (m²)','calculated_lpd_W_m2':'Calculated fixture density on recorded area (W electrical/m²)',
        'native_reported_lpd_W_m2':'Recorded native fixture density (W/m²)','budget_density_W_m2':'Budget density on recorded area (W electrical/m²)',
        'annotation_budget_density_W_m2':'Budget density on annotation area (W electrical/m²)'}
    rows=''.join('<tr><td>'+e(label)+'</td><td>'+e(format(data['totals'][key],'.6g'))+'</td></tr>' for key,label in labels.items())
    notes=''.join('<li>'+e(s)+'</li>' for s in data['pending'])
    metrics=''.join('<tr><td>'+e(r['metric'])+'</td><td>'+e(r['value'])+' '+e(r['unit'])+'</td><td>'+e(r['calculation_surface'])+'</td><td>'+e(r['page'])+'</td></tr>' for r in data['native_measurements'])
    return '<!doctype html><meta charset="utf-8"><title>Lighting source power audit</title><style>body{font:16px Arial;max-width:1000px;margin:36px auto;color:#172334}table{border-collapse:collapse;width:100%;margin:24px 0}td,th{border:1px solid #bac5ce;padding:10px;text-align:left}h1,h2{color:#124668}</style><h1>Lighting source power audit</h1><p>Source consistency: '+e(data['status'])+'. Engineering and regulatory acceptance remain pending.</p><h2>Power and area basis</h2><table>'+rows+'</table><h2>Recorded workplane metrics — not desk task acceptance</h2><table><tr><th>Metric</th><th>Value</th><th>Surface</th><th>Original PDF page</th></tr>'+metrics+'</table><h2>Scope and unresolved checks</h2><ul>'+notes+'</ul>'
