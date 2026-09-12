# v2 六分量幅度审计（`±2.5e-4`、`±5e-4`）

本记录延续 [`v2_abacus_sixstrain_api_audit_20260913.md`](v2_abacus_sixstrain_api_audit_20260913.md)
的 BaTiO3/P4mm、PBEsol、ABACUS LCAO 设置。reference 使用同一 tight fixed-cell
结构；每个幅度只改变工程 Voigt 应变，仍由生成器自动补正负 pair：
`(xx, yy, zz, 2yz, 2xz, 2xy)`。

## 资源和完成状态

每个 stage 使用 `40 MPI x 1 OpenMP`、`scf_thr=1e-8`、`force_thr_ev=1e-4`。
每个几何只运行一次 PYATB，得到 a/b/c 三方向极化。reference 不重复计算。

| ensemble | ABACUS stage | ABACUS wall-time 总和 | 40 核 core-hours | SCF 次数 | 重启 |
|---|---:|---:|---:|---:|---:|
| `amp-00025` (`±2.5e-4`) | 12/12 | 9303.4 s | 103.37 | 648 | 1 次 `yy−` 中断后干净重跑 |
| `amp-0005` (`±5e-4`) | 12/12 | 9977.1 s | 110.86 | 726 | 0 |

两个 ensemble 的 24 个扰动 stage 均有 ABACUS `Relaxation is converged`、
`STRU_ION_D` 和完整 PYATB precision metadata；中断目录被移到 scratch 的
`failures/`，没有混入 collector 的有效输出。

## 三种幅度的张量比较

在 `P4mm` 允许子空间中拟合，`e` 是直接有限差分的 relaxed-ion improper
压电张量，单位 `C/m^2`；行是 `(P_x,P_y,P_z)`，列是
`(xx,yy,zz,2yz,2xz,2xy)`。

| 幅度 | `e31=e32` | `e33` | `e15=e24` | 极化残差最大值 |
|---:|---:|---:|---:|---:|
| `±1e-3` | 0.0159727 | 3.8909187 | 5.0764775 | 1.94e-5 C/m² |
| `±2.5e-4` | 0.0156427 | 3.8727065 | 4.9696334 | 3.58e-6 C/m² |
| `±5e-4` | 0.0159984 | 3.8912306 | 5.0169027 | 5.13e-6 C/m² |

三幅度范围内，`e31/e32` 的最大相对展宽约 2.2%，`e15/e24` 约 2.1%，
`e33` 约 0.5%；三者的 `P4mm` 禁止分量均由约束严格投影为零。这个结果支持
“当前 BaTiO3 几何的线性响应已初步幅度收敛”，但不是普适误差上界。

弹性张量先将本次 ABACUS raw stress 按独立能量曲率审计确定为
compression-positive，再显式转为 tension-positive；单位 `kbar`：

| 幅度 | `C11` | `C12` | `C13` | `C33` | `C44=C55` | `C66` | 残差最大值 |
|---:|---:|---:|---:|---:|---:|---:|---:|
| `±1e-3` | 3563.76 | 1358.64 | 1043.52 | 1420.08 | 1131.99 | 1399.60 | 2.64e-2 kbar |
| `±2.5e-4` | 3564.24 | 1358.98 | 1042.52 | 1420.47 | 1135.57 | 1399.62 | 5.27e-3 kbar |
| `±5e-4` | 3564.36 | 1358.62 | 1043.65 | 1419.79 | 1133.59 | 1399.61 | 1.19e-2 kbar |

六个特征值在三种幅度下都为正，最小值分别为 881.17、882.52 和
880.86 kbar；major symmetry 违例保持在数值舍入量级。raw stress 符号仍只对
本次 ABACUS/PBEsol 输入成立，不能作为后端通用默认值。

内部位移 `Lambda` 使用
`wrapped(final_fractional-initial_fractional) @ initial_cell`，单位 Å，未施加
acoustic gauge。最大拟合残差为 `6.90e-6`、`1.63e-6` 和 `2.77e-6 Å`（依次对应
三种幅度）；`strain→displacement` 表示允许秩为 14。Born 电荷和质量/体积
规范尚未接入这里的最终 relaxed-ion 代数接口。

## 结论

幅度审计降低了有限差分截断误差疑虑，并复核了实际序列化应变、branch matching、
单位、rank/residual、内部位移和机械稳定性。由于仍是单一材料、单一后端、单一
参考相，Gate C 仍阻塞：下一步必须做独立后端/高精度参考交叉验证、应力
work-conjugacy 独立核对和适用的多维度案例，然后才能冻结压电/弹性稳定接口。
