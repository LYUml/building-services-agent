"""One common report consumer; no numerical or drawing engine is duplicated."""
from html import escape


def render(model, inputs=None):
    rows = []
    for entity in model['entities']:
        for name, q in entity['quantities'].items():
            cells = [entity['kind'], entity['source_id'], name,
                     str(q['value'])+' '+q['unit'], str(q['si_value'])+' '+q['si_unit'],
                     q['classification'], q['source_pointer']]
            rows.append('<tr>'+''.join('<td>'+escape(c)+'</td>' for c in cells)+'</tr>')
    text = ('<!doctype html><html lang="en"><meta charset="utf-8">'
            '<title>Engineering data review</title><style>'
            'body{font:14px sans-serif;margin:24px}table{border-collapse:collapse}'
            'td,th{border:1px solid #bbb;padding:6px;text-align:left}'
            '</style><h1>Engineering data review</h1><p>Project: '+escape(model['project_id'])+
            '; scenario: '+escape(model['scenario_id'])+'</p><p>Derived view of a verified '
            'producer; original data and engineering acceptance remain separate.</p><pre>'+
            escape(str(model['source_acceptance']))+'</pre><pre>'+escape(str(model['source_flags']))+
            '</pre><table><thead><tr>'+''.join('<th>'+s+'</th>' for s in
            ('Entity type', 'Source ID', 'Quantity', 'Original', 'SI', 'Classification', 'Source pointer'))+
            '</tr></thead><tbody>'+''.join(rows)+'</tbody></table>')
    if inputs is not None:
        owners = {e['id']: e['kind']+' / '+e['source_id'] for e in model['entities']}
        text += '<h2>Source inputs: review required</h2><p>'+escape(inputs['scope'])+'</p><table><tr>'
        text += ''.join('<th>'+s+'</th>' for s in ('Owner', 'Parameter', 'Source value', 'SI', 'Classification', 'Source pointer', 'Source note'))+'</tr>'
        for row in inputs['parameters']:
            q = row['quantity']
            cells = [owners[row['entity_id']], row['name'], str(q['value'])+' '+row['source_unit'],
                     str(q['si_value'])+' '+q['si_unit'], q['classification'],
                     q['source_pointer'], row['source_text']]
            text += '<tr>'+''.join('<td>'+escape(c)+'</td>' for c in cells)+'</tr>'
        text += '</table><p>Numeric input coverage: '+escape(str(inputs['coverage']))+'</p>'
    return text+'</html>'
