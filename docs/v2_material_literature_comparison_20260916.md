# v2 已计算材料：文献映射与正确性判定（2026-09-16）

本报告只审计当前分支 `zstar-v2-development` 中已有可追溯的 **v2 机电响应**
输出：wurtzite ZnO、AlN、GaN、zinc-blende GaAs，以及 3C-SiC 的弹性
后端基准。它不把 v1 的 BEC、Gamma 声子、介电或光谱案例重新包装为 v2
压电验证，也不把“张量对称性通过”误报为“材料常数已正确”。

## 可比性规则

所有 `e` 均为 relaxed-ion、proper、零宏观电场的
`e_{alpha,mu}=dP_alpha/deta_mu`，单位 C/m2；本分支由同一 `e` 和
`C^E` 采用 `d=e(C^E)^-1` 得出 `d`，单位 pm/V (= pC/N)。应变列为工程
Voigt `(xx, yy, zz, 2yz, 2xz, 2xy)`；六方晶体取 `z || [0001]`。

本报告的**验收百分比只对理论计算文献给出**：同一 `e`/`d` 类型、相同的
relaxed-ion 边界条件、相同的张量分量和已对齐的坐标手性。`e15`/`d15`
的符号可随剪切轴或原胞手性翻转，未完成手性映射时只比较绝对值。实验仅可在
将来作为次级现实性 sanity check，绝不用于本报告的通过/失败判定。

泛函匹配是硬门，而不是备注：**PBEsol 文献 → PBE 文献 → 其他 GGA → LDA**。
只有前一层不存在可核对的同定义结果时才允许降级，且降级层级必须写入表格；
不同泛函之间的百分比是定位误差的诊断量，不是严格误差条。

## 文献覆盖

| 材料 | 可直接映射的来源 | 本轮可用于数值判断的量 |
|---|---|---|
| ZnO, AlN, GaN | Hoang *et al.* (2013) | 同一 CRYSTAL/PBEsol 的 bulk `e31/e33/e15` 与五个独立 `C`；本轮的**一级**比较 |
| ZnO | Dal Corso *et al.* (1994), Gopal--Spaldin (2006), Catti *et al.* (2003) | LDA/SIC/other-functional 的补充理论范围，不作 PBEsol 通过判定 |
| AlN, GaN | Bernardini--Fiorentini--Vanderbilt (1997), Bernardini--Fiorentini (2002), Wright (1997) | relaxed-ion `e31/e33`、`d31/d33/d15`、弹性 |
| GaAs | Beya-Wakata--Prodhomme--Bester (2011), de Gironcoli--Baroni--Resta (1989), McKitterick (1983) | GGA `e14`；尚未定位 PBEsol 或明确 PBE 的同定义文献值 |
| 3C-SiC | Lambrecht *et al.* (1991), Wang *et al.* (1995) | `C11/C12/C44`；当前只找到 LDA FP-LMTO 可用理论锚点；本轮未产出可审计的 SiC 压电张量 |

链接和 DOI 已记录在 [v2_literature_sources.bib](v2_literature_sources.bib)。关键
数值来源为 Bernardini--Fiorentini--Vanderbilt 的原始 Berry-phase 氮化物
计算、Gopal--Spaldin 的 ZnO `e/C` 表，以及 Bernardini--Fiorentini 的直接
`d` 计算；后者同时明确 `d=e(C^E)^{-1}` 的边界条件。

## 数值对照

百分比为 `(|v2|-|reference|)/|reference|`。`+` 表示本次绝对值较大，`-`
表示较小；不是统计误差条。

| 材料 / 量 | v2 值 | 文献锚点 | 差异 | 判断 |
|---|---:|---:|---:|---|
| ZnO `e31/e33/e15` (C/m2) | -0.615/1.267/-0.477 | -0.706/1.389/-0.591 (Hoang *et al.*, PBEsol) | -12.9/-8.8/-19.3% | 一级比较；`e15` 需补幅度审计 |
| ZnO `C11/C12/C13/C33/C44` (GPa) | 213.6/127.6/113.9/210.8/39.9 | 215.9/132.3/119.2/229.6/32.0 (Hoang *et al.*, PBEsol) | -1.0/-3.6/-4.4/-8.2/+24.7% | 一级比较；`C44` 是明确缺口 |
| AlN `e31/e33/e15` (C/m2) | -0.693/1.696/-0.374 | -0.618/1.647/-0.374 (Hoang *et al.*, PBEsol) | +12.1/+3.0/-0.0% | 一级比较，主压电分量相符 |
| AlN `C11/C12/C13/C33/C44` (GPa) | 391.7/145.9/116.1/363.7/112.3 | 397.0/145.6/114.2/376.9/114.4 (Hoang *et al.*, PBEsol) | -1.3/+0.2/+1.6/-3.5/-1.9% | 一级比较，通过 |
| AlN `d31/d33/|d15|` (pm/V) | -2.66/6.36/3.33 | -2.1/5.4/2.9 (Bernardini--Fiorentini, GGA) | +26.8/+17.8/+14.9% | **二级 GGA**；PBEsol `d` 文献待补 |
| GaN `e31/e33/e15` (C/m2) | -0.372/0.660/-0.254 | -0.520/0.904/-0.373 (Hoang *et al.*, PBEsol) | -28.5/-26.9/-31.8% | 一级比较，当前**不通过定量验收** |
| GaN `C11/C12/C13/C33/C44` (GPa) | 348.5/128.2/93.0/386.1/91.8 | 378.0/144.3/107.1/419.4/94.2 (Hoang *et al.*, PBEsol) | -7.8/-11.1/-13.2/-7.9/-2.5% | 一级比较，弹性偏软 |
| GaN `d31/d33/|d15|` (pm/V) | -1.23/2.30/2.77 | -1.4/2.7/1.8 (Bernardini--Fiorentini, GGA) | -12.2/-14.7/+53.8% | **二级 GGA**；只能作诊断，`d15` 仍未通过 |
| GaAs `e14` (C/m2) | -0.2627 | -0.342 (Beya-Wakata *et al.*, GGA; lattice known too大) | -23.2% | **三级 other-GGA**；尚无 PBEsol/PBE 同定义锚点 |
| GaAs `C11/C12/C44` (GPa) | 110.2/49.3/56.1 | 100/47/50（Zhang *et al.*, PBE-PAW DFT） | +10.2/+4.9/+12.2% | **二级 PBE**；PBEsol--LCAO 与 PBE--PAW 不作严格误差条 |
| 3C-SiC `C11/C12/C44` (GPa), ABACUS | 363.4/110.6/252.8 | 420/126/287（Lambrecht *et al.*, LDA FP-LMTO） | -13.5/-12.2/-11.9% | 张量拟合稳定；材料数值为条件通过 |
| 3C-SiC `C11/C12/C44` (GPa), VASP | 383.5/126.7/264.3 | 420/126/287（Lambrecht *et al.*, LDA FP-LMTO） | -8.7/+0.6/-8.0% | 与理论参考相符；仍需匹配 Hamiltonian 收敛 |

Hoang *et al.* 的 PBEsol 结果是本轮最接近的统一 bulk 理论锚点：同一文献明确给出
五个独立弹性常数，并以 Berry-phase 总极化对应变求导给出三个 `e`。ZnO 的
`e15=-0.477 C/m2` 还可与 Catti *et al.* 的完整张量理论研究交叉检查，但后者不是
PBEsol，不能替代一级比较。
同理，3C-SiC 这轮仅验证弹性；没有输出 SiC `e14/d14`，因而不能声称其压电已验证。

## 算法正确性与材料准确性的分层结论

| 材料 | 算法/数值自洽性 | 文献一致性 | 当前状态 |
|---|---|---|---|
| ZnO | 13 个结构、`P6_3mc`、压电 rank 3、弹性正定；严格 `scf_thr=1e-10`、`force_thr=1e-6 eV/A`；`e` 对称投影相对残差 0.407% | PBEsol `e` 差 9--19%，`C44` +25% | **条件通过**：主量合理，但不是完整高精度基准 |
| AlN | 对称投影、rank、稳定性通过；旧协议为 `scf_thr=1e-8`、应变力阈值 `1e-5 eV/A` | PBEsol `e` 差 0--12%，`C` 差 0--4% | **最强的候选验证案例**；还应以 strict 协议复核 |
| GaN | rank 3/3，直接 e、C、d 逻辑闭合；旧协议 `scf_thr=1e-8` | PBEsol `e` 低 27--32%，`C` 低 3--13% | **不通过定量验收**：先做 strict/幅度/结构审计 |
| GaAs | `F-43m` 允许子空间和等价分量到约 1e-6 C/m2，最强的对称性单元测试 | 仅有 other-GGA/PBE 降级参照 | **方法通过、材料验收待 PBEsol 或明确 PBE 对照** |
| 3C-SiC | ABACUS ±0.005/±0.0025 幅度差 ≤0.054%，与 VASP 张量结构一致 | 相对 LDA 理论 `C` 为约 8--14% | **弹性算法通过、材料常数条件通过**；不得扩展为 SiC 压电结论 |

所以答案不是“所有材料都已经达到同协议高精度”。按 PBEsol 一级比较，目前 **AlN
最接近可冻结的 v2 机电基准**；ZnO 有可解释但必须收敛的 `C44/e15` 缺口；GaN
在三个 `e` 分量上均低约 27--32%，明确不通过；GaAs 仍缺少 PBEsol（或明确 PBE）
同定义 `e14` 对照；SiC 只支持弹性算法的交叉后端验证。

## 下一步（按证据缺口排序）

1. 以 AlN 作为首个候选冻结案例，但先用 `scf_thr=1e-10`、
   `force_thr=1e-6 eV/A` 与 `relax_nmax=100` 的 strict 协议复核；只有仍保持
   PBEsol 对照时的 0--12% `e`、0--4% `C` 一致性，才升级。
2. 对 ZnO 做 `e15/C44` 的专向幅度与收敛审计；对 GaN 做 strict 结构、幅度与
   极化分支审计，目标是解释相对 PBEsol 的 27--32% `e` 缺口，随后才讨论 `d15`。
3. 对 GaAs 不增加材料数量，先复算一个严格 `e14` 收敛阶梯（晶格参数、k 点、
   cutoff/基组、`+-` 应变幅度），并继续寻找 PBEsol（退而求其次明确 PBE）的
   `e14` 理论文献；现有 other-GGA 与 LDA 只保留为降级诊断，不追逐实验锚点。
4. 对 SiC 优先定位 `C12` 的晶格参数和 Hamiltonian 差异；得到独立 piezo 输出前，
   保持“elastic-only benchmark”标签。

本报告取代 `docs/v2_piezo_benchmark_report_20260914.md` 中关于 ZnO 当前状态的
旧判定：旧报告使用较早的 `1e-5 eV/A` 应变弛豫数据；本报告使用已完成的 strict
`1e-6 eV/A` / `scf_thr=1e-10` 数据。旧报告保留为可追溯的阶段记录。
