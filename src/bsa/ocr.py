"""Offline OCR sidecars for PDF pages; recognized values always need source review."""
import argparse
import importlib.metadata
import json
from pathlib import Path
import shutil
import subprocess
from .cli import digest
from .engine import ProjectError


def render_pdf_page(source,prefix,executable,page,*,dpi=180,max_side=None):
    """Shared existing Poppler invocation; no OCR or dimensional interpretation."""
    scale=['-r',str(dpi)] if max_side is None else ['-scale-to',str(max_side)]
    try:
        subprocess.run([str(executable),*scale,'-f',str(page),'-l',str(page),'-singlefile','-png',str(source),str(prefix)],
                       check=True,timeout=120,capture_output=True)
    except (subprocess.CalledProcessError,subprocess.TimeoutExpired) as exc:
        log=Path(prefix).with_suffix('.renderer.log');error=exc.stderr or b''
        log.write_bytes(error if isinstance(error,bytes) else error.encode('utf-8'))
        raise ProjectError('PDF renderer failed or timed out; inspect '+str(log)) from exc
    return Path(prefix).with_suffix('.png')


def run(source, out, renderer=None):
    from pypdf import PdfReader
    import rapidocr_onnxruntime
    from rapidocr_onnxruntime import RapidOCR
    source, out = source.resolve(), out.resolve()
    if source.suffix.lower() != '.pdf':raise ProjectError('OCR adapter currently accepts PDF only')
    if out in source.parents or out == source:raise ProjectError('output must not contain source')
    executable=Path(renderer or shutil.which('pdftoppm') or '')
    if not executable.is_file():raise ProjectError('supply a Poppler pdftoppm executable')
    reader=PdfReader(source)
    if reader.is_encrypted:raise ProjectError('encrypted PDF needs an authorized decrypted copy')
    before=digest(source)
    out.mkdir(parents=True,exist_ok=False)
    engine=RapidOCR(intra_op_num_threads=2,inter_op_num_threads=2)
    pages=[]
    for n in range(1,len(reader.pages)+1):
        prefix=out/f'page-{n:04}'
        image=render_pdf_page(source,prefix,executable,n)
        result,_=engine(str(image),text_score=0.1)
        lines=[dict(box=[[float(v) for v in point] for point in box],text=text,confidence=float(score))
               for box,text,score in (result or [])]
        pages.append(dict(page=n,image=image.name,image_sha256=digest(image),lines=lines))
    models=Path(rapidocr_onnxruntime.__file__).parent/'models'
    result=dict(version=1,source_sha256=before,source_name=source.name,dpi=180,
                engine='rapidocr_onnxruntime',engine_version=importlib.metadata.version('rapidocr_onnxruntime'),
                onnxruntime_version=importlib.metadata.version('onnxruntime'),
                model_sha256={p.name:digest(p) for p in models.glob('*.onnx')},
                renderer_sha256=digest(executable),text_score_threshold=0.1,pages=pages,
                acceptance='pending visual transcription review; confidence is not correctness')
    if digest(source)!=before:raise ProjectError('source PDF changed during OCR')
    (out/'ocr.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    return result


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('source',type=Path);p.add_argument('--out',type=Path,required=True)
    p.add_argument('--pdftoppm',type=Path)
    a=p.parse_args();r=run(a.source,a.out,a.pdftoppm)
    print(json.dumps(dict(pages=len(r['pages']),lines=sum(len(p['lines']) for p in r['pages']),review='pending')))


if __name__=='__main__':main()
