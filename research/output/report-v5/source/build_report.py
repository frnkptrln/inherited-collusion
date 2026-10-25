#!/usr/bin/env python3
"""Fill the retained official DOCX; require explicit completeness for final builds.

Use the bundled workspace Python. Preserve existing template parts except the
document body and the minimal relationships/content types needed for new figures.
"""
from __future__ import annotations

import argparse
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys
from zipfile import ZipFile

from lxml import etree as ET

BUILD = Path(__file__).resolve().parent
REFERENCE = BUILD / "official-template.docx"
REFERENCE_SHA = "59537583d295f683fe069b96030a3a56ebadb0387733308cdb926f25bf4b082c"
NS = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
W = "{" + NS["w"] + "}"
XML_SPACE = "{http://www.w3.org/XML/1998/namespace}space"
REL_NS = "http://schemas.openxmlformats.org/package/2006/relationships"
DOC_REL_NS = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
DRAW_NS = "http://schemas.openxmlformats.org/drawingml/2006/main"
PIC_NS = "http://schemas.openxmlformats.org/drawingml/2006/picture"
WP_NS = "http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing"
CT_NS = "http://schemas.openxmlformats.org/package/2006/content-types"


def elem(tag, **attrs):
    return ET.Element(W + tag, {W + k: str(v) for k, v in attrs.items()})


def child(parent, tag, **attrs):
    node = elem(tag, **attrs)
    parent.append(node)
    return node


def prop(parent, tag, **attrs):
    node = parent.find("w:" + tag, NS)
    if node is None:
        node = child(parent, tag)
    for k, v in attrs.items():
        node.set(W + k, str(v))
    return node


def scrub_ids(node):
    for el in node.iter():
        for key in list(el.attrib):
            if ET.QName(key).localname in {"paraId", "textId"}:
                del el.attrib[key]
    for el in node.xpath(".//w:bookmarkStart | .//w:bookmarkEnd", namespaces=NS):
        el.getparent().remove(el)


def make_p(pattern, text, *, bold=False, center=False, size=None, after=None, before=None, keep=False):
    p = deepcopy(pattern)
    scrub_ids(p)
    for node in list(p):
        if node.tag != W + "pPr":
            p.remove(node)
    pp = prop(p, "pPr")
    for node in list(pp):
        if node.tag in {W + "numPr", W + "pageBreakBefore"}:
            pp.remove(node)
    if center:
        prop(pp, "jc", val="center")
    if after is not None or before is not None:
        spacing = prop(pp, "spacing")
        if after is not None:
            spacing.set(W + "after", str(int(after * 20)))
        if before is not None:
            spacing.set(W + "before", str(int(before * 20)))
    if keep:
        prop(pp, "keepNext", val="1")
    r = child(p, "r")
    rp = child(r, "rPr")
    child(rp, "rFonts", ascii="Old Standard TT", hAnsi="Old Standard TT", cs="Old Standard TT")
    if bold:
        child(rp, "b", val="1")
    if size is not None:
        child(rp, "sz", val=int(size * 2))
        child(rp, "szCs", val=int(size * 2))
    child(rp, "color", val="000000")
    for i, line in enumerate(str(text).split("\n")):
        if i:
            child(r, "br")
        t = child(r, "t")
        t.set(XML_SPACE, "preserve")
        t.text = line
    return p


def make_table(body_pattern, headers, rows, widths=None):
    widths = widths or [9360 // len(headers)] * len(headers)
    if len(widths) != len(headers) or sum(widths) > 9360:
        raise ValueError("Invalid table widths")
    t = elem("tbl")
    tp = child(t, "tblPr")
    child(tp, "tblW", w=sum(widths), type="dxa")
    child(tp, "tblLayout", type="fixed")
    borders = child(tp, "tblBorders")
    for edge in ("top", "left", "bottom", "right", "insideH", "insideV"):
        child(borders, edge, val="single", sz="4", color="D9D9D9")
    margins = child(tp, "tblCellMar")
    for edge in ("top", "left", "bottom", "right"):
        child(margins, edge, w=80, type="dxa")
    grid = child(t, "tblGrid")
    for width in widths:
        child(grid, "gridCol", w=width)
    for ri, values in enumerate([headers] + rows):
        if len(values) != len(headers):
            raise ValueError("Non-rectangular table")
        tr = child(t, "tr")
        trp = child(tr, "trPr")
        child(trp, "cantSplit", val="1")
        if ri == 0:
            child(trp, "tblHeader", val="1")
        for width, value in zip(widths, values):
            tc = child(tr, "tc")
            tcp = child(tc, "tcPr")
            child(tcp, "tcW", w=width, type="dxa")
            child(tcp, "vAlign", val="center")
            if ri == 0:
                child(tcp, "shd", val="clear", fill="EDEDED")
            p = make_p(body_pattern, value, bold=ri == 0, size=10, after=2)
            prop(prop(p, "pPr"), "spacing", line="252", lineRule="auto")
            # Keep short evidence tables together; long matrices may split with
            # their header repeated, without splitting individual rows.
            if len(rows) <= 4 and ri < len(rows):
                prop(prop(p, "pPr"), "keepNext", val="1")
            tc.append(p)
    return t


def picture_paragraph(body_pattern, rid, index, image_data, width_inches, alt):
    from io import BytesIO
    from PIL import Image
    with Image.open(BytesIO(image_data)) as im:
        width, height = im.size
        if im.format != "PNG":
            raise ValueError("Scientific figures must be retained PNG files")
    if not 1 <= width_inches <= 6.5:
        raise ValueError("Figure must fit template text width")
    cx = round(width_inches * 914400)
    cy = round(cx * height / width)
    p = make_p(body_pattern, "", center=True, after=3, before=4, keep=True)
    run = p.find("w:r", NS)
    drawing = child(run, "drawing")
    inline = ET.SubElement(drawing, "{" + WP_NS + "}inline", distT="0", distB="0", distL="0", distR="0")
    ET.SubElement(inline, "{" + WP_NS + "}extent", cx=str(cx), cy=str(cy))
    ET.SubElement(inline, "{" + WP_NS + "}docPr", id=str(index), name=f"Figure {index}", descr=alt)
    lock = ET.SubElement(inline, "{" + WP_NS + "}cNvGraphicFramePr")
    ET.SubElement(lock, "{" + DRAW_NS + "}graphicFrameLocks", noChangeAspect="1")
    graphic = ET.SubElement(inline, "{" + DRAW_NS + "}graphic")
    data = ET.SubElement(graphic, "{" + DRAW_NS + "}graphicData", uri=PIC_NS)
    pic = ET.SubElement(data, "{" + PIC_NS + "}pic")
    nonvisual = ET.SubElement(pic, "{" + PIC_NS + "}nvPicPr")
    ET.SubElement(nonvisual, "{" + PIC_NS + "}cNvPr", id="0", name=f"v4-figure-{index}.png", descr=alt)
    ET.SubElement(nonvisual, "{" + PIC_NS + "}cNvPicPr")
    fill = ET.SubElement(pic, "{" + PIC_NS + "}blipFill")
    ET.SubElement(fill, "{" + DRAW_NS + "}blip", {"{" + DOC_REL_NS + "}embed": rid})
    stretch = ET.SubElement(fill, "{" + DRAW_NS + "}stretch")
    ET.SubElement(stretch, "{" + DRAW_NS + "}fillRect")
    shape = ET.SubElement(pic, "{" + PIC_NS + "}spPr")
    transform = ET.SubElement(shape, "{" + DRAW_NS + "}xfrm")
    ET.SubElement(transform, "{" + DRAW_NS + "}off", x="0", y="0")
    ET.SubElement(transform, "{" + DRAW_NS + "}ext", cx=str(cx), cy=str(cy))
    geometry = ET.SubElement(shape, "{" + DRAW_NS + "}prstGeom", prst="rect")
    ET.SubElement(geometry, "{" + DRAW_NS + "}avLst")
    return p


def development_rows(spec, project_root):
    rows, provenance = [], []
    for run in spec.get("development_runs", []):
        path = Path(run["path"])
        if not path.is_absolute():
            path = project_root / path
        manifest = json.loads((path / "manifest.json").read_text())
        if manifest["config"]["backend"] != "hf":
            raise ValueError("Mock run cannot be development model evidence")
        gates = list((path / "gates").glob("*-probes.json"))
        parts = [r for p in gates for r in json.loads(p.read_text())["rows"]]
        task = [r for r in parts if r["kind"] == "comprehension"]
        note = [r for r in parts if r["kind"].startswith("note_")]
        summary = json.loads((path / "summary.json").read_text())
        responses = [json.loads(p.read_text()) for p in sorted((path / "calls").glob("*/response.json"))]
        model_labels = {
            "Qwen/Qwen3-235B-A22B-Instruct-2507": "235B Instruct",
            "Qwen/Qwen3-235B-A22B-Thinking-2507": "235B Thinking",
            "Qwen/Qwen3.6-35B-A3B": "3.6-35B-A3B",
        }
        requested = manifest["config"]["model"]
        reported = sorted({r.get("model", "absent") for r in responses})
        rows.append([run["label"], model_labels.get(requested, requested), ", ".join(model_labels.get(m, m) for m in reported), f"{sum(r['passed'] for r in task)}/{len(task)}", f"{sum(r['passed'] for r in note)}/{len(note)}", str(summary["episodes"])])
        provenance.append({"path": run["path"], "source_hash": manifest["source_hash"], "requested_model": requested, "reported_models": reported, "calls": len(responses), "summary_sha256": hashlib.sha256((path / "summary.json").read_bytes()).hexdigest()})
    return rows, provenance


def build(spec, output, draft, project_root, artifact_root=None):
    artifact_root = artifact_root or project_root
    for item in spec.get("evidence_inputs", []):
        path = Path(item["path"])
        if not path.is_absolute():
            path = project_root / path
        if hashlib.sha256(path.read_bytes()).hexdigest() != item["sha256"]:
            raise ValueError(f"Evidence input changed: {path}")
    for item in spec.get("supplementary_inputs", []):
        path = BUILD / item["path"]
        if hashlib.sha256(path.read_bytes()).hexdigest() != item["sha256"]:
            raise ValueError(f"Supplementary report input changed: {path}")
    source = REFERENCE.read_bytes()
    if hashlib.sha256(source).hexdigest() != REFERENCE_SHA:
        raise ValueError("Retained official template changed")
    def text_values(value):
        if isinstance(value, str):
            yield value
        elif isinstance(value, dict):
            for item in value.values():
                yield from text_values(item)
        elif isinstance(value, list):
            for item in value:
                yield from text_values(item)
    serialized = "\n".join(text_values(spec))
    if not draft:
        if spec.get("ready_for_final") is not True:
            raise ValueError("Input has not been marked ready_for_final")
        if re.search(r"\b(PENDING|TODO|TBD)\b|\[\[", serialized):
            raise ValueError("Final report still contains unresolved placeholders")
        wc = len(spec["abstract"].split())
        if not 150 <= wc <= 250:
            raise ValueError(f"Abstract has {wc} words; expected 150-250")
    with ZipFile(REFERENCE) as z:
        replacements, additions, figure_evidence = {}, {}, []
        rel_name = "word/_rels/document.xml.rels"
        relationships = ET.fromstring(z.read(rel_name))
        content_types = ET.fromstring(z.read("[Content_Types].xml"))
        existing_rids = {r.get("Id") for r in relationships}
        doc = ET.fromstring(z.read("word/document.xml"))
        body = doc.find("w:body", NS)
        body_ps = body.findall("w:p", NS)
        body_pattern = next(p for p in body_ps if "What problem" in "".join(p.xpath(".//w:t/text()", namespaces=NS)))
        heading_pattern = next(p for p in body_ps if "1. Introduction" in "".join(p.xpath(".//w:t/text()", namespaces=NS)))
        sub_pattern = next(p for p in body_ps if "Limitations" == "".join(p.xpath(".//w:t/text()", namespaces=NS)))
        section = deepcopy(body.find("w:sectPr", NS))
        original_title_table = body.find("w:tbl", NS)
        title_table = deepcopy(original_title_table)
        for tr in title_table.findall("w:tr", NS)[1:]:
            title_table.remove(tr)
        row = title_table.find("w:tr", NS)
        rp = row.find("w:trPr", NS)
        if rp is not None:
            for fixed in rp.findall("w:trHeight", NS):
                rp.remove(fixed)
        cell = row.find("w:tc", NS)
        title_pattern = next(p for p in cell.findall("w:p", NS) if "PROJECT TITLE" in "".join(p.xpath(".//w:t/text()", namespaces=NS)))
        footnote_runs = [deepcopy(r) for r in title_pattern.findall("w:r", NS) if r.find("w:footnoteReference", NS) is not None]
        title = make_p(title_pattern, spec["title"], bold=True, center=True, size=20, before=8, after=8)
        for r in footnote_runs:
            title.append(r)
        for p in list(cell):
            if p.tag != W + "tcPr":
                cell.remove(p)
        cell.append(title)
        scrub_ids(title_table)
        for node in list(body):
            body.remove(node)
        body.append(title_table)
        body.append(make_p(body_pattern, spec["author"], center=True, size=11, before=8, after=0))
        body.append(make_p(body_pattern, spec["affiliation"], center=True, size=11, after=8))
        if spec.get("subtitle"):
            body.append(make_p(body_pattern, spec["subtitle"], center=True, size=11, after=8))
        body.append(make_p(body_pattern, "Abstract", bold=True, center=True, size=14, after=6))
        body.append(make_p(body_pattern, spec["abstract"], after=8))
        if draft:
            body.append(make_p(body_pattern, "Internal working draft. Results fields remain pending; this file is not a submission.", bold=True, after=8))
        dev_rows, provenance = development_rows(spec, project_root)
        pending_page_break = False
        for block in spec["blocks"]:
            kind = block["type"]
            if kind == "page_break":
                pending_page_break = True
                continue
            first_new_index = len(body)
            if kind in {"p", "caption"}:
                body.append(make_p(body_pattern, block["text"], bold=kind == "caption", after=block.get("after", 6), keep=kind == "caption"))
            elif kind == "heading":
                pattern = heading_pattern if block.get("level", 2) == 2 else sub_pattern
                body.append(make_p(pattern, block["text"], bold=True, size=14 if block.get("level", 2) == 2 else 13, before=10, after=4, keep=True))
            elif kind == "table":
                body.append(make_table(body_pattern, block["headers"], block["rows"], block.get("widths")))
                body.append(make_p(body_pattern, "", after=3))
            elif kind == "figure":
                path = Path(block["path"])
                if not path.is_absolute():
                    path = artifact_root / path
                image_data = path.read_bytes()
                sha = hashlib.sha256(image_data).hexdigest()
                if sha != block["sha256"]:
                    raise ValueError(f"Figure evidence changed: {path}")
                index = len(figure_evidence) + 1
                rid = f"rIdV4Figure{index}"
                if rid in existing_rids:
                    raise ValueError("New image relationship collides with retained template")
                name = f"word/media/v4-figure-{index}.png"
                if name in z.namelist():
                    raise ValueError("New media collides with retained template")
                ET.SubElement(relationships, "{" + REL_NS + "}Relationship", Id=rid,
                              Type=DOC_REL_NS + "/image", Target=f"media/v4-figure-{index}.png")
                additions[name] = image_data
                figure_evidence.append({"path": block["path"], "sha256": sha, "part": name})
                body.append(picture_paragraph(body_pattern, rid, index, image_data,
                                              block.get("width_inches", 6.5), block.get("alt", block["caption"])))
                body.append(make_p(body_pattern, block["caption"], size=10, after=6))
            elif kind == "development_table":
                body.append(make_table(body_pattern, ["Run", "Requested model", "Reported model", "Task", "Note", "Successor episodes"], dev_rows, [900, 2400, 2400, 700, 700, 2260]))
                body.append(make_p(body_pattern, "", after=3))
            else:
                raise ValueError(f"Unknown block type {kind}")
            if pending_page_break:
                first = body[first_new_index]
                first_p = first if first.tag == W + "p" else first.find(".//w:p", NS)
                if first_p is None:
                    raise ValueError("Page break has no following paragraph")
                prop(prop(first_p, "pPr"), "pageBreakBefore", val="1")
                pending_page_break = False
        body.append(section)
        xml = ET.tostring(doc, xml_declaration=True, encoding="UTF-8", standalone=True)
        replacements["word/document.xml"] = xml
        if figure_evidence:
            replacements[rel_name] = ET.tostring(relationships, xml_declaration=True, encoding="UTF-8", standalone=True)
            if not any(item.get("Extension", "").lower() == "png" for item in content_types):
                ET.SubElement(content_types, "{" + CT_NS + "}Default", Extension="png", ContentType="image/png")
                replacements["[Content_Types].xml"] = ET.tostring(content_types, xml_declaration=True, encoding="UTF-8", standalone=True)
        output.parent.mkdir(parents=True, exist_ok=True)
        if output.resolve() == REFERENCE.resolve():
            raise ValueError("Never overwrite the reference")
        with ZipFile(output, "w") as zout:
            for info in z.infolist():
                zout.writestr(info, replacements.get(info.filename, z.read(info.filename)))
            for name, data in additions.items():
                zout.writestr(name, data)
    with ZipFile(REFERENCE) as a, ZipFile(output) as b:
        changed = [n for n in a.namelist() if a.read(n) != b.read(n)]
        if set(changed) != set(replacements):
            raise ValueError(f"Unexpected package mutations: {changed}")
        if set(b.namelist()) - set(a.namelist()) != set(additions):
            raise ValueError("Unexpected new template package parts")
    audit = {"draft": draft, "source_sha256": REFERENCE_SHA, "changed_parts": changed, "added_parts": list(additions), "figures": figure_evidence, "author": spec["author"], "development_evidence": provenance, "abstract_words": len(spec["abstract"].split()), "rendered": False, "evidence_inputs": spec.get("evidence_inputs", []), "phase": spec.get("phase"), "supplementary_inputs": spec.get("supplementary_inputs", []), "posthoc_review": spec.get("posthoc_review")}
    output.with_suffix(".audit.json").write_text(json.dumps(audit, indent=2) + "\n")
    return audit


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", type=Path, default=BUILD / "report-input.json")
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--draft", action="store_true")
    ap.add_argument("--render", action="store_true")
    ap.add_argument("--project-root", type=Path, default=BUILD.parents[2] if len(BUILD.parents) > 2 else Path.cwd(), help="Root containing the saved runs/ directory")
    ap.add_argument("--artifact-root", type=Path, help="Root containing the relative output/ figure assets; defaults to project root")
    ap.add_argument("--renderer", type=Path, help="Optional path to Documents skill render_docx.py")
    args = ap.parse_args()
    spec = json.loads(args.input.read_text())
    audit = build(spec, args.out, args.draft, args.project_root.resolve(), args.artifact_root.resolve() if args.artifact_root else None)
    audit.update(input_sha256=hashlib.sha256(args.input.read_bytes()).hexdigest(),
                 builder_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                 follow_up=spec.get("follow_up"))
    if args.render:
        if args.renderer is None or not args.renderer.is_file():
            raise ValueError("--render requires --renderer /path/to/render_docx.py; otherwise export the DOCX with a local office suite")
        render_dir = args.out.parent / (args.out.stem + "-render")
        subprocess.run([sys.executable, str(args.renderer), str(args.out), "--output_dir", str(render_dir), "--emit_pdf"], check=True)
        from pypdf import PdfReader
        pdf = render_dir / (args.out.stem + ".pdf")
        pages = PdfReader(pdf).pages
        refs = next((i for i, p in enumerate(pages) if re.match(r"\s*References\b", p.extract_text() or "")), None)
        audit.update(rendered=True, pdf=str(pdf), pages=len(pages), main_pages=refs, visual_review_required=True)
        if refs is not None and refs > 8:
            raise ValueError(f"Main text is {refs} pages; maximum is 8")
        args.out.with_suffix(".audit.json").write_text(json.dumps(audit, indent=2) + "\n")
    args.out.with_suffix(".audit.json").write_text(json.dumps(audit, indent=2) + "\n")
    print(json.dumps(audit, indent=2))


if __name__ == "__main__":
    main()
