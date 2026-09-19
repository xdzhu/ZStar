# PBE 完整压电张量对比：2026-09-18

## 结论与来源

2026-09-19 四体系完整双后端差异与单列 d33 已整理于
[完整 e/C/d 比较](v2_completed_backend_pair_audit_20260919.md)。
明确区分已验收 d 和 VASP 原生 e/C 的诊断代数值，不改变原生 null d 或质量门。

本轮双后端、五体系验证尚未全部完成。已经取得可靠的 **AlN/VASP/PBE 完整 e、C、d**，
来自用户指定会话已完成的原生优先实现，而非本轮参考结构优化。
该实现位于独立 worktree `D:/Work/Code/zstar-vasp-native`、分支
`codex/vasp-native-response`，提交 `bbaf059a`；本报告只读复用已验收结果，未合并分支。

原生 AlN 案例：`examples/VASP_Native_Response/AlN/results/validation.json` 的
`passed=true`，`elastic: reliable derived d emitted=true`。
采用 `results/elastic/vasp_native_response.json` 中通过质量门的原生有限差分结果；
不将具有内部应变力平衡警告的预备 DFPT 数据替代为最终结果。
后续 VASP 开发应复用这一原生支持，不重复建设外部应变差分默认路线。

### 实际扰动幅度核查：不是同一套应变步长

已完成GaN/VASP原任务的OUTCAR实际几何审计得到：一个参考结构、12个晶胞应变点、
24个原子位移点；工程应变六分量均为±0.01（±1%），原子位移为±0.01 Å。
原生执行次序先应变、后原子位移，不把内部结构迭代号直接当成已完成原子位移点数。
本轮ABACUS/PYATB中心应变采用±0.005（±0.5%）；所以跨后端表并非相同差分步长。
不能把后端差值全部解释为赝势效应，也不能凭POTIM的数字推断两种扰动的单位。
证据为`outputs/pbe_database_comparison_20260918/GaN_native_actual_geometry_audit.json`，
包含实际工程应变向量、非仿射位移、晶胞、输入输出哈希及解析软件版本。
OUTCAR原子坐标只有五位小数，审计分类容差3e-5 Å仅处理文本序列化误差，
不是放宽物理收敛精度或spglib/Phonopy的1e-3 Å阈值。
其他原生档案待逐一核查，不将GaN的幅度和次序直接当作所有VASP任务的实测证据。

## PTO / ABACUS / PBE：2026-09-19 完整中心应变结果已收集

四方铁电相 PbTiO3（P4mm，SG99）具有压电响应；本轮计算的是三维单畴体相，
不是高温中心对称立方相，也不是陶瓷畴壁/畴翻转贡献。
已有235任务完成参考加六分量正负应变共13个几何，本次只收集和审计，未重复提交DFT。
采用PBE、ABACUS LCAO、100 Ry、kspacing0.1、工程应变±0.005中心差分、
SCF1e-8、力1e-4 eV/Å、relax_nmax100，参考stress门为0.5 kbar。
一次PYATB后处理给出三个方向极化，合计13次PYATB，而非三个方向分别NSCF。

| 分量 | PTO/ABACUS/PBE (C/m²) | 同相PBE数据库 mp-20459 (C/m²) | 有符号差值 (C/m²) | 绝对相对差异 |
|---|---:|---:|---:|---:|
| e31 | 1.710979 | 1.643650 | +0.067329 | 4.10% |
| e33 | 2.114819 | 2.792120 | −0.677301 | 24.26% |
| e15 | 2.895233 | 3.259890 | −0.364657 | 11.19% |

**d33=49.084674 pC/N（等价pm/V）**；d31=−1.465454、d15=97.529358 pm/V。
d由同一组完整proper e与relaxed-ion C^E求得，不用单个e33/C33代替全矩阵求解。
C33=45.580518 GPa，最小弹性特征值28.440409 GPa、条件数8.76820；
输入应变rank6、e拟合18/18、C拟合21/21，d/e/C闭合最大差4.44e-16 C/m²。
13点均SCF收敛，12个应变点均离子收敛且力≤1e-4；参考静态SCF最大力7.1251e-5 eV/Å，
最大应力0.03156975 kbar，最小PBE间隙1.929862 eV。
参考SCF的ionic_relaxation_converged=false不表示失败：它不是离子优化任务。
应变晶胞的非零应力是待求响应，不要求逐点满足参考cell-relax的stress门。
e对称投影最大差5.88e-6 C/m²，Lambda去平移后最大对称残差3.46e-6 Å/strain；
全部原始分量保留，没有事后投影改善文献对比，也不据此声称独立Z*Lambda分解已验证。

平衡R2r文件SHA256为e59d1e33b370399437458583e0f96199532108fd9a4ebd30662dbc0f8d58c63c；
生成的reference/STRU文件哈希不同，但逐项核对晶格、原子顺序和分数坐标，确认几何相同。
固定spglib symprec1e-3 Å，与数据库同SG99、同+c极性畴；c较数据库大4.3666%，
a/b小0.9237%。因此24.26%的e33差异不能全部归因于软件或赝势，亦不能宣称严格外部复现。
全18分量e差的Frobenius比为14.5936%，见PTO_ABACUS_full_tensor_comparison.csv。
选定冻结档案没有PTO同来源C/d参考，d33外部参考与百分差保持空缺。
VASP原生PTO的d质量门仍未通过，不把其诊断代数d33充当已验收参考。

13个几何的累计ABACUS19668 s、PYATB139 s；40 MPI×1 OMP对应220.0778 rank-wall core-hours，
分布于cu25/cu16。统计191次SCF循环、1779条电子迭代行；不含参考优化、历史失败，
累计阶段时间不是并行任务的端到端wall time。
完整张量、逐点收敛、文件哈希、实际应变与费用见
`outputs/pbe_database_comparison_20260918/PTO_ABACUS/completed_response_audit.json`。
本次既有比较/续算测试11项通过；未修改核心API/CLI、main或正式v1论文。

## PTO / VASP / PBE 原生响应完成，完整 e/C/d 验收仍待补充

Slurm27720995确认COMPLETED/0:0，node203、32 MPI × 1 OMP、wall time1:40:46，
分配计53.7422 core-hours（含参考处理），native阶段档案计28.1828 rank-wall core-hours；
两种计时口径不混用。收集完整原生e/C、BORN/IFC与内部应变诊断。
参考结构力6.9970e-5 eV/Å、最大应力0.00585573 kbar、PBE间隙1.9272 eV、SG99。
同+c极化畴，c较数据库大3.5467%，a/b约小0.90%，不隐式调整结构或张量符号。

| 分量 | PTO/VASP/PBE (C/m²) | 同相PBE数据库 (C/m²) | 绝对相对差异 |
|---|---:|---:|---:|
| e31 | 1.66857 | 1.64365 | 1.52% |
| e33 | 2.43823 | 2.79212 | 12.67% |
| e15 | 2.79621 | 3.25989 | 14.22% |

全部18分量差异见`PTO_VASP_full_tensor_comparison.csv`，全e Frobenius相对差12.7033%。
弹性矩阵最小特征值26.5624 GPa为正，major symmetry通过。
原生内应变raw平移相对残差0.00106288793，略高于现有0.001门，
native仍未输出d（包括d33）；保持`scientific_gate_pending`，不填诊断代数值。
这项raw残差不是最终d误差的直接估计。独立ABACUS结果现已收集（见上节），
后续继续结合内部贡献审计解释跨后端差异，而非提高SCF精度或直接为填表放宽门槛。

PTO完成档案的实际几何也已审计：参考1、应变12、原子位移30；正负配对通过，
工程应变±1%、原子位移±0.01 Å；同样先应变、后原子位移。
证据`PTO_native_actual_geometry_audit.json`保留输入/OUTCAR哈希、实际向量、晶胞、
顺序及软件版本；pymatgen实际版本2025.10.7，未冒称skill的2026固定快照或升级环境。

数据库来自 [de Jong et al., Scientific Data 2, 150053 (2015)](https://doi.org/10.1038/sdata.2015.53)，
原文可访问 [作者机构 PDF](https://perssongroup.lbl.gov/papers/sdata2015-piezoprops.pdf)。
它报告 VASP/PAW/PBE/DFPT 的 proper、relaxed-ion 压电 e 张量，使用 IEEE 坐标约定。
完整 941 条记录已由 [matminer 官方数据目录](https://hackingmaterials.lbl.gov/matminer/dataset_summary.html#piezoelectric-tensor)
给出的 [数据下载](https://ndownloader.figshare.com/files/13220621) 取得。
SHA256 与官方元数据一致：
`dc9d04836f7f91ecb4ef6dc23e42468571be857f0fccafdfb51a5a40f19db898`。

## GaN/ABACUS：完整中心应变结果已收集

13 个几何（参考与六分量正负应变）均已完成，PBE、工程应变±0.5%、
SCF1e-8、力1e-4 eV/Å、relax_nmax100。
参考几何哈希与固定spglib1e-3 Å的SG186、同+c极性畴审计一致。
原始结果为`GaN_ABACUS/summary.json`与`response_document.json`，
完整18分量表为`GaN_ABACUS_full_tensor_comparison.csv`，均位于本轮结果目录。
没有事后投影或翻转张量符号来改善与数据库的比较。

| 分量 | ABACUS/PBE（C/m²） | de Jong/PBE mp-804（C/m²） | 有符号差值（C/m²） | 绝对相对差值 |
|---|---:|---:|---:|---:|
| e31 | -0.30384652 | -0.28982 | -0.01402652 | 4.84% |
| e33 | 0.52506936 | 0.46451 | 0.06055936 | 13.04% |
| e15 | -0.18817385 | -0.139315 | -0.04885885 | 35.07% |

全e Frobenius相对差 **14.4173%**，最大绝对差0.0605594 C/m²；
数据库零分量的最大计算绝对值0.000589958 C/m²。
尤其保留35.07%的e15差异，不能把“内部一致”写成严格外部复现。

**d33=1.87223918 pm/V（等价pC/N）**，由本次完整proper e及relaxed C求得。
该e数据库没有同计算来源的C/d，故d33数据库参考和百分差保持空缺。
原生GaN/VASP尚未通过d质量门，不用其诊断代数d作为已验收参考值。

内部诊断：参考最大力6.87816e-5 eV/Å；13几何均绝缘，最小PBE gap1.71143 eV。
输入应变rank6，e拟合18/18，C拟合21/21；C最小特征值92.60196 GPa，条件数5.75476。
e–C–d闭合最大差1.11e-16 C/m²；e对称投影相对残差0.00225776，
C对称投影相对残差0.000120548，沿用现有混合/相对容差检查，未改变质量门。
应变增量拟合相对残差e为0.0296684、C为0.00927843；它们不是张量误差条或精度保证。

与本轮GaN/VASP原任务的全张量差（以VASP为分母）：e Frobenius **21.6406%**、
C Frobenius **3.89412%**；最大绝对差分别0.1051194 C/m²与15.17386 GPa。
两者参考几何、赝势/基组、原生应变步长不同，VASP内部应变警告仍在。
此比较提供独立证据，但不能单独证明差异全部由赝势导致，也不能据此放宽原生d门。

实际资源审计：13个ABACUS几何任务与13个PYATB后处理（每次同时输出三个极化方向），
ABACUS累计3967 s、PYATB130 s；40 MPI×1 OMP对应 **45.5222 rank-wall core-hours**。
日志统计96次SCF循环、726条电子迭代行，二者不混用；不含R1/R2r参考优化及历史失败费用。
逐点记录见`GaN_ABACUS/response_cost_audit.json`；原始runtime与SCF日志仍保存在cu17共享目录。

## AlN：全部 18 个分量，不做事后对称投影

单位 C/m²；列为 `(xx, yy, zz, yz, xz, xy)`，对应工程剪切应变；行是极化方向。
案例与参考均采用 x 沿 +a、z 沿 +c 的约定，不进行隐式极性翻转。

```text
ZStar / VASP / PBE
[[-0.00004, -0.00003, -0.00001,  0.00000, -0.30952,  0.00001],
 [ 0.00000,  0.00003, -0.00004, -0.30960, -0.00001,  0.00000],
 [-0.58162, -0.58151,  1.46150,  0.00000, -0.00001, -0.00001]]

PBE 数据库 mp-661，空间群 186
[[ 0,  0, 0,  0,        -0.289305, 0],
 [ 0,  0, 0, -0.289305,  0,        0],
 [-0.58006, -0.58006, 1.46115, 0, 0, 0]]
```

| 分量 | ZStar/VASP/PBE | 数据库/PBE | 有符号差值 | 绝对相对差值 |
|---|---:|---:|---:|---:|
| e31 | -0.58162 | -0.58006 | -0.00156 | 0.269% |
| e32 | -0.58151 | -0.58006 | -0.00145 | 0.250% |
| e33 | 1.46150 | 1.46115 | +0.00035 | 0.024% |
| e15 | -0.30952 | -0.289305 | -0.020215 | 6.987% |
| e24 | -0.30960 | -0.289305 | -0.020295 | 7.015% |
| d33（pC/N，等价 pm/V） | 5.324396 | 未直接提供 | — | — |

百分差为 `100*abs(计算值-参考值)/abs(参考值)`。参考为零的分量只报告绝对差，
不计算百分差；完整逐分量表保存于
`outputs/pbe_database_comparison_20260918/AlN_full_tensor_comparison.csv`。

完整 e 张量 Frobenius 相对差为 **1.6654%**，最大绝对差为 **0.020295 C/m²**；
数据库零分量对应的最大计算绝对值为 **4e-5 C/m²**。
本案例自身的 `d C /1000 = e`（d 为 pm/V，C 为 GPa）闭合和弹性正定性检查通过。
完整 C、d 及诊断保存在同目录 `comparison.json`。

这支持 AlN 原生 VASP/PBE 压电结果的外部一致性，但不等于所有材料已验证。
剪切分量约 7% 的差异应保留，不能只用 e33 的良好一致性替代全张量审计。
案例 ENCUT=600 eV、Gamma 8×8×6；数据库论文采用 1000 eV、2000 k 点/倒空间原子密度设置。
因此属于同泛函、同后端、同相比较，**不是完全相同输入的复现**。
本案例原生响应 EDIFF=1e-9，是已有验证计算的设置，不据此提高其他生产任务默认精度。

## 其余材料：参考已取得，不填造计算结果

| 体系 | 精确数据库 ID | 空间群 | e31 | e33 | e15 |
|---|---|---:|---:|---:|---:|
| AlN | mp-661 | 186 | -0.58006 | 1.46115 | -0.289305 |
| GaN | mp-804 | 186 | -0.28982 | 0.46451 | -0.139315 |
| ZnO | mp-2133 | 186 | -0.53751 | 1.03681 | -0.38500 |
| PTO / TiPbO3 | mp-20459 | 99 | 1.64365 | 2.79212 | 3.25989 |
| PZT50/50 [001] 有序模型 | 无匹配记录 | 99（目标） | — | — | — |

已排除同化学式的闪锌矿条目，不能与纤锌矿 e33 混比。
PZT 有序模型不等同于无序陶瓷。该压电数据库不直接提供 C 或 d33；
不能将其他数据库不同几何、不同计算的 C 拼接成严格的 d33 参考。

## 235 本轮计算状态（初始参考优化检查，历史快照）

目录：`/home/zhuxd/abacus/agent-runs/20260918-v2-pbe-dual-backend`。
截至本次检查，队列只执行参考结构优化，尚无完整响应 ensemble 或新 e/C/d 文件。

| 材料 | ABACUS/PBE 参考结构 | VASP/PBE 参考结构 |
|---|---|---|
| AlN | 优化收敛，力/应力/空间群检查通过 | 优化收敛，力/应力/空间群检查通过 |
| GaN | 优化收敛，力/应力/空间群检查通过 | ZBRENT 失败，未通过 |
| ZnO | 优化收敛，力/应力/空间群检查通过 | ZBRENT 失败，未通过 |
| PTO | 优化收敛，力/应力/空间群检查通过 | ZBRENT 失败，未通过 |
| PZT50/50 | 检查时仍在优化，第 85 步，未收敛 | 返回码零但无收敛标记，最终最大力 7.43e-4 eV/Å，未通过 |

ABACUS 收集器在这些优化日志中尚未得到 band gap，绝缘性门仍需补验。
不能把“参考结构已优化”描述为“压电已算完”。已结束九个参考任务共约
**43.83 core-hours**；PZT/ABACUS 检查时已约 4 小时、约 160 core-hours，仍增长。
cu26 检查有 40 个 ABACUS rank、零个 VASP rank，没有本队列重复运行证据。
所有失败输入与日志保留，未盲目重投。

下一步先解决失败参考优化与绝缘性核验，再复用原生 VASP e/C 路线和已有
ABACUS/PYATB 差分路线，取得其余材料同泛函完整 e/C/d。不得用旧 PBEsol 数据填补。

## 可复现处理与测试

```powershell
python tools/compare_v2_pbe_database.py --database E:/TEMP/zstar-pbe-database-20260918/piezoelectric_tensor.json.gz --native-case D:/Work/Code/zstar-vasp-native/examples/VASP_Native_Response/AlN --output outputs/pbe_database_comparison_20260918
python -m pytest tests/test_v2_pbe_database_comparison.py -q
```

脚本不运行 DFT，验证下载哈希、记录数、精确条目/相、完整张量形状、非有限值、
原生验收与 d/e/C 闭合；逐分量保留数值禁戒分量，不掩盖残差。
本次新增两项测试通过；连同 PBE 输入准备、应变、VASP 收集与机电换算回归，
合计 **51 passed**（14 项 spglib 弃用提示，无失败）。
所有新增文件仅在 v2 分支；main、v1 论文及发布接口未修改。

## ABACUS/PBE 参考结构的坐标与极性畴审计

采用 pymatgen 2025.10.7，空间群识别明确指定 `symprec=1e-3 Å`，
不调用内部使用默认阈值的 IEEE 自动旋转。四个当前 R1 结构均为右手坐标，
`+a || +x`、`+c || +z`，与选定数据库条目同相、同 c 方向极性畴。
拟合仅允许同元素原子对应和共同周期平移；另独立检查 c 反射后的参考结构，
不旋转结构、不修改张量符号。该审计限于本轮已对齐的 SG186/99 体相晶胞。

| 材料 | 空间群（计算/数据库） | 同畴内部坐标 RMS Å | 反畴 RMS Å | a 差值 % | c 差值 % |
|---|---|---:|---:|---:|---:|
| AlN | 186 / 186 | 0.00146 | 0.59634 | +0.261 | +0.463 |
| GaN | 186 / 186 | 0.00098 | 0.64675 | +0.441 | +0.530 |
| ZnO | 186 / 186 | 0.00275 | 0.63824 | +0.253 | −0.117 |
| PTO | 99 / 99 | 0.04332 | 0.65704 | −0.924 | +4.367 |

RMS 使用数据库晶胞度量，去除共同平移，**不包含晶胞应变**；
同畴判断是结构匹配的诊断推断，不是选取使张量更接近数据库的符号。
PTO 的晶格与内部坐标差异明显，后续响应偏差不能全部归因于后端或赝势。
最终响应参考若经过 R2r 或 VASP 续优化，必须对其实际参考结构重新审计，
不得把本表的 R1 哈希直接作为其他结构的验收证据。

证据：`outputs/pbe_database_comparison_20260918/ABACUS_reference_domain_audit.json`，
保留源结构 SHA256、数据库哈希、原子对应与平移；原始计算目录仍保留输入。
新增平移/同元素置换、反畴与错误坐标方向测试，相关回归 **60 passed**。

## 已收集 PBE 响应更新：ABACUS 四体系完整；AlN/GaN/ZnO 原生 e/C/d 通过

以下均为三维 bulk proper relaxed-ion e，单位 C/m²。
差值百分比为 `100 × abs(计算值−数据库值)/abs(数据库值)`；
禁戒零分量只比较绝对误差，不填无穷百分比。参考仍为 de Jong/VASP/PBE，
不是实验值。完整18分量保存在对应 `*_full_tensor_comparison.csv`。

| 材料/计算器 | 分量 | ZStar PBE | 数据库 PBE | 绝对相对差 % | 科学验收状态 |
|---|---|---:|---:|---:|---|
| AlN/ABACUS+PYATB | e31 | −0.568978 | −0.580060 | 1.91 | 内部 e/C/d 检查通过 |
| AlN/ABACUS+PYATB | e33 | 1.387956 | 1.461150 | 5.01 | 同上 |
| AlN/ABACUS+PYATB | e15 | −0.297343 | −0.289305 | 2.78 | 同上 |
| AlN/VASP native，`ISYM=2` | e31 | −0.581490 | −0.580060 | 0.25 | e/C/d 已验收，600 eV 与数据库1000 eV不同 |
| AlN/VASP native，`ISYM=2` | e33 | 1.461400 | 1.461150 | 0.017 | 同上 |
| AlN/VASP native，`ISYM=2` | e15 | −0.309530 | −0.289305 | 6.99 | 同上 |
| GaN/ABACUS+PYATB | e31 | −0.303847 | −0.289820 | 4.84 | 内部完整e/C/d检查通过，外部差异保留 |
| GaN/ABACUS+PYATB | e33 | 0.525069 | 0.464510 | 13.04 | 同上 |
| GaN/ABACUS+PYATB | e15 | −0.188174 | −0.139315 | 35.07 | 同上，未称严格外部复现 |
| GaN/VASP native，`ISYM=2` | e31 | −0.264450 | −0.289820 | 8.75 | 总 e/C/d 已验收；内应变分解警告保留 |
| GaN/VASP native，`ISYM=2` | e33 | 0.422860 | 0.464510 | 8.97 | 同上 |
| GaN/VASP native，`ISYM=2` | e15 | −0.146180 | −0.139315 | 4.93 | 同上 |
| ZnO/ABACUS+PYATB | e31 | −0.521673 | −0.537510 | 2.95 | 直接e/C/d内部检查通过；独立内应变张量警告保留 |
| ZnO/ABACUS+PYATB | e33 | 1.047482 | 1.036810 | 1.03 | 同上 |
| ZnO/ABACUS+PYATB | e15 | −0.384008 | −0.385000 | 0.26 | 同上 |
| ZnO/VASP native，精确六方 `ISYM=2` | e31 | −0.536880 | −0.537510 | 0.12 | 总 e/C/d 已验收；结构投影仅去除序列化噪声 |
| ZnO/VASP native，精确六方 `ISYM=2` | e33 | 1.042050 | 1.036810 | 0.51 | 同上 |
| ZnO/VASP native，精确六方 `ISYM=2` | e15 | −0.399280 | −0.385000 | 3.71 | 同上 |
| PTO/ABACUS+PYATB | e31 | 1.710979 | 1.643650 | 4.10 | 完整中心差分e/C/d；外部差异保留 |
| PTO/ABACUS+PYATB | e33 | 2.114819 | 2.792120 | 24.26 | 同上，不宣称严格复现 |
| PTO/ABACUS+PYATB | e15 | 2.895233 | 3.259890 | 11.19 | 同上 |
| PTO/VASP native | e31 | 1.668570 | 1.643650 | 1.52 | 已计算；原生d门待解决 |
| PTO/VASP native | e33 | 2.438230 | 2.792120 | 12.67 | 同上 |
| PTO/VASP native | e15 | 2.796210 | 3.259890 | 14.22 | 同上 |

### d33 单列：不伪造数据库参考

2026-09-19补充：e档案确实不直接提供d，但可结合独立冻结弹性档案构造
AlN/GaN/ZnO的**有条件跨档案PBE d33参考**，并注明几何、设置和极性取向差异。
数值与完整C比较见[v2_pbe_cross_archive_d_reference_20260919.md](v2_pbe_cross_archive_d_reference_20260919.md)。
下表“此数据库d33”仍指直接报告值，不将跨档案推导值冒充原生数据库字段。
PTO在该弹性档案没有配对C，外部d33仍空缺；其 native 重算完成前仍不提升旧值。

| 材料/计算器 | d33 pm/V（=pC/N） | 此数据库 d33 | 备注 |
|---|---:|---|---|
| AlN/ABACUS+PYATB | 4.975410 | 未提供 | 同一组 proper e 与 C^E 导出 |
| AlN/VASP native，`ISYM=2` | 5.323688 | 未提供 | 已验收 native strain 路线；`e=dC` 闭合通过 |
| GaN/ABACUS+PYATB | 1.872239 | 未提供 | 同一组proper e与relaxed C导出；外部d验证未完成 |
| GaN/VASP native，`ISYM=2` | 1.583054 | 未提供 | 总 e/C、弹性稳定性与 `e=dC` 闭合通过；内应变分解警告保留 |
| ZnO/ABACUS+PYATB | 9.666372 | 未提供 | 由本次直接proper e和relaxed C导出；不宣称内应变张量已验收 |
| ZnO/VASP native，精确六方 `ISYM=2` | 9.750071 | 未提供 | 总 e/C/d 已验收；不把结构序列化噪声修正冒充物理优化 |
| PTO/ABACUS+PYATB | 49.084674 | 未提供 | 同一组proper e与relaxed C导出；外部d验证未完成 |
| PTO/VASP native | 未发布 | 未提供 | raw内应变警告保留；诊断代数值不代替合格d |

AlN 两后端 d33 差6.54%（以新 `ISYM=2` VASP 结果为分母）；此前完整张量
Frobenius 比基于旧验收档案，待统一结果档案重生成后更新，不混用新旧来源。
C 全矩阵 Frobenius 差1.32%。这些是后端/不同平衡结构/不同数值设置的整体差异，
不能当成同输入下仅赝势误差的分离证明。ABACUS e 对数据库全张量差4.39%。

AlN/ABACUS：13个结构、13次PYATB（每次3个极化方向），6个独立应变方向均取±0.005，
e 拟合rank18/18、C rank21/21，参考力2.073e-5 eV/Å，13个阶段均绝缘。
C 最小本征值113.133 GPa，d/e/C闭合2.22e-16 C/m²。
e 对称性投影最大偏差2.19e-4 C/m²，未用投影替换原始张量。
保存原始差分拟合残差：e max3.279e-4 C/m²、relative1.936%；
C max0.18013 kbar、relative0.9154%。二者是±扰动线性模型残差，
不是外部参考误差，亦不是通过代数闭合证明绝对精度。

实际 R2r 的 AlN/GaN/ZnO 已重做同相/同畴审计；原结构与哈希保留。
ZnO/VASP 的 c/a 存在微小轴向漂移，采用显式正交 frame：z沿实际c，x沿a在垂直c平面的投影。
旋转后晶胞残余剪切最大8.16e-5 Å，保留而非标准化/圆整，空间群仍在symprec1e-3 Å下为186。
对 e/C/d 分别使用工程应变/普通应力的正确坐标变换，保存原始 e、旋转矩阵与审计证据；
不翻转符号、不靠旋转抹除内应变警告。
证据 `outputs/pbe_database_comparison_20260918/current_reference_domain_audit.json`。

### GaN/ZnO 原生警告与有界对照

GaN：displaced-atom 内应变平移残差0.10137 eV/Å，relative1.223%；
strained-cell route残差仅1e-5 eV/Å，两个导数最大互易差0.06785 eV/Å。
ZnO：对应为0.11230 eV/Å、relative1.515%、1e-5 eV/Å与0.06894 eV/Å。
原生 ionic e/C 使用 displaced-atom contraction，不能简单替换成平衡更好的另一导数
然后仍宣称原生结果已验收。d 拒绝原因完整保留。

GaN 单次独立对照作业27721360，HF node272，32MPI×1OMP、非独占。
复用已合格平衡POSCAR，仅运行新的native参考SCF和响应，保持EDIFF1e-8、ENCUT1000、
POTIM0.01、NFREE2、k网格和PBE PAW不变。设置ISYM2/SYMPREC1e-3/NCORE1，
不再relax、不提高精度、不自动重试；仅验证对称性保留是否改善应力-位移导数。
这是尚待结果验证的假说，不是已证实根因。
NCORE1是为避开旧版本原生k点变化兼容限制，见
[VASP官方讨论](https://vasp.at/forum/viewtopic.php?t=19315) 与
[IBRION官方定义](https://vasp.at/wiki/index.php/IBRION)。

AlN/ABACUS响应部分 ABACUS累计2841 s，PYATB累计91 s，日志计数109次已收敛SCF cycle，
40 rank-wall约32.578 core-hours；不含R1/R2r、不冒充实测rank CPU。
历史GaN/VASP作业27720982总分配46m04s×32≈24.569 core-hours，历史ZnO/VASP恢复
作业27721213总分配26m55s×32≈14.356 core-hours。当前验收重算分别为GaN
27723293（18m29s，9.858 rank-wall core-hours）和精确六方ZnO 27723364
（15m52s，8.462 rank-wall core-hours）；失败的隔离控制另行记录，不能并入成功作业
制造加速比。
这些不同材料/阶段成本不能作为同任务加速比。

可复现比较需增加
`--additional-calculations outputs/pbe_database_comparison_20260918/completed_calculations.json`。
冻结旧比较JSON中的GaN/ZnO/PTO状态为 `scientific_gate_pending`；当前GaN/ZnO已由
新对称性开启重算及 e/C/d 闭合证据取代，PTO仍等待本轮重算完成。
AlN/GaN/ZnO/PTO ABACUS完整收集；PZT的ABACUS及原生对称性对照尚需收齐，目标未完成。

## ZnO / ABACUS / PBE 完成与逐响应质量边界

PBS714456.mu01的tracejob确认Exit_status=0、wall time00:38:58；
尾部006±与005±全部DONE。仅运行现有收集器，13个几何与13个PYATB后处理齐全，
不重新优化、重算SCF或改变既定阈值。原串行driver的failure.json完整保留：
exit10是遇到PBS仍占用005+时的互锁，不是该DFT阶段失败。
`ZnO_ABACUS/continuation_collected.json`明确保留原准备记录和互锁的哈希与解释。
实际参考哈希匹配既有SG186、同+c畴审计，不隐式调转极化或投影e来改善比较。

完整18分量CSV为`ZnO_ABACUS_full_tensor_comparison.csv`；全e Frobenius差1.727342%。
数据库零分量的最大原始计算值为e16=0.002185528 C/m²，必须保留：
它不满足“所有禁戒分量均小于1e-3”的更强说法。
现有非零e张量混合门为max(0.02 C/m²,2%×响应尺度)，本次检查通过；没有调整门。
对称投影相对残差e=0.00240819、C=0.000198111；后者最大差0.41059446 kbar。
应变增量拟合相对残差e=0.0279900、C=0.0112118，不是统计误差条。

直接proper e、relaxed C的输入rank6，拟合rank分别18/18与21/21。
参考最大力6.001024e-5 eV/Å，全部13几何绝缘，最小PBE gap0.639271 eV。
C最小特征值41.661535 GPa，条件数9.52124；d=e(C^E)^-1闭合约1e-15 C/m²。
**d33=9.666371551 pm/V（=pC/N）**。数据库不提供配对C/d，不伪造d33参考或百分差。

独立测得的内部位移导数Lambda，对称投影最大残差0.008119229 Å/strain，
超过该响应既有0.001门，状态allowed_subspace_violation；Gamma检查为consistent。
因此只说直接e/C/d内部检查通过，不说全部内应变/分解响应均已验收。
该Lambda残差乘0.005约4.06e-5 Å，提示极小内部位移噪声可能被求导放大，
但这仅是数量级诊断，尚不是根因证明或放宽质量门的理由。
本次直接极化/应力拟合的e/C/d不以Lambda重建为输入，两种质量结论分开记录。

资源：40 MPI×1 OMP，ABACUS7278 s、PYATB138 s，共82.4 rank-wall core-hours，
154次SCF循环、1119条电子迭代行；不含参考优化和历史失败费用。
逐点计时及日志哈希见`ZnO_ABACUS/response_cost_audit.json`。

### GaN原生对称性控制已结束：改善但未通过d门

Slurm27721360 COMPLETED、ExitCode0:0，分配17m42s×32=9.44 core-hours；
native两阶段及收集记录9.0625 rank-wall core-hours，二者统计口径不同。
参考POSCAR哈希与原任务完全一致；PBE PAW、k点、ENCUT、EDIFF、
POTIM/NFREE不变，仅ISYM0/NCORE4变为ISYM2/SYMPREC1e-3/NCORE1。
同时改变ISYM、SYMPREC和NCORE三个设置，不能分别归因其中某一参数。

| 指标 | 原生原任务 | 对称性控制 |
|---|---:|---:|
| displaced-atom Gamma平移残差 eV/Å | 0.10137 | 0.02736 |
| 相对平移残差 | 1.22345% | 0.330385% |
| strained-cell Gamma平移残差 eV/Å | 0.00001 | 0.00001 |
| Gamma两路线最大差 eV/Å | 0.06785 | 0.03129 |
| e31 C/m² | −0.26749 | −0.26445 |
| e33 C/m² | 0.41995 | 0.42286 |
| e15 C/m² | −0.14675 | −0.14618 |
| e31对同相PBE数据库绝对相对差 | 7.70478% | 8.75371% |
| e33对同相PBE数据库绝对相对差 | 9.59290% | 8.96644% |
| e15对同相PBE数据库绝对相对差 | 5.33683% | 4.92768% |
| d验收 | 未通过，未发出 | 未通过，未发出 |

对照相对原任务e全矩阵Frobenius变化0.983414%，
C全矩阵变化0.213787%，最大C差0.49027 GPa；
对照C最小本征值89.2749 GPa、major symmetry通过。
这些是确定性设置敏感度，不是误差上界或统计置信度。
改善后的Gamma残差仍大于原生既定1e-3门，保留`scientific_gate_pending`，
不为了发出d而改门，不把balanced strained-cell数据悄悄替换到原生ionic e/C。
该单次对照未完全解决问题，暂不批量复制到ZnO/PTO/PZT，不提升精度或盲目重投。
下一步优先使用既有BORN/IFC及两条Gamma路线检查原生内部贡献重现关系，
并等待独立ABACUS中心应变结果；若需新的VASP应变响应，必须有明确针对性而非重试。
独立归档`outputs/pbe_database_comparison_20260918/GaN_VASP_symmetry_control/`，
含native JSON、continuation、BORN、FORCE_CONSTANTS与全部18分量数据库比较，
不覆盖原任务或主比较表。

## PZT有序模型：独立列示，不混入匹配数据库主表

Slurm27720985已COMPLETED/0:0，72/72扰动完成并收集；实际参考1、原子位移60、
工程应变12。PBE/PAW/ENCUT1000/EDIFF1e-8、ISYM0/NCORE4，32 MPI×1 OMP。
当前accepted参考SG99、force8.25900e-5 eV/Å、stress0.00862859 kbar、gap1.8381 eV。
对应10原子[001]有序PZT50/50，不是无序陶瓷或MPB。

| 独立模型量 | PZT/VASP PBE | 匹配PBE数据库值 | 百分差 |
|---|---:|---:|---:|
| e31 / C/m² | 1.11308 | — | — |
| e33 / C/m² | 2.99118 | — | — |
| e15 / C/m² | 6.63810 | — | — |
| d33 / pm/V，displaced-route诊断 | 231.5118 | — | — |
| d33 / pm/V，strained-route诊断 | 246.9153 | — | — |

941条冻结数据库formula中无同时含Pb/Ti/Zr的条目；不伪造配对参考或陶瓷实验百分差。
原生C正定，最小特征值9.514530 GPa；光学Phi的几何正交补rank27、全部正、
最小0.540549109 eV/Å²。raw内应变净力relative0.003988243，原生未输出d。
两路线诊断d33变化6.6534%，全d最大差24.2181 pm/V/Frobenius6.76352%；
小e/C路线差不能保证软弹性材料d也稳定。两种d都不是已验收benchmark。
资源分配92.72 core-hours，native-driver79.52898 core-hours，范围重叠不相加。
详见[模型结果与完整审计](v2_pzt_ordered_model_results_20260919.md)及PZT_VASP/model_summary.json。
