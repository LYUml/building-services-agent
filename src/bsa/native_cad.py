"""Isolated AutoCAD Core Console conversion and native entity inspection.

Never attaches to or closes a user's GUI session. Only generated copies are writable.
"""
import argparse
import csv
import json
import shutil
import subprocess
from pathlib import Path
from .cli import digest
from .engine import ProjectError

DEFAULT_EXE = Path("C:/Program Files/Autodesk/AutoCAD 2027/accoreconsole.exe")


def lisp_string(value):
    return json.dumps(str(value).replace("\\", "/"), ensure_ascii=True)


def execute(exe, drawing, script, log, timeout):
    with log.open("wb") as f:
        proc = subprocess.run([str(exe), "/i", str(drawing), "/s", str(script), "/l", "en-US"],
                              cwd=script.parent, stdout=f, stderr=subprocess.STDOUT, timeout=timeout)
    if proc.returncode:
        raise ProjectError(f"AutoCAD exited {proc.returncode}; inspect {log}")


def convert(source, out, exe=DEFAULT_EXE, timeout=120):
    source, out, exe = source.resolve(), out.resolve(), exe.resolve()
    if not exe.is_file() or not source.is_file():
        raise ProjectError("AutoCAD executable and source DXF must exist")
    if source.suffix.lower() != ".dxf":
        raise ProjectError("this adapter accepts generated DXF overlays only")
    if out in source.parents or out == source:
        raise ProjectError("output directory must not contain source")
    import ezdxf
    document=ezdxf.readfile(source)
    if any(e.dxftype() not in ("CIRCLE", "TEXT") for e in document.modelspace()):
        raise ProjectError("native adapter currently supports CIRCLE/TEXT overlays only")
    if any(any(ch in e.dxf.text for ch in ',\r\n') for e in document.modelspace().query("TEXT")):
        raise ProjectError("native CSV inspection currently requires labels without commas or line breaks")
    before = digest(source)
    out.mkdir(parents=True, exist_ok=False)
    copied = out/"input.dxf"
    shutil.copyfile(source, copied)
    dwg, audit = out/"devices.dwg", out/"native-entities.csv"
    # Verify the opened drawing name and directory before mutating the isolated document.
    script = out/"convert.scr"
    expected_path=lisp_string(copied)
    # Guard encloses every mutation: a wrong document produces no DWG.
    condition=f'(= (strcase (vl-string-translate (chr 92) "/" (strcat (getvar "DWGPREFIX") (getvar "DWGNAME")))) (strcase {expected_path}))'
    script.write_text(f'(if {condition} (progn (setvar "FILEDIA" 0) (setvar "CMDDIA" 0) (command "_.ZOOM" "_E") (command "_.SAVEAS" "2018" {lisp_string(dwg)})) (princ "BSA WRONG DOCUMENT"))\n_.QUIT\n_Y\n',encoding="ascii")
    execute(exe,copied,script,out/"convert.log",timeout)
    if not dwg.is_file():
        raise ProjectError("DWG missing; inspect convert.log")
    inspect = out/"inspect.scr"
    # Only read native entities in a second independent AutoCAD process; no source modification.
    inspect.write_text(f'(setq f (open {lisp_string(audit)} "w"))\n'+
        '(write-line "type,layer,x,y,radius,text" f)\n'+
        '(setq ss (ssget "_X" (list (cons 410 "Model"))))\n'+
        '(if ss (progn (setq i 0) (repeat (sslength ss) (setq e (entget (ssname ss i)) typ (cdr (assoc 0 e)) pt (cdr (assoc 10 e))) (if (member typ (list "CIRCLE" "TEXT")) (write-line (strcat typ "," (cdr (assoc 8 e)) "," (rtos (car pt) 2 9) "," (rtos (cadr pt) 2 9) "," (if (= typ "CIRCLE") (rtos (cdr (assoc 40 e)) 2 9) "") "," (if (= typ "TEXT") (cdr (assoc 1 e)) "")) f)) (setq i (1+ i)))))\n'+
        '(write-line (strcat "UNITS," (itoa (getvar "INSUNITS"))) f)\n(close f)\n_.QUIT\n',encoding="ascii")
    execute(exe,dwg,inspect,out/"inspect.log",timeout)
    if not audit.is_file():
        raise ProjectError("native inspection file missing")
    import ezdxf
    expected=ezdxf.readfile(source)
    lines=audit.read_text().splitlines()
    rows=list(csv.DictReader(lines[:-1]))
    actual_c=[r for r in rows if r["type"]=="CIRCLE"]
    actual_t=[r for r in rows if r["type"]=="TEXT"]
    def circles_native():
        return sorted((r["layer"],round(float(r["x"]),8),round(float(r["y"]),8),round(float(r["radius"]),8)) for r in actual_c)
    expected_c=sorted((e.dxf.layer,round(e.dxf.center.x,8),round(e.dxf.center.y,8),round(e.dxf.radius,8)) for e in expected.modelspace().query("CIRCLE"))
    expected_t=sorted((e.dxf.layer,round(e.dxf.insert.x,8),round(e.dxf.insert.y,8),e.dxf.text) for e in expected.modelspace().query("TEXT"))
    native_t=sorted((r["layer"],round(float(r["x"]),8),round(float(r["y"]),8),r["text"]) for r in actual_t)
    checks=dict(circles_match=circles_native()==expected_c,labels_match=native_t==expected_t,
                metre_units=lines[-1]=="UNITS,6",source_unchanged=digest(source)==before)
    result=dict(engine=str(exe),source_sha256=before,dwg_sha256=digest(dwg),
                checks=checks,native_reopen_pass=all(checks.values()),
                plot_visual_review="pending",design_accepted=False)
    (out/"native-verification.json").write_text(json.dumps(result,indent=2),encoding="utf-8")
    if not all(checks.values()):
        raise ProjectError(f"native verification failed: {checks}")
    return result


def plot(dwg, source_dxf, output_pdf, exe=DEFAULT_EXE, timeout=120):
    """Plot a padded schematic window. Fit-to-page is explicitly not a fixed scale."""
    import ezdxf
    dwg, output_pdf = dwg.resolve(), output_pdf.resolve()
    if output_pdf.exists():
        raise ProjectError("refusing to overwrite existing PDF")
    doc=ezdxf.readfile(source_dxf)
    points=[]
    for e in doc.modelspace():
        if e.dxftype()=="CIRCLE":
            c,r=e.dxf.center,e.dxf.radius
            points.extend([(c.x-r,c.y-r),(c.x+r,c.y+r)])
        elif e.dxftype()=="TEXT":
            c,h=e.dxf.insert,e.dxf.height
            points.extend([(c.x,c.y-h),(c.x+len(e.dxf.text)*h,c.y+h)])
        else:
            raise ProjectError("plot adapter supports CIRCLE/TEXT overlays only")
    if not points:
        raise ProjectError("no plottable entities")
    xmin=min(x for x,y in points);xmax=max(x for x,y in points)
    ymin=min(y for x,y in points);ymax=max(y for x,y in points)
    margin=max((xmax-xmin)*0.08,0.5)
    window=[f"{xmin-margin},{ymin-margin}",f"{xmax+margin},{ymax+margin}"]
    script=output_pdf.with_suffix(".scr")
    condition=f'(= (strcase (vl-string-translate (chr 92) "/" (strcat (getvar "DWGPREFIX") (getvar "DWGNAME")))) (strcase {lisp_string(dwg)}))'
    commands=['(setvar "FILEDIA" 0)','(setvar "CMDDIA" 0)',
        '(setvar "BACKGROUNDPLOT" 0)','(setvar "PLOTSTAMP" 0)',
        '_.-PLOT','_Y','Model','DWG To PDF.pc3','ISO full bleed A4 (297.00 x 210.00 MM)',
        '_M','_L','_N','_W',*window,'_F','_C','_Y','monochrome.ctb','_Y','_A',
        lisp_string(output_pdf),'_N','_Y','_.QUIT','_Y']
    setup=" ".join(commands[:3])
    # PLOTSTAMP is not a writable integer sysvar on all versions; omit it.
    plot_args=commands[4:-2]
    plot_expr="(command "+" ".join(lisp_string(x.strip('"')) for x in plot_args)+")"
    script.write_text(f'(if {condition} (progn {setup} {plot_expr}) (princ "BSA WRONG DOCUMENT"))\n_.QUIT\n_Y\n',encoding="ascii")
    before=digest(dwg)
    execute(exe,dwg,script,output_pdf.with_suffix(".log"),timeout)
    if not output_pdf.is_file() or not output_pdf.read_bytes().startswith(b"%PDF-"):
        raise ProjectError("AutoCAD did not produce a PDF")
    if digest(dwg)!=before:
        raise ProjectError("plot unexpectedly changed the DWG")
    return {"pdf_sha256":digest(output_pdf),"scale":"fit-to-page schematic", "visual_review":"pending"}


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("source",type=Path);p.add_argument("--out",type=Path,required=True)
    p.add_argument("--exe",type=Path,default=DEFAULT_EXE)
    a=p.parse_args()
    result=convert(a.source,a.out,a.exe)
    result["plot"]=plot(a.out/"devices.dwg",a.source,a.out/"devices.pdf",a.exe)
    (a.out/"native-verification.json").write_text(json.dumps(result,indent=2),encoding="utf-8")
    print(json.dumps(result,indent=2))

if __name__=="__main__":main()
