# ZStar v2 测试、验证和 benchmark 计划

**范围：**第一轮只定义可执行的测试和证据门；不提交大规模计算。

## 1. 测试金字塔

### 1.1 纯数学/合成响应（无 calculator）

生成已知 `Z*`、`Phi`、`Gamma`、`e0`、`C0` 的响应，作用任意空间群表示并验证：

* 约束最小二乘在满秩时恢复输入张量；
* 对称禁止分量严格为零，允许但很小的分量保持 `allowed_but_small`；
* `rank`/条件数/残差和缺失方向可解释；
* `e = e0 + qe/Omega * Z* Lambda`、
  `Crel = C0 - Lambda^T Phi Lambda/Omega` 数值一致；
* e/d/g/h 转换往返误差低于浮点和给定输入误差；
* BEC/IFC 轴转置、Voigt engineering shear 和 Cartesian rotation 可逆。

### 1.2 结构和对称性

使用 Pm-3m、P4mm、P6_3/mmc/P6_3mc、Pnma 和 P1 五类结构，再加低维 slab/wire
与分子。每一类检查：空间群/Hall 稳定性、原子映射双射、位移和应变 orbit、允许
子空间秩、完整采样任务数和 all-atom control 的一致性。

### 1.3 数值差分

对每个 synthetic model 和至少一个小型真实输出做 `0.5h/h/2h` 步长扫描；比较
forward 与 central 收敛阶，使用 actual serialized vector 作分母；记录 SCF 噪声、
Berry branch jump、condition number 和 residual。故意删除一个 stage，验证错误信息
给出最少新增 ± 扰动。

### 1.4 单位和边界

覆盖 Å↔m、eÅ↔C m、eV/Å↔N、GPa↔Pa、relative epsilon↔absolute epsilon；覆盖 bulk、
2D sheet、1D line 和 molecule normalization。对 slab 改变真空高度，intrinsic sheet
量应收敛而真空稀释 3D 量应被明确标记；分子应拒绝 bulk piezo/elastic 入口。

### 1.5 失败和安全性

* 金属/零带隙、缺失 STRU/INPUT/KPT、SCF 未完成；
* 非唯一赝势/轨道、输入 hash 改变、原子排序改变；
* spglib dataset 为 `None`、对称操作混合周期/开放方向、磁性或带电胞；
* stress 缺失、± stage 不成对、rank 不足、residual 超阈值、机械不稳定；
* backend command 不可用、非零退出、重启后不得重复已完成 stage。

每个失败测试都要断言“原因 + 最小解决动作 + 保留日志/状态路径”。

### 1.6 v1 回归

每次 v2 提交运行当前完整 suite，并固定基线：`394 passed`（当前工作区，含 1114 个
依赖弃用警告）。测试必须验证 v1 canonical CLI、`response.json` 1.0、Unified
`shared_response.json`、旧案例和旧命令 alias 没有行为变化；v2 新 schema 不能让 v1
reader 接触到未知字段后崩溃。

## 2. 代表性验证矩阵

| 案例 | 目的 | 首要证据 | 交叉证据 |
|---|---|---|---|
| cubic BaTiO3 | 立方禁戒项、非极性参考、C/e 约束 | ABACUS finite difference | ABINIT/VASP 或文献 |
| tetragonal PbTiO3/HfO2 | 极性轴、proper e、relaxed-ion | ABACUS | VASP/ABINIT |
| SiC | 非铁电极性响应参考、BEC/IFC | ABACUS | VASP |
| 低对称 P1/Pnma | 近乎无约化、6 应变满秩 | ABACUS synthetic+smoke | ABINIT |
| monolayer hBN/MoS2 | sheet normalization、面内 e/C、真空扫描 | ABACUS + cube | VASP/文献 |
| alpha-In2Se3 | 2D 极性、面外边界和相比较 | ABACUS | 文献/独立后端 |

每个真实案例都要保存 `inputs/`、`run/`、`results/`、赝势/轨道、`provenance.json`，
并给出结构/空间群、绝缘性、独立扰动数、polarization/force/stress/BEC/phonon、
piezo/elastic/internal-strain、tensor symmetry、rank/residual、稳定性、单位换算和
文献/独立结果差异。真实计算之前先完成单 stage smoke test。

## 3. 正确性与效率指标

每个 benchmark 至少记录：

```text
independent_first_principles_tasks
total_scf_iterations
postprocessing_tasks
cpu_core_hours, wall_time, nodes, MPI, OpenMP
max_tensor_error, rank, residual, condition_number
symmetry_forbidden_max, ASR/reciprocity error
failed_stages, restart_count
separate_control_cost, v2_cost, efficiency_ratio
```

效率提升只有在相同 functional、cutoff、k mesh、SCF threshold、扰动幅度和收敛标准下
报告，并同时报告绝对 core-hours、失败重跑成本和张量最大误差；不能只报 speedup。

## 4. 计算资源和提交门

本轮不访问 235、不提交 cu20/cu23/cu24/cu25/cu26 任务。进入小规模验证阶段后：

1. 先查询这些节点的当前队列和负载，只选明确空闲且不抢占他人任务的节点；
2. 单 stage smoke test 通过后再扩展 ± strain/relaxation；
3. 每个任务记录节点、核数、MPI/OpenMP、开始/结束时间和日志；
4. 使用 `.zstar/v2/` 状态断点续算，失败保留输入/日志，不盲目重复提交；
5. 结果同步到案例 `provenance.json`，临时目录和大缓存不入 Git。

## 5. 阶段性验收门

* **A（本轮）**：文献、理论、对称方案、架构和测试计划完成；无大计算；满足。
* **B**：所有 synthetic symmetry/units/rank/residual/failure tests 通过，v1 回归全绿；
  当前 draft model/algebra/structure/ensemble 测试已通过，但 schema 评审和 failure
  contract 仍未冻结，因此只记为 **B-in-progress**。
* **C**：ABACUS 两个晶系的 clamped-ion/relaxed-ion smoke + 步长扫描通过，schema
  和 provenance 完整。
* **D**：至少 cubic、tetragonal、hexagonal、orthorhombic/低对称、2D 五类真实验证，
  有独立后端或可靠文献对照，效率和误差同时达标。
* **E**：仅在 D 之后设计并公开 `piezo`/`elastic` CLI；phase/finite-T/flexo/resonant
  继续各自走理论与证据门。
