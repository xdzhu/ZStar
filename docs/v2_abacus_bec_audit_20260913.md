# v2 exact-geometry BEC 审计（2026-09-13）

## 目的与边界

这是一轮面向 v2 代数链路的 research audit：在与 relaxed-ion/clamped-ion
应变 ensemble 完全相同的 tetragonal BaTiO3 P4mm tight reference 上，使用 v1
Unified symmetry-adapted 生成器准备 Born 有效电荷（BEC）位移。它不改变 v1
入口、案例或正式论文，也不把结果升级为稳定 CLI 或普适材料常数。

## 生成与计算设置

* 结构：5 原子 tetragonal BaTiO3，晶格
  `(3.8999997427, 3.8999997427, 4.0999997295) Angstrom`，P4mm，8 个空间群
  操作；独立原子代表为 Ba、Ti、O(3)、O(5)，即 4 个 site。
* 生成：`prepare_shared_abacus` 的 Unified Phonopy central ensemble，实际写入
  8 个 stage（每个代表原子一对正负位移）；每个实际笛卡尔位移范数均为
  `0.0100000000 Angstrom`，不是只记录名义步长。位移方向允许由对称性约化器
  选取的非轴向向量，重建时使用实际序列化向量。
* ABACUS：3.10.0-LTS，PBEsol、LCAO、100 Ry、同一 UPF/orbital/KPT，`cal_force=1`、
  `cal_stress=1`、`scf_thr=1e-8`，40 MPI x 1 OpenMP；9 个几何（reference + 8）
  均完成 SCF。
* PYATB：每个几何一次 `pyatb_input --polar --valence auto`，一次 PYATB
  precision adapter 输出 `polarization.dat` 中的 a/b/c 三个方向；没有用三个
  ABACUS NSCF 代替一个 PYATB。branch matching 的方向量子一致，整数 branch
  shift 为 0。
* 共享目录：
  `/home/zhuxd/zstar-v2-tbto-relaxed40-20260912/bec-0001/ensemble`。

首次尝试保留了生成器的 `init_chg file`，但 ABACUS 3.10 在当前目录读取该
`SPIN1_CHG.cube` 仍返回初始化失败；失败日志被保留在各 stage 的
`aborted_runs/` 审计目录。随后按已有 v1 案例改用 `init_chg auto`，9 个 stage
全部成功。该故障是输入初始化契约问题，不是 SCF 或 Berry 极化物理失败。

## 资源记录

| stage | 节点 | wall time (s) | SCF (`E_Harris`) |
|---|---|---:|---:|
| 0.no-move | cu17 | 115.156 | 14 |
| disp-001/002 | cu17 | 131.157 / 131.635 | 15 / 15 |
| disp-003/004/005 | cu24 | 130.556 / 131.384 / 149.047 | 15 / 15 / 15 |
| disp-006/007/008 | cu26 | 164.745 / 146.495 / 146.747 | 15 / 15 / 15 |

ABACUS `time.json` wall-time 合计 `1246.922 s`，按 40 核折算为
`13.855 core-hours`；总 SCF 迭代 134。PYATB 运行次数为 9，按 stage 顺序
完成，没有记录到失败的 PYATB 输出。

## BEC 结果

张量采用 `Z[atom, polarization, displacement]`，单位 `e`；只列出对称投影后的
结果，非对角禁止分量以数值零保存：

```text
Ba = [[ 2.73144822, 0,          0         ],
      [ 0,           2.73144822, 0         ],
      [ 0,           0,           2.85652322]]

Ti = [[ 7.09827767, 0,          0         ],
      [ 0,           7.09827767, 0         ],
      [ 0,           0,           5.30641533]]

O(3) = [[-5.66139674, 0,           0         ],
        [ 0,          -2.13332365,  0         ],
        [ 0,           0,          -1.92554730]]

O(4) = [[-2.13332365, 0,           0         ],
        [ 0,          -5.66139674,  0         ],
        [ 0,           0,          -1.92554730]]

O(5) = [[-2.03500550, 0,           0         ],
        [ 0,          -2.03500550,  0         ],
        [ 0,           0,          -4.31184395]]
```

投影前每个 site 的输入位移秩为 3，投影后满足 P4mm 允许子空间；极化 site
拟合最大残差为 `3.31e-4 e Angstrom`（Ti site），这是电子 Berry 数值/有限步长
误差诊断，不能抹成零。投影后的 Born 声学和为
`max |sum_i Z*_i| = 8.9e-16 e`；这项检查通过。

## 与内应变和 relaxed-ion e 的闭环

用同一 P4mm `±1e-3` relaxed-ion 应变 ensemble 的实际结构拟合
`Lambda = d u / d eta`，输出单位为 Angstrom；允许秩为 14、拟合秩为 14，
`Lambda` 拟合最大残差 `6.90e-6 Angstrom`。采用体积
`Omega = 6.23609876594e-29 m^3`、上述 BEC、clamped-ion 直接导数后，调用
`relaxed_piezoelectric(..., internal_strain_unit="angstrom")` 得到内部贡献：

```text
e_internal (C/m^2) =
[[0, 0, 0, 0, 5.07979116, 0],
 [0, 0, 0, 5.07979116, 0, 0],
 [0.14142026, 0.14142026, 4.34083528, 0, 0, 0]]
```

重建的 relaxed-ion improper `e` 为

```text
[[0, 0, 0, 0, 5.07584569, 0],
 [0, 0, 0, 5.07584569, 0, 0],
 [0.01597694, 0.01597694, 3.89086038, 0, 0, 0]] C/m^2
```

与同一 relaxed-ion ensemble 直接拟合的
`[[0,0,0,0,5.07647754,0], [0,0,0,5.07647754,0,0],
[0.01597270,0.01597270,3.89091867,0,0,0]] C/m^2` 相比最大差为
`6.32e-4 C/m^2`。这支持 `e = e^(0) + (q/Omega) Z* Lambda` 的单位一致实现，
但仍不是 Gate C 完成的充分条件：需要 acoustic gauge、Gamma/IFC 和独立后端或
高精度参考的复核，并需把 proper/improper 规范分开保存。

## 结论与下一步门控

1. v1 Unified 约化位移路径已在 exact-geometry BEC 上成功得到完整 5 原子 BEC，
   且声学和、rank 和实际位移检查通过。
2. 每个几何一次 PYATB 得三方向极化的路线可复现；不需要三次 ABACUS NSCF。
3. `scf_thr=1e-8` 在本轮构型上完成了全部 SCF；`1e-10` 应作为困难离子构型或
   收敛敏感性审计选项，而不是未经比较就强制全流程。
4. 目前只支持继续做 v2 代数/数据结构验证，不足以开放 piezo/elastic CLI，也不
   能宣称跨材料普适性。下一门控是独立验证 BEC/`Lambda` 的 acoustic gauge、
   Gamma/IFC 单位以及 stress work-conjugacy。
