# ZStar v2 三个 3D 体系验证矩阵（2026-09-14）

本矩阵回答“计算是否完成”和“科学验证是否完成”两个不同问题。对象是当前
3D bulk 扩展批次的 wurtzite AlN、wurtzite ZnO 和 zinc-blende GaAs；wurtzite
GaN 是此前冻结的首个候选 benchmark，单独记录在
[`v2_piezo_benchmark_gate.md`](v2_piezo_benchmark_gate.md)，不在本表重复计数。

## Gate 定义

* **G0 计算闭环**：reference + 六个工程应变分量的实际 `+/-` 结构齐全，13 个
  ABACUS stage 和 13 次 PYATB 后处理完成；每次 PYATB 同时读取三个 Berry 极化
  方向；无未处理 branch shift。
* **G1 数据/可复现性**：输入哈希、实际 cell/应变、force、stress、polarization、
  单位/Voigt/边界标签和 provenance 齐全。
* **G2 机械检查**：弹性矩阵对称化后正定，并保存特征值和拟合诊断。
* **G3 响应闭合**：proper piezo、elastic、Gamma force--strain coupling 和
  internal-strain 都通过 persisted symmetry intertwiner 的 rank/residual 审计。
  其中 raw 张量从不因投影而被替换；`allowed_subspace_violation` 不能标为通过。
* **G4 外部核验**：至少一组原始理论文献和一组实验/数据库值完成逐分量的单位、
  轴向、坐标手性、泛函及 clamped/relaxed 边界匹配；必要时有独立后端或高精度
  参考。

物理空间群和准备/收集流程统一使用 v2 固定 `symprec=1e-3`。这不是把数值残差
“调到通过”：响应 residual 仍按独立的预先声明 gate 审计。

## 结果矩阵

| 体系 | 计算资源/闭环 | G0 | G1 | G2 | G3 响应闭合 | G4 文献/独立核验 | 当前结论 |
|---|---|---:|---:|---:|---|---|---|
| wurtzite AlN (`P6_3mc`) | HF，13 stage + 13 PYATB | PASS | PASS | PASS；最小特征值 112.25 GPa | **CONDITIONAL**：proper piezo、elastic、Gamma coupling 通过；internal-strain 仍约 3.19% 投影残差 | PENDING | 计算完成，不能作为最终材料常数 |
| wurtzite ZnO (`P6_3mc`) | 235/cu17，40 MPI×1 OMP，13 stage + 13 PYATB | PASS | PASS | PASS；最小特征值 39.87 GPa | **FAIL/CONDITIONAL**：proper piezo 相对投影残差约 0.71%（raw fit residual 14.2%）；Gamma 已通过，internal-strain 仍约 2.94% 投影残差 | PENDING | 需要响应质量审计/必要时重算 |
| zinc-blende GaAs (`F-43m`) | HF，13 stage + 13 PYATB | PASS | PASS | PASS；最小特征值 56.12 GPa | **PASS（内部）**：四类响应均 `consistent`；proper piezo 投影相对残差约 `5.9e-6` | PENDING | 最接近可升级的研究 benchmark，但仍非稳定功能 |

数值来自各案例 `results/summary.json`；完整矩阵、张量、输入协议及文献锚点见
[`v2_piezo_benchmark_report_20260914.md`](v2_piezo_benchmark_report_20260914.md)。

## 归档可复现性复核

2026-09-14 对三个案例分别从原始 ensemble 目录重新运行了 post-processing
collector（输出写入 `tmp/recollect-*`，没有启动 ABACUS/PYATB）。AlN、ZnO、GaAs
均重新得到 13 个 stage、13 次 PYATB、`branch_shift_max=0`、机械稳定性为真，且
`e`、`C`、`Lambda`、Gamma 四个张量与案例归档逐元素最大差为 `0.0`。因此 G0/G1
的结果归档链条是可重放的；这项检查不等同于 G3/G4 的物理正确性或文献一致性。

## 逐体系关键数值

| 体系 | proper `e`（C/m²） | `d`（pm/V） | branch residual 最大值（C/m²） | 参考态最大力（eV/Å） |
|---|---|---|---:|---:|
| AlN | `e31=e32≈−0.723`, `e33≈1.696`, `e15≈−0.374` | `d31≈−2.75`, `d33≈6.43`, `d15≈−3.33` | 2.40e-3 | 1.39e-4 |
| ZnO | `e31≈−0.602/−0.615`, `e33≈1.266`, `e15≈−0.472/−0.478` | `d31≈−5.82/−6.00`, `d33≈12.38`, `d15≈−11.82/−11.99` | 1.60e-3 | 7.64e-4 |
| GaAs | `e14=e25=e36≈−0.262715` | `d14≈−4.682` | 2.63e-4 | 0 |

这些数值只代表当前 PBEsol/Dojo-NC-FR/100 Ry/指定晶格和应变幅度下的研究结果。
它们不能脱离坐标手性、工程剪切约定、proper/improper 选择和电学/力学边界条件
直接与文献单个数字比较。

## 进入下一阶段的条件

1. **先修算法质量，不先扩 CLI**：共同不变度量 Cartesian 表示已修正 AlN/ZnO
   Gamma 的假阳性违例；仍需定位 internal-strain 的真实残差来源（原子对应、力的
   坐标约定、弛豫后的内部位移和 acoustic gauge），并用离线完整采样或新的受限
   重建测试证明修复有效。
2. **再做外部核验**：逐分量完成 AlN、ZnO、GaAs 的文献表格，统一 `e`/`d`、轴向、
   符号和 clamped/relaxed 边界；不为了“对上文献”任意改坐标或删分量。
3. **最后才升级状态**：只有 G0--G4 全部通过，且 v1 回归测试保持通过，案例才
   能从 `completed_research_gate_pending_literature_audit` 升级为可发表的研究
   benchmark；稳定 CLI、手册和 v2 论文仍需另行 gate。

## 相关物理审计边界

BEC/IFC、Gamma acoustic gauge、`Z*Lambda` 内应变贡献以及 stress work-conjugacy
是相互关联但不等价的规范检查；它们不能用单一空间群阈值替代，也不能因为
proper `e` 已拟合良好就自动视为全部通过。
