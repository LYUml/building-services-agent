import argparse
import hashlib
import html
import json
from pathlib import Path
from .engine import ProjectError, calculate, validate


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def dxf(p):
    import io
    import ezdxf
    doc = ezdxf.new("R2010")
    doc.units = 6  # metres, DXF $INSUNITS
    doc.layers.new("BSA_DEVICES", dxfattribs={"color": 2})
    doc.layers.new("BSA_LABELS", dxfattribs={"color": 7})
    msp = doc.modelspace()
    for d in p["devices"]:
        msp.add_circle((d["x_m"], d["y_m"]), 0.12,
                       dxfattribs={"layer": "BSA_DEVICES"})
        msp.add_text(d["id"] + " / " + d["circuit"], dxfattribs={
            "layer": "BSA_LABELS", "height": 0.12,
            "insert": (d["x_m"] + 0.2, d["y_m"])})
    stream = io.StringIO()
    doc.write(stream)
    return stream.getvalue()


def run(project, out):
    project = project.resolve()
    out = out.resolve()
    if project == out or out in project.parents:
        raise ProjectError("output directory must not contain the input project")
    before = digest(project)
    p = validate(json.loads(project.read_text(encoding="utf-8-sig")))
    result = calculate(p)
    if any(not d["id"].isascii() or not d["circuit"].isascii() or
           any(x in d["id"]+d["circuit"] for x in "\r\n") for d in p["devices"]):
        raise ProjectError("DXF labels currently require ASCII IDs without line breaks")
    # Never silently overwrite a previous run or unrelated files.
    out.mkdir(parents=True, exist_ok=False)
    (out/"calculations.json").write_text(json.dumps(result,indent=2),encoding="utf-8")
    (out/"devices.dxf").write_text(dxf(p),encoding="ascii")
    ds = p["devices"]
    xmin=min(d["x_m"] for d in ds)-1; ymin=min(d["y_m"] for d in ds)-1
    width=max(d["x_m"] for d in ds)-xmin+2; height=max(d["y_m"] for d in ds)-ymin+2
    svg=[f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="{xmin} {ymin} {width} {height}">']
    for d in ds:
        svg.append(f'<circle cx="{d["x_m"]}" cy="{d["y_m"]}" r="0.12" fill="none" stroke="black" stroke-width="0.02"/>')
        svg.append(f'<text x="{d["x_m"]+0.2}" y="{d["y_m"]}" font-size="0.15">{html.escape(d["id"]+" / "+d["circuit"])}</text>')
    svg.append('</svg>')
    (out/"preview.svg").write_text("".join(svg),encoding="utf-8")
    rows="".join(f'<tr><td>{html.escape(c["id"])}</td><td>{c["design_current_a"]:.3f}</td><td>{c["voltage_drop_percent"]:.3f}</td><td>{all(c["checks"].values())}</td></tr>' for c in result["circuits"])
    sources="".join(f'<li>{html.escape(k)}: {html.escape(v)}</li>' for k,v in p["sources"].items())
    (out/"report.html").write_text('<!doctype html><meta charset="utf-8"><title>BSA conditional analysis</title><h1>'+html.escape(p["name"])+
        '</h1><p>Conditional calculation only. Design acceptance: PENDING. Geometry in metres; SVG is a schematic preview with downward Y, not a plotted CAD sheet.</p><table border="1"><tr><th>Circuit</th><th>Ib (A)</th><th>Voltage drop (%)</th><th>Calculated checks pass</th></tr>'+rows+
        '</table><h2>Unresolved checks</h2><ul>'+''.join('<li>'+html.escape(x)+'</li>' for x in result['pending'])+'</ul><h2>Input sources</h2><ul>'+sources+'</ul><img src="preview.svg" alt="Schematic device overlay">',encoding="utf-8")
    if digest(project)!=before:
        raise ProjectError("input changed during run")
    manifest=dict(input_path=str(project),input_sha256=before,input_unchanged=True,
        device_count=len(ds),dxf_circle_count=(out/"devices.dxf").read_text().count("\nCIRCLE\n"),
        outputs={f.name:digest(f) for f in out.iterdir() if f.is_file()})
    if manifest["device_count"]!=manifest["dxf_circle_count"]:
        raise ProjectError("drawing device count mismatch")
    (out/"manifest.json").write_text(json.dumps(manifest,indent=2),encoding="utf-8")
    return result


def main():
    parser=argparse.ArgumentParser(description="Building Services Agent engineering tools")
    sub=parser.add_subparsers(dest="command",required=True)
    for command in ("validate","run"):
        s=sub.add_parser(command);s.add_argument("project",type=Path)
        if command=="run": s.add_argument("--out",type=Path,required=True)
    a=parser.parse_args()
    try:
        if a.command=="validate":
            validate(json.loads(a.project.read_text(encoding="utf-8-sig")))
            print("Valid electrical project; engineering acceptance not assessed.")
        else:
            result=run(a.project,a.out)
            print(json.dumps({"output":str(a.out),"calculated_checks_pass":result["calculated_checks_pass"],"design_accepted":False}))
            if not result["calculated_checks_pass"]: return 2
    except (ProjectError, OSError, ValueError) as e:
        parser.exit(2,str(e)+"\n")
    return 0


if __name__=="__main__":
    raise SystemExit(main())
