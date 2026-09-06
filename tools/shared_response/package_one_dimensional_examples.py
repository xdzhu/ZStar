"""Build self-contained examples from hash-verified, completed evidence archives."""

import argparse
import hashlib
import json
from pathlib import Path
import shutil
import tarfile

from ase import Atoms
from ase.io import write
from zstar.shared_response import read_structure

NAMES = {'BN_6_0': 'Nanotube_BN_6_0', 'BN_9_0': 'Nanotube_BN_9_0',
         'Sb2S3': 'Nanowire_Sb2S3'}


def build(root, repo, name):
    evidence = root / name / 'evidence'
    archive = root / f'{name}-evidence.tar.gz'
    with tarfile.open(archive) as tar:
        manifest = json.load(tar.extractfile('evidence_manifest.json'))
        for row in manifest['files']:
            member = tar.getmember(row['path'])
            if not member.isfile() or member.issym():
                raise ValueError('Evidence contains a nonregular file')
            data = tar.extractfile(member).read()
            if hashlib.sha256(data).hexdigest() != row['sha256']:
                raise ValueError(f'Archive checksum mismatch: {row["path"]}')
            local = evidence / row['path']
            if not local.is_file() or hashlib.sha256(local.read_bytes()).hexdigest() != row['sha256']:
                raise ValueError(f'Extracted evidence mismatch: {row["path"]}')
    target = repo / 'examples/IR_Raman_Spectra' / NAMES[name]
    target.mkdir(exist_ok=False)
    shutil.copytree(evidence / 'response-seed', target / 'run')
    shutil.copytree(evidence / 'seed', target / 'run/relaxation')
    for folder in [target / 'run', target / 'run/relaxation']:
        atoms = read_structure(folder / 'STRU')
        write(folder / 'structure.vasp', Atoms(symbols=atoms.symbols, cell=atoms.cell,
              scaled_positions=atoms.scaled_positions, pbc=True), format='vasp', direct=True)
    results = target / 'results'
    results.mkdir()
    for name_out, source in [('IR', 'ir'), ('Raman', 'raman_spectrum')]:
        shutil.copytree(evidence / source, results / name_out)
    from zstar.artifacts import resolve_artifact
    for name_out in ['BEC.dat', 'BEC.raw.dat', 'BORN', 'FORCE_CONSTANTS', 'FORCE_CONSTANTS.raw',
                     'qpoints.yaml', 'phonopy.yaml', 'irreps.yaml', 'response.json',
                     'response_fit.json', 'shared_response.json', 'STRU']:
        shutil.copy2(resolve_artifact(evidence / 'unified' / name_out, explicit=False), results / name_out)
    for name_out in ['relaxation-audit.json', 'rigid-mode-audit.json']:
        shutil.copy2(evidence / name_out, results / name_out)
    shutil.copy2(archive, results / 'native_evidence.tar.gz')
    comparison = root / name / 'comparison'
    if comparison.exists():
        shutil.copytree(comparison, results / 'comparison')
    if name == 'Sb2S3':
        reference = root / 'reference/Sb2S3'
        shutil.copytree(reference / 'B3LYP-D3', results / 'reference/B3LYP-D3')
        shutil.copytree(reference / 'extracted', results / 'reference/extracted')
    times = []
    for path in [evidence / 'unified/component_times.jsonl',
                 *sorted((evidence / 'raman').glob('part-*/component_times.jsonl'))]:
        stage = 'response' if 'unified' in path.parts else 'raman'
        times.extend({**json.loads(line), 'stage': stage} for line in path.read_text().splitlines())
    costs = {stage: {kind: sum(t['allocated_core_hours'] for t in times
                              if t['stage'] == stage and t['kind'] == kind)
                     for kind in ['ABACUS', 'PYATB', 'preparation']}
             for stage in ['response', 'raman']}
    relaxation = json.loads((evidence / 'relaxation-audit.json').read_text())
    costs['relaxation_core_hours'] = relaxation['relaxation_core_hours']
    costs['interruption_caveat'] = ('cu20 reboot interrupted one PYATB call; its elapsed cost is unrecorded. '
                                   'Listed totals cover completed calls, not the full billed total.'
                                   if name == 'BN_9_0' else 'No interrupted call recorded.')
    (results / 'compute_costs.json').write_text(json.dumps(costs, indent=2) + '\n')
    gap = json.loads((evidence / 'unified/0.no-move/zstar_insulation.json').read_text())['gap_eV']
    modes = json.loads((evidence / 'rigid-mode-audit.json').read_text())
    optical = [x for x in modes if not x['classified_rigid']]
    xc = 'PBE-D3(BJ)' if name == 'Sb2S3' else 'PBE'
    label = 'Sb2S3 isolated full chain' if name == 'Sb2S3' else f'BN({6 if name == "BN_6_0" else 9},0) nanotube'
    warning = ('Raman relative intensities differ substantially from the B3LYP-D3(BJ) reference; '
               'this is not quantitative intensity validation. The reference 31.5762 cm^-1 mode '
               'has about 98.3% axial-rotation overlap and remains in its original curve.'
               if name == 'Sb2S3' else
               'Literature uses different functionals and screened electronic responses. '
               'Frequency agreement does not establish absolute Raman-intensity accuracy; '
               'transverse depolarization effects require particular care.')
    (target / 'run.sh').write_text('''#!/usr/bin/env bash
set -euo pipefail
ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
REPO=$(cd "$ROOT/../../.." && pwd)
export PYTHONPATH="$REPO${PYTHONPATH:+:$PYTHONPATH}"
exec python "$REPO/tools/shared_response/run_one_dimensional_example.py" --case "$ROOT" "$@"
''', newline='\n')
    text = f'''# {label}

ABACUS + PYATB, {xc}, `dim=1`, periodic z. No hydrogen passivation.
The structure is centered in the transverse xy cell. `structure.vasp` is a
visualization/exchange file, not a VASP calculation input for this example.

## Run

Use the complete ZStar repository and a Python environment with ZStar's
dependencies, ABACUS, PYATB and `pyatb_input`. From this directory:

```bash
bash run.sh --dry-run
export OMP_NUM_THREADS=1
export ABACUS_COMMAND="mpirun -np 40 abacus"
export PYATB_COMMAND="mpirun -np 40 pyatb"
bash run.sh
```

Replace executable names/launchers with your installation. The example runner
uses these environment variables or `--abacus-command`/`--pyatb-command`; it does
not read scheduler headers. Scheduler directives and module activation belong
in your own parent job script. Recorded production used ABACUS 1 MPI x 40 OMP
and PYATB 40 MPI x 1 OMP, so the above convenient launch layout is not a timing
benchmark reproduction. Native PYATB capability detection is retained.

`--stage response` stops after BEC and Gamma phonons; `--stage raman` resumes
IR/Raman preparation and calculation after response; `--stage post` recollects
completed Raman data. `--work /path/to/new-work` selects a separate workspace.
Repeating the command resumes native completed stages. Inputs must remain
unchanged for a given work directory. No file in `run/` or `results/` is modified.

## Files and Settings

- `run/`: optimized reference STRU, SCF INPUT/KPT, pseudopotentials and orbitals.
- `run/relaxation/`: original clean optimization inputs, with private `assets/`.
- `results/`: BEC, raw/projected force constants, Gamma eigenvectors, IR/Raman,
  diagnostics, costs and a hash-manifested compact native evidence archive.
- `work/`: generated by `run.sh`; reference, displacements and Raman calculations.

To repeat optimization separately, copy `run/relaxation/` to an empty working
directory and run ABACUS there. Require an explicit geometry convergence message
and converged forces/stress; recenter xy before using a new optimized structure.
Default `run.sh` intentionally starts from the supplied optimized geometry.

The response ensemble uses Phonopy displacements of 0.02 bohr (approximately
0.010584 Angstrom), actual structure differences for reconstruction, SCF threshold
1e-8, and axial k sampling 1 x 1 x 12. The reference must pass the insulating
check and a 0.005 eV/Angstrom force-norm gate. Raman uses explicit +/- normal-mode
displacements, amplitude 0.02 Angstrom sqrt(amu), 298 K, 532 nm and Lorentzian
FWHM 8 cm^-1. Three translations and axial rigid rotation are identified from
mass-weighted eigenvector overlaps, not removed through arbitrary peak fitting.

## Recorded Results

From the repository root, perform read-only tensor/spectrum reconstruction and
native archive checksum verification, without a DFT executable:

```bash
python -m tools.shared_response.verify_one_dimensional_example --case examples/IR_Raman_Spectra/{NAMES[name]} --verify-archive
```

Band gap: {gap:.3f} eV. Positive nonrigid Gamma modes: {len(optical)};
lowest {min(x['frequency_cm1'] for x in optical):.2f} cm^-1.
This is a Gamma spectroscopy calculation, not a full phonon-band stability test.

`BEC.dat` and `response.json` use rows `Z[displacement,polarization]`.
The reconstruction record `response_fit.json` uses
`Z[polarization,displacement]`; inspect each file's convention before conversion.
Units are e. The 1D dielectric output is a line
polarizability under the stated source-field convention, not a bulk permittivity.
Raman line-polarizability derivatives use the Gaussian normalization A/(4*pi).

{warning}

See `compute_costs.json` for separate ABACUS/PYATB and optimization core-hours.
{costs['interruption_caveat']}

## References

- Wirtz et al., lattice dynamics and selection rules, ABINIT/LDA:
  https://doi.org/10.1103/PhysRevB.68.045425
- Wirtz et al., BN Raman spectra, including (9,0):
  https://doi.org/10.1103/PhysRevB.71.241402
- Erba et al., CRYSTAL/B3LYP BN frequencies, Table I includes (6,0):
  https://doi.org/10.1063/1.4788831
- For Sb2S3 only: G. Ulian's public CRYSTAL/B3LYP-D3(BJ) full-chain dataset,
  CC BY 4.0, https://doi.org/10.17632/6tntvw37tr.1 .

Original journal PDFs are not redistributed. Comparative curves are not shifted
or fitted. Included pseudopotential/orbital files retain their original contents;
their upstream notices and licenses remain applicable.
'''
    (target / 'README.md').write_text(text)
    (target / 'README.zh-CN.md').write_text(f'''# {label}

采用 ABACUS + PYATB，{xc} 泛函，`dim=1`，z 方向周期；不需要氢钝化。
结构主体已平移到 xy 横截面中心。`structure.vasp` 用于 VESTA 等结构查看工具，
不表示此案例使用 VASP 计算。

## 快速复算

保留完整 ZStar 仓库，激活包含依赖与 PYATB 的 Python 环境，并配置 ABACUS。

```bash
bash run.sh --dry-run
export OMP_NUM_THREADS=1
export ABACUS_COMMAND="mpirun -np 40 abacus"
export PYATB_COMMAND="mpirun -np 40 pyatb"
bash run.sh
```

软件路径、MPI 命令按本地环境替换。脚本使用上述环境变量或同名命令行参数；
队列头与 module 放在外层作业脚本中。原始生产任务采用 ABACUS 1 MPI x 40 OMP、
PYATB 40 MPI x 1 OMP，因此示范启动配置不是严格机时 benchmark 的相同并行配置。

`run/` 仅保存优化后的输入、赝势与轨道；`run/relaxation/` 保留原始结构优化输入。
`results/` 保存已有结果、诊断和带哈希的原始证据包；新计算输出到 `work/`。
默认从优化好的结构开始，避免无意覆盖输入和参考结果。需要重新优化时，将
`run/relaxation/` 复制到新工作目录再运行 ABACUS，检查几何收敛、力和轴向应力，
并将优化后的结构重新居中。再次运行脚本会复用已完成阶段。

可使用 `--stage response` 仅计算 BEC 和 Gamma 声子，`--stage raman` 继续谱学，
`--stage post` 重做已有 Raman 后处理，或用 `--work` 指定新目录。

## 结果边界

band gap 为 {gap:.3f} eV；有 {len(optical)} 个正频率非刚体 Gamma 模式，最低
{min(x['frequency_cm1'] for x in optical):.2f} cm^-1。这不是全布里渊区稳定性验证。
三个位移刚体模和一个轴向刚体转动模按本征向量识别，不任意删峰或平移峰位。
一维响应报告线极化率，不把含真空的超胞介电常数称为纳米线本征介电常数。

不同泛函、电子响应近似和横向去极化处理会影响文献比较；频率接近不等于
Raman 绝对强度已验证。Sb2S3 的 Raman 相对强度与 B3LYP-D3(BJ) 参考明显不同，
不能宣称定量吻合。BN(9,0) 曾遇 cu20 重启，计时表不包含无法追回的中断损耗。
详细参数、单位、文献 DOI 和比较限制见英文 README 与结果元数据。
''', encoding='utf-8')
    print(target)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('campaign_root', type=Path)
    parser.add_argument('--repo', type=Path, default=Path.cwd())
    parser.add_argument('--case', choices=list(NAMES), required=True)
    args = parser.parse_args()
    build(args.campaign_root, args.repo, args.case)
