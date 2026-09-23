# SiC BEC 位移幅度收敛性

该案例使用 `run/` 中随案例提供的两原子 SiC 输入，将 `--displacement` 依次设为
0.005、0.010、0.015、0.020、0.025 和 0.030 Angstrom。各点均使用对称性适配的
Unified 位移集合，并以写入 `STRU` 的真实位移向量重建响应。流程保留绝缘性
检查，但不计算与 BEC 收敛无关的电子介电张量。

```bash
bash run.sh
python analyze.py
```

235 的 PBS 环境可直接运行 `bash run_pbs.sh`。`ZSTAR_CONVERGENCE_ROOT` 可指定
求解器输出位置；`bash run.sh --dry-run` 只准备并检查六个任务。

分析结果写入 `results/SiC_displacement_convergence.csv` 及对应 PDF/PNG 图，
并给出 Si 对角 BEC 平均值和相对于 0.010 Angstrom 结果的最大张量差异。

## 保留结果

在完整的 0.005--0.030 Angstrom 扫描中，对称性投影后的 Si 响应保持在
`2.70024--2.70097 e`。相对于 0.010 Angstrom 结果的最大分量差异为
`7.30e-4 e`，约占 BEC 大小的 `0.027%`；C 张量与之等大反向。JSON 结果以
小数点后八位保留每个位移量对应的完整张量。
