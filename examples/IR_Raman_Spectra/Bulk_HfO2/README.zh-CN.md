# 四方 HfO2：IR 与 Raman

`run/` 使用论文对应的 PBEsol、9 bohr 数值轨道、100 Ry 截断能、
10x10x7 Gamma 中心网格和 `scf_thr 1e-8`。赝势与轨道随案例附带。
`results/` 保存匹配的 BEC、声子、IR/Raman 数据及 `provenance.json`。
更早的输入仅存放在 `legacy/before_20260906/`，不可混入本次结果。

```bash
bash run.sh --dry-run
bash run.sh
```

实际运行读取 ZStar 的软件路径与 MPI/OMP 配置，也可用
`ABACUS_COMMAND`、`PYATB_COMMAND` 和 `OMP_NUM_THREADS` 覆盖。
默认 Unified BEC/力响应需要 4 个位移和 1 个参考态；IR 使用模式有效电荷，
Raman 另外计算 15 个光学模式的正负位移，共 30 个极化率响应任务。
已有谱采用 532 nm 激光和 8 cm-1 展宽。新增计算写入 `work/`，不覆盖结果档案。
