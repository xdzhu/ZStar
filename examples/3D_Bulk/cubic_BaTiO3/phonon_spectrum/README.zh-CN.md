# 立方 BaTiO3：声子能带、声子 DOS 与 NAC

本例在立方 BaTiO3 的 BEC 归档基础上，按需开展有限波矢声子计算。计算采用与
父级 BEC 例子一致的 PBEsol 设置；`run/` 只保留 ABACUS 输入、赝势和轨道，
计算结果统一放在 `results/`。

为控制示例规模，本例明确使用 `2 2 2` 超胞。用户不指定 `--supercell` 时，
ZStar 会在每个周期性方向选择使晶格矢量长度严格大于 10 Angstrom 的对角扩胞；
非周期方向保持为 1。位移由 Phonopy 生成，力常数由 Phonopy 收集，能带路径由
Seekpath 调用 spglib 标准化结构并提供高对称点标签。

## 分步运行

先在当前 Python 环境配置 ABACUS，然后在本目录执行：

```bash
zstar phonon pre --spectrum --stru STRU --input INPUT --root run \
  --supercell "2 2 2" --physical-dim 3
zstar phonon run --root run
zstar phonon post --root run --stru STRU --physical-dim 3
cp ../results/unified/BORN run/BORN
zstar phonon spectrum --root run --nac --band-only --omit-disconnected-tail
```

如需额外生成适合论文正文的仅能带对比图，可使用：

```bash
zstar phonon spectrum --root run --nac --band-only
```

也可以执行 `bash run.sh`。该脚本在隔离的 `work/` 中运行，不修改 `run/` 和
归档结果。`phonon post` 后的 NAC 步骤需要已完成 BEC 计算生成的 BORN；本例
附带的 BORN 仅为复现方便，脚本以普通文件复制，不对密度或 cube 文件建立软链接。

## 输出

当 BORN 存在时，`zstar phonon spectrum` 默认生成三张矢量图。频率轴单位为 THz，
绘图范围设为 `-8` 到 `25 THz`。

| 文件 | 含义 |
| --- | --- |
| `phonon_band_dos_wo_nac.pdf` | 未施加 NAC 的声子能带与 DOS |
| `phonon_band_dos_with_nac.pdf` | 施加三维 bulk NAC 的声子能带与 DOS |
| `phonon_band_dos_nac_comparison.pdf` | 蓝色/红色叠加对比图 |
| `phonon_band_nac_comparison.pdf` | 可选的仅能带蓝色/红色叠加对比图 |

同时输出 PNG 预览、`phonon_spectrum_result.json`、路径标签以及 Phonopy 的
`FORCE_SETS` 和 `phonopy.yaml`。力常数保留在 Phonopy 的 YAML 归档中，以保持
原胞到超胞的映射关系。对比图先绘制蓝色曲线，再绘制红色曲线，未改变的分支
会清楚地重合。

当前 NAC 工作流只对三维 bulk 响应开放。对于 slab、nanowire 或 molecule，
ZStar 会明确报错，而不会套用不适用的三维库仑修正。
