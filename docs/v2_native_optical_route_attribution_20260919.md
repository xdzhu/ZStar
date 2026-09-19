# 原生内应变双路线的光学模式归因（研究诊断）

本轮分类为**实质进展**：新增完整三维、模式分辨的确定性归因，解释已有
VASP 档案的双路线差异。没有执行新 DFT、改变生产精度、修改 native d 验收门，
也没有把诊断 d 提升为合格结果。PTO/PZT 的 ABACUS 任务和 HF 对称性测试另行继续。

## 模型与继承关系

复用 v1 `shared_response.project_response` 的 IFC reciprocity/translation 和 BEC
中性投影，只作用于诊断副本；原始档案、原始残差及 native 拒绝原因保留。
所有输入 SHA256 必须匹配已冻结的 ionic reconstruction 审计；不重新标准化结构，
不改变原子顺序、Cartesian 坐标、晶胞或极化畴。

理论依据是 [Wu, Vanderbilt and Hamann, PRB 72, 035105 (2005), II.B](https://www.physics.rutgers.edu/~dhv/pubs/local_copy/xfw_sys.pdf)，
DOI: 10.1103/PhysRevB.72.035105。这里采用每晶胞能量 Hessian，VASP `Xi=dF/deta`
与 ZStar `Gamma=-Xi` 的符号关系沿用既有同源 ionic e/C 重建，不通过文献值调整符号。

所有结构为 3D 周期体相、零温、固定宏观电场；应变为工程 Voigt
`[xx,yy,zz,2yz,2xz,2xy]`。去掉三个几何整体平移方向后，对 Cartesian 光学
力常数矩阵进行谱分解。设光学列向量 q、正曲率 k，某谱块的两路线响应为：

```text
Lambda_block = q diag(1/k) q^T Xi
e_ionic_block = (elementary_charge / volume) Z Lambda_block
C_ionic_block = -Xi^T q diag(1/k) q^T Xi / volume
```

Xi 单位 eV/Å，k 单位 eV/Å²，Lambda 单位 Å/strain，Z 单位 e。
偶极先由 e·Å 转 C·m，体积由 Å³ 转 m³，因此 e 为 C/m²；C 由 eV/Å³ 转 GPa。
这里的 k **没有质量加权，不是声子频率或 THz**。编号按此光学曲率递增排序，
不是 native phonon 编号，也未在近对称输入上擅自指定不可约表示。

以 a=displaced-atoms、b=strained-cells 定义差值。对每个谱块使用精确有限变化恒等式：

```text
delta_d_block = 1000 delta_e_block S_b - d_a delta_C_block S_b
S_b = C_b^{-1}   [1/GPa]
d              [pm/V]
```

求和严格恢复完整 3×6 的 `d_b-d_a`，不是一阶近似。d 的两条路线仍是已有的
diagnostic algebra，不是新原生输出、独立准确性证明、误差上界或统计不确定度。
固定共同 Phi/Z 和 clamped e/C；因此该归因只定位 **Xi 路线差异** 的传播，
不能排除共同 BEC、IFC、clamped 张量、赝势或几何误差。

数值谱块容差为 1e-8 eV/Å²，**不是结构对称性 symprec**；spglib/Phonopy 仍遵守
用户指定的 1e-3 Å。精确简并模式只报告块和，避免任意简并基选择的误导；
近简并块保留每个原始特征值，不用块均值替代。

## 新的定位结论

| 档案 | 两路线总 delta d33 pm/V | 最大绝对贡献光学编号 | 曲率 eV/Å² | 该块 delta d33 pm/V | e 路径部分 pm/V | C 路径部分 pm/V |
|---|---:|---:|---:|---:|---:|---:|
| AlN 已验收档案 | +0.030962 | 3 | 24.116930 | +0.030961 | +0.019235 | +0.011726 |
| GaN 主档案 | +0.023358 | 3 | 21.203222 | +0.023367 | +0.020725 | +0.002642 |
| GaN symmetry control | +0.018559 | 3 | 21.201637 | +0.018559 | +0.016105 | +0.002454 |
| ZnO 主档案 | +0.065175 | 3 | 11.430911 | +0.065201 | +0.035050 | +0.030151 |
| PTO 主档案 | −0.479963 | 8 | 8.607457 | −1.648560 | −0.315356 | −1.333204 |
| PZT50/50 [001] | +15.403460 | 26 | 38.293532 | +8.770294 | +0.225819 | +8.544474 |

表中是 signed attribution，不是百分比精度。最大单项可能超过总差，因为不同谱块
会抵消；不能把 signed contribution 当成非负误差预算。

PTO 的编号 12 贡献 +1.135420 pm/V，编号 9 贡献 +0.034724 pm/V，部分抵消编号 8。
所以总 d33 路线差只有 −0.479963 pm/V，不能据此判定全部内应变导数都准确，
也不能替代先前发现的剪切 d 路线敏感度。

PZT 的编号 26/19/16 分别贡献 +8.770294/+5.687781/+1.502742 pm/V，
曲率分别为 38.293532/7.847648/6.631192 eV/Å²；其 C 路径部分分别为
+8.544474/+5.211576/+1.377158 pm/V。最大项不是最小曲率模式。
这细化了“软弹性放大”的解释：共同软 compliance 可以放大高曲率模式产生的
弹性修正差异，**不能简单声称错误来自最低光学软模**。
归因不是 VASP 数值误差的唯一根因，也未证明某个原子或某类扰动必须重算。

全部六组完整 e/C/d 分块和恢复误差最大为 9.06e-13 pm/V。
完整矩阵、原始输入哈希、投影诊断、曲率、脚本哈希和包版本保存在：

- `outputs/pbe_database_comparison_20260918/native_optical_route_mode_attribution_strict_20260919.json`
- 初版 `native_optical_route_mode_attribution_20260919.json` 保留，不覆盖历史证据。

两版 calculations 数值相同；后版仅增加严格 JSON 非有限常数/重复键拒绝。
代码最终算法 SHA256 为 `ae69f3e003d075bafe2cb74bc7e952c5719f4ed7560d482cd50ff2c727f1d67b`。

## 测试、资源和边界

新增 `tests/test_v2_native_optical_route_modes.py`：三维全 9 位移/6 应变轴，
精确简并块任意正交混合与符号翻转不变性、全部谱块与直接 Cartesian 逆矩阵收缩一致、
精确有限 delta d 的完整矩阵闭合、零/负光学曲率拒绝、无效体积拒绝、
近简并曲率不平均，以及重复 JSON 键/NaN 拒绝。
脚本是研究后处理，不是正式 CLI，不调用任何计算器，不写回现有输入或结果。
已验收 AlN 用全原子 `vasp_bec.json`，不复制 compact BORN 的不等价原子代表；
其余档案沿用冻结审计建立的全原子 BORN 顺序或显式带物种/索引的全原子 JSON。

首次控制 5 passed；联合此前声学和完整张量对称性控制 15 passed、4 条依赖警告。
严格 JSON 修订后的全套回归单独记录在 continuation 报告，不把先前 622 passed
当作本次新增代码的测试证据。单位静态审计 0 findings/0 suppressions；
未安装 Pint 或升级生产环境，沿用已经测试的显式单位层。
standard uncertainty 保持 null，不从两路线差异虚构统计分布或置信区间。

最终强化近简并控制后，全部本worktree回归 **630 passed、4345 warnings、31.08s**，
终态 session 44021 已观察，源代码/测试/输出哈希记录在
`local_full_regression_native_optical_modes_20260919.json`。
该近简并控制采用不等耦合并显式拒绝平均曲率的负对照，避免等权抵消使测试失去敏感性。
先前31.54s的已观察完整测试作为独立历史修订记录保留。

从研究worktree重现（输出必须为新路径，已有文件会明确拒绝覆盖）：

```powershell
$env:PYTHONPATH='D:/Work/Code/zstar-v2-development'
python tools/audit_v2_native_optical_route_modes.py --archive outputs/pbe_database_comparison_20260918 --output outputs/pbe_database_comparison_20260918/native_optical_route_mode_attribution_repeat_20260919.json
python -m pytest -q tests/test_v2_native_optical_route_modes.py
```

本诊断新增第一性原理任务数/SCF/集群 core-hours 均为 0。
真实正在运行的 ABACUS/PZT/HF 任务成本由各自作业 provenance 记录，不与本诊断混记。
main、v1 正式论文、发布接口、独立 native worktree 和科学验收门均未修改。

下一阶段的科学动作仍是：收齐 PTO/PZT 的 ABACUS 中心差分独立响应；
检查正在运行的 exact-symmetry/ISYM1 静态电场诊断是否完成且保持绝缘与对称性；
结合完整 e/C/d 而非只看 d33 决定是否需要有针对性的后续导数验证。
未完成之前不声称全部双后端 d 已验收，不直接重投整套 72 个 PZT 扰动点。
