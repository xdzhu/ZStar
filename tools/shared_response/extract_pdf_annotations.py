"""Retain annotation text, selected words and popup links without editing a PDF."""
from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from pathlib import Path

import pymupdf as fitz


def extract(source: Path) -> dict:
    doc = fitz.open(source)
    rows = []
    raw_annotations = []
    for page in doc:
        raw_annotations.extend(
            {"page": page.number + 1, "xref": xref, "type": kind, "name": name}
            for xref, kind, name in page.annot_xrefs()
        )
        for annot in page.annots() or []:
            vertices = annot.vertices or []
            quads = [fitz.Quad(vertices[i:i + 4]) for i in range(0, len(vertices), 4)]
            words = page.get_text("words", sort=True)
            selected = []
            for word in words:
                box = fitz.Rect(word[:4])
                center = (box.tl + box.br) / 2
                if any(q.rect.contains(center) for q in quads):
                    selected.append(word[4])
            rows.append({
                "id": f"A{len(rows) + 1:02d}", "page": page.number + 1,
                "xref": annot.xref, "type": annot.type[1],
                "info": annot.info, "selected_text": " ".join(selected),
                "rect": list(annot.rect), "vertices": vertices,
                "popup_xref": annot.popup_xref,
                "raw_object": doc.xref_object(annot.xref),
                "popup_object": doc.xref_object(annot.popup_xref) if annot.popup_xref else None,
            })
    return {
        "source": str(source), "sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
        "pages": len(doc), "annotations": rows, "raw_annotations": raw_annotations,
        "counts": dict(Counter(a["type"] for a in rows)),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    result = extract(args.source)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
    lines = ["# PDF annotation inventory", "", f"Source SHA256: `{result['sha256']}`", ""]
    for row in result["annotations"]:
        lines += [f"## {row['id']} / page {row['page']} / xref {row['xref']}", "",
                  row["info"]["content"], "", "Selected: " + row["selected_text"], ""]
    args.output.with_suffix(".md").write_text("\n".join(lines), encoding="utf-8")
    print(json.dumps({"counts": result["counts"], "raw_objects": len(result["raw_annotations"]),
                      "output": str(args.output)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
