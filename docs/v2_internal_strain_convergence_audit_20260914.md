# ZStar v2 internal-strain 收敛审计（2026-09-14）

本审计用于判断 wurtzite AlN/ZnO 的 internal-strain 残差究竟来自对称算法还是
strained-cell 离子收敛。它不修改 raw 张量，不通过调大 `symprec` 获得通过状态；
所有空间群、原子映射和响应基底固定使用 `symprec=1e-3`。

## AlN 已完成结果

参考结构复用 HF Slurm job `27678427`（node148）；12 个 `±1e-3` 工程应变结构在
job `27682276`（node268，32 MPI × 1 OMP，非独占）中用 `scf_thr=1e-8`、
`force_thr_ev=1e-5 eV/Å` 重新弛豫。每个 strained geometry 随后只运行一次 PYATB，
同一次结果提供三个极化方向。12 个 stage 的最终最大力范围为
`1.079e-6`--`9.276e-6 eV/Å`。

| 诊断 | 原 `force_thr_ev=1e-3` | 新 `force_thr_ev=1e-5` | 结论 |
|---|---:|---:|---|
| proper symmetry projection relative | 1.888e-4 | 3.496e-4 | 通过 1e-3 gate |
| elastic symmetry projection relative | 2.351e-4 | 9.304e-5 | 通过 |
| Gamma symmetry projection relative | 1.441e-4 | 1.441e-4 | 不受 relaxed displacement 变化影响，保持通过 |
| internal-strain symmetry projection relative | 3.194e-2 | 4.153e-4 | 从违例恢复到允许子空间 |
| internal-displacement raw fit relative | 1.088e-2 | 2.592e-2 | 未收敛为更小值，需幅度审计 |

新 proper 主要分量为 `e31=-0.69308/-0.69280 C/m²`、
`e33=1.69613 C/m²`、`e15=-0.3740 C/m²`；由同一 `C^E` 得
`d31=-2.664/-2.662 pm/V`、`d33=6.363 pm/V`、`d15=-3.33 pm/V`。
弹性矩阵保持正定，最小特征值 `112.246 GPa`。

结论是：此前 3.19% 的 internal-strain 对称违例主要是 strained-stage 离子收敛
误差，并非共同不变度量表示或 `symprec` 造成；但 `±1e-3` 的 raw 位移响应仍存在
2.59% 拟合残差，必须通过第二应变幅度或逐对 `+/-` 反对称性审计判断是有限差分
非线性还是剩余数值噪声。

本次新计算（不计复用 reference）ABACUS wall-time 求和 `2763 s`，PYATB
wall-time 求和 `263 s`，按 32 核计约 `26.90 core-hours`。包含复用 reference 的
归档 runtime 求和为 `3075 s`、约 `27.33 core-hours`。

## ZnO 已完成同阈值审计，但仍为 conditional

ZnO 使用 235 上由用户 PBS 占位作业保留的 cu24、cu25、cu26。占位状态不是资源
冲突；启动前检查实际进程和负载，每个节点只允许一个 40 MPI × 1 OMP ABACUS。
12 个 strained stage 使用 `scf_thr=1e-8`、`force_thr_ev=1e-5 eV/Å`，分片为：

* cu24：`strain-002+`, `strain-003-`, `strain-003+`；
* cu25：`strain-004-`, `strain-004+`, `strain-005-`；
* cu26：`strain-005+`, `strain-006-`, `strain-006+`；
* cu17 先前已完成 `strain-001-`, `strain-001+`, `strain-002-`，现已退出该 root。

每个完成的 ABACUS stage 后只生成并运行一次 PYATB 三方向极化；13 个 stage 和
13 个 PYATB 输出现已重收集。最初的临时 PYATB 调用误将 Zn/O 的 `valence_e`
写为 `12 6`，该批输出已经隔离为无效数据，**没有进入任何张量**；保留的 ABACUS
输出不受此错误影响，随后只重跑了 PYATB，使用 Dojo Zn/O 的正确 `20 6` 价电子数。

| 诊断 | `force_thr_ev=1e-5` 结果 | 结论 |
|---|---:|---|
| proper symmetry projection relative | `5.781e-4` | 通过 `1e-3` gate |
| elastic symmetry projection relative | `2.414e-4` | 通过 |
| Gamma symmetry projection relative | `5.820e-4` | 通过 |
| internal-strain symmetry projection relative | `1.188e-2` | 仍违例，不能投影掩盖 |
| proper raw finite-difference fit relative | `1.465e-1` | 未通过线性/数值质量 gate |
| internal-displacement raw fit relative | `1.153e-1` | 未通过 |

当前 proper 分量为 `e31=-0.61522/-0.61535 C/m²`、`e33=1.26810 C/m²`、
`e15=-0.47693/-0.47701 C/m²`；由同一个 `C^E` 得
`d31=-5.969/-5.961 pm/V`、`d33=12.464 pm/V`、`d15=-11.964/-11.957 pm/V`。
弹性矩阵正定，最小特征值 `39.863 GPa`。这些是当前协议下的研究数值，不能因
proper/elastic/Gamma 的对称门通过而升级为文献验证后的材料常数。

为定位最大 internal-strain 违例的 `yz` shear，另对 `strain-004±` 试过
`force_thr_ev=1e-6`：负点收敛，但正点连续两次达到默认 50 个离子步仍未收敛。
这对严格阈值结果均已归档并从收集器排除，两个 stage 已恢复至统一的、离子收敛的
`1e-5` 数据。该尝试只说明当前 LCAO/离子优化设置下不能宣称 1e-6 审计成功，
不是新的材料张量结果。此失败也暴露了输入协议缺口：该试算沿用了 `scf_thr=1e-8`
和 50 步上限。后续 `1e-6` 审计已统一要求 `scf_thr=1e-10`、`relax_nmax=100`，
不得用这批旧失败输出续算或比较张量。
