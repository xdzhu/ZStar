"""Verify the tested local integration snapshot and record exact source hashes."""
import hashlib
import json
from pathlib import Path
import re

repo=Path(__file__).resolve().parents[2]
out=repo/'docs/research/unified_spectroscopy_20260906'
digest=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
summary=json.loads((out/'summary.json').read_text())
for name,sha in summary['source_sha256'].items():
    assert digest(Path(name))==sha, name
for name,sha in summary['analysis_code_sha256'].items():
    assert digest(Path(__file__).parent/name)==sha, name
for row in summary['records']:
    assert row['parallelism_matched'] and row['Raman_extra_SCF_unified']==0
    assert abs(row['full_core_h_old']/row['full_core_h_unified']-row['assembled_speedup'])<1e-12
article=Path('D:/Work/Zstar/zstar-article')
tex=(article/'zstar_CPC-full.tex').read_text(encoding='utf-8')
assert tex.index('\\subsection{\\textcolor{blue}{Infrared and Raman spectra}}') < tex.index('\\subsection{\\textcolor{blue}{Efficiency benchmark of ZStar}}')
assert digest(article/'Figure_2_BEC_physical_picture.pdf')==digest(article/'annotated/final_review_20260906/original_figures/Figure_2_BEC_physical_picture.pdf')
from tools.shared_response.bibliography_labels import bibliography_labels
numbers=bibliography_labels(article/'zstar_CPC-clean.bbl')
assert numbers==json.loads((repo/'docs/paper_figures/reference_numbers.json').read_text())
for name in ('clean','full'):
    log=(article/f'zstar_CPC-{name}.log').read_text(errors='replace')
    assert not re.search(r'(Citation|Reference).*undefined|There were undefined|multiply defined',log)
files=sorted(p for p in (repo/'zstar').rglob('*') if p.is_file() and p.suffix in ('.py','.md','.json'))
files += [repo/'pyproject.toml',repo/'README.md',repo/'README.zh-CN.md',repo/'README_PYPI.md']
files += sorted(p for p in (repo/'tests').glob('test_*raman*.py'))
files += [repo/'docs/unified_spectroscopy.md',repo/'docs/unified_spectroscopy.zh-CN.md']
record=dict(scope='Local 0.3.0rc5 source snapshot with Unified spectroscopy integration; not uploaded',
    source_sha256={p.relative_to(repo).as_posix():digest(p) for p in files},
    manuscript_sha256={name:digest(article/name) for name in ('zstar_CPC-full.tex','zstar_CPC-clean.pdf','zstar_CPC-full.pdf','Figure_1_ZStar_workflow.pdf','Figure_2_BEC_physical_picture.pdf')},
    tests=388,subtests=66,real_cli_case='CH4 on cu26; run and resume',
    offline_run_sh_cases=['Bulk_HfO2','2D_MoS2','Nanowire_Sb2S3','Molecule_CH4'],
    bibliography_numbers=len(numbers),cost_records=summary['records'])
(out/'integration_checksums.json').write_text(json.dumps(record,indent=2)+'\n')
print('Source, costs, restored Figure 2, bibliography labels and LaTeX references verified.')
