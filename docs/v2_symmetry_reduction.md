# ZStar v2 任意空间群对称性约化方案（第一轮）

**状态：算法设计和验证计划；尚未接入 v1 CLI**
**依赖基线：** v1 的 `spglib`/Phonopy 结构识别、`shared_response.py` 的联合
BEC/力常数拟合以及可恢复 workflow state。

## 1. 目标和不变量

给定参考结构 \(R_0=(h,s_a,Z_a)\)、空间群操作 \(g=(W_g,t_g)\) 和计算边界条件，
需要生成一个最小但完备的扰动集合，使 polarization、force、stress 和 displacement
response 可以在同一个线性模型中重建。约化只允许使用实际 Hamiltonian、化学种类、
磁序和电静边界都保持不变的操作；“坐标看起来对称”不足以建立等价类。

不变量如下：

* 原子排序、元素/同位素标签、晶胞和周期轴在 reference 与每个 stage 中一致；
* Cartesian 旋转由晶格 metric 从 fractional `W_g` 转换得到，并检查正交性；
* 每个独立扰动保存真实序列化向量，而不是只有名义幅度；
* 对称性约化失败时退回 all-atom/all-component 采样，禁止静默使用错误映射；
* `rank`、条件数和 residual 是每个张量的强制诊断，不是可选日志。

## 2. 群作用和响应表示

空间群操作给出原子置换 \(p_g\) 与 Cartesian 旋转 \(R_g\)。位移、力和极化向量
的表示分别为

```text
(D_u(g) u)_[p_g(i)] = R_g u_i
(D_F(g) F)_[p_g(i)] = R_g F_i
D_P(g) P = R_g P
```

应变是对称二阶张量：\(D_\eta(g)\eta=R_g\eta R_g^T\)。在工程 Voigt 基底中用
一个由这条关系生成的 6x6 矩阵 `V(g)`，而不是手写晶系分量表。stress 用同一
张量作用后再应用 engineering-shear 的度量因子。

一个线性响应算子 \(L\)（例如 `dP/du`、`dF/du`、`dP/deta` 或 `dstress/deta`）
必须满足 intertwining 约束

```text
L D_input(g) = D_output(g) L    for every accepted g.
```

因此允许的响应空间是所有群操作的固定子空间/交织子空间。用群平均投影
`Pi(L) = (1/|G|) sum_g D_output(g) L D_input(g)^T` 可得到理论允许的张量；实际
计算则在该子空间中做最小二乘拟合，保留未投影 residual 以审计数值误差。

## 3. 独立扰动的生成

### 3.1 原子和位移

1. 用 `spglib.get_symmetry_dataset` 得到 `equivalent_atoms`、`rotations`、
   `translations`；用元素/同位素/磁标签过滤允许操作。
2. 对每个等价类选 canonical representative（原始排序中最小 index）。
3. 对 representative 的每个 seed 方向 `e_beta`，计算 site stabilizer
   `G_i={g | p_g(i)=i}` 的轨道 `{R_g e_beta}`，用 QR/SVD 取独立基。
4. 若三维位移空间的秩不足 3，则添加一个确定性、与已有方向正交的 seed；若仍不足，
   报告 `rank < 3` 并改用显式 Cartesian 三方向，而不是猜测缺失分量。
5. 为每个方向生成 `+/-` 结构（central）或单边结构（forward），并从写出的结构
   重新读取 \(\Delta u\)。

site stabilizer 只用于旋转响应，不把不同 Wyckoff site 的原子合并；原子等价类由
完整 `p_g` 决定。

### 3.2 应变

1. 生成六个工程 Voigt canonical seed。
2. 对每个响应输出表示（polarization、stress/strain 或 internal displacement）
   建立 intertwiner null-space。对一个候选应变 (v)，把所有允许基矩阵作用后的
   输出列堆成 design block；按 canonical index 贪心保留能增加联合系数秩的方向。
   这给出“在 canonical seed 集合内”的最小可识别集合，而不是未经证明的晶系特例。
3. 对多个输出取 block-diagonal 联合秩：clamped-ion 至少联合 polarization 与
   strain/stress；relaxed-ion 再加入 displacement。若 `identified_rank` 小于允许
   参数总数，停止并返回需要补充的方向，不得零填充。
4. 形变晶胞为 `h'=(I+eta)h`；clamped-ion 保持分数坐标，relaxed-ion 在每个
   image 独立弛豫并记录最终坐标和残余力。
5. 对 stress、polarization 和 internal displacement 同时应用设计矩阵；应变
   response 的完整重建要求采样矩阵覆盖所有对称允许列。
6. 对 2D/1D 只在周期应变子空间生成任务；开放方向分量若需要定义，必须另有 slab/
   wire 边界模型，不得从 bulk 约化表借用。

当前 draft API `symmetry_adapted_input_plan(report, input_kind="strain", output_kinds=...)`
实现了上述 rank 选择，返回 canonical vectors、selected indices、各输出允许秩、
identified rank、容差和 `complete` 标志。`prepare_abacus_strain_ensemble` 通过
`symmetry_reduce=True` 采用这个计划；默认仍保留显式六分量路径以便与已有审计和 all-
component control 对照。P4mm BaTiO3 的联合 `(polarization, strain, displacement)`
计划由 6 个分量降为 `(xx, zz, 2yz, 2xy)` 4 个方向（8 个正负 stage），允许秩为
`3+7+14=24` 且 identified rank 为 24；P1 则保留全部 6 个应变分量。

### 3.3 联合 response ensemble

对每个 stage 写入：

```json
{
  "stage": "strain-003+",
  "perturbation": {"kind": "strain", "vector": [..], "unit": "1"},
  "actual_vector": [..],
  "reference_hash": "...",
  "expected_outputs": ["polarization", "forces", "stress"]
}
```

位移和应变可以共享同一个 SCF reference 与 provenance，但不能因为“共享”而跳过
所需的 polarization/force/stress 输出。V1 的 `.zstar/stages/*.json` 可作为状态
实现参考；v2 应在 `.zstar/v2/` 命名空间保存自己的 manifest，避免读写 v1 stage。

## 4. 线性重建、rank 和 residual

把所有观测堆成 `Y`，把实际扰动向量堆成 `X`。无约束拟合是

```text
J_hat = argmin_J || W^(1/2) (X J - Y) ||_2
```

受对称性约束时，先用 null-space/SVD 得到允许参数基 `B`，拟合 `J=B c`；也可把
每一条 intertwining 约束放入增广线性系统。报告至少包含：

* `input_rank`、`allowed_rank`、`fit_rank`；
* 最小/最大奇异值、条件数、SVD cutoff；
* raw residual 的 max、RMS、相对 Frobenius 值；
* 群约束违例（投影前/后）；
* ASR、应力/力平衡、Hessian reciprocity；
* 实际 stage 数、缺失 stage、重启次数。

完备性条件是 `fit_rank == allowed_rank` 且 residual 小于输入收敛误差传播后的阈值。
`rank` 不足必须是 actionable error：指出缺哪些扰动方向、建议的最小新增 stages，
并保留已经完成的结果。

严格禁止的分量由群投影的零空间判定（理论上为零）；拟合后“数值上很小”但投影
允许的分量必须标为 `allowed_but_small`，不能写成 `symmetry_forbidden`。

## 5. 空间群识别不稳定和非标准晶胞

* 在 `symprec` 候选网格（例如 `1e-6 ... 1e-2 Angstrom`）重复识别；要求国际符号、
  Hall number、原子映射和周期子空间在容差窗口内稳定。
* 若结构优化留下微小破缺，默认使用实际低对称结构；只有用户明确选择
  `idealize_reference` 且能量/坐标偏差通过阈值检查时才允许升高对称。
* 若 `spglib` 返回 `None`、映射非双射、元素标签冲突、旋转非正交、操作混合周期与
  开放方向，状态为 `symmetry_untrusted`；可继续 all-atom 采样，但不得 symmetry
  reconstruct。
* 非标准晶胞先在 Cartesian metric 中验证操作，再记录原胞/常规胞变换矩阵；完整
  tensor 输出统一到用户声明坐标系，不能混用 fractional rotation。
* 磁性、带门控外场、带电胞或自旋轨道耦合只在 backend 明确提供相应磁空间群/场
  对称时约化；当前 v1 的非磁性限制应原样保留并在 v2 preflight 中说明。

## 6. 低维和分子处理

`dim=3` 可使用完整三维空间群。`dim=2` 要求操作保持 slab normal 和周期平面，
`dim=1` 要求操作保持 wire 轴；现有 v1 对“混合周期/开放方向”的拒绝逻辑应升级为
可解释的 capability check。开放方向的极化、stress 或 flexo 只有在相应电静边界
和归一化实现后才允许进入 allowed subspace。`dim=0` 不调用周期空间群约化，改由
分子点群和刚体平移/旋转投影处理；bulk e/C/equation-of-state 不自动定义。

## 7. 伪代码

```text
analyze(structure, dimensionality, boundary, symprec_grid):
    candidates = identify_symmetry_datasets(structure, symprec_grid)
    dataset = choose_stable_dataset(candidates) or untrusted
    ops = validate_operations(dataset, species, magnetic_state, boundary)
    if untrusted or invalid(ops):
        return all_atom_plan(status="symmetry_untrusted")

    atom_orbits = canonical_atom_orbits(ops)
    U_atom = independent_stabilizer_orbits(atom_orbits, ops)
    allowed_basis = intertwiner_nullspace(ops, input_axes, output_axes)
    E_strain = symmetry_adapted_input_plan(
        report, input_kind="strain", output_kinds=required_outputs
    )
    assert E_strain.complete
    plan = plus_minus_stages(U_atom, E_strain.vectors, actual_vector_required=True)
    assert rank(plan.design_matrix) >= sum(E_strain.allowed_ranks.values())
    return plan, symmetry_report(ops, atom_orbits, E_strain, allowed_basis)

reconstruct(observations, report):
    validate_hashes_and_atom_order(observations)
    J = constrained_weighted_lstsq(observations, report.allowed_basis)
    diagnostics = rank_residual_asr_reciprocity(J, observations, report)
    if diagnostics.fit_rank < diagnostics.allowed_rank:
        raise IncompleteSampling(actionable_missing_directions(diagnostics))
    return raw_and_projected(J, diagnostics)
```

## 8. 失败条件和最小恢复动作

| 失败 | 不允许的行为 | 最小恢复动作 |
|---|---|---|
| `spglib=None/None dataset` | 假设高对称或静默丢 stage | all-atom 计划，或调整 `symprec` 后重新审计 |
| 原子映射非双射/跨元素 | 合并不等价原子 | 检查排序、分数坐标和元素标签 |
| 周期/开放方向被旋转混合 | 当作 3D bulk 处理 | 降低操作集合或使用兼容边界 |
| `rank < allowed_rank` | 用零填充缺列 | 生成诊断建议的最少新增 ± stages |
| residual 超阈值 | 只输出对称化张量 | 保留 raw，检查 SCF、branch、step 和坐标 |
| 微小破缺导致 dataset 跳变 | 强制升高空间群 | 使用实际低对称或用户确认 idealization |

## 9. 五类以上测试方案

1. **Cubic**：Pm-3m BaTiO3 或 diamond Si；验证三轴等价、立方弹性 3 参数和
   对称禁止压电分量。
2. **Tetragonal polar**：P4mm PbTiO3/HfO2；验证 `e_33/e_31/e_15` 允许项、
   极性轴和 improper/proper 修正。
3. **Hexagonal**：P6_3/mmc hBN（非极性）与 P6_3mc 参考（极性）；验证六方
   应变轨道、2D 周期平面和面外边界拒绝。
4. **Orthorhombic**：Pnma 结构；验证低等价类、剪切 Voigt 因子和非对角 IFC。
5. **Triclinic/低对称**：P1 合成晶体；无约化或仅恒等操作，6 个应变和全部独立
   位移必须达到满秩。
6. **Symmetry-breaking sweep**：对上述结构人为施加 1e-6--1e-2 Å 破缺，检查
   dataset 稳定性报告和 all-atom fallback。
7. **低维/分子**：单层 MoS2、hBN、z-wire 和 H2O；检查周期/开放轴、真空归一化、
   刚体模投影及禁止 bulk piezo/elastic 的错误入口。

每个测试都使用合成线性响应（已知 `J`）先验证 exact reconstruction，再用小规模
calculator 输出验证单位、SCF 噪声下的 residual 阈值；对称性关闭后的全采样只作为
内部审计控制，不作为 v2 用户方法名称。
