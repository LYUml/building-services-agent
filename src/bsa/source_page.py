"""Source-preserving PDF page rasterization for actual host visual review."""
import json
from pathlib import Path
from .cli import digest
from .workspace import allowed,intake_output
from .ocr import render_pdf_page


def run(source,page,out,*,renderer=None,max_side=2048):
    from PIL import Image
    from pypdf import PdfReader
    source,out=Path(source).resolve(),Path(out).resolve()
    if not allowed(source) or not intake_output(out) or source.suffix.lower()!='.pdf' or not source.is_file():raise ValueError('Existing project PDF and selected output workspace required')
    if type(page) is not int or page<1 or type(max_side) is not int or not 512<=max_side<=2560:raise ValueError('One-based page and bounded 512..2560 pixel side required')
    if out.exists() or out==source or out in source.parents:raise ValueError('Fresh preview output separate from source required')
    if renderer is None or not Path(renderer).is_file():raise ValueError('Host Poppler pdftoppm runtime required; no page rendered')
    executable=Path(renderer).resolve();before={str(p):digest(p) for p in (source,executable,Path(__file__).resolve())}
    from . import ocr
    before[str(Path(ocr.__file__).resolve())]=digest(Path(ocr.__file__))
    reader=PdfReader(source)
    if reader.is_encrypted:raise ValueError('Authorized decrypted PDF required')
    if page>len(reader.pages):raise ValueError('Page exceeds actual source PDF page count')
    box=reader.pages[page-1].mediabox
    page_points=[float(box.width),float(box.height)]
    out.mkdir(parents=True)
    image=render_pdf_page(source,out/'page',executable,page,max_side=max_side)
    with Image.open(image) as rendered:
        size=list(rendered.size);rendered.verify()
    if min(size)<=0 or max(size)>max_side:raise ValueError('Rendered page violates requested pixel bound')
    if any(not Path(p).is_file() or digest(Path(p))!=sha for p,sha in before.items()):raise ValueError('PDF source or renderer changed during rendering')
    result=dict(schema='bsa.source-page/1',source=str(source),source_sha256=before[str(source)],page=page,page_count=len(reader.pages),
        media_box_pdf_units=page_points,pdf_user_unit=reader.pages[page-1].user_unit,page_rotation=reader.pages[page-1].rotation,render_policy='Full source MediaBox with native rotation; fit within maximum pixel side, not an engineering plot scale',
        max_side_px=max_side,image='page.png',image_sha256=digest(image),image_size_px=size,inputs=before,
        source_unchanged=True,visual_review='not_performed_by_renderer',extraction_review_cleared=False,design_accepted=False)
    (out/'page.json').write_text(json.dumps(result,indent=2),encoding='utf-8');return result
