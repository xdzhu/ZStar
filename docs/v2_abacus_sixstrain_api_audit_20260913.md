# v2 ABACUS/PYATB 六分量 API 验证（2026-09-13）

## 目的与边界

本记录是 v2 **实验性 API/collector 验证**，不是稳定 CLI、不是 v2 正式
benchmark，也不修改 v1 的入口或论文。计算对象为当前 v2 生成的
`ResponseEnsemble`，用于检查：

* 一个平衡 reference 和六个工程应变分量的正负扰动是否由同一组 reference
  分数坐标生成；
* ABACUS 力、应力、能量、`STRU_ION_D` 是否能被 calculator-neutral collector
  读取；
* 每个几何是否只需一次 PYATB，即可取得 a/b/c 三个晶格方向的 Berry 极化；
* 实际序列化应变、极化 branch、对称性约束、rank/residual 和机械稳定性是否
  能在后处理中统一检查。

正式数据仍位于共享目录：
`/home/zhuxd/zstar-v2-tbto-relaxed40-20260912/api-sixstrain-20260913`。

## 输入和计算设置

* 材料：tetragonal BaTiO3，空间群由 v2 识别为 `P4mm`（8 个操作）；
* 泛函/基组：PBEsol、ABACUS LCAO，`ecutwfc=100`，与 tight reference 相同的
  赝势、数值轨道和 KPT；
* reference：fixed-cell `scf`，`scf_thr=1e-8`，最大力约
  `2.34e-6 eV/Angstrom`；
* 应变阶段：fixed-cell `relax`，`force_thr_ev=1e-4`，
  `scf_thr=1e-8`；工程 Voigt 顺序为
  `(xx, yy, zz, 2yz, 2xz, 2xy)`，每个分量采用 `+/-1e-3`；
* ABACUS：每个阶段一个 `40 MPI x 1 OpenMP` 任务。第一波使用 cu24--cu26，
  后续阶段在节点释放后继续运行；未修改用户的 PBS 占位作业；
* PYATB：在 cu17 后处理。每个几何一次 `pyatb_precision`，一次输出同时包含
  a/b/c 三个方向的极化，输出保留 16 位科学计数法；没有用三次 ABACUS NSCF
  代替 PYATB；
* 所有 stage 的输入哈希、`STRU_INITIAL`、实际 cell 应变均由 collector 复核。

## ABACUS 结果摘要

`total` 为 ABACUS `time.json` 的 wall 秒数；`SCF` 为最终日志中累计的
`E_Harris` 次数；最大力使用最终 `TOTAL-FORCE` 块的逐原子范数。

| stage | 扰动 | total (s) | SCF | max force (eV/Å) |
|---|---:|---:|---:|---:|
| reference | 0 | 127.1 | 14 | 2.34e-6 |
| strain-001± | xx ±1e-3 | 665.2 / 673.2 | 53 / 53 | 8.12e-5 / 7.64e-5 |
| strain-002± | yy ±1e-3 | 740.2 / 739.2 | 53 / 53 | 8.12e-5 / 7.64e-5 |
| strain-003± | zz ±1e-3 | 855.8 / 655.9 | 69 / 56 | 7.24e-6 / 2.55e-5 |
| strain-004± | 2yz ±1e-3 | 1499.1 / 1666.9 | 104 / 104 | 4.51e-5 / 4.51e-5 |
| strain-005± | 2xz ±1e-3 | 1491.9 / 1502.8 | 104 / 104 | 4.51e-5 / 4.51e-5 |
| strain-006± | 2xy ±1e-3 | 121.2 / 135.2 | 14 / 14 | 6.06e-6 / 6.06e-6 |

这些阶段的 ABACUS wall-time 总和为 `10873.6 s`（串行等效约 3.02 h，按
40 核折算约 120.8 core-hours）；这是资源记录，不是效率 benchmark。剪切阶段
明显更慢，说明在报告效率前必须把节点 I/O、SCF 次数和离子步数分开统计。

## collector 和响应重建

本地 v2 collector 成功读取 13 个 stage（reference + 12 个正负扰动），并完成
13 次 PYATB 读取。PYATB 的 branch shift 最大值为 0；报告的
`branch_residual_max=5.2741e-3 C/m^2` 是样本相对 reference 的物理极化差，
不是 branch 跳跃判据。

在 `P4mm` 的允许子空间内，直接有限差分（当前为 improper、relaxed-ion 草稿
结果）得到：

```text
e (C/m^2, rows=P_x/P_y/P_z, columns=xx yy zz 2yz 2xz 2xy)
[[0, 0, 0, 0, 5.07647754, 0],
 [0, 0, 0, 5.07647754, 0, 0],
 [0.0159727, 0.0159727, 3.89091867, 0, 0, 0]]
```

拟合输入秩为 6，`P4mm` 压电允许秩为 3，拟合秩为 3；最大极化拟合残差
`1.94e-5 C/m^2`，RMS `5.34e-6 C/m^2`。`xx` 与 `yy` 的 `P_z` 斜率相同到当前
数值精度；横向 `10^-8 C/m^2` 分量被对称性严格投影为零。

ABACUS raw stress 的符号不能由 parser 猜测。对本次 BaTiO3 数据，比较应变能
曲率与应力差分后确认 raw 输出对应 compression-positive；显式转换为
tension-positive 后，在 `P4mm` strain→strain 子空间并施加 major symmetry 得到
（单位 kbar）：

```text
C =
[[3563.7605, 1358.6395, 1043.5184,    0,       0,       0],
 [1358.6395, 3563.7605, 1043.5184,    0,       0,       0],
 [1043.5184, 1043.5184, 1420.0840,    0,       0,       0],
 [   0,       0,       0,       1131.9926,    0,       0],
 [   0,       0,       0,          0,    1131.9926,    0],
 [   0,       0,       0,          0,       0,    1399.5997]]
```

弹性拟合秩为 6，最大 stress 残差 `2.64e-2 kbar`，RMS `8.60e-3 kbar`；六个
机械稳定性特征值为 `881.17, 1131.99, 1131.99, 1399.60, 2205.12,
5461.31 kbar`，均为正。这个符号结论只适用于本次 ABACUS 输出和该独立能量
审计，不能写成后端无条件规则。

内部位移以 `wrapped(final_fractional-initial_fractional) @ initial_cell` 保存，
单位 Å；未偷偷施加 acoustic gauge。未约束拟合的输出形状为 `(5*3, 6)`，最大
残差 `6.90e-6 Å`；同一 `P4mm` displacement←strain 表示的允许秩为 14。因而
`Lambda` 到 relaxed-ion 压电贡献的代数链路已可检查，但尚未把 Born 电荷和
质量/体积规范写成最终稳定接口。

## 重要代码修正

PYATB 后处理会把原始 `STRU` 复制为 `STRU_INITIAL`，保留弛豫前 fractional
coordinates。旧哈希把字面文件名也纳入摘要，会将这个合法别名误判为输入被改动。
v2 现将 `STRU_INITIAL` 按逻辑输入名 `STRU` 计入哈希，并加入回归测试；内容改变
仍会被拒绝。该修正记录在 commit `15c4fd6`，不触及 v1 分支。

## 当前结论和 Gate C 状态

* 算法链路（实际 cell 应变 → ABACUS force/stress/energy → `STRU_ION_D` → 一次
  PYATB 三方向极化 → branch/units/rank/residual）已在本次 13-stage 数据上跑通；
* `P4mm` 允许子空间、stress 符号、机械稳定性和能量曲率已有可审计数值；
* 这仍是单一材料、单一后端、单一应变幅度的 relaxed-ion 审计，不能声称普适性，
  也不能代替多幅度和独立后端交叉验证；
* Gate C 仍未通过。下一步先做 ±`2.5e-4`/±`5e-4` 的六分量幅度审计、应力
  work-conjugacy/单位复核、Λ+Born 的统一规范，再考虑稳定 CLI 和集群工程优化。
