# 有限波矢声子能带与 NAC

Unified BEC 流程已经提供 Gamma 点力常数和可供 Phonopy 使用的 `BORN` 文件。
需要有限波矢声子能带和声子 DOS 时，使用 `zstar phonon spectrum`。这是一条
独立的扩胞声子计算流程，不会重复 Unified Gamma 点 BEC 的自洽计算。

## 工作流

准备包含 `STRU`、`KPT`、带有 `cal_force 1` 的 ABACUS 输入文件以及 ABACUS 赝势和轨道的
目录。默认输入文件名为 `INPUT`，也可以显式指定用户自己的 CPU 或 GPU 输入文件：

```bash
zstar phonon pre --spectrum --root . --stru STRU --input INPUT --physical-dim 3
zstar phonon run --root .
zstar phonon stat --root .
zstar phonon post --root . --stru STRU --physical-dim 3
```

`--input` 不会改写或规范化源文件，只会在每个位移目录中将选定文件作为
`INPUT` 使用，因此 GPU 版 `ks_solver` 等计算器相关设置仍完全由用户控制。
输入文件必须打开 `cal_force 1`，因为后续需要由 Phonopy 收集力。

对于三维 bulk，通常建议设置 `OMP_NUM_THREADS=1`，并将可用 CPU 核心尽量分配给
MPI ranks。低维体系或分子则可能更适合较少 MPI ranks、更多 OpenMP 线程。
ZStar 不强制固定组合，具体资源由用户的作业头文件和执行配置决定。

不指定 `--supercell` 时，每个周期性晶格矢量会自动扩展到长度严格大于
10 Angstrom。需要显式指定时，例如使用 `--supercell "2 2 2"`。Seekpath 负责生成
标准化高对称路径，标签使用 spglib 的对称性数据。

对于极性三维体材料，将 `zstar bec post` 产生的 `BORN` 复制到声子目录，然后执行：

```bash
cp path/to/bec/BORN .
zstar phonon spectrum --root . --nac
```

如需额外生成适合正文排版、只包含两组能带的紧凑对比图，可添加：

```bash
zstar phonon spectrum --root . --nac --band-only
```

如果自动路径的末尾包含与主路径不连续的分支，可以添加
`--omit-disconnected-tail` 去掉这个尾段。该选项适合突出 LO-TO 劈裂的图，
默认不启用：

```bash
zstar phonon spectrum --root . --nac --band-only --omit-disconnected-tail
```

默认生成三张矢量图。声子频率轴使用 Phonopy 归档的原生单位 THz。绘图范围固定为
`-8` 到 `25 THz`，这样既能显示较小的虚频，又不会让图面过于紧凑。

| 文件 | 内容 |
| --- | --- |
| `phonon_band_dos_wo_nac.pdf` | 未加非解析修正的声子能带与 DOS |
| `phonon_band_dos_with_nac.pdf` | 加入体材料 NAC 的声子能带与 DOS |
| `phonon_band_dos_nac_comparison.pdf` | 蓝红叠加对比图 |
| `phonon_band_nac_comparison.pdf` | 可选的仅能带蓝红叠加对比图 |

PDF 同目录还会写出 PNG 预览和 `phonon_spectrum_result.json`。JSON 记录标准化
空间群、路径标签、q 点路径、DOS 网格和输出文件名。`--no-nac` 只生成未修正图。
NAC 仅对具有匹配 `BORN` 文件的三维体材料启用，不把三维 bulk 近似用于二维、
纳米线或分子。

## 随包案例

完整的 cubic BaTiO3 案例位于
`examples/3D_Bulk/cubic_BaTiO3/phonon_spectrum/`。其中 `run/` 是干净的输入目录，
`results/` 保存经过验证的归档和图，`run.sh` 会在隔离的工作目录中执行同样的步骤。
