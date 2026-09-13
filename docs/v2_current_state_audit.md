# ZStar v1 现状审计与 v2 隔离基线

**审计日期：2026-09-12**
**工作分支：`zstar-v2-development`**
**v1 保护原则：不修改 `main`、v1 正式论文、发布/上传配置。**

## 1. Git 和工作区状态

* 审计起点为 `main` 的 `6748e50`（`origin/main` 同步），已创建独立分支
  `zstar-v2-development`。
* 创建分支时工作区不是 clean：存在 4 个未提交的 v1/图表相关修改
  （`docs/paper_figures/make_validation_figures.py`、`tests/test_raman_response.py`、
  `zstar/raman_response.py`、`zstar/unified_spectra.py`）以及未跟踪的
  `.codex-finalizer-hzo-bec/`。这些内容属于既有工作区状态，本轮不清理、不覆盖、不
  纳入 v2 提交。
* 本分支随后只增加了隔离在 `zstar/v2/` 下的 draft-only model、units、代数、对称性、
  ensemble 和 ABACUS collector；没有改变 v1 Python/CLI、README、案例或正式论文。
* 已在用户授权节点完成研究审计，但没有提交 PyPI、GitHub release 或合并到 `main`。

## 2. v1 能力边界

| 层 | 已存在实现 | v2 继承/限制 |
|---|---|---|
| 极化/BEC | ABACUS+PYATB Unified、VASP、CP2K、QE 适配；分子 APT | 复用响应语义；不重命名为 v2 新方法 |
| Gamma 声子/IFC | Phonopy 1x1x1 Gamma 联合 force fit、NAC/BORN 输出 | BEC+IFC 作为 `u-u`/`E-u` 基础；应变需新扰动 |
| 介电/IR/Raman | calculator-neutral 后处理；bulk/2D/1D/molecule 约定 | 非共振 Raman 可作为已有观测；共振先研究 |
| 对称性 | spglib 等价原子、Phonopy 旋转/置换、site-stabilizer 拟合 | 扩展为位移/应变/输出的表示约束和 rank 检查 |
| 状态与恢复 | `.zstar/stages/*.json`、`workflow.jsonl`、manifest、输入哈希 | 在 `.zstar/v2/` 建命名空间，保持 v1 state 可读 |
| 响应 schema | `zstar-response` 1.0；`ResponseQuantity/ResponseRecord` 带 unit、axes、source | 提供 v1 adapter；不修改 1.0 读写行为 |
| 后端发现 | `BackendRegistry`、能力按 `dimension` 声明、配置 resolver | 增加 electromechanical capability keys 前先冻结接口 |

当前 `BackendRegistry` 的内建后端为 `abacus`、`cp2k`、`phonopy`、`qe`、`vasp`。
它已经能声明 structure/forces/band_gap/polarization/density/dipole/APT/BEC/dielectric/
gamma/IR/Raman；v2 draft collector 已能读取 ABACUS 的 strain/stress/relaxed structure，
但稳定的 `elastic`、`piezo`、`internal_strain` capability 仍未冻结，不能据此开放正式 CLI。

## 3. 数据和案例资产

已审计的 v1 案例覆盖：

* 3D：cubic BaTiO3、tetragonal HfO2、SiC；
* 2D：hBN、MoS2、alpha-In2Se3；
* 1D：BN(9,0)、GaAs nanowire、Sb2S3；
* 0D：H2O、CH4、CO2。

案例和 benchmark 已保留输入、赝势/轨道、`results/`、图表源数据和部分 provenance；
它们可作为 v2 的参考/回归输入，但不能未经检查地声称包含压电/弹性结果。第一轮不
复制或重排这些大体积目录。

## 4. 测试基线

在当前工作区、未修改 v1 代码的条件下执行：

```text
pytest -q
503 passed, 1155 warnings
```

警告主要来自 spglib、Phonopy 和 fontTools 的弃用提示，没有失败测试。v2 专项测试
当前收集为 110 项，覆盖 32 个点群联合响应、cubic/P4mm/P-6m2/Pmmm/P1 空间群
fixture、BEC/IFC 轴顺序、单位/Voigt、低维归一化
门、断点状态、后端路由、rank/residual、acoustic-SR、Raman/介电输出和 v1 案例完整性。
该结果是 v2 每个阶段必须保持的回归门；警告升级或依赖版本变化时需单独记录，不能把
警告当作物理验证。

## 5. 现状中的关键风险

1. `shared_response.py` 的 v1 联合拟合仍以 3 个 Cartesian 位移分量为输入；v2 的
   应变/应力观测在独立 collector 中实现，尚未替换 v1 联合拟合，也没有稳定 e/d/g/h
   后端能力键。
2. `symmetry_reduction.py` 目前以 `equivalent_atoms` 选择原子代表，分子 dim=0
   明确不使用周期空间群；它还不是任意输入/输出张量的群表示约化器。
3. v1 的 2D/1D 约定有明确的 slab-normal/wire-axis 限制，不能从真空胞自动推断
   intrinsic elastic 或 piezo 常数。
4. `ResponseQuantity` 已要求 unit、normalization、axes，但没有专门的坐标系、Voigt
   约定、clamped/relaxed、electric/mechanical boundary 字段；v2 必须增加不破坏 v1
   的新 schema/adapter。
5. 当前 CLI 的 canonical family 尚未包含 `piezo`/`elastic`；按照用户要求，理论、
   数据结构、内部测试稳定之前不能增加入口。

## 6. v2 隔离基线和进入下一阶段条件

当前隔离条件满足：独立分支已建立、v1 测试基线已记录、v2 代码路径限定在独立命名空间，
没有外部发布或合并。进入“理论和 schema 评审”前必须完成
[`v2_theory.md`](v2_theory.md)、[`v2_symmetry_reduction.md`](v2_symmetry_reduction.md)
和 [`v2_architecture.md`](v2_architecture.md) 的审阅，并由测试计划
[`v2_test_validation_plan.md`](v2_test_validation_plan.md) 定义可重复的 rank、residual、
units 和边界条件检查。

截至 2026-09-13，Gate A 已满足；Gate B 仍在进行（schema/failure contract 尚未冻结）。
Gate C 已完成 P4mm BaTiO3 的 clamped-ion、relaxed-ion、多幅度和 exact-geometry BEC
ABACUS/PYATB 审计，但 acoustic gauge 的独立 Gamma/IFC、stress work-conjugacy、低
对称材料、二维归一化和独立后端仍缺证据，因此尚未通过。
