"""Explicit host visual transcription bound to actual rendered PDF pages."""
import json
import math
from pathlib import Path
from .cli import digest
from .module_contract import read_json
from .workspace import allowed,intake_output

SCHEMA='bsa.visual-transcription/1'


def validate(source,sidecar,data,page_count):
    source,sidecar=Path(source).resolve(),Path(sidecar).resolve();root=sidecar.parent
    if not isinstance(data,dict) or set(data)!={'schema','source_sha256','pages'} or data['schema']!=SCHEMA or data['source_sha256']!=digest(source):raise ValueError('Exact visual transcription/source identity required')
    if not isinstance(data['pages'],list) or len(data['pages'])!=page_count:raise ValueError('Every source page needs an explicit visual record')
    from . import source_page,ocr
    pins={str(source):digest(source),str(Path(__file__).resolve()):digest(Path(__file__))};rows=[];seen=set();renderers=set()
    for page in data['pages']:
        if not isinstance(page,dict) or set(page)!={'page','receipt','lines'} or type(page['page']) is not int or not 1<=page['page']<=page_count or page['page'] in seen:raise ValueError('Distinct exact one-based visual page records required')
        seen.add(page['page']);name=page['receipt']
        if not isinstance(name,str) or Path(name).is_absolute():raise ValueError('Relative source page receipt required')
        receipt=(root/name).resolve()
        if not receipt.is_relative_to(root) or not receipt.is_file():raise ValueError('Page receipt must remain inside transcription tree')
        meta=read_json(receipt);image=(receipt.parent/meta.get('image','')).resolve()
        if meta.get('schema')!='bsa.source-page/1' or meta.get('source')!=str(source) or meta.get('source_sha256')!=data['source_sha256'] or meta.get('page')!=page['page'] or meta.get('page_count')!=page_count or meta.get('source_unchanged') is not True or meta.get('extraction_review_cleared') is not False or meta.get('design_accepted') is not False:raise ValueError('Source-matching unaccepted rendered page receipt required')
        if not image.is_relative_to(receipt.parent) or not image.is_file() or digest(image)!=meta.get('image_sha256'):raise ValueError('Rendered visual source image changed')
        required={str(source),str(Path(source_page.__file__).resolve()),str(Path(ocr.__file__).resolve())}
        inputs=meta.get('inputs',{});extras=set(inputs)-required if isinstance(inputs,dict) else set()
        if not isinstance(inputs,dict) or not required<=set(inputs) or len(extras)!=1 or Path(next(iter(extras))).name.lower() not in ('pdftoppm','pdftoppm.exe') or any(not Path(p).is_file() or digest(Path(p))!=sha for p,sha in inputs.items()):raise ValueError('Rendered source/method/renderer evidence changed or incomplete')
        renderers.update(extras)
        from PIL import Image
        with Image.open(image) as img:size=list(img.size)
        if meta.get('image_size_px')!=size:raise ValueError('Saved page dimensions differ')
        if not isinstance(page['lines'],list):raise ValueError('Explicit visual lines required')
        lines=[]
        for line in page['lines']:
            if not isinstance(line,dict) or set(line)!={'text','box'} or not isinstance(line['text'],str) or not line['text'].strip():raise ValueError('Literal text and visual locator required; no OCR confidence is generated')
            box=line['box']
            if not isinstance(box,list) or len(box)!=4 or any(not isinstance(p,list) or len(p)!=2 or any(type(v) not in (int,float) or not math.isfinite(v) or not 0<=v<=size[i] for i,v in enumerate(p)) for p in box):raise ValueError('Four finite in-image pixel locator points required')
            if max(p[0] for p in box)<=min(p[0] for p in box) or max(p[1] for p in box)<=min(p[1] for p in box):raise ValueError('Nonempty visual locator region required')
            lines.append(line)
        rows.append(dict(page=page['page'],lines=lines,image_sha256=digest(image),receipt_sha256=digest(receipt)))
        pins.update(inputs);pins.update({str(receipt):digest(receipt),str(image):digest(image)})
    return rows,pins,renderers


def apply(document,source,sidecar):
    data=read_json(sidecar);pages,pins,renderers=validate(source,sidecar,data,document['page_count'])
    filled={p['page'] for p in pages if p['lines']}
    issues=[dict(i) for i in document['issues'] if not (i['code']=='no_text' and i['locator']['page'] in filled)]
    rows=list(document['passages'])
    for page in pages:
        issues.append(dict(code='visual_transcription_review',severity='review',locator=dict(page=page['page']),message='Inspect complete source page and every host visual transcription; this is not OCR confidence or semantic/engineering acceptance'))
        for index,line in enumerate(page['lines'],1):
            rows.append(dict(text=line['text'],page=page['page'],visual_line=index,pixel_box=line['box'],
                locator_basis='Host visual pixel region, not a measured physical length',transcription_method='host_visual_transcription',
                image_sha256=page['image_sha256'],page_receipt_sha256=page['receipt_sha256'],visual_sidecar_sha256=digest(Path(sidecar))))
    for index,issue in enumerate(issues,1):issue['id']=f'I{index:03}'
    rows=sorted(rows,key=lambda r:r['page'])
    for index,row in enumerate(rows,1):row=dict(row);row['id']=f'P{index:03}';rows[index-1]=row
    if any(digest(Path(p))!=sha for p,sha in pins.items()):raise ValueError('Visual transcription source changed during extraction')
    document.update(passages=rows,issues=issues,supporting_files=sorted(set(document.get('supporting_files',[]))|(set(pins)-renderers)|{str(Path(sidecar).resolve())}),
        coverage_status='blocked' if any(i['severity']=='blocking' for i in issues) else 'needs review')
    return document


def prepare(source,pages,sidecar,target):
    source,sidecar,target=[Path(p).resolve() for p in (source,sidecar,target)]
    if not all(allowed(p) for p in (source,sidecar,target)) or not intake_output(target) or sidecar.parent!=target.parent or not source.is_relative_to(target.parent) or sidecar.exists() or target.exists() or sidecar==target or any(p.suffix!='.json' for p in (sidecar,target)):raise ValueError('Fresh distinct project-local sidecar and scaffold beside source tree required')
    if source.suffix.lower()!='.pdf':raise ValueError('Visual transcription currently supports PDF only')
    from pypdf import PdfReader
    reader=PdfReader(source)
    if reader.is_encrypted:raise ValueError('Authorized decrypted PDF required')
    data=dict(schema=SCHEMA,source_sha256=digest(source),pages=pages)
    rows,pins,_=validate(source,sidecar,data,len(reader.pages))
    if not any(row['lines'] for row in rows):raise ValueError('At least one literal source line required')
    sidecar.parent.mkdir(parents=True,exist_ok=True)
    with sidecar.open('x',encoding='utf-8') as stream:json.dump(data,stream,indent=2,ensure_ascii=False,allow_nan=False)
    from .workflow_draft import draft
    result=draft(source,target,ocr=sidecar)
    if any(digest(Path(p))!=sha for p,sha in pins.items()):raise ValueError('Source changed during visual scaffold preparation')
    return dict(status='needs_source_review',sidecar=str(sidecar),plan=str(target),pages=len(rows),lines=sum(len(p['lines']) for p in rows),
        transcription_method='host_visual_transcription',draft=result,source_unchanged=True,design_accepted=False)
