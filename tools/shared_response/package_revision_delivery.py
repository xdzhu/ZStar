"""Package the current source, public examples and matching manuscript without rewriting evidence."""

import argparse
import hashlib
import json
from pathlib import Path
import re
import zipfile


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--article',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--review-id', default='final-review-20260906')
    parser.add_argument('--repo', type=Path, help='Independent source snapshot to package.')
    parser.add_argument('--packages', type=Path)
    parser.add_argument('--audit', type=Path)
    parser.add_argument('--editable', type=Path)
    args=parser.parse_args()
    repo=args.repo or Path(__file__).resolve().parents[2]
    version=re.search(r'^version\s*=\s*"([^"]+)"',(repo/'pyproject.toml').read_text(),re.M)[1]
    candidates={}
    excluded={'__pycache__','.pytest_cache','work','work-vasp','.git','node_modules'}
    for folder in ('zstar','tests','tools','docs','examples','.github'):
        for path in (repo/folder).rglob('*'):
            if not path.is_file() or excluded.intersection(path.relative_to(repo).parts):
                continue
            if path.suffix in {'.pyc','.pyo'} or path.name=='POTCAR':
                continue
            if 'nbse2' in str(path.relative_to(repo)).lower():
                raise ValueError('Internal collaboration data must not enter this delivery')
            if path.is_symlink():
                raise ValueError(f'Package inputs must be real files: {path}')
            candidates['source/'+path.relative_to(repo).as_posix()]=path
    for name in ('pyproject.toml','MANIFEST.in','LICENSE','CHANGELOG.md','CITATION.cff',
                 'README.md','README.zh-CN.md','README_PYPI.md','.gitattributes','.gitignore'):
        candidates['source/'+name]=repo/name
    for path in (args.packages or repo/'dist'/args.review_id).iterdir():
        if path.suffix in {'.whl','.gz'} and (
                path.name.startswith(f'zstar-{version}-') or path.name==f'zstar-{version}.tar.gz'):
            candidates['packages/'+path.name]=path
    text=(args.article/'zstar_CPC-full.tex').read_text(encoding='utf-8')
    figure_names=re.findall(r'\\includegraphics(?:\[[^]]*\])?\{([^}]+)\}',text)
    assert figure_names and all(Path(n).name==n and n.startswith('Figure_') and n.endswith('.pdf') for n in figure_names)
    names=figure_names+['zstar_CPC-full.tex','zstar_CPC-clean.tex','zstar.bib','zstar-elsarticle-num.bst',
                       'zstar_CPC-clean.pdf','zstar_CPC-full.pdf',
                       'zstar_CPC-clean.bbl','zstar_CPC-full.bbl']
    for name in names:
        candidates['manuscript/'+name]=args.article/name
    if args.audit:
        for path in args.audit.rglob('*'):
            if path.is_file():
                candidates['audit/'+path.relative_to(args.audit).as_posix()]=path
    for path in (args.editable or args.article/'editable_figures'/args.review_id.replace('-','_')).glob('*'):
        if not path.is_file() or path.suffix not in {'.pptx','.pdf','.mjs','.ps1','.md'}:
            continue
        candidates['editable_figures/'+path.name]=path
    for name,path in candidates.items():
        if not path.is_file():
            raise FileNotFoundError(path)
    args.output.parent.mkdir(parents=True,exist_ok=True)
    if args.output.exists():
        raise FileExistsError(args.output)
    manifest={}
    with zipfile.ZipFile(args.output,'w',zipfile.ZIP_DEFLATED,compresslevel=6) as archive:
        for name,path in sorted(candidates.items()):
            data=path.read_bytes()
            manifest[name]={'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest()}
            entry=zipfile.ZipInfo(name)
            entry.create_system=3
            entry.external_attr=(0o100755 if path.suffix=='.sh' else 0o100644)<<16
            entry.compress_type=zipfile.ZIP_DEFLATED
            archive.writestr(entry,data)
        readme=f'''# ZStar {version}: annotated manuscript candidate

## Start

- Install `packages/zstar-{version}-py3-none-any.whl` with pip, or run `pip install .` in `source/`.
- Read `source/README.md` or `source/README.zh-CN.md`; matching PDFs are under `source/docs/`.
- Each public case has its own run/results contract. Start with its README and `bash run.sh --dry-run`.
- External DFT programs are not bundled. VASP licensed inputs remain user-supplied.
- The wheel and sdist intentionally exclude examples; this complete delivery includes them separately.

## Manuscript

The clean and blue-revision PDFs have matching content. Figures use PDF basenames beside the TeX source.
Compile from `manuscript/` with `latexmk -pdf zstar_CPC-clean.tex`.
Figure 1 has an editable PowerPoint with optional assets on slide 2 and awaits author artwork approval.
Figure 2 and the accepted remaining artwork are preserved.
This is not a claim of completed journal submission, a public tag, or a PyPI upload.

## 核验与使用

先阅读各案例的 README：离线复算与重新运行 DFT 是不同操作，原始结果不应覆盖。
所有文件的 SHA256 均记录在 `SHA256.json`。执行 `python verify_delivery.py` 核验解压内容。
论文保留作者确认的结构布局；图 1 提供可继续修改的原生 PPTX，第二页为备选示意素材。
'''
        verify='''import hashlib,json\nfrom pathlib import Path\nroot=Path(__file__).resolve().parent\nrows=json.loads((root/'SHA256.json').read_text())\nfor name,row in rows.items():\n p=root/name\n assert p.is_file(),name\n assert hashlib.sha256(p.read_bytes()).hexdigest()==row['sha256'],name\nprint(f'Verified {len(rows)} files')\n'''
        archive.writestr('START_HERE.md',readme)
        archive.writestr('verify_delivery.py',verify)
        archive.writestr('SHA256.json',json.dumps(manifest,indent=2))
    # Verify bytes inside the archive, not merely file existence.
    with zipfile.ZipFile(args.output) as archive:
        assert archive.testzip() is None
        for name,row in manifest.items():
            assert hashlib.sha256(archive.read(name)).hexdigest()==row['sha256'],name
    checksum=hashlib.sha256(args.output.read_bytes()).hexdigest()
    args.output.with_suffix('.zip.sha256').write_text(checksum+'  '+args.output.name+'\n')
    print(json.dumps({'archive':str(args.output),'files':len(manifest),'bytes':args.output.stat().st_size,
                      'sha256':checksum},indent=2))


if __name__=='__main__':
    main()
