# VASP原生内应变与离子贡献审计，2026-09-18

## 范围与状态

仅使用已经完成的AlN原生验收档案、GaN原任务、GaN单次对称性控制、ZnO恢复任务。
没有新增DFT任务、精度升级、修改native结果、改变验收门或重跑参考优化。
GaN/ZnO原生d拒绝原因保持原样；以下研究诊断值不能填入已验收benchmark或论文主表。
原生GaN控制已正常结束，但原始displaced-atom平移残差仍未过现有1e-3门。

## 复用的模型和单位

复用v1 `project_response`，显式将BEC施加charge-neutral projection、
Phi施加reciprocity/equal-weight translation projection；
复用v2 `remove_acoustic_translation`、`solve_internal_strain_response`、
`relaxed_piezoelectric`、`relaxed_elastic`，不另写新的BEC/IFC规范或逆矩阵算法。

本研究计算单位胞总能量Hessian定义Gamma，区别于VASP force-response Xi：

```text
Gamma_ZStar = d²E_total/du/deta = -dF/deta = -Xi_VASP
Lambda = Phi_optical^+ Xi_optical
e_ion = (elementary_charge / volume) Z_projected Lambda
C_ion = -Xi_optical.T Phi_optical^+ Xi_optical / volume
e_total = e_clamped + e_ion
C_total = C_clamped + C_ion
d_diagnostic = e_total (C_total in Pa)^-1
```

Phi为eV/Å²，Xi为eV/Å，Lambda为Å/engineering-strain，Z为单位e的数值，
Z索引为[atom,polarization,displacement]，Voigt为[xx,yy,zz,2yz,2xz,2xy]。
参考体积从Å³在函数边界转换为m³；弹性修正从eV/Å³转换为GPa。
诊断d先由Pa得到C/N，再转换为pm/V数值（等于pC/N数值）。
离子弹性贡献取负的依据为Wu/Vanderbilt/Hamann原论文Eq.(15)，
而非直接复制不同软件文档中的符号记法；伪逆须排除平移零模，
见该论文Eq.(14)–(16)后续讨论。
[原文，PRB72,035105(2005), DOI10.1103/PhysRevB.72.035105](https://www.physics.rutgers.edu/~dhv/pubs/local_copy/xfw_sys.pdf)。
VASP force-response Xi的定义参见
[官方静态线性响应文档](https://vasp.at/wiki/Static_linear_response:_theory)。
该页面的C离子项展示符号与原论文Eq.(15)不同，本审计以能量消元及原论文为准。
符号由这些定义和原生内部闭合检查，不通过选择文献匹配符号。

AlN的Phonopy BORN仅含两个不等价原子，不能直接作为四原子完整数组，
也不简单复制来扩充。使用原生`vasp_bec.json`的all_atoms档案，
核对编号及Al/Al/N/N顺序，将其明确的[displacement,polarization]逐原子转置。
GaN/ZnO实际BORN为四原子完整且文件头明确[polarization,displacement]。
所有源文件及平衡结构哈希均记录在证据JSON；不使用响应末帧位移结构。

## 与原生离子贡献的完整矩阵重现

四例Phi光学秩均为9、全部九个光学本征值为正；
投影后Phi/Gamma声学兼容与Lambda平衡检查通过。
使用displaced-atom route的重现结果如下，均比较完整矩阵，不只e33。

| 档案 | e_ion最大差 C/m² | e_ion相对Frobenius差 | C_ion最大差 GPa | C_ion相对Frobenius差 |
|---|---:|---:|---:|---:|
| AlN，已验收 | 5.433e-6 | 5.788e-6 | 4.949e-5 | 5.692e-7 |
| GaN，原任务 | 6.558e-6 | 6.106e-6 | 4.629e-5 | 7.386e-7 |
| GaN，对称性控制 | 4.260e-6 | 3.586e-6 | 6.342e-5 | 8.870e-7 |
| ZnO，原任务 | 5.568e-6 | 5.025e-6 | 7.664e-5 | 1.348e-6 |

这直接支持这些档案的单位、索引、Xi到Gamma符号、体积及原生contraction来源。
它是同源内部重现，不是独立第一性原理精确性验证，也不是普适后端验证。
平移残差不可以直接当成最终张量相对误差；
native输出与光学子空间公式相容，但不据此声称已检查VASP内部源码实现。

## 两条导数路线的敏感度，不是验收替换

改用投影后的strained-cell Xi，重建结果相对原生离子项最大差为：

| 档案 | e_ion最大差 C/m² | C_ion最大差 GPa |
|---|---:|---:|
| AlN，已验收 | 0.005287 | 0.44521 |
| GaN，原任务 | 0.007008 | 0.41710 |
| GaN，对称性控制 | 0.004365 | 0.26066 |
| ZnO，原任务 | 0.006123 | 0.40594 |

另检查displaced/strained混合导数的弹性contraction，它比同displaced-route
的重现误差明显大，因此不能把原生ionic e/C描述为该混合重建。
保留混合矩阵与major symmetry诊断，不将其替换为正式C。
电子与离子压电项相消时，总e的相对敏感度会高于离子项自身的相对敏感度；
不能只根据Gamma或离子项的相对变化断言总e已经收敛。

下表仅为每条路线上相容的e/C求解得到的代数d33诊断，均不改变native门：

| 档案 | displaced route pm/V | strained route pm/V |
|---|---:|---:|
| AlN，已验收档案的重建检查 | 5.324398 | 5.355360 |
| GaN，原任务 | 1.577099 | 1.600457 |
| GaN，对称性控制 | 1.583040 | 1.601599 |
| ZnO，原任务 | 9.714688 | 9.779863 |

AlN原生已验收d33=5.324396，重建差约2.1e-6 pm/V。
所有诊断e/d/C闭合检查通过；该代数闭合不能提供截断误差或绝对准确性证明。
de Jong数据库未直接提供d或C，不给这些诊断d33制造数据库差值。

## 对后续动作的科学约束

原始Gamma平移残差、光学互易性差异、最终响应敏感度和外部差异是不同指标。
现有raw-Gamma 1e-3拒绝门不能被解释为“超过它就证明d的误差过大”。
反过来，同源contraction重现也不足以直接撤销该门并提升为稳定功能。
先等待独立ABACUS中心应变e/C/d对照，再评估生产门应如何区分
raw translation warning、明确投影、光学完备性与响应容差。
不因为原生门未通过就自动提高EDIFF或再跑同样的IBRION6任务。

## 可复现证据与测试

运行`.codex-output/audit_native_ionic_contractions.py`，输出
`outputs/pbe_database_comparison_20260918/native_ionic_contribution_reconstruction_audit.json`。
JSON包含完整矩阵、各route、d诊断状态、源哈希、单位、模型、投影幅度、秩与残差。
`native_acceptance_changed=false`，`new_DFT_calculations=0`。
uncertainty-and-units skill促使本审计明确区分确定性敏感度与测量不确定度；
输入分布/自由度未知，standard_uncertainty=null，不编造±或置信区间。
Pint未安装，不改变科学环境；使用既有显式单位层。
该skill的静态单位审计0 findings、无suppression；这是启发式检查，不是物理证明。
脚本的实际秩、光学正性、声学兼容、完整数组、原子顺序与e/d/C闭合断言全部通过。

## PTO 五原子原生档案扩展审计

运行同一脚本的`--pto`仅审计新PTO，不覆盖上文四原子审计档案。
复用v1投影、v2内应变求解和单位转换，不增加DFT或修改任何native拒绝门。
完整五原子BORN与FORCE_CONSTANTS匹配输入原子顺序；光学子空间rank12，
最小光学Phi特征值2.133431705 eV/Å²，全部12个光学方向为正。
BEC投影最大2.0e-6 e，IFC投影Frobenius相对幅度1.75585e-4。
两条路线内部平衡相对残差分别2.12e-16、2.21e-16，d/e/C闭合通过。

| 路线 | 对native e_ion最大差 C/m² | 对native C_ion最大差 GPa | 诊断d33 pm/V |
|---|---:|---:|---:|
| displaced atoms | 6.9731e-6 | 5.8395e-5 | 63.829746 |
| strained cells | 0.0379621 | 1.0053993 | 63.349783 |

strained-route对displaced-route的d33变化为−0.75194%，
mixed-route对native C_ion最大差0.5080282 GPa。
再次支持现有原生ionic e/C的同displaced-route重建解释，未发现符号/单位错配。
raw平移残差0.00106288793不是0.1063%的d误差估计；
同源重建和两路线敏感度也不是独立精度证明，两个d33仍为诊断值，不入验收表。
详细完整矩阵与哈希见`PTO_native_ionic_contribution_reconstruction_audit.json`。
uncertainty-and-units静态审计0 findings、无suppression；Pint仍未安装，
沿用已测试单位层，不升级环境、不编造统计不确定度。

## 完整总e/C/d的路线敏感度：不能只看d33

仅读取上述五个已有档案，以共同投影Phi/Z和两条Xi路线计算完整总张量差。
不增加DFT、不改变native拒绝门、不把诊断d写入已验收案例表。

| 档案 | 总e最大差 C/m² | 总C最大差 GPa | 总d最大差 pm/V | d33路线有符号变化 % |
|---|---:|---:|---:|---:|
| AlN已验收档案 | 0.00528715 | 0.445235 | 0.0309618 | +0.58151 |
| GaN原任务 | 0.00700721 | 0.417121 | 0.0233580 | +1.48107 |
| GaN对称性控制 | 0.00436826 | 0.260665 | 0.0185591 | +1.17237 |
| ZnO原任务 | 0.00612198 | 0.406018 | 0.0651749 | +0.67089 |
| PTO原任务 | 0.0379671 | 1.00535 | 3.87329 | −0.75194 |

用既有幅度稳定性目标作为**说明性的数值尺度**比较：
e=max(0.02 C/m²,2%)、C=max(2 GPa,2%)、d=max(0.2 pm/V,3%)。
这些目标原用于步长稳定性，不自动成为双导数路径验收门，更不取代native raw-Gamma门。
四个六方档案的全部张量分量未超此说明性尺度；PTO总e/C未超，但总d有3个分量超出。
PTO d15从87.53078到83.75293 pm/V，d24从88.23423到84.36094 pm/V；
总d Frobenius差3.88760%，而d33只有−0.75194%。
因此接近门边界的raw平移残差不足以说明全部d误差很小，纵向d33也不能代替剪切分量审计。
同时，GaN/ZnO较大的raw平移残差不应直接换算成d误差；证据支持后续区分
平移规范与可观测响应敏感度，但尚未给出外部准确性或完整验收证明。

证据`native_total_route_sensitivity.json`含两条路线的完整18/36/18数组、源哈希、
逐张量最大差/Frobenius差及说明性尺度超限数。
所有路线C正定、e/C/d闭合断言通过；单位静态审计0 findings/0 suppressions。
standard_uncertainty仍为null；这是同源确定性敏感度，不是置信区间或误差上界。

## 三维算法控制：声学诊断不能代替光学响应误差

新增 `tests/test_v2_acoustic_response_invariance.py`，不重写 v1 框架；
直接复用 `shared_response.project_response` 和 v2 内应变、单位转换及 e/C/d API。
模型为三原子三维体相的全部 9 个位移自由度、6 个工程应变分量，不是一维链。

设归一化整体平移基 T、Π=I−TTᵀ，Φ=ΠΦΠ 且 ZT=0。
则 Φ⁺T=0，向 Γ 增加 TA 不改变 Λ=−Φ⁺Γ；
e 的 ZΛ 和 C 的 ΓᵀΦ⁺Γ 收缩不变，因此正定 C 下完整 d=eC⁻¹ 也不变。
原始 Γ 的净力诊断及未经投影的平衡残差仍然变化，必须保留，不能藏掉。
依据：[Wu–Vanderbilt–Hamann, PRB72 035105, II.B](https://www.physics.rutgers.edu/~dhv/pubs/local_copy/xfw_sys.pdf)。

新测试覆盖三个污染幅度、完整 e/C/d 不变性、原始严格声学检查拒绝、
显式投影后的严格检查通过；负控制表明光学 Γ 误差改变完整 e/C/d。
额外光学零模即使满足声学和规则仍被 rank/residual 拒绝；
刚体位移规范不变性还要求 BEC 电荷中性，非中性负控制不会误通过。
这些证明的是算法条件与错误分类，不是 GaN/ZnO/PTO 的独立 DFT 准确性。
没有改动 native 验收门，没有把诊断 d 转为已验收结果。

相关六文件定向回归共 111 passed，4051 条已有依赖弃用警告，零失败：
新控制、v2_response_algebra、v2_electromechanical、shared_response、
v2_pbe_database_comparison、v2_pbe_polar_domains。
包含 v1 共享重建的 32 点群测试及已有档案解析回归；不是全部 v1/v2 测试完成声明。

## 2026-09-19 完整 e/C/d 空间群审计：不是只检查 d33

新增研究后处理器 `tools/audit_v2_native_tensor_symmetry.py`，复用当前v2空间群、
应变/应力表示、intertwiner SVD和弹性major-symmetric basis；不重写v1重建，
不改原生门或正式CLI。三维周期输入POSCAR保持晶胞、坐标、原子顺序和极化畴，
原始source哈希逐一对应既有内应变审计；不读取POTCAR，不标准化或写回结构。
pymatgen技能用于受限POSCAR解析/校验/警告保留，实际版本2025.10.7；
按用户指令固定spglib symprec1e-3 Å，未采用技能中一般性的阈值扫描建议。
近对称晶格的群表示沿用v2已有共同度量处理，并保存全部操作/诊断。

令R为Cartesian极向量操作，A为工程应变表示，B为tensorial stress表示。
保持机械功要求BᵀA=I，张量不变性要求

```text
e A = R e        [e: C/m²]
C A = B C        [C: GPa, major symmetry C=Cᵀ]
d B = R d        [d: pm/V; D=d stress, d=e C⁻¹]
```

因此d不能照搬e的六维输入表示。pm/V×GPa/1000=C/m²；
实际档案的完整d C/1000=e最大闭合误差1.78e-15 C/m²，
所有群操作后的闭合最大4.88e-15 C/m²。反射等det−1操作仍按极张量处理，
不错误使用仅接受proper coordinate rotation的接口。
SVD允许子空间参数数：hexagonal e/C/d为3/5/3，tetragonal为3/6/3。
投影只用于报告原始矩阵偏离，不覆盖e/C/d，不作为新的响应计算结果。
使用SVD正交投影，未在非正交工程Voigt表示上用错误的Dinᵀ群平均。

| 档案 | 空间群 | 原生e最大偏离 C/m² | 原生C最大偏离 GPa | 诊断d最大偏离：位移路线 pm/V | 应变路线 pm/V |
|---|---|---:|---:|---:|---:|
| AlN已验收 | P6₃mc | 0.000055 | 0.045870 | 0.000264 | 0.001549 |
| GaN主档案 | P6₃mc | 0.001960 | 0.386570 | 0.005241 | 0.003186 |
| GaN symmetry control | P6₃mc | 2.20e-10 | 0.000101 | 0.0000178 | 0.001251 |
| ZnO主档案 | P6₃mc | 0.005450 | 0.504550 | 0.077987 | 0.065810 |
| PTO主档案 | P4mm | 0.007430 | 0.123330 | 0.351724 | 0.304007 |
| PZT50/50[001]模型 | P4mm | 0.018050 | 0.142260 | 7.118926 | 2.290662 |

PZT两路线d的相对投影残差为1.61755%/0.59050%；PTO为0.42979%/0.32954%。
这些是同一声明坐标系中Voigt矩阵的确定性残差，不是最终误差、置信区间或d33
误差百分比，也不等同于此前PZT d33双路线6.6534%的敏感度。
这里使用的Voigt Frobenius范数不宣称一般坐标旋转不变。
“对称性禁止”通过允许basis某个元素行严格为零判定；原始轴偏斜时
不凭肉眼把标准晶轴形式的零分量强加给原始Cartesian框架。
独立e/C/d投影不被当作重新求解的共同热力学张量组。

证据：`outputs/pbe_database_comparison_20260918/native_full_tensor_symmetry_audit_versioned_20260919.json`，
含算法/source哈希、完整原始/诊断投影/残差矩阵、单位、边界、操作、rank及警告。
先前同数值审计保留为`native_full_tensor_symmetry_audit_20260919.json`，未覆盖历史。
单位技能促使区分stress/strain轴和残差/不确定度；单位静态审计0 findings/0 suppression，
没有为此升级Python或安装Pint，也未捏造standard uncertainty。

新增三个完整三维测试：四方极性群3/6/3参数和反射、一般旋转下d的stress表示
与错误复用strain表示负对照、禁止分量保留而不抹零。3 passed/4已有依赖警告。
随后全本worktree `python -m pytest -q`：622 passed、4345 warnings、43.68 s；
记录在`local_full_regression_native_symmetry_20260919.json`。仍不覆盖独立native
worktree或支持安装/发布环境；已知本地NumPy/Phonopy低于声明最低版本。
新增DFT为0，native d科学门未解除，独立ABACUS及PZT路线敏感度仍待处理。

后续仅把optional POSCAR解析器导入移至实际文件审计入口；没有改变数值算法。
新exclusive输出`native_full_tensor_symmetry_audit_lazy_parser_20260919.json`的
全部六组calculations与前版完全一致，算法最终SHA256写入该JSON。
将pymatgen模块显式设为不可导入后，三个三维代数测试仍3 passed（0.75 s），
保证基础算法测试不无意依赖VASP optional安装。
最终全套`python -m pytest -q --disable-warnings`再次622 passed/4345 warnings/40.12 s；
此参数只隐藏警告正文，没有过滤警告或改变数量，记录在同一receipt的后续修订字段。
单位静态审计仍零finding/零suppression，旧运行记录不覆盖。
