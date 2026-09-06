# BEC 与声子效率对照

材料案例按物理维度放入 `3D_Bulk`、`2D_Slab`、`1D_Nanowire` 和
`0D_Molecules`。本目录只保留公共运行工具、计时记录和独立声子对照。
[案例索引](README.md)列出了十个体系的入口；谱学和静电势目录保持不变。

在仓库根目录执行：

```bash
bash examples/3D_Bulk/SiC/run.sh
python examples/Benchmarks/run_control.py SiC --prepare-only
python examples/Benchmarks/verify.py
python examples/3D_Bulk/cubic_BaTiO3/verify.py
```

实际计算需要配置 ABACUS 与 PYATB。离线核验在临时副本中重建 BEC、Gamma
频率和静态响应，不调用 DFT，不覆盖原始结果。每个材料具有独立的 `run/`
输入、`results/` 已有结果，以及执行时建立的 `work/`。

Unified 从同一批位移 SCF 同时获得 BEC 和 Gamma 力常数。Separate 的机时
包含 Cartesian BEC 与另外实际执行的力计算。立方 BTO 历史计时采用 forward，
其他九个体系采用 central；论文参考态表统一列出的 central **准备任务数**
不等于这些任务都已执行，也不用于替换历史 forward 实测分母。

[独立声子档案](independent_phonons/README.md)保留实际力计算证据。计时包括
成功的 ABACUS/PYATB、参考态及能带检查，不包括优化、传输和无完整计时的中断。
历史 BEC 任务中输出力的开销没有扣除。

默认位移为 0.02 bohr，导数使用实际 STRU 差分距离。立方 BTO 不输出稳定的
静态声子介电响应。Gamma 统一框架不能代替完整声子能带或额外的 Raman
极化率导数。历史 `shared_response.json` 等原始文件名、数据键不为美化目录而改写。
