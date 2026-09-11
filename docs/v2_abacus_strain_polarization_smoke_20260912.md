# ZStar v2 应变–Berry 极化耦合 smoke（2026-09-12）

## 目的与适用范围

本次计算验证新加入的 preparation、triplet collection、reference branch matching
和 raw e 拟合能否串联工作。材料是 centrosymmetric cubic BaTiO₃（`Pm-3m`），
因此 `strain → polarization` 在该结构的对称性约束下应为严格禁止；本结果只作为
对称性/分支/数据链审计，不作为非零压电材料的验证，也不替代 proper/improper
修正或独立后端交叉验证。

## 输入和资源

* 结构：5 原子 cubic BaTiO₃ primitive cell；
* 后端：ABACUS v3.10.0，commit `e84abb4`；
* PBEsol、LCAO、`ecutwfc=100 Ry`、`9×9×9` k 点；
* 所有 NSCF 阶段使用已完成 SCF 的 `POLAR-CHARGE-DENSITY.restart`，
  `berry_phase=1`、`symmetry=0`，每个 `gdir` 一个独立目录；
* reference 三方向沿用 [`v2_abacus_polarization_smoke_20260912.md`](v2_abacus_polarization_smoke_20260912.md)；
* `strain-001-` 的 3 个阶段在 cu25 顺序执行，`strain-001+` 的 3 个阶段在 cu26
  顺序执行；每阶段 1 MPI rank × 1 OpenMP thread，没有修改 PBS 占位作业。

实际序列化应变（从 `STRU` 反算）为：

| 样本 | `eta_xx` | 其余 engineering-Voigt 分量 |
|---|---:|---|
| reference | `0` | `0` |
| `strain-001-` | `-0.001000000000000223` | `|eta_i| < 1.2×10⁻¹⁶` |
| `strain-001+` | `+0.0009999999999996678` | `|eta_i| < 1.2×10⁻¹⁶` |

## Berry 输出和资源

每个阶段的 `exit_code` 均为 0，且每个 NSCF 日志包含 1 次 `E_Harris`。wall time
如下；总计 526.1188 s：

| 样本 | 节点 | `gdir=1` | `gdir=2` | `gdir=3` |
|---|---|---:|---:|---:|
| reference | cu25/cu26 | 56.9934 s | 57.2715 s | 56.5239 s |
| `strain-001-` | cu25 | 59.21 s | 59.09 s | 59.03 s |
| `strain-001+` | cu26 | 59.48 s | 59.34 s | 59.18 s |

解析到的标量极化和量子（直接 `C/m²` 记录优先）为：

| 样本 | `gdir=1` quantum | `gdir=2` quantum | `gdir=3` quantum | Cartesian 极化向量 |
|---|---:|---:|---:|---|
| reference | 2.0199409 | 2.0199409 | 2.0199409 | `(0, 0, 0)` |
| `strain-001-` | 2.0199409 | 2.0219629 | 2.0219629 | `(0, 0, 0)` |
| `strain-001+` | 2.0199409 | 2.0179230 | 2.0179230 | `(0, 0, 0)` |

量子随晶胞应变变化，而极化仍为零；这正是不能把固定 reference quantum 或文件
顺序当作通用坐标约定的实际例子。

## branch matching 和 e 审计

将三组 triplet 的 Cartesian tuple 组成 wrapped 向量，并以每个样本对应的对角量子
矩阵（仅因为本例晶胞为正交 cubic）执行 `match_polarization_ensemble`：

* `matched_values`：三个样本均为 `(0, 0, 0) C/m²`；
* `branch_shifts`：三个样本均为 `(0, 0, 0)`；
* `residuals`：三个样本均为 0。

结构空间群识别为 `Pm-3m`，`allowed_response_basis(report, input_kind="strain",
output_kind="polarization")` 的允许秩为 0。将匹配结果交给
`fit_piezoelectric_ensemble` 得到：

* e 矩阵：3×6 全零（单位应为 C/m²，但此处仍是 draft raw fit）；
* `fit_rank=0`、`allowed_rank=0`、`residual_max=0`；
* `complete=True` 的含义是“对称性允许子空间已完整确定为零”，不是已经验证了
  一般材料的压电响应。

本审计没有计算 relaxed-ion e、内部应变贡献、proper 修正或非中心对称材料的非零
响应。下一步必须在 tetragonal/hexagonal 极性结构中重复相同链条，并用独立后端或
可靠文献数据核对张量数值。

## response schema 回读

将 reference 与 `strain-001±` 的 force/stress/energy 目录和三方向 Berry 目录通过
显式 `polarization_stages` 映射交给 `collect_abacus_strain_response`，成功生成
`zstar-v2-response` 0.1 草稿文档。文档包含：

* `strain_vector` `(3, 6)`、`forces` `(3, 5, 3)`、`stress_raw` `(3, 3, 3)` 和
  `energy` `(3,)`；
* `polarization_gdir`、`polarization_quantum` `(3, 3)`，以及完整的
  `polarization_cartesian_directional` `(3, 3, 3)`；
* `polarization_collected=true`、`polarization_cartesian_collected=true`，每个量的
  单位/轴/后端/日志 provenance。

该回读使用 JSON 中的字符串 gdir 键（`"1"`、`"2"`、`"3"`），并已加入回归测试。
低维 ensemble 即使有同样的日志映射也会被明确拒绝，直到 sheet/line 归一化和边界
条件接口完成。
