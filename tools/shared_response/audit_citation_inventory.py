"""Check cited BibTeX records and retain their locations and citation purposes."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import re

from pybtex.database import parse_file


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--article", required=True, type=Path)
    args = parser.parse_args()
    article = args.article
    tex = (article / "zstar_CPC-full.tex").read_text(encoding="utf-8")
    bib = parse_file(article / "zstar.bib")
    keys = re.findall(r"\\bibitem(?:\[[^\]]*\])?\{([^}]+)\}",
                      (article / "zstar_CPC-clean.bbl").read_text(encoding="utf-8"))
    records = []
    for number, key in enumerate(keys, 1):
        entry = bib.entries[key]
        locations = []
        for line, text in enumerate(tex.splitlines(), 1):
            if any(key in group.split(",") for group in re.findall(r"\\cite\{([^}]+)\}", text)):
                locations.append({"line": line, "context": text})
        records.append({
            "number": number, "key": key, "type": entry.type,
            "title": entry.fields.get("title"), "year": entry.fields.get("year"),
            "doi": entry.fields.get("doi"), "url": entry.fields.get("url"),
            "authors": [str(person) for person in entry.persons.get("author", [])],
            "editors": [str(person) for person in entry.persons.get("editor", [])],
            "locations": locations,
        })
    missing = [r["key"] for r in records if not r["title"] or not r["url"] or not r["doi"]]
    first_use = []
    for group in re.findall(r"\\cite\{([^}]+)\}", tex):
        first_use.extend(key for key in group.split(",") if key not in first_use)
    output = article / "review_20260907/citation_inventory.json"
    output.write_text(json.dumps({
        "records": records, "missing_title_doi_or_url": missing,
        "bibliography_matches_first_use_order": keys == first_use,
        "scope": "Bibliographic completeness and manuscript citation contexts, not full-text validation."
    }, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps({"cited": len(keys), "missing": missing,
                      "first_use_order_matches": keys == first_use}))


if __name__ == "__main__":
    main()
