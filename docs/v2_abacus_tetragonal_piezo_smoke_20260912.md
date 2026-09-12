# ZStar v2 tetragonal BaTiO₃ piezoelectric-chain smoke（2026-09-12）

## 目的和边界

这是第一个非中心对称结构的应变–Berry 链路审计：reference SCF → `gdir=1,2,3`
Berry triplet → 轴向 Cartesian tuple 求和 → reference branch matching → 对称约束
raw-`e` fit。结构是人为选取的 tetragonal BaTiO₃（`P4mm`），不是弛豫后的材料
基准；本记录不支持文献数值或普适性结论。proper/improper 几何修正、relaxed-ion
贡献、应变幅度外推和独立后端交叉验证仍未完成。

## 输入和计算资源

* 结构：5 原子 tetragonal cell，`a≈3.90 Å`、`c≈4.10 Å`，极性位移仅用于
  产生非中心对称测试结构；
* 后端：ABACUS v3.10.0，commit `e84abb4`；PBEsol、LCAO、100 Ry、Γ-centered
  `9×9×9`；SCF `scf_thr=1e-8`，Berry 阶段 `symmetry=0`；
* 资源：cu24、cu25、cu26，各 1 MPI × 1 OpenMP；未修改 PBS 占位作业。cu26
  同时存在用户的 40-rank VCNEB 任务，故其 gdir=3 wall time 单独标记为受资源
  竞争影响；
* 阶段：3 个 SCF（reference、`strain-001−`、`strain-001+`）和 9 个 NSCF
  Berry 阶段，均 `exit_code=0`，总共 12 个第一性原理任务。

序列化后从 `STRU` 反算的应变为：

| 样本 | `eta_xx` | 其余分量 |
|---|---:|---|
| reference | `0` | `0` |
| `strain-001−` | `-0.001000000000000223` | `|eta_i|<1.2×10⁻¹⁶` |
| `strain-001+` | `+0.000999999999999668` | `|eta_i|<1.2×10⁻¹⁶` |

输入哈希（SHA-256）已在本地临时 provenance 中保留：

* reference `STRU`: `9cec10dcce286cfa7f5401c8d5b2b34f151274ce3a63ebdcf4881c6142e207fb`；
* `strain-001−` `STRU`: `e1d294985074e4db6c6381f100e3fa7cde1b305b4066a5cc6d7734d41996af56`；
* `strain-001+` `STRU`: `8ee247d163b91272e9cfbdba4eaca895a3ddd146a6ffa83114cc8d43888573a6`；
* 三个 `INPUT` 哈希相同：`b1e34c2704a8ffb6e1a354bde00bccd16be8912eade23a096230f4f4813e89e5`；
* 三个 `KPT` 哈希相同：`36ed6ce38df591bb0c19c8c77ffed5527ff49d2e7eeaf3143785518b201a0085`。

## SCF 和 Berry 计时

| 样本 | SCF wall time | Berry gdir=1 | gdir=2 | gdir=3 |
|---|---:|---:|---:|---:|
| reference | 233 s | 128 s | 131 s | 282 s* |
| `strain-001−` | 242 s | 135 s | 129 s | 302 s* |
| `strain-001+` | 241 s | 131 s | 133 s | 131 s |

`*` cu26 上的用户 40-rank VCNEB 任务造成明显竞争；这些任务没有被停止或修改。

## 极化回读

解析器优先使用 ABACUS 直接输出的 `C/m²` 记录，同时保留每个 gdir 的量子和
Cartesian directional tuple。轴向 tuple 求和后的 Cartesian 极化为：

| 样本 | `P_x` | `P_y` | `P_z` | gdir 量子（C/m²） |
|---|---:|---:|---:|---|
| reference | 0 | 0 | 0.3480690 | `(2.0024659, 2.0024659, 2.1051565)` |
| `strain-001−` | 0 | 0 | 0.3481275 | `(2.0024659, 2.0044704, 2.1072637)` |
| `strain-001+` | 0 | 0 | 0.3480102 | `(2.0024659, 2.0004654, 2.1030534)` |

相对于 reference 的 branch matching 得到 branch shifts 全为 `(0,0,0)`，residual
为 `0`、`5.85×10⁻⁵`、`5.88×10⁻⁵ C/m²`。residual 是真实应变诱导的极化差，不能
被误判为 branch jump；因此本次 fit 显式使用 `residual_tolerance=1e-3`。

## 对称性和 rank gate

`spglib` 在 `symprec=1e-4` 下识别为 `P4mm`，报告状态 `stable`，8 个操作。该
结构的 strain→polarization 允许子空间秩为 3。当前只采样 `eta_xx` 的正负对，故
实际输入秩为 2、拟合秩为 1，`complete=False`；未观测的 `e_33`/剪切相关自由度
不能从本算例推断。任何由欠定最小二乘产生的数值都不作为结果：必须先补齐至少
允许子空间所需的独立应变方向（随后还要做多幅度收敛和 proper 修正）。

因此，本 smoke 的有效结论只有：

1. 非中心对称 tetragonal 输入确实得到非零参考极化；
2. Berry 三方向、方向 tuple 求和、branch matching 和 schema collector 可以串联；
3. rank gate 能阻止把单一应变方向伪装成完整压电张量。

## 可复现资产

最小输入保存在 [`examples/3D_Bulk/tetragonal_BaTiO3`](../examples/3D_Bulk/tetragonal_BaTiO3)。
真实 ABACUS 输出、restart 和完整 provenance 留在节点共享目录的临时 smoke 目录，
未提交到 Git；后续若将此案例升级为 benchmark，必须补充独立计算器/高精度参考、
完整六分量或对称完备应变集合、`proper e`、relaxed-ion e 及收敛表。

## 补齐独立应变后的完整性 smoke

随后补充了 `eta_yy`、`eta_zz` 和 `eta_xz` 的正负对（总计 4 个应变方向、8 个
应变结构，加 reference 共 9 个 SCF；每个结构再做 3 个 gdir，共 27 个 Berry
NSCF）。全部阶段 `exit_code=0`，解析器、轴向 tuple 求和和 reference branch
matching 均成功。SCF wall time 为 226–251 s；Berry wall time 为 126–139 s，
此前受 cu26 竞争影响的 gdir=3 除外（reference/`strain-001−` 分别 282/302 s）。
按日志的串行 wall-time 加总为 SCF 2160 s、Berry 3888 s；实际采用三节点分波，
未修改 PBS 占位作业。

`P4mm` 允许的 strain→polarization 子空间秩为 3；这组采样的输入秩为 4、拟合
秩为 3，`complete=True`。以 branch-matched 的轴向求和 Cartesian 极化做 draft raw
fit（单位 C/m²，engineering-Voigt 顺序 `xx,yy,zz,2yz,2xz,2xy`）得到：

```text
e_raw = [[ 0,        0,        0,        0,        0.32860, 0],
         [ 0,        0,        0,        0.32860,  0,       0],
         [-0.05865, -0.05865, -0.44435,  0,        0,       0]] C/m^2
```

其中 `e15=e24` 和 `e31=e32` 与 `P4mm` 约束一致；线性 fit 的最大重建残差为
`5.5×10⁻⁷ C/m²`。各样本 branch shift 仍为零，最大 reference-matching residual
为 `4.449×10⁻⁴ C/m²`，这是有限应变引起的物理 ΔP，不是 branch jump。

该矩阵只证明“独立响应自由度已被采样且数值链闭合”，不能作为 BaTiO₃ 的发表值：
结构是人为极性位移、未做离子弛豫；只有 `|eta|=0.001` 一个幅度；还未分离
clamped-ion/relaxed-ion、proper/improper 和内部应变贡献，也未与 VASP/QE 或高精度
ABACUS 参考交叉验证。任何正式结果必须先通过多幅度、收敛、应力符号和独立后端门控。
