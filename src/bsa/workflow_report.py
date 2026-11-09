"""Static local requirement-to-artifact report; no acceptance promotion."""
import html
from pathlib import PurePosixPath
from urllib.parse import quote
from .engine import ProjectError


def render(report):
    esc=lambda value: html.escape(str(value),quote=True)
    def link(name):
        path=PurePosixPath(name)
        if path.is_absolute() or '..' in path.parts or '\\' in name or ':' in name or not path.parts:
            raise ProjectError('report artifact must be a safe relative path')
        if name not in report['artifact_hashes']:raise ProjectError('report evidence missing from artifact manifest')
        return '<a href="'+quote(name,safe='/')+'">'+esc(name)+'</a> <small>SHA256 '+esc(report['artifact_hashes'][name])+'</small>'
    sections=[]
    for row in report['requirements']:
        inputs=[i for i in report.get('unresolved_inputs',[]) if row['task'] in i['blocks_tasks']]
        input_notice='<h3>Unresolved design inputs</h3><ul>'+''.join('<li>'+esc(i['id'])+' ('+esc(i['kind'])+'): '+esc(i['description'])+'<br>Source citations: '+esc(i['sources'])+'</li>' for i in inputs)+'</ul>' if inputs else ''
        files=sorted(set(row['evidence']))
        evidence='<ul>'+''.join('<li>'+link(name)+'</li>' for name in files)+'</ul>' if files else '<p>No artifacts generated for this task.</p>'
        sections.append('<section><h2>'+esc(row['id'])+' · '+esc(row['task'])+'</h2>'
            '<p><strong>Execution: '+esc(row['execution_status'])+'</strong> · Acceptance: pending review</p>'
            '<h3>Source requirement</h3><blockquote>'+esc(row['quote'])+'</blockquote>'
            '<p>Source locator: '+esc(row.get('source_locator',{}))+'</p>'
            '<h3>Acceptance target</h3><p>'+esc(row['acceptance'])+'</p>'
            '<h3>Executed scope</h3><p>'+esc(row['execution_scope'])+'</p>'
            +input_notice+
            '<details><summary>Task artifacts ('+str(len(files))+')</summary>'+evidence+'</details></section>')
    statuses={s:sum(t['status']==s for t in report['tasks'].values()) for s in ('pass','fail','pending')}
    return '''<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>MEP workflow evidence</title>
<style>body{font:16px/1.55 system-ui,sans-serif;background:#f3f5f7;color:#182735;margin:0}
main{max-width:1100px;margin:32px auto;padding:0 24px}section{background:white;border:1px solid #d5dde3;border-radius:8px;padding:20px;margin:20px 0}
h1{font-size:28px}h2{font-size:21px}h3{font-size:16px;margin-bottom:4px}blockquote{border-left:3px solid #62859d;margin:8px 0;padding:8px 16px;white-space:pre-wrap}
a{color:#125b91}li{margin:10px 0;overflow-wrap:anywhere}small{display:block;color:#556574;font-family:monospace}
summary{cursor:pointer;font-weight:600}p{overflow-wrap:anywhere}.notice{padding:16px;background:#fff0cd;border-left:4px solid #986b0a}
</style></head><body><main><h1>MEP workflow evidence</h1>
<p class="notice">Design acceptance: pending. Passing execution is not engineering or regulatory acceptance.
Failed tasks may retain diagnostic artifacts; those files are not approved deliverables.</p>'''+ '<p>'+esc(statuses['pass'])+' passed · '+esc(statuses['fail'])+' failed · '+esc(statuses['pending'])+' pending</p><p>Source inputs unchanged at execution: '+esc(report['inputs_unchanged'])+'</p><p><a href="workflow.json">Full machine-readable report</a></p>'+''.join(sections)+'</main></body></html>'
