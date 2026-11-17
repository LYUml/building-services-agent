"""One common report consumer; no numerical or drawing engine is duplicated."""
from html import escape


def render(model):
    rows = []
    for entity in model['entities']:
        for name, q in entity['quantities'].items():
            cells = [entity['kind'], entity['source_id'], name,
                     str(q['value'])+' '+q['unit'], str(q['si_value'])+' '+q['si_unit'],
                     q['classification'], q['source_pointer']]
            rows.append('<tr>'+''.join('<td>'+escape(c)+'</td>' for c in cells)+'</tr>')
    return ('<!doctype html><html lang="en"><meta charset="utf-8">'
            '<title>Engineering data review</title><style>'
            'body{font:14px sans-serif;margin:24px}table{border-collapse:collapse}'
            'td,th{border:1px solid #bbb;padding:6px;text-align:left}'
            '</style><h1>Engineering data review</h1><p>Project: '+escape(model['project_id'])+
            '; scenario: '+escape(model['scenario_id'])+'</p><p>Derived view of a verified '
            'producer; original data and engineering acceptance remain separate.</p><pre>'+
            escape(str(model['source_acceptance']))+'</pre><pre>'+escape(str(model['source_flags']))+
            '</pre><table><thead><tr>'+''.join('<th>'+s+'</th>' for s in
            ('Entity type', 'Source ID', 'Quantity', 'Original', 'SI', 'Classification', 'Source pointer'))+
            '</tr></thead><tbody>'+''.join(rows)+'</tbody></table></html>')
