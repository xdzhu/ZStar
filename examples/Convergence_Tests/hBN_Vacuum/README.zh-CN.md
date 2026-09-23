# 单层 hBN BEC 真空尺寸收敛性

该案例将垂直胞长 `Lz` 依次设为 15、20、30 和 40 Angstrom，并保持 hBN 位于
分数坐标 `z=0.5`。面内晶格、k 点密度、赝势和轨道均由 `run/` 中随案例提供的
输入固定。流程保留绝缘性检查，但不计算电子介电张量。

```bash
bash run.sh
python analyze.py
```

235 的 PBS 环境可直接运行 `bash run_pbs.sh`。分析比较面内与面外 BEC，而不
比较随真空体积稀释的原始超胞介电常数。精简结果保存在
`results/hBN_vacuum_convergence.csv` 及对应 PDF/PNG 图中。

## 保留结果

在 15--40 Angstrom 范围内，B 原子的面内响应展宽仅为 `1.41e-5 e`。面外
响应则由 15 Angstrom 时的 `0.36355 e` 降至 40 Angstrom 时的 `0.33607 e`，
其中 30 到 40 Angstrom 仍相差 `0.00520 e`。因此该扫描明确展示了不同张量
分量应分别判断收敛性，而不把 40 Angstrom 的面外值宣称为精确的无限真空
极限。JSON 结果保留了全部张量分量。
