"""Create an isolated clean manuscript candidate without changing artwork."""

import argparse
import hashlib
import json
from pathlib import Path
import re
import shutil
import zipfile


parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('article', type=Path)
parser.add_argument('output', type=Path)
parser.add_argument('--bbl', type=Path, required=True,
                    help='Bibliography from the matching clean manuscript build.')
parser.add_argument('--version', required=True, help='Version of the accompanying source snapshot.')
args = parser.parse_args()
source = args.article/'zstar_CPC-full.tex'
text = source.read_text(encoding='utf-8')
figures = re.findall(r'\\includegraphics(?:\[[^]]*\])?\{([^}]+)\}', text)
assert figures and len(set(figures)) == len(figures), figures
assert all(Path(f).name == f and f.startswith('Figure_') and f.endswith('.pdf') for f in figures)
if not args.bbl.is_file():
    raise FileNotFoundError(args.bbl)
args.output.mkdir(parents=True, exist_ok=False)
(args.output/'zstar_CPC.tex').write_text('\\def\\ZStarClean{1}\n'+text, encoding='utf-8')
for name in [*figures, 'zstar.bib', 'zstar-elsarticle-num.bst']:
    shutil.copy2(args.article/name, args.output/name)
shutil.copy2(args.bbl, args.output/'zstar_CPC.bbl')
(args.output/'BUILD.md').write_text(
    f'# ZStar CPC candidate {args.version}\n\n'
    'Compile with `latexmk -pdf zstar_CPC.tex`. All figure paths are basenames.\n\n'
    'This is a submission candidate, not a record of journal submission.\n'
    'Figures 1 and 2 describe the current Unified framework; editable PowerPoint\n'
    'sources accompany the complete delivery. Packaging does not modify artwork.\n', encoding='utf-8')
hashes = {p.name: hashlib.sha256(p.read_bytes()).hexdigest()
          for p in sorted(args.output.iterdir()) if p.is_file()}
(args.output/'SHA256.json').write_text(json.dumps(hashes, indent=2)+'\n', encoding='utf-8')
archive_path = args.output.with_name(args.output.name + '.zip')
with zipfile.ZipFile(archive_path, 'w', zipfile.ZIP_DEFLATED) as archive:
    for path in sorted(args.output.iterdir()):
        archive.write(path, path.name)
print(archive_path)
