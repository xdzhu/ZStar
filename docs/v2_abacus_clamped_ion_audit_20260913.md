# v2 ABACUS/PYATB clamped-ion 边界条件审计（2026-09-13）

## 目的

本审计在与 relaxed-ion 六分量 ensemble 相同的 tight reference、晶胞和
`±1e-3` 工程 Voigt 应变基底上，计算固定离子（clamped-ion）响应。它用于把

* 固定应变下的电子/离子冻结极化导数；
* 允许内部原子弛豫后的 relaxed-ion 导数；
* 内应变 `Lambda` 和 Born 电荷之间的后续代数链路

分开验证。它不是稳定 CLI 或正式 benchmark，也不修改 v1 入口和论文。

## 设置与资源

* 体系：tetragonal BaTiO3，v2/spglib 识别为 `P4mm`（8 个操作）；
* ABACUS：PBEsol、LCAO、`ecutwfc=100`、同一 tight reference 赝势/轨道/KPT；
* 每个 stage：固定 cell、固定 `STRU`、`calculation=scf`、
  `scf_thr=1e-8`，`cal_force=1`、`cal_stress=1`；不进行离子弛豫；
* 参考态加 12 个正负应变 stage，共 13 个 ABACUS 任务，每个 `40 MPI x 1
  OpenMP`，未占用或修改其他用户任务；
* 每个几何只做一次 PYATB `--polar`，一次输出 a/b/c 三个晶格方向极化；
  使用 `--valence auto` 从对应 UPF 解析价电子数，再由
  `zstar.pyatb_precision` 保留 16 位科学计数法。没有用三个 ABACUS NSCF
  代替一次 PYATB；
* 共享目录：
  `/home/zhuxd/zstar-v2-tbto-relaxed40-20260912/clamped-0001`。

ABACUS `time.json` 的 wall-time 总和为 `1658.389 s`，按 40 核折算为
`18.43 core-hours`；最终日志共 190 个 `E_Harris` SCF 迭代。各 stage 的
wall-time/SCF 次数如下（`+/-` 仍按实际生成顺序记录）：

| stage | total (s) | SCF | 最终最大力 (eV/Å) |
|---|---:|---:|---:|
| reference | 127.089 | 14 | 2.3391e-6 |
| strain-001+ / 001- | 121.710 / 122.742 | 15 / 15 | 4.508e-3 / 4.432e-3 |
| strain-002+ / 002- | 136.905 / 122.477 | 15 / 15 | 4.508e-3 / 4.432e-3 |
| strain-003+ / 003- | 115.498 / 114.791 | 14 / 14 | 2.608e-2 / 2.583e-2 |
| strain-004+ / 004- | 146.989 / 132.635 | 15 / 15 | 2.394e-3 / 2.394e-3 |
| strain-005+ / 005- | 131.232 / 146.217 | 15 / 15 | 2.394e-3 / 2.394e-3 |
| strain-006+ / 006- | 120.323 / 119.781 | 14 / 14 | 6.058e-6 / 6.058e-6 |

这些力没有被当成“离子收敛”判据；它们是固定离子应变结构的 Hellmann--Feynman
力，正是 relaxed-ion 与 clamped-ion 分离所需要的诊断量。

## collector、branch 和 rank

本地 collector 成功读取 13 个 ABACUS stage 和 13 个 PYATB 输出：输入哈希、
实际序列化 cell 应变、`force/stress/energy`、三方向极化和 precision metadata
均通过。参考极化为

```text
(7.03798952e-08, 5.98886237e-08, 3.9517389583267953e-01) C/m^2
```

分支匹配没有发生整数极化量子跳变（`branch_shift_max=0`）；样本物理差异的
最大值为 `4.50594e-4 C/m^2`。`P4mm` 的 strain→polarization 允许秩为 3，
输入秩 6、拟合秩 3，所有禁止分量由对称约束投影为严格零。

## clamped-ion 压电张量

用 branch-matched Cartesian 极化拟合 `Delta P = e eta`，工程 Voigt 顺序为
`(xx, yy, zz, 2yz, 2xz, 2xy)`。结果（直接 improper 导数，单位 `C/m^2`）为

```text
e_clamped =
[[ 0,          0,          0,          0,         -0.00394546467, 0],
 [ 0,          0,          0,         -0.00394546467, 0,          0],
 [-0.12544332115, -0.12544332115, -0.44997490170, 0, 0,          0]]
```

拟合最大残差为 `6.19e-7 C/m^2`，RMS 为 `2.24e-7 C/m^2`。与同一 `±1e-3`
relaxed-ion ensemble 的直接差分结果比较：

| 分量 | clamped-ion | relaxed-ion | relaxed - clamped |
|---|---:|---:|---:|
| `e31=e32` | -0.125443 | 0.015973 | 0.141416 |
| `e33` | -0.449975 | 3.890919 | 4.340894 |
| `e15=e24` | -0.003945 | 5.076478 | 5.080423 |

差值是内部原子弛豫贡献的数值证据，但还不能直接称为最终规范化的
`e_relaxed-ion - e_clamped-ion = (Z* / Omega) Lambda`：Born 电荷、声学规范、
体积和 proper/improper 几何修正仍需在统一接口中明确后再冻结该公式。

## clamped-ion 弹性张量

ABACUS raw stress 的 compression-positive 符号沿用独立能量曲率审计结果，拟合前
显式转换为 tension-positive。`P4mm` strain→strain 允许秩在 major symmetry
下为 6；结果（`kbar`）为

```text
C_clamped =
[[3687.7752, 1287.0637, 1177.2950,    0,       0,       0],
 [1287.0637, 3687.7752, 1177.2950,    0,       0,       0],
 [1177.2950, 1177.2950, 3194.0380,    0,       0,       0],
 [   0,         0,         0,       1280.1405,  0,       0],
 [   0,         0,         0,          0,    1280.1405,  0],
 [   0,         0,         0,          0,       0,    1399.5997]]
```

输入秩、允许秩和拟合秩均为 6；最大 stress 残差为 `2.54e-2 kbar`，RMS
`8.67e-3 kbar`。特征值为

```text
1280.1405, 1280.1405, 1399.5997, 2196.3548, 2400.7116, 5972.5221 kbar
```

全部为正，`C=C.T` 的 antisymmetric 最大值为 `4.55e-13 kbar`，当前矩阵满足
机械稳定性检查。相比 relaxed-ion，`C33` 从 `3194.04` 降到 `1420.08 kbar`，
`C44` 从 `1280.14` 降到 `1131.99 kbar`；这与内部弛豫软化的预期一致，但
`C12` 的变化方向提醒我们不能只用“所有分量都降低”作判据。

## 结论与门控

这批数据首次在同一结构、同一应变序列和同一 PYATB 后处理中把 clamped-ion
和 relaxed-ion 分开，并验证了应力、极化、rank/residual 和稳定性字段的边界
条件。它支持继续做 `Lambda`+BEC 的统一响应代数，但仍有三个门控未完成：

1. Born 电荷与内部位移的 acoustic gauge、质量/体积规范及 proper/improper 修正；
2. ABACUS stress work-conjugacy 的独立高精度/独立后端复核；
3. 非 `P4mm` 材料和至少一个低维体系的边界条件验证。

因此 Gate C 仍保持阻塞；本结果不升级为稳定 CLI、用户入口或普适材料常数。
