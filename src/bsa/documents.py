"""Read-only document extraction with source locators and explicit coverage gaps."""
from pathlib import Path
import zipfile
import xml.etree.ElementTree as ET
from .engine import ProjectError

W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"


def text_rows(text, extra=None):
    rows, parts, start = [], [], None
    for n, line in enumerate(text.splitlines() + [""], 1):
        if line.strip():
            if start is None:
                start = n
            parts.append(line)
        elif start is not None:
            rows.append(dict(start_line=start, end_line=n-1,
                             text="\n".join(parts), **(extra or {})))
            start, parts = None, []
    return rows


def extract(path, ocr_path=None):
    path = Path(path)
    suffix = path.suffix.lower()
    rows, issues = [], []

    def issue(code, message, severity="review", **locator):
        issues.append(dict(id=f"I{len(issues)+1:03}", code=code,
                           severity=severity, message=message, locator=locator))

    if suffix in (".md", ".txt"):
        rows = text_rows(path.read_text(encoding="utf-8-sig"))
    elif suffix == ".pdf":
        try:
            from pypdf import PdfReader
        except ImportError:
            raise ProjectError('PDF intake requires pip install -e ".[documents]"')
        reader = PdfReader(path)
        if reader.is_encrypted:
            raise ProjectError("encrypted PDF: supply an authorized decrypted working copy")
        for page_no, page in enumerate(reader.pages, 1):
            value = page.extract_text() or ""
            if not value.strip():
                content=page.get_contents()
                if (content is None or not content.get_data().strip()) and not page.get('/Annots'):
                    issue('blank_page','Empty page content stream and no annotations; confirm blank page in rendered source',page=page_no)
                else:
                    issue("no_text", "No extractable text; OCR or source inspection required before planning",
                          "blocking", page=page_no)
            else:
                rows.extend(text_rows(value, {"page": page_no}))
            issue("pdf_layout", "Review rendering for reading order, tables, equations, figures and drawing notes",
                  page=page_no)
            if page.get("/Annots"):
                issue("pdf_annotations", "Annotations or form widgets may contain additional requirements",
                      page=page_no)
    elif suffix == ".docx":
        try:
            with zipfile.ZipFile(path) as package:
                names = package.namelist()
                if len(names) > 5000 or sum(i.file_size for i in package.infolist()) > 100_000_000:
                    raise ProjectError("DOCX package exceeds intake limits")
                if "word/document.xml" not in names:
                    raise ProjectError("missing Word main document")
                parts = ["word/document.xml"] + sorted(
                    n for n in names if n.startswith("word/") and n.endswith(".xml")
                    and (Path(n).name.startswith(("header", "footer"))
                         or Path(n).name in ("footnotes.xml", "endnotes.xml", "comments.xml")))
                block = 0
                for part in parts:
                    tree = ET.fromstring(package.read(part))
                    if any(e.tag in (W+"ins", W+"del", W+"moveFrom", W+"moveTo") for e in tree.iter()):
                        issue("tracked_changes", "Resolve tracked changes in an authorized working copy before planning",
                              "blocking", part=part)
                    if any(e.tag in (W+"drawing", W+"pict", W+"object", W+"altChunk") for e in tree.iter()):
                        issue("embedded_content", "Drawings, text boxes, objects or external content need rendered inspection",
                              part=part)
                    if any(e.tag in (W+"fldChar", W+"instrText") for e in tree.iter()):
                        issue("fields", "Field text may contain stale cached results", part=part)
                    if any('officeDocument/2006/math' in e.tag for e in tree.iter()):
                        issue("equations", "OMML equations are not transcribed; inspect and record their requirements", part=part)
                    if any(e.tag == W+'numPr' for e in tree.iter()):
                        issue("numbering", "Automatic numbering is not resolved into paragraph text", part=part)

                    def walk(node, location):
                        nonlocal block
                        if node.tag == W+"p":
                            segments = []
                            def paragraph_content(element):
                                # Nested text-box paragraphs get their own source locator.
                                for child in element:
                                    if child.tag == W+'p':
                                        continue
                                    yield child
                                    yield from paragraph_content(child)

                            for element in paragraph_content(node):
                                if element.tag in (W+"t", W+"delText"):
                                    segments.append(element.text or "")
                                elif element.tag == W+"tab":
                                    segments.append("\t")
                                elif element.tag in (W+"br", W+"cr"):
                                    segments.append("\n")
                            value = "".join(segments).strip()
                            if value:
                                block += 1
                                rows.append(dict(text=value, part=part, xml_path=location, block_index=block))
                        counters = {}
                        for child in node:
                            name = child.tag.rsplit("}", 1)[-1]
                            counters[name] = counters.get(name, 0)+1
                            walk(child, f"{location}/{name}[{counters[name]}]")

                    walk(tree, "/"+tree.tag.rsplit("}", 1)[-1])
                if any(n.startswith("word/media/") for n in names):
                    issue("media", "Verify that extracted text covers figure requirements")
                if any(n.startswith(("word/charts/", "word/diagrams/")) for n in names):
                    issue("charts", "Chart/diagram data is not interpreted by this extractor")
                issue("word_layout", "Review rendering for numbering, table relationships, pagination and equations; XML locators are not page numbers")
        except (zipfile.BadZipFile, ET.ParseError) as exc:
            raise ProjectError(f"invalid DOCX: {exc}")
    else:
        raise ProjectError("supported brief formats: Markdown, text, PDF and DOCX")
    if not rows and not any(i["severity"] == "blocking" for i in issues):
        issue("empty", "No source text extracted", "blocking")
    for i, row in enumerate(rows, 1):
        row["id"] = f"P{i:03}"
    result = dict(format=suffix.lstrip("."), extractor_version="2", passages=rows,
                issues=issues, coverage_status="blocked" if any(i["severity"] == "blocking" for i in issues)
                else "needs review" if issues else "text extracted")
    if suffix == '.pdf':result['page_count'] = len(reader.pages)
    return apply_ocr(result, path, ocr_path) if ocr_path else result


def apply_ocr(document, source, sidecar):
    import json
    import math
    from .cli import digest
    if document['format'] != 'pdf':raise ProjectError('OCR sidecars are supported for PDF only')
    sidecar = Path(sidecar).resolve()
    data = json.loads(sidecar.read_text(encoding='utf-8'))
    if data.get('schema')=='bsa.visual-transcription/1':
        from .visual_transcription import apply
        return apply(document,source,sidecar)
    if data.get('version') != 1 or data.get('source_sha256') != digest(source):
        raise ProjectError('OCR sidecar version/source hash mismatch')
    pages = data.get('pages')
    if not isinstance(pages, list):raise ProjectError('OCR page list required')
    seen, supplements, supporting = set(), [], [str(sidecar)]
    missing = {i['locator']['page'] for i in document['issues'] if i['code'] == 'no_text'}
    filled = set()
    for page in pages:
        n = page.get('page')
        if type(n) is not int or n < 1 or n > document['page_count'] or n in seen:
            raise ProjectError('invalid or duplicate OCR page')
        seen.add(n)
        image = (sidecar.parent/page.get('image', '')).resolve()
        if not image.is_relative_to(sidecar.parent) or not image.is_file() or digest(image) != page.get('image_sha256'):
            raise ProjectError('OCR page image missing, escaped or changed')
        supporting.append(str(image))
        lines = page.get('lines')
        if not isinstance(lines, list):raise ProjectError('OCR lines required')
        for index, line in enumerate(lines, 1):
            text, score, box = line.get('text'), line.get('confidence'), line.get('box')
            if not isinstance(text, str) or not text.strip():raise ProjectError('nonempty OCR text required')
            if type(score) not in (int, float) or not math.isfinite(score) or not 0 <= score <= 1:
                raise ProjectError('invalid OCR confidence')
            if not isinstance(box, list) or len(box) != 4 or any(
                    not isinstance(point, list) or len(point) != 2 or any(
                        type(v) not in (int, float) or not math.isfinite(v) for v in point) for point in box):
                raise ProjectError('OCR quadrilateral coordinates required')
            if n in missing:
                supplements.append(dict(text=text, page=n, ocr_line=index, confidence=score,
                                        pixel_box=box, image_sha256=page['image_sha256'],
                                        ocr_sidecar_sha256=digest(sidecar)))
                filled.add(n)
    if seen != set(range(1, document['page_count']+1)):
        raise ProjectError('OCR sidecar must account for every PDF page')
    issues = [i for i in document['issues'] if not (i['code'] == 'no_text' and i['locator']['page'] in filled)]
    for n in sorted(filled):
        issues.append(dict(code='ocr_review', severity='review', locator={'page':n},
                           message='Check each OCR line, symbol, decimal and unit against the rendered page; confidence is not correctness'))
    for i, issue in enumerate(issues, 1):issue['id'] = f'I{i:03}'
    rows = sorted(document['passages']+supplements, key=lambda r:r['page'])
    for i, row in enumerate(rows, 1):row['id'] = f'P{i:03}'
    document.update(passages=rows, issues=issues, supporting_files=supporting,
                    coverage_status='blocked' if any(i['severity']=='blocking' for i in issues) else 'needs review')
    return document


def check_review(document, review):
    blockers = [i for i in document["issues"] if i["severity"] == "blocking"]
    if blockers:
        raise ProjectError("document extraction blocked: "+"; ".join(i["message"] for i in blockers))
    if not isinstance(review, dict):
        raise ProjectError("document_review must map issue IDs to review notes")
    expected = {i["id"] for i in document["issues"]}
    if set(review) != expected or any(not isinstance(v, str) or not v.strip() for v in review.values()):
        raise ProjectError("each extraction issue needs an explicit source-inspection note")
