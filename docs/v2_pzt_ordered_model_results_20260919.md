# PZT50/50 [001] 有序模型：PBE 原生响应结果与诊断边界

## 完成状态与模型

HF Slurm27720985在node25完成，COMPLETED/0:0，32 MPI×1 OMP。
原生日志确认72/72扰动完成；完整e/C、all-atom BEC、Gamma IFC已收集。
本轮仅收集和代数审计，不增加DFT、不修改原输入或native质量门。

对象是三维周期10原子Pb2TiZrO6，沿[001]有序的50/50 Ti/Zr模型，SG99。
保留原晶胞/原子顺序，不代表无序陶瓷、MPB、温度或畴壁贡献。
当前参考最大力8.25900e-5 eV/Å、最大应力0.00862859 kbar、PBE gap1.8381 eV。
accepted POSCAR SHA256为04636815007af358a93855b5415b1b98365bb525831fe5134615aa4826e8efa2。
continuation.source.reference_accepted=false是原R1来源metadata，原样保留；
后续当前reference_gate与精确accepted POSCAR另行审计，不能用旧字段抹去当前验证或覆盖历史。

参数为PBE、原PAW、ENCUT1000 eV、EDIFF1e-8、IBRION6/ISIF3、
NFREE2/POTIM0.01、ISYM0/NCORE4。spglib固定1e-3 Å，未改VASP SYMPREC。
从完成OUTCAR核查参考1、原子位移60、应变12、mixed0；
实际中心工程应变±1%，原子位移约±0.01 Å；不是ABACUS的±0.5%协议。
OUTCAR序列化的最大非仿射位移0.010004819 Å、最大工程应变0.010000000097；
保留全部实际向量、正负配对与打印精度限制，不只凭POTIM推断点数。

## 原生e/C

坐标为原Cartesian frame，+z近似+c；工程Voigt顺序xx,yy,zz,2yz,2xz,2xy，固定宏观E。
下面是未投影的原生relaxed-ion值，不是平均或改符号后的数据库拟合值。

| 分量 | 本模型VASP/PBE | 匹配数据库值 | 百分差 |
|---|---:|---:|---:|
| e31 / C/m² | 1.11308 | — | — |
| e32 / C/m² | 1.11346 | — | — |
| e33 / C/m² | 2.99118 | — | — |
| e15 / C/m² | 6.63810 | — | — |
| e24 / C/m² | 6.65339 | — | — |
| C33 / GPa | 41.23857 | — | — |

完整18分量e与36分量C见model_summary.json和原native JSON，禁戒小分量也保留。
C最小特征值9.514530 GPa、最大302.103175 GPa，正定但较软；
major symmetry通过。这是当前局部零温响应证据，不是全部q声子/有限温稳定性证明。
投影后的几何光学子空间有27个正特征值，最小Phi=0.540549109 eV/Å²。
光学基由三维整体平移的正交补构造，不能简单丢弃排序最低三本征值来隐藏不稳定模。
BEC中性投影最大2e-6 e，Phi投影Frobenius幅度1.32121e-4；
三个原始近零声学频率微负值仍保留在native文件，不伪装为严格零。

冻结的de Jong PBE数据库SHA与既有比较一致，941条formula中没有同时含Pb/Ti/Zr的条目。
因此该冻结集没有匹配有序模型：不填入不匹配材料、陶瓷实验d33或拼接C产生百分差。
这不是宣称所有文献都没有匹配模型，后续独立理论文献比较仍待完成。

## d33单独审计：已有数值，但尚非验收benchmark

原生backend没有发出d，因为displaced-atom内应变净力最大0.1628 eV/Å，
relative0.003988243超过原生既定门；strained-cell净力仅2e-5 eV/Å，
两路线Xi最大差0.06054 eV/Å。原始警告和拒绝原因保留。

复用v1的显式中性/平移/互易投影和v2单位感知内应变求解，
将两条Xi路径分别收缩，不替换原生已收集结果；全rank27、平衡残差约1.6e-16。
同displaced-route收缩重现原生ionic e最大差6.8069e-5 C/m²、ionic C最大差4.8019e-4 GPa。
这核查符号/单位/索引闭合，不是独立DFT准确性证明。

| 研究诊断量 | displaced-atom路线 | strained-cell路线 | 路线差 |
|---|---:|---:|---:|
| d33 / pm/V (=pC/N) | 231.5118 | 246.9153 | +6.6534% |
| d15 / pm/V | 359.5926 | 383.8107 | — |
| d24 / pm/V | 359.1118 | 382.0797 | — |

完整d两路线最大差24.2181 pm/V，Frobenius差6.76352%；
e/C的Frobenius差分别1.04148%/0.492044%。
13个d分量超过已有幅度稳定性目标作为说明性尺度的比较，
但没有把该尺度偷换成新的native验收门或误差条。

精确矩阵恒等式为delta_d=(delta_e-d_a delta_C) S_b，转换单位后：
delta_d[pm/V]=1000 delta_e[C/m²] S_b[1/GPa]−d_a[pm/V] delta_C[GPa] S_b[1/GPa]。
其d33分解为+0.893757 pm/V（e项）和+14.509703 pm/V（C项），
合计+15.403460 pm/V，闭合最大1.51e-14 pm/V。
C条件数约31.75/33.68，说明较软弹性方向会放大d路线差；
此代数归因不是唯一物理噪声源证明，也不是独立准确性或统计置信区间。
因此不能把“e/C差小”直接写成“d已高精度验证”，当前d仍标诊断值。

## 资源与可复现审计

本作业分配wall2h53m51s，32核共92.72 allocated core-hours；
native driver两个阶段加收集8947.010s，79.52898 rank-wall core-hours；
response OUTCAR elapsed8680.823s。三者范围重叠，不能相加。
不包含其他任务/历史失败的全campaign费用，另见ISYM实验账目。

研究档案位于outputs/pbe_database_comparison_20260918/PZT_VASP；
SHA和完整units/axes/provenance记录在model_summary.json。
审计命令（在v2研究目录）为：

```powershell
$env:PYTHONPATH='D:/Work/Code/zstar-v2-development'
python .codex-output/audit_native_perturbation_geometry.py --outcar outputs/pbe_database_comparison_20260918/PZT_VASP/response_OUTCAR --poscar outputs/pbe_database_comparison_20260918/PZT_VASP/reference_POSCAR --output NEW_actual_perturbation_audit.json
python .codex-output/audit_native_ionic_contractions.py --pzt --output NEW_PZT_ionic_audit.json
python .codex-output/summarize_native_route_sensitivity.py --pzt --output NEW_PZT_route_sensitivity.json
python .codex-output/audit_pzt_native_d_sensitivity.py --output NEW_PZT_d_sensitivity.json
```

首次执行的已归档输出使用exclusive创建；再次审计需保留历史并选择新输出，
不能覆盖旧证据或将FileExists误判为需要重跑DFT。
路线汇总与d分解默认仅读取冻结档案，新输出用于重复核查，不悄悄切换其来源。
uncertainty-and-units skill促使明确单位及确定性敏感度边界：
standard_uncertainty=null、distribution unknown，无伪造±；沿用现有单位层，不升级科学环境。
本轮相关5文件55测试通过，3183已有依赖弃用警告；三个单位静态审计0 findings/0 suppression。
新增三维完整矩阵有限变化分解测试，e/C两项精确相加还原完整delta d。
三份审计以新exclusive输出实际重复执行，完整JSON与冻结档案逐项一致；无新增DFT或覆盖。
这是定向回归，不是全v1/v2回归完成声明。

## 未完成事项

ABACUS/PYATB本模型中心±0.5%响应的原始任务已经终止，但只有11/12个应变端点
通过固定门槛。`005+`运行满100个离子步后最大笛卡尔力分量仍为
`1.486934e-4 eV/Å`，驱动器拒绝该点且未运行PYATB，因此不能重建或独立比较完整
ABACUS e/C/d张量。精确对称`ISYM=1`完整电子对照已经结束；其结论见下节，
不再沿用“仍排队”的历史状态。
PZT诊断d的路线敏感性需明确处理，不能仅因材料“明星”或数值大就提升为验证结果。

2026-09-19进一步完成全e/C/d空间群审计：P4mm允许e/C/d参数数3/6/3；
原生e/C最大对称偏离0.018050 C/m²、0.142260 GPa。
诊断d位移/应变路线最大偏离7.118926/2.290662 pm/V，相对残差1.61755%/0.59050%。
这些不是d33误差或置信区间，没有覆盖native d拒绝条件或替换张量；
详见内应变审计文档新增完整表与versioned symmetry JSON。
包含新增三维剪切/旋转负控制的全本地测试622通过，但本地依赖最低版本问题保留，
不等同于独立native worktree、外部DFT或发布审查通过。

## 最新终态补充：精确对称 ISYM=1 对照

上述排队信息属于历史快照。HF27722088现已COMPLETED/0:0，实际36原子+12应变扰动，
轨道补全输入秩30/30与6/6。完整原生e/C相对原任务差0.384%/0.216%，
但原生d仍未输出，两路线诊断d33为232.397456/250.678969 pm/V，差7.8665%。
这是改善后的完整对照，不把静态电子成功或任务减少当作d已验收；
详见[终态完整对照及费用口径](v2_pzt_isym_completed_comparison_20260919.md)。
ABACUS本模型原始响应随后以11/12个合格端点终止：`005+`在100步后未过
`1e-4 eV/Å`力门，故原档案仍没有可验收的完整ABACUS e/C/d张量。
