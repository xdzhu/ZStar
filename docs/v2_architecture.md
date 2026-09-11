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
| `symmetry.py` | 空间群/点群表示、原子/应变 orbit、intertwiner basis（draft 已实现） | SCF 运行 |
| `finite_difference.py` | 实际向量、中心/单边差分、步长扫描和拟合（当前由 `fit.py` 提供） | 选择物理公式 |
| `mechanical.py` | stress/strain、C/S、稳定性和 Voigt 转换（draft 已实现） | 生成结构文件 |
| `piezo.py` | e、internal-strain、relaxed-ion 组合和 BC 检查（当前由 `algebra.py` 提供） | 计算电子响应 |
| `ensemble.py` | 联合 polarization/force/stress/displacement task graph、v2 状态（draft 已实现） | 具体命令行 |
| `backends/abacus.py` | 调用既有 ABACUS/PYATB adapter 并收集输出 | 修改 ABACUS |
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
periodic_axes: [x, y, z]
normalization: cell_volume | area | length | molecule
source: finite_difference | DFPT | postprocess
backend: abacus | vasp | cp2k | qe | abinit
provenance: { ... }
diagnostics: {rank: ..., residual: ..., condition_number: ...}
```

顶层还需要 structure hash、space-group/Hall、dimensionality、reference branch、
functional、pseudopotential/orbital、k mesh、cutoff、SCF thresholds、perturbation
vectors、task graph、restart state、CPU/wall-time 和失败事件。所有矩阵轴要能由
metadata 唯一解释；不允许匿名数组。

## 4. Task graph 和恢复

v2 采用 reference-first、serial-resumable 的图：

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
