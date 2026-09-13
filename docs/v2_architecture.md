# ZStar v2 总体架构草案

**目标：**在不改变 v1 Unified 框架的前提下，扩展为 calculator-neutral 的
electromechanical/higher-order response 平台。本文是设计冻结前的架构草案，不是
实现承诺。当前已在 `zstar/v2/` 落地 draft-only 的 model、units、Voigt、代数、
intertwiner、结构对称性和可恢复 ensemble 原型；它们尚未构成稳定 API。

## 1. 分层原则

```text
┌──────────────────────────────────────────────────────────┐
│ CLI（最后设计）：piezo / elastic / phase / spectra       │
├──────────────────────────────────────────────────────────┤
│ v2 orchestration：task plan, restart, provenance, gates  │
├──────────────────────────────────────────────────────────┤
│ response algebra：units, axes, Voigt, BC, rank/residual  │
├──────────────────────────────────────────────────────────┤
│ symmetry engine：space-group representations/intertwiner │
├──────────────────────────────────────────────────────────┤
│ backend adapters：ABACUS first; VASP/CP2K/QE/ABINIT     │
├──────────────────────────────────────────────────────────┤
│ v1 foundation：polarization/BEC/Gamma IFC/Phonopy        │
└──────────────────────────────────────────────────────────┘
```

核心层不导入 calculator 专用输出解析器；adapter 把计算器结果转换为统一的
`Observation`。v1 模块作为稳定依赖，v2 只通过公开函数和文件格式连接，不复制其
大段逻辑。

## 2. 推荐模块边界（实现阶段）

建议继续扩展 `zstar/v2/` 命名空间；当前已实现的研究原型边界如下：

| 模块 | 责任 | 明确不负责 |
|---|---|---|
| `model.py` | 带单位的 quantity、tensor、boundary、provenance dataclass（draft 已实现） | calculator 解析 |
| `symmetry.py` | 空间群/点群表示、原子/应变 orbit、intertwiner basis（draft 已实现；force 复用 displacement，stress 使用 tensorial-Voigt） | SCF 运行 |
| `structure.py` | Cartesian 表示、允许响应子空间与 canonical 输入秩计划（draft 已实现） | 代替计算器能力验证 |
| `normalization.py` | 显式 2D sheet/1D line 极化几何归一化（draft 已实现） | 电静边界、低维 e/C 或 flexoelectricity |
| `finite_difference.py` | 实际向量、中心/单边差分、步长扫描和拟合（当前由 `fit.py` 提供） | 选择物理公式 |
| `mechanical.py` | stress/strain、C/S、稳定性和 Voigt 转换（draft 已实现） | 生成结构文件 |
| `piezo.py` | e、internal-strain、relaxed-ion 组合和 BC 检查（当前由 `algebra.py` 提供） | 计算电子响应 |
| `reconstruct.py` | 从已收集的 calculator-neutral `ResponseDocument` 拟合并追加带单位/轴/边界/诊断的 raw piezo、elastic、Gamma 和 Lambda quantities（draft 已实现） | proper-piezo 修正、BEC/IFC 规范或外部后端验证 |
| `ensemble.py` | 联合 polarization/force/stress/displacement task graph、v2 状态（draft 已实现） | 具体命令行 |
| `capabilities.py` | calculator-neutral 能力声明、维度/金属 Berry 安全门和可操作失败信息（draft 已实现） | 代替后端实际能力测试或物理验证 |
| `backends/abacus.py` | 调用既有 ABACUS/PYATB adapter 并收集输出；生产极化优先使用每个结构一次 PYATB，ABACUS Berry 仅作交叉审计 | 修改 ABACUS |
| `backends/{vasp,cp2k,qe,abinit}.py` | 能力声明和后续交叉验证 | 假设未验证能力 |
| `phase.py` | 参考相配对、插值、branch matching、路径检查 | 默认执行 NEB |
| `finite_temperature.py` | 外部 ML/q-NEP 数据导出/回读、统计分析 | 训练 ML 势 |
| `flexo.py` | 长波/表面规范可行性研究后再实现 | 用超胞差分冒充 bulk flexo |
| `resonant_raman.py` | 频率依赖电子响应接口（研究阶段） | 用展宽开关冒充共振 |

## 3. v2 响应记录草案

不修改 v1 `zstar-response` 1.0。v2 可采用独立 schema 名称或显式 major version，
例如 `zstar-v2-response`，最终名称在 schema 评审后冻结。每个 quantity 至少包含：

```yaml
name: piezoelectric
values: ...
unit: C m^-2
axes: [polarization_cartesian, voigt_engineering]
coordinate_system: cartesian_right_handed
voigt_convention: [xx, yy, zz, 2yz, 2xz, 2xy]
ion_relaxation: clamped-ion | relaxed-ion | internal-contribution
electric_boundary: E | D | open-circuit | short-circuit
mechanical_boundary: strain | stress
periodic_axes: [x, y, z]  # must match the document dimensionality
normalization: cell_volume | area | length | molecule
source: finite_difference | DFPT | postprocess
backend: abacus | vasp | cp2k | qe | abinit
provenance: { ... }
diagnostics: {rank: ..., residual: ..., condition_number: ...}
```

顶层还需要 structure hash、space-group/Hall、dimensionality、reference branch、
functional、pseudopotential/orbital、k mesh、cutoff、SCF thresholds、perturbation
vectors、task graph、restart state、CPU/wall-time 和失败事件。所有矩阵轴要能由
metadata 唯一解释；不允许匿名数组。`ResponseDocument` 会拒绝 quantity 的
`periodic_axes` 与顶层 `DimensionSpec` 不一致的文档，避免把 1D/2D/分子结果默认为
三维 bulk 响应。

v1 已验证的生产路径是：每个结构的 ABACUS SCF 导出实空间矩阵，随后一次 PYATB
运行在同一个 `POLARIZATION` 区块内部完成 a/b/c 三个 Berry loop，并在一个
`polarization.dat` 中写入三个方向的标量极化和量子。v2 现提供
`parse_pyatb_polarization`/`collect_pyatb_polarization`，保留这一 calculator-neutral
语义；应变 ensemble 仍需每个独立结构各运行一次 PYATB，但不为 a/b/c 各启动一次
ABACUS NSCF。branch matching 仍是独立的后处理步骤，不能从原始三个标量自动推断
自发极化。

PYATB 默认 writer 只有六位小数；有限差分必须沿用 v1 的 zstar.pyatb_precision
writer（不改变数值 kernel，只把同一结果保存为 16 位），并同时保留原始舍入文件。
未启用 precision writer 的输出只能用于流程/定性检查，不能作为小应变的定量张量。

ABACUS `gdir=1,2,3` NSCF collector 仍保留为可选 backend-audit lane：它适合核对
Berry 实现或在 PYATB 不可用时给出明确的替代路径，不是默认生产路线。该 lane 的
`polarization_gdir`/`polarization_quantum` 与可选方向 tuple 都保留原始来源；缺失
方向不补零，也不把 ABACUS 目录数量误报为独立材料响应数量。

ABACUS [官方 Berry phase 文档](https://abacus.deepmodeling.com/en/v3.6.2/advanced/elec_properties/Berry_phase.html)
把括号 tuple 定义为“沿所选晶格方向的 Cartesian components”，因此
三行 tuple 不是 `(x,y,z)` 标量向量。对于 PYATB 输出，a/b/c 标量必须结合
`input.json` 的晶格方向显式重建 Cartesian 极化；正交晶胞时退化为分量读取，非正交
晶胞必须解方向投影方程并检查 rank/condition number。这里不再把三个方向的标量或
tuple 机械相加作为通用坐标变换，也不做隐含分支选择。

当前 collector 对 `dimensionality < 3` 的 Berry 极化请求默认拒绝。只有显式传入
`normalize_low_dimensional=True` 才会在已声明周期轴和 slab/wire 边界下追加
`polarization_intrinsic`；原始 `C/m^2` 量仍保留为诊断值，不被重新解释。二维 slab
使用 `Omega/A` 高度，一维 wire 使用横截面积，分子体系仍拒绝 bulk Berry 极化。
低维归一化保持研究性，不进入稳定用户入口，也不自动开放低维 e/C 响应。

## 4. Task graph 和恢复

v2 采用 reference-first、serial-resumable 的图。`ResponseEnsemble` 还持久化
`dimensionality` 与 `periodic_axes`；低维任务不能依赖读取端的默认轴顺序。

```text
reference gate
  ├─ symmetry audit + capability audit
  ├─ displacement ± stages -> polarization + force
  └─ strain ± stages -> polarization + force + stress
              ↓
       constrained reconstruction
              ↓
      raw/projected tensors + diagnostics
```

状态文件放在 `.zstar/v2/`，每个 stage 记录 input hash、actual vector、SCF、collection、
fit 状态和错误。可复用 v1 的 `WorkflowStateStore` 设计和原子替换写入，但不得让 v2
状态覆盖 `.zstar/stages` 或改变 v1 `workflow.jsonl` 的语义。

`prepare_abacus_strain_ensemble` now hashes each serialized stage input (INPUT,
STRU/KPT and copied UPF/ORB assets) and stores a separate reference-input hash.
The collector verifies these hashes before parsing outputs.  Relaxed-ion
post-processing may replace `STRU` with `STRU_ION_D`; the immutable
`STRU_INITIAL` is used for verification in that case.  A mismatch stops
collection with a regenerate/restore action rather than silently combining
outputs produced from different inputs.

For relaxed-ion stages, the ABACUS collector retains both the first and final
`TOTAL-FORCE` blocks. `forces_initial` is explicitly labeled as the candidate
fixed-ion force response for a future Gamma fit; `forces` remains the final
ionic-convergence observable. A Gamma reconstruction must still verify the
initial block/`STRU_INITIAL` correspondence and cannot infer it from the final
zero-force block.

The calculator-neutral `fit_strain_force_coupling` API consumes the retained initial
force blocks and the actual serialized strain vectors to fit `Gamma = -dF/deta`. It
accepts either `(stage, atom, cartesian)` or flattened force observations, keeps the
force-unit convention explicit, and reports rank/residual diagnostics without claiming
that an unverified initial block is a complete Gamma/IFC result.
If a document declares `relaxed-ion` but lacks `forces_initial`, the reconstruction layer
rejects the final converged `forces` block instead of treating its near-zero values as Gamma.

The optional `symmetry_reduce=True` preparation path calls
`symmetry_adapted_input_plan`. It selects canonical strain directions from the
combined rank of the requested polarization, strain/stress, and (for relaxed
ion) internal-displacement intertwiner spaces. The selected vectors and rank
diagnostics are serialized in `ensemble.json`; the historical all-six-component
path remains available as an explicit control.

## 5. Backend capability contract

adapter 在准备阶段返回：结构读写、绝缘性门、polarization、force、stress、BEC、IFC、
homogeneous strain、relaxation、finite field/DFPT、低维边界的能力和单位。缺能力时
必须指出：

* 可由另一后端交叉验证；
* 可只完成 clamped-ion 或只完成电子项；
* 必须停止（例如金属 Berry polarization、没有开放方向 dipole）；
* 不得把缺失项填 0。

ABACUS 优先接入既有 `shared_abacus.py`/PYATB；VASP/CP2K/QE/ABINIT 只有当输入限制、
输出轴和边界条件均有测试后才提升 capability。运行时仍要检查可执行文件、版本、
赝势/轨道匹配和输出格式。

`collect_pyatb_strain_response` also honors an explicit
`ensemble.metadata.insulating: false` declaration and stops before reading
calculator outputs. This is a safety gate, not a band-gap calculation: the
adapter or user must supply the independently verified insulating status.

The collector remains bulk-normalized by default. An explicitly selected
`normalize_low_dimensional=True` path may append `polarization_intrinsic` for a
2D slab (`C/m`, periodic-plane projection and `Omega/A` height) or a 1D wire
(`C`, periodic-axis projection and transverse area). The geometric factor,
projection, periodic axes, and boundary-condition label are serialized in the
quantity provenance. This is a normalization/inspection path only: it does
not establish an open-boundary electrostatic solution or authorize 1D/2D
piezoelectric, elastic, flexoelectric, or molecular-polarization claims.

## 6. CLI 设计门

第一轮不增加 CLI。后续顺序必须是：

1. Python API + dataclass + 合成响应测试（已开始，仍属研究 API）；
2. ABACUS dry-run/小规模 smoke test；
3. 断点/失败/单位/rank 回归；
4. 再设计 `zstar piezo pre/run/stat/post` 和 `zstar elastic ...`；
5. `phase`、`finite-temperature`、`flexo`、`resonant` 各自独立 gate，不共享未验证
   的 CLI 参数。

CLI manifest 必须含 `api_version`/`schema_version`，并与 v1 canonical family 分开；
旧命令继续路由到 v1，不能把 v2 参数注入旧命令产生隐式行为变化。

## 7. 阶段门和论文边界

* Gate A：文献、公式、schema、对称约化算法审阅通过；无代码。
* Gate B：合成响应和 rank/residual/units 测试通过；只允许研究 API。
* Gate C：ABACUS clamped-ion/relaxed-ion 小胞 + 独立后端核对通过；才可称为 v2
  electromechanical prototype。
* Gate D：代表性案例、效率和失败率完整记录；才可写入 v2 论文的 implemented 部分。
* finite-T、phase switching、flexo、resonant Raman 在各自 Gate 未通过前只写 roadmap，
  不写成论文结果或稳定功能。
