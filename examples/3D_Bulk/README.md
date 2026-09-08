# Bulk BEC examples / 三维体材料

Each case keeps clean inputs in `run/`, retained evidence in `results/`, and
an executable `run.sh`. Read its README before starting a calculation.
各案例的 `run/` 为干净输入，`results/` 为已有结果；请在案例目录执行 `bash run.sh`。

| Case | Purpose / 用途 |
|---|---|
| [cubic_BaTiO3](cubic_BaTiO3/) | Cubic PBEsol Unified/Separate efficiency benchmark / 立方相效率对照 |
| [BaTiO3](BaTiO3/) | Archived tetragonal PBEsol BEC tensors / 四方相张量 |
| [BaTiO3_cubic](BaTiO3_cubic/) | Earlier cubic preparation example / 早期立方相输入 |
| [HfO2](HfO2/) | Tetragonal PBEsol BEC and dielectric results / BEC 与介电结果 |
| [t_HfO2](t_HfO2/) | Matched Unified/Separate benchmark / 同设置效率对照 |
| [SiC](SiC/) | 3C-SiC PBE Unified/Separate benchmark / 统一框架对照 |

Different structures and calculation settings are deliberately kept separate.
不同晶相或参数的案例不会合并结果。[Efficiency index / 效率索引](../Benchmarks/README.md)。
