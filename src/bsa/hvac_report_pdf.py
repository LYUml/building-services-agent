"""Paginate the generated HVAC HTML with pinned ReportLab and explicit font."""
from html.parser import HTMLParser
from pathlib import Path
import json
from xml.sax.saxutils import escape
from .cli import digest


class Parser(HTMLParser):
    def __init__(self):
        super().__init__();self.blocks=[];self.tag=None;self.buf=[];self.table=None;self.row=None;self.cell=None
    def handle_starttag(self,tag,attrs):
        if tag=='table':self.table=[]
        elif tag=='tr':self.row=[]
        elif tag in ('th','td'):self.cell=[]
        elif self.table is None and tag in ('h1','h2','p'):self.tag=tag;self.buf=[]
    def handle_data(self,data):
        if self.cell is not None:self.cell.append(data)
        elif self.tag:self.buf.append(data)
    def handle_endtag(self,tag):
        if tag in ('td','th') and self.cell is not None:self.row.append(''.join(self.cell));self.cell=None
        elif tag=='tr':self.table.append(self.row);self.row=None
        elif tag=='table':self.blocks.append(('table',self.table));self.table=None
        elif tag==self.tag:self.blocks.append((tag,''.join(self.buf)));self.tag=None


def verify_report_inputs(report):
    if any(not Path(p).is_file() or digest(Path(p))!=sha for p,sha in report['inputs'].items()):
        raise ValueError('Report source evidence changed')


def run(directory,output,font):
    directory,output,font=map(lambda p:Path(p).resolve(),(directory,output,font))
    if output.exists() or output==directory or output in directory.parents or directory in output.parents or output in font.parents:
        raise ValueError('New PDF directory separate from report and font required')
    source=directory/'HVAC System Design.html';manifest=directory/'report.json'
    report=json.loads(manifest.read_text(encoding='utf-8'))
    if digest(source)!=report['html_sha256']:
        raise ValueError('Report source evidence changed')
    verify_report_inputs(report)
    pins={str(p):digest(p) for p in (source,manifest,font)}
    parser=Parser();parser.feed(source.read_text(encoding='utf-8'))
    review_paragraphs=report.get('adpi_review_summary',[])
    if not isinstance(review_paragraphs,list) or any(not isinstance(p,str) or ('p',p) not in parser.blocks for p in review_paragraphs):
        raise ValueError('ADPI review summary differs from report manifest')
    tables=[v for k,v in parser.blocks if k=='table'];counts=report['counts']
    expected=[counts[k] for k in ('terminal_direction_rows','leaf_groups','duct_sections','requirements')]
    if len(tables)!=6 or [len(t)-1 for t in tables[2:]]!=expected:
        raise ValueError('Report tables do not match manifest counts')
    import reportlab
    if reportlab.Version!='4.4.9':raise ValueError('Pinned ReportLab 4.4.9 required')
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    from reportlab.platypus import SimpleDocTemplate,Paragraph,Spacer,LongTable,TableStyle,CondPageBreak
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.lib.pagesizes import landscape,A4
    from reportlab.lib import colors
    from reportlab.lib.units import mm
    fontname='BsaReport'+pins[str(font)][:12];pdfmetrics.registerFont(TTFont(fontname,str(font)))
    styles=getSampleStyleSheet()
    for style in styles.byName.values():style.fontName=fontname
    styles['BodyText'].fontSize=8;styles['BodyText'].leading=10
    styles['Heading1'].keepWithNext=False;styles['Heading2'].keepWithNext=False
    story=[]
    for kind,value in parser.blocks:
        if kind=='table':
            cols=len(value[0]);widths=[261/cols]*cols
            if value[0][0]=='Input':widths=[40,30,40,151]
            if value[0][0]=='ID' and cols==5:widths=[29,83,22,27,100]
            rows=[[Paragraph(escape(cell),styles['BodyText']) for cell in row] for row in value]
            table=LongTable(rows,colWidths=[w*mm for w in widths],repeatRows=1,hAlign='LEFT')
            table.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),colors.HexColor('#e8f1f3')),('GRID',(0,0),(-1,-1),.3,colors.HexColor('#bbcbd0')),('VALIGN',(0,0),(-1,-1),'TOP'),('TOPPADDING',(0,0),(-1,-1),4),('BOTTOMPADDING',(0,0),(-1,-1),4)]));story.extend([table,Spacer(1,5*mm)])
        else:
            if kind in ('h1','h2'):story.append(CondPageBreak(100*mm))
            style=styles['Heading1' if kind=='h1' else 'Heading2' if kind=='h2' else 'BodyText']
            story.append(Paragraph(escape(value),style));gap=Spacer(1,2*mm);gap.keepWithNext=False;story.append(gap)
    def footer(canvas,doc):
        canvas.setFont(fontname,8);canvas.drawString(18*mm,10*mm,'HVAC System Design | Design study - acceptance pending');canvas.drawRightString(279*mm,10*mm,str(doc.page))
    output.mkdir(parents=True);target=output/'HVAC System Design.pdf'
    SimpleDocTemplate(str(target),pagesize=landscape(A4),leftMargin=18*mm,rightMargin=18*mm,topMargin=15*mm,bottomMargin=18*mm,title='HVAC System Design').build(story,onFirstPage=footer,onLaterPages=footer)
    from pypdf import PdfReader
    pages=PdfReader(target).pages;flat=' '.join(' '.join(p.extract_text() for p in pages).split())
    # Compare every complete numeric row, not just IDs or row totals.
    numeric=[row for table in tables[1:5] for row in table[1:]]
    if any(' '.join(' '.join(row).split()) not in flat for row in numeric):raise ValueError('PDF numerical row missing or changed')
    if any(' '.join(paragraph.split()) not in flat for paragraph in review_paragraphs):raise ValueError('PDF ADPI applicability/evidence paragraph missing or changed')
    if any(digest(Path(p))!=sha for p,sha in pins.items()):raise ValueError('Report/font changed during rendering')
    verify_report_inputs(report)
    result=dict(inputs=pins,pdf_sha256=digest(target),reportlab_version=reportlab.Version,pages=len(pages),numerical_rows_checked=len(numeric),requirement_rows=counts['requirements'],visual_review='pending',design_accepted=False)
    result['adpi_review_paragraphs_checked']=len(review_paragraphs)
    (output/'render.json').write_text(json.dumps(result,indent=2),encoding='utf-8');return result


if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('report_directory');p.add_argument('--out',required=True);p.add_argument('--font',required=True)
    a=p.parse_args();print(run(a.report_directory,a.out,a.font))
