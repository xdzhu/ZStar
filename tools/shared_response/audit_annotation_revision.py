"""Check PDF-comment extraction and protected manuscript content after revision."""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import re
import xml.etree.ElementTree as ET

from pypdf import PdfReader
import pymupdf as fitz


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def compact(text):
    return re.sub(r"\s+", "", text)


def extract_region(tex, start, end):
    return tex.split(start, 1)[1].split(end, 1)[0]


def audit(article):
    work = article / "review_20260907"
    inventory = json.loads((work / "annotations.json").read_text(encoding="utf-8"))
    source = Path(inventory["source"])
    reader = PdfReader(source)
    counts = Counter()
    comments = {}
    for page in reader.pages:
        for reference in page.get("/Annots", []):
            annotation = reference.get_object()
            kind = annotation.get("/Subtype")
            counts[kind] += 1
            if kind != "/Highlight":
                continue
            rich = annotation.get("/RC")
            text = "".join(ET.fromstring(str(rich)).itertext())
            comments[reference.idnum] = text
    matches = [{
        "id": row["id"], "page": row["page"], "xref": row["xref"],
        "rich_text_matches": compact(comments.get(row["xref"], ""))
        == compact(row["info"]["content"]),
    } for row in inventory["annotations"]]
    tex = (article / "zstar_CPC-full.tex").read_text(encoding="utf-8")
    before = (work / "before/zstar_CPC-full.tex").read_text(encoding="utf-8")
    abstract = lambda s: extract_region(s, r"\begin{abstract}", r"\end{abstract}")
    body = re.sub(r"\\begin\{figure\*?\}.*?\\end\{figure\*?\}", "", tex, flags=re.S)
    panel_sets = {
        "fig:bulk_bec_structures": "ab",
        "fig:two_dimensional_bec_structures": "ab",
        "fig:one_dimensional_bec_structures": "ab",
        "fig:molecular_apt_structures": "ab",
        "fig:dielectric_response_examples": "abcd",
        "fig:cross_dimensional_spectroscopy": "abcdefghijkl",
        "fig:potential_examples": "abcdef",
    }
    missing = [f"{key}({panel})" for key, panels in panel_sets.items()
               for panel in panels if rf"\ref{{{key}}}({panel})" not in body]
    spectroscopy = extract_region(
        body, r"\subsection{\textcolor{blue}{Infrared and Raman spectra}}",
        r"\subsection{\textcolor{blue}{Efficiency benchmark of ZStar}}")
    prose = re.sub(r"\\(?:begingroup|endgroup|FloatBarrier|color\{blue\})", "", spectroscopy)
    paragraphs = [p.strip() for p in re.split(r"\n\s*\n", prose) if p.strip()]
    row_checks = {}
    for key in ("tab:unified_efficiency", "tab:unified_spectra_efficiency"):
        rows = lambda s: extract_region(
            extract_region(s, rf"\label{{{key}}}", r"\end{table}"),
            r"\midrule", r"\bottomrule").strip()
        row_checks[key] = rows(tex) == rows(before)
    logs = {}
    for name in ("clean", "full"):
        log = (article / f"zstar_CPC-{name}.log").read_text(errors="replace")
        logs[name] = {
            "errors": re.findall(
                r"^!.*|.*(?:There were undefined|multiply defined|end occurred inside a group).*",
                log, re.M),
            "overfull": re.findall(r"^Overfull.*", log, re.M),
        }
    labels = set(re.findall(r"\\label\{([^}]+)\}", tex))
    labels.update(re.findall(r"label=\{([^}]+)\}", tex))
    refs = set(re.findall(r"\\(?:eqref|ref)\{([^}]+)\}", tex))
    result = {
        "source_sha256": digest(source),
        "source_unchanged": digest(source) == inventory["sha256"],
        "independent_pdf_object_counts": dict(counts),
        "annotation_crosscheck": matches,
        "comments_complete": len(comments) == len(matches) == 16
        and all(row["rich_text_matches"] for row in matches),
        "abstract_unchanged": abstract(tex) == abstract(before),
        "missing_subpanel_references": missing,
        "spectroscopy_paragraphs": len(paragraphs),
        "benchmark_rows_unchanged": row_checks,
        "undefined_tex_labels": sorted(refs - labels),
        "logs": logs,
        "manuscript_sha256": digest(article / "zstar_CPC-full.tex"),
        "pdf_sha256": {name: digest(article / f"zstar_CPC-{name}.pdf")
                       for name in ("clean", "full")},
    }
    result["passed"] = all((
        result["source_unchanged"], result["comments_complete"],
        result["abstract_unchanged"], not missing, len(paragraphs) == 6,
        all(row_checks.values()), not result["undefined_tex_labels"],
        all(not value["errors"] for value in logs.values()),
    ))
    return result


def render(article):
    output = article / "review_20260907/rendered"
    output.mkdir(parents=True, exist_ok=True)
    doc = fitz.open(article / "zstar_CPC-clean.pdf")
    for index, page in enumerate(doc):
        page.get_pixmap(matrix=fitz.Matrix(1.5, 1.5)).save(output / f"page-{index+1:02d}.png")
    for start in range(0, len(doc), 12):
        sheet = fitz.open()
        page = sheet.new_page(width=1200, height=1600)
        for pos, index in enumerate(range(start, min(start + 12, len(doc)))):
            col, row = pos % 3, pos // 3
            rect = fitz.Rect(col * 400, row * 400 + 20, (col + 1) * 400, (row + 1) * 400)
            page.show_pdf_page(rect, doc, index)
            page.insert_text((col * 400 + 10, row * 400 + 15), f"Page {index+1}", fontsize=12)
        page.get_pixmap().save(output / f"sheet-{start//12+1}.png")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--article", required=True, type=Path)
    parser.add_argument("--render", action="store_true")
    args = parser.parse_args()
    result = audit(args.article)
    output = args.article / "review_20260907/revision_audit.json"
    output.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
    if args.render:
        render(args.article)
    print(json.dumps(result, indent=2, ensure_ascii=False))
    raise SystemExit(0 if result["passed"] else 1)


if __name__ == "__main__":
    main()
