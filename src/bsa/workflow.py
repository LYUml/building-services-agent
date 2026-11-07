"""Auditable handoff from a host AI's brief interpretation to engineering tools.

This module does not pretend regex can interpret arbitrary engineering requirements.
The host agent supplies a source-linked plan; execution accepts only known adapters.
"""
import argparse
import html
import json
import re
from pathlib import Path
from .cli import digest
from .engine import ProjectError


def read_json(path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def passages(brief):
    text=brief.read_text(encoding="utf-8-sig")
    rows=[];start=None;parts=[]
    for line_no,line in enumerate(text.splitlines()+[""],1):
        if line.strip():
            if start is None:start=line_no
            parts.append(line)
        elif start is not None:
            value="\n".join(parts)
            rows.append(dict(id=f"P{len(rows)+1:03}",start_line=start,end_line=line_no-1,text=value))
            start=None;parts=[]
    return rows


def intake(brief,out):
    brief,out=brief.resolve(),out.resolve()
    if brief.suffix.lower() not in (".md",".txt"):
        raise ProjectError("intake currently accepts UTF-8 Markdown/text; extract other formats with page provenance first")
    if out==brief:raise ProjectError("cannot overwrite brief")
    if out.exists():raise ProjectError("refusing to overwrite intake")
    result=dict(brief=str(brief),brief_sha256=digest(brief),passages=passages(brief),
        interpretation_status="pending host-agent interpretation",requirements=[])
    out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding="utf-8")
    return result


def local_path(root,value):
    if not isinstance(value,str) or Path(value).is_absolute():raise ProjectError("plan inputs must use relative paths")
    path=(root/value).resolve()
    if not path.is_relative_to(root) or not path.is_file():raise ProjectError(f"invalid input path: {value}")
    return path


def validate_plan(path):
    root=path.resolve().parent;p=read_json(path)
    if not isinstance(p,dict) or type(p.get("version")) is not int or p.get("version")!=1:raise ProjectError("plan version 1 required")
    brief=local_path(root,p.get("brief"))
    if digest(brief)!=p.get("brief_sha256"):raise ProjectError("brief hash differs; re-interpret current source")
    source={x["id"]:x for x in passages(brief)}
    dispositions=p.get("passage_dispositions")
    if not isinstance(dispositions,dict) or set(dispositions)!=set(source):
        raise ProjectError("every brief passage needs an explicit requirement/context disposition")
    if any(v not in ("requirement","context") for v in dispositions.values()):raise ProjectError("invalid passage disposition")
    tasks=p.get("tasks");requirements=p.get("requirements")
    if not isinstance(tasks,list) or not tasks or not isinstance(requirements,list) or not requirements:
        raise ProjectError("nonempty tasks and requirements required")
    ids=set();inputs={brief}
    for t in tasks:
        if not isinstance(t,dict) or not isinstance(t.get("id"),str) or not re.fullmatch(r"[A-Za-z0-9_-]+",t["id"]) or t["id"] in ids:
            raise ProjectError("task ids must be unique path-safe strings")
        kind=t.get("kind")
        if kind not in ("electrical","energy","native_cad","manual"):
            raise ProjectError("unknown task adapter")
        if kind in ("electrical","energy"):
            inputs.add(local_path(root,t.get("project")))
        if kind=="native_cad" and t.get("depends_on") not in ids:
            raise ProjectError("native task must depend on an earlier electrical task")
        if kind=="native_cad" and next(x for x in tasks if x["id"]==t["depends_on"])["kind"]!="electrical":
            raise ProjectError("native task requires electrical overlay")
        ids.add(t["id"])
    seen=set();cited=set()
    for r in requirements:
        if not isinstance(r,dict) or not isinstance(r.get("id"),str) or not r["id"] or r["id"] in seen:
            raise ProjectError("unique requirement ids required")
        seen.add(r["id"])
        passage=r.get("passage")
        if not isinstance(passage,str) or passage not in source or dispositions[passage]!="requirement":raise ProjectError("invalid requirement source passage")
        if not isinstance(r.get("quote"),str) or not r["quote"].strip() or r["quote"] not in source[passage]["text"]:
            raise ProjectError("requirement quote does not match source")
        if r.get("task") not in ids:raise ProjectError("unknown requirement task")
        if not isinstance(r.get("acceptance"),str) or not r["acceptance"].strip():raise ProjectError("acceptance description required")
        cited.add(passage)
    if cited!={k for k,v in dispositions.items() if v=="requirement"}:
        raise ProjectError("requirement passage omitted from matrix")
    if {r["task"] for r in requirements}!=ids:raise ProjectError("every task must map to a requirement")
    return p,inputs


def execute(plan,out,energyplus=None,autocad=None):
    plan,out=plan.resolve(),out.resolve()
    p,inputs=validate_plan(plan);inputs.add(plan)
    if any(out==f or out in f.parents for f in inputs):raise ProjectError("run output must not contain inputs")
    before={str(f):digest(f) for f in inputs}
    out.mkdir(parents=True,exist_ok=False)
    evidence={};tasks={}
    root=plan.parent
    for t in p["tasks"]:
        folder=out/t["id"]
        status="pending";reason="";payload=None
        try:
            if t["kind"]=="electrical":
                from .cli import run
                payload=run(local_path(root,t["project"]),folder)
                status="pass" if payload["calculated_checks_pass"] else "fail"
                reason="conditional electrical checks only; remaining design checks are in calculations.json"
            elif t["kind"]=="energy":
                if energyplus:
                    from .energy import run
                    payload=run(local_path(root,t["project"]),folder,energyplus)
                    status="pass";reason="design-day engine execution; no annual energy or physical HVAC routing asserted"
                else:reason="EnergyPlus executable not supplied"
            elif t["kind"]=="native_cad":
                upstream=tasks[t["depends_on"]]
                if upstream["status"]=="fail":reason="upstream electrical task failed"
                elif autocad:
                    from .native_cad import convert,plot
                    dxf=out/t["depends_on"]/"devices.dxf"
                    payload=convert(dxf,folder,autocad)
                    payload["plot"]=plot(folder/"devices.dwg",dxf,folder/"devices.pdf",autocad)
                    (folder/"native-verification.json").write_text(json.dumps(payload,indent=2),encoding="utf-8")
                    status="pass";reason="native reopen/geometry checks and PDF generation; visual acceptance pending"
                else:reason="AutoCAD executable not supplied"
            else:reason=t.get("description","manual engineering/visual verification required")
        except Exception as exc:
            status="fail";reason=f"{type(exc).__name__}: {exc}"
        tasks[t["id"]]=dict(kind=t["kind"],status=status,scope=reason)
        # An executed adapter is evidence for its narrow scope, not every interpreted requirement.
        evidence[t["id"]]=[f.relative_to(out).as_posix() for f in folder.rglob("*") if f.is_file()] if folder.exists() else []
    unchanged=all(f.is_file() and digest(f)==before[str(f)] for f in inputs)
    source_rows={x["id"]:x for x in passages(local_path(root,p["brief"]))}
    matrix=[]
    for r in p["requirements"]:
        task=tasks[r["task"]]
        matrix.append(dict(**r,execution_status=task["status"],acceptance_status="pending review",
                           source_locator={k:source_rows[r["passage"]][k] for k in ("start_line","end_line")},
                           execution_scope=task["scope"],evidence=evidence[r["task"]]))
    result=dict(inputs=before,inputs_unchanged=unchanged,tasks=tasks,requirements=matrix,
        artifact_hashes={f.relative_to(out).as_posix():digest(f) for f in out.rglob("*") if f.is_file()},
        execution_pass=unchanged and all(x["status"]=="pass" for x in tasks.values()),
        design_accepted=False,acceptance_note="Host agent must compare each artifact to the complete acceptance text; execution is not engineering acceptance")
    (out/"workflow.json").write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding="utf-8")
    rows="".join('<tr><td>'+html.escape(r['id'])+'</td><td>'+html.escape(r['quote'])+'</td><td>'+html.escape(r['execution_status'])+'</td><td>'+html.escape(r['execution_scope'])+'</td><td>Pending review</td></tr>' for r in matrix)
    (out/"index.html").write_text('<!doctype html><meta charset="utf-8"><title>MEP workflow evidence</title><h1>MEP workflow evidence</h1><p>Design acceptance: pending. Source hashes unchanged: '+str(unchanged)+'</p><table border="1"><tr><th>Requirement</th><th>Source quote</th><th>Execution</th><th>Scope</th><th>Acceptance</th></tr>'+rows+'</table>',encoding="utf-8")
    if not unchanged:raise ProjectError("source inputs changed during workflow")
    return result


def verify(run_directory):
    root=run_directory.resolve()
    report=read_json(root/"workflow.json")
    issues=[]
    for name,expected in report["inputs"].items():
        path=Path(name)
        if not path.is_file() or digest(path)!=expected:issues.append(f"input changed or missing: {name}")
    for name,expected in report["artifact_hashes"].items():
        path=(root/name).resolve()
        if not path.is_relative_to(root) or not path.is_file() or digest(path)!=expected:
            issues.append(f"artifact changed or missing: {name}")
    return dict(integrity_pass=not issues,issues=issues,design_accepted=False,
                scope="Recorded inputs and task artifact bytes only; no semantic or engineering acceptance")


def main():
    p=argparse.ArgumentParser(description=__doc__);sub=p.add_subparsers(dest="command",required=True)
    i=sub.add_parser("intake");i.add_argument("brief",type=Path);i.add_argument("--out",type=Path,required=True)
    v=sub.add_parser("validate");v.add_argument("plan",type=Path)
    e=sub.add_parser("execute");e.add_argument("plan",type=Path);e.add_argument("--out",required=True,type=Path)
    e.add_argument("--energyplus",type=Path);e.add_argument("--autocad",type=Path)
    v=sub.add_parser("verify");v.add_argument("run_directory",type=Path)
    a=p.parse_args()
    try:
        if a.command=="intake":r=intake(a.brief,a.out);print(f"Indexed {len(r['passages'])} source passages; interpretation pending")
        elif a.command=="validate":validate_plan(a.plan);print("Source-linked plan valid; interpretation accuracy still requires review")
        elif a.command=="verify":
            r=verify(a.run_directory);print(json.dumps(r,indent=2))
            if not r["integrity_pass"]:return 2
        else:
            r=execute(a.plan,a.out,a.energyplus,a.autocad)
            print(json.dumps({"tasks":r["tasks"],"design_accepted":False},indent=2))
            if not r["execution_pass"]:return 2
    except (ProjectError,OSError,ValueError) as exc:p.exit(2,str(exc)+"\n")
    return 0

if __name__=="__main__":raise SystemExit(main())
