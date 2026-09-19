# PZT strain-005-：终态力与能量轨迹审计

这是研究诊断，不是合格压电响应点，不改变生产精度或验收门。
模型仍为PBE、10原子PZT50/50 [001]有序周期晶体，不代表随机合金、陶瓷或MPB。

## 可核查证据

原始日志来自PBS714459、cu15、40MPI×1OMP。
100步达到relax_nmax100后driver停止；ABACUS returncode0不等于离子收敛。
输入force_thr_ev1e-4、scf_thr1e-8、stress_thr0.5未改。
归档的有效INPUT确认relax_method=cg、relax_new=1、relax_scale_force=0.5；
不能把该失败解释为已经证实的BFGS往复。

复用`zstar/v2/abacus.py`的力块解析器和`zstar/v2/units.py`单位层，
按唯一连续ionic step划分日志；每步核查ION索引、电子收敛、SCF能量和唯一力块。
全部100步通过电子收敛配对检查，原子顺序Pb1/Pb2/Ti1/Zr1/O1–O6不变。
日志最大梯度与最大Cartesian力分量在六位小数打印精度内一致；
它不等于最大原子力向量范数。

| 诊断量 | 实际值 | 说明 |
|---|---:|---|
| 第100步最大力分量 | 1.609807e-4 eV/Å | 未达到1e-4 |
| 第100步最大原子力范数 | 2.05939008e-4 eV/Å | 同样未达到1e-4；最大来自Zr |
| 第81–100步最大力分量的最小值 | 1.562851e-4 eV/Å | 末段从未跨过输入阈值 |
| 第81–100步最大力分量的最大值 | 3.131873e-4 eV/Å | 非单调下降 |
| 第81–100步能量跨度 | 3.30399416e-7 eV | 能量几乎不变不等于力达标 |
| 第81–100步能量上升次数 | 2/19 | 不据此单独推断优化器故障或SCF噪声 |

这些是不同离子几何下的确定性诊断量，不是重复同几何采样的噪声估计，
standard_uncertainty/distribution/degrees_of_freedom保留null，不给虚构置信区间。
本地Python3.10未安装Pint；不改依赖环境，复用已有明确单位层。

## 尚未证明的根因与恢复前置条件

已证明停止条件是100步内离子未收敛，不是电子SCF失败或观察超时。
目前不能区分优化器收敛慢与电子/基组力噪声，也不能仅由该轨迹证明数值力误差大小。
未进行力—坐标配对或位移轨迹解释，不能将力波动直接视为SCF误差。

末步DIRECT坐标在末步力之后打印，且与最终STRU_ION_D的坐标相同。
最初仅凭打印顺序没有证明其坐标是在力计算前还是优化更新后。
随后核对原始日志头记录commit=e84abb4，与235源码完整HEAD
`e84abb490c853f5abefa13cde897af15e64afc7a`一致；下面两份源码相对HEAD无修改。
`source/module_relax/relax_driver.cpp`在第69行计算力，第81行调用relax_step，
第104行写出STRU_ION_D；`relax_new/relax.cpp`第70行先检查收敛，
未收敛则第83/88行调用move_cell_ions，第636行更新坐标，第639行打印坐标。
因此在本失败分支中，最后记录的力先于最后一次坐标更新，不能当作最终写出几何的力。
这解释了配对风险，不是已证明的离子不收敛微观根因。
两文件SHA256分别为
`27d34aa3f475d56092df3ac92acc02200a0468cd810a5623ae111991595b8633`和
`ede5bf5d63d7545ab526b4c2f7dc9ea725dee217f1870b038b92581ebd7314ca`。
失败端点不得无条件把末步力、最终结构和已有矩阵输出配成合格响应记录。
成功收敛案例未因此被重算或改动。

下一项有辨识力的检查是：在独立目录，对实际序列化终点运行一次相同生产设置的SCF，
检查该几何的力、绝缘性与输出完整性。若需估计电子力重复性，还必须使用同一几何，
不能把与未配对旧力的差异直接称为SCF噪声。
先核查授权空闲资源，再执行这一单任务检查；不增加精度、不扫描参数，
也不盲目从原始未弛豫结构重跑100步。
独立终点SCF检查已提交HF Slurm **27722541**，确认RUNNING于node43，32MPI×1OMP，
非独占节点；只是诊断，不是再跑100步弛豫，不自动将失败点变为accepted。
三个235授权节点检查时均忙，未追加重叠任务。
目录：`/public/home/iai806/abacus/agent-runs/20260919-v2-pzt-endpoint-scf`。
终点STRU逐字节复用归档STRU_ION_D，KPT保持9×9×4；
INPUT仅改变calculation的物理设置为scf，其余生产参数保持原值。
四种赝势和四种8au轨道全部核对原235 SHA256一致。
HF旧案例有10au轨道，**未以其替代**本次8au源轨道。

必须披露构建差别：235 ABACUS v3.10.0 commit=e84abb4，binary SHA256
`0c79137116199e417fea8aa8a97f85802b1025fdb17fe4303d6842d7e9068206`；
HF也是v3.10.0，但运行日志commit=f7cb1d3，binary SHA256
`88ea7f91c9f3091ef5fb4f410ab88267b14ecfe7f35c86dfaee9bf9319cace7a`。
这项跨构建诊断可检查HF构建下该实际几何的力，不是严格同二进制重复性实验，
不能用它与未配对旧力的差异估计SCF噪声，也不能自动填入235中心差分ensemble。
如需原构建验收或严格噪声比较，仍需原构建同几何检查。
恢复弛豫决策尚未执行，未发布稳定功能或新的验收政策。

## 可复现审计

```powershell
$env:PYTHONPATH='D:/Work/Code/zstar-v2-development'
python .codex-output/audit_pzt_relaxation_trajectory.py --archive outputs/pbe_database_comparison_20260918/PZT_ABACUS_pending/terminal_strain005_minus_714459_20260919 --natoms 10 --output NEW_force_energy_trajectory_audit.json
python -m pytest -q tests/test_v2_pzt_relaxation_trajectory.py
```

输出路径必须不存在；工具只分析日志，不运行计算器、不重启作业、不接受响应点。
实际输出为上述归档目录的`force_energy_trajectory_audit.json`，包含100步完整力、能量、单位、
坐标定义、原子标签、源日志SHA256、算法和复用解析器SHA256。
日志SHA256：6f672a9010f744987f975d682396b70899d84b7802fa500e115915e1261a926b。
有效INPUT另存`INPUT.effective`，本地/远程SHA256一致：
674da2f9a57ab84e749548ed56da8b1c9addf881d569e63d8076228a659ccc2c。
原七文件及terminal_receipt保持不变。

新增6项测试通过，覆盖三维力分量/范数差异、step配对、电子失败、原子顺序变化、
打印梯度不一致与能量缺失。对原始36.5 MB日志完成真实解析，非仅合成测试。
随后重新执行整个独立v2目录`python -m pytest -q`：669 passed，4347 warnings，31.54秒，exit0。
这是本地软件回归证据，不是未完成PZT第一性原理计算的替代。
本次ABACUS技能影响是保留原输入、核对实际有效优化器和禁止盲目重投；
单位技能影响是显式区分力分量与范数、不把轨迹散布伪装成统计不确定度。

## 终点SCF完成及三维坐标配对结果

HF27722541已COMPLETED0:0，node43/32MPI×1OMP；电子收敛，唯一力块完整。
复用v2力/应力/能量/istate解析器，归档11文件SHA256与远程一致，
机器记录的全部力、应力、能量、带隙逐项与原输出再解析一致。
`endpoint_scf_HF_27722541/completed_diagnostic.json`保存完整三维原子力及来源。

| 实际序列化终点诊断量 | 数值 |
|---|---:|
| 最大Cartesian力分量 | 1.442751e-4 eV/Å，不达标 |
| 最大原子力范数 | 1.56940693e-4 eV/Å，不达标；O6 |
| 带隙 | 1.84202768 eV，绝缘 |
| 固定应变晶胞最大原始应力分量 | 1.34330522 kbar |
| SCF rank-wall core-hours | 2.77333333，仅312秒×32核；非实测cputime |
| Slurm walltime | 313秒；与SCF时间重叠，不能相加 |

1.343kbar是被施加剪切应变晶胞的响应应力，不能拿参考结构0.5kbar门拒绝它；
本点真正未达到的是力要求。未运行PYATB、不收录中心差分点，不将跨构建力差称为噪声。

原构建100步三维配对另写入`force_coordinate_pairing_audit.json`，
复用v1 Unified的STRU读取；使用pymatgen Lattice对实际倾斜3D晶胞求最近周期镜像，
不按分数坐标直接四舍五入位移，不排序、不投影或对称化原子。
日志初始/终态坐标与文件相差0（周期等价意义），cell序列化最大差1.0e-10 Å。
正确配对是F_j属于更新前坐标，Δu_j连接更新前/后坐标；
一阶预测ΔE_j=-Σ_i F_ij·Δu_ij，与下一步同构建SCF能量差另列，二者不能强制相等。
第100步更新后的同构建力/能量尚未计算，不混入HF跨构建结果充当下一步。

末20步最大原子位移范围1.99009349e-6至1.41720983e-5 Å；
一阶预测上坡的移动数为0/20。第100步仍移动1.99009349e-6 Å，
一阶预测能量下降1.34806493e-9 eV，力—位移余弦0.99644021。
这支持末段仍沿下降方向作很小的更新，而非已经证明的严格二点往复；
也不证明力噪声、优化器bug或其唯一微观原因。
这里的离子优化更新量不是BEC采样步长，不应为凑0.01 Å而改写它。

配对分析新增5项测试通过，覆盖三维倾斜晶胞跨边界位移/功、
过大移动、非有限值、维数/原子顺序及重复坐标块；实际100步解析无parser warnings。
算法SHA256：`be44c351aac131c6d3ce4687b1758b5eb68cd786c0bcea983091efb4a507d6e2`。
首次测试的nested pytest.approx使用错误已修正为NumPy数组；
首次脚本运行缺PYTHONPATH未生成结果，修正调用环境后5 passed、真实审计exit0。
软件环境如实记录Python3.10.9、pymatgen2025.10.7、NumPy1.23.5，未安装或升级依赖。
材料分析技能影响是保留实际晶胞/周期性、最近镜像和原子对应；
单位技能影响是显式将F·Δu作为eV的一阶功，不当作统计误差或有限步精确能量。

```powershell
$env:PYTHONPATH='D:/Work/Code/zstar-v2-development'
python -m pytest -q tests/test_v2_pzt_force_coordinate_pairing.py
python .codex-output/audit_pzt_force_coordinate_pairing.py --archive outputs/pbe_database_comparison_20260918/PZT_ABACUS_pending/terminal_strain005_minus_714459_20260919 --output NEW_force_coordinate_pairing_audit.json
```

下一步优先原构建同几何力核查，并评估从保存终点重置优化状态的单点恢复实验；
不提高精度、不扩大单次100步上限、不从未弛豫初始结构盲目重跑。
本轮尚未执行该恢复弛豫；其余原作业仍按既定计划推进。

新增配对分析后的完整独立v2回归实测：
`python -m pytest -q --disable-warnings`，674 passed、4347 warnings、31.51秒、exit0。
配对/轨迹/压电collector针对性联合测试为16 passed、4 warnings、0.91秒。
结果写入`local_full_regression_pzt_pairing_20260919.json`，不覆盖旧669项快照。

## 后续实际提交：保存终点的单次 CG 状态重置试验

此前“尚未执行恢复弛豫”是历史观察；随后已提交 HF Slurm **27722565**。
实际观察为 RUNNING、node43、32 MPI×1 OMP、非独占，elapsed 00:03:48；
运行回执 start_unix=1789769010。新目录为
`/public/home/iai806/abacus/agent-runs/20260919-v2-pzt-endpoint-cg-reset`。

假设是从已保存、接近收敛且绝缘的终点重新开始，清除旧 CG 历史可能改善收敛。
INPUT 与失败生产 INPUT 字节相同，仅 STRU 换为已核查的 STRU_ION_D；
SCF 1e-8、力 1e-4 eV/Å、单次 relax_nmax=100 不变，KPT、PP、8au轨道哈希核查通过。
新目录和运行标记禁止重复提交；不覆盖原日志、不提高精度、不自动重试或启动PYATB。
记录见 `PZT_ABACUS_pending/endpoint_cg_reset_HF_submission_27722565.json`。

实际构建 f7cb1d3 与 HF 终点 SCF 27722541 一致，但不同于原235构建 e84abb4。
因此这是跨构建隔离恢复试验，不是同原构建重复性检验，不自动填回235响应ensemble。
原计划仍为6/12完成点；本试验运行不增加完成点计数。
须待电子/离子收敛、最大原子力范数≤1e-4 eV/Å及绝缘性逐项核查，
计算器的收敛标记本身不足以验收；目前终态力、带隙和资源消耗尚未确定。
即使成功，也不能据此唯一归因于CG历史或宣称已排除构建差异。

## CG 重置试验终态与实际验收

HF27722565已COMPLETED0:0，node43、32MPI×1OMP，Slurm3520秒；
实际ABACUS运行3519秒（31.28 rank-wall core-hours，与调度时间重叠，不相加）。
共14个连续唯一离子步、14个完整force blocks，逐步电子收敛、最终离子收敛。
末步最大原子力范数6.549119033e-5 eV/Å，occupation-manifold gap1.842055684 eV，
均满足既定1e-4 eV/Å及0.01 eV门；没有提高SCF或离子精度、没有改100步设置。

10份输入/运行/结构/本征值原始文件与远程SHA256一致，归档于
`PZT_ABACUS_pending/endpoint_cg_reset_HF_27722565`。
复用现有ABACUS collector；三维有序Pb2TiZrO6、原子顺序及结构近邻检查通过。
核查收敛末步力后没有坐标更新，末步被求力几何与STRU_ION_D分数坐标差≤5.1e-11；
因此不会重复原失败第100步“更新后几何尚未求力”的错误配对。
完整来源、固定symprec1e-3 Å/angle5°、实际版本与警告保存在terminal_intake.json。
捕获一条既有依赖警告`Set OLD_ERROR_HANDLING to false and catch the errors directly.`，
未屏蔽，也没有据此修改结构或自动升级环境。

结论仅为：保存终点在HF同一f7cb1d3构建下、重置CG历史后能达到既定力收敛。
还没有该最终几何的极化，也没有验证与235 e84abb4构建的响应兼容性，
`accepted_response_point=false`，不将隔离诊断加入原235采样完成计数。
下一步应取得该几何的极化并核查跨构建兼容性，之后才讨论是否纳入原响应集合；
不因成功而宣称旧失败唯一由CG历史造成。

## 原235 build的新完成点：strain-003-（2026-09-19）

本轮检查cu26驱动发现新的DONE strain-003-；原任务没有重启或重复提交。
随后收集INPUT/KPT/STRU/STRU_INITIAL、末步结构、running_relax.log、istate.info、
两阶段运行记录、三方向极化/精度记录、PYATB input.json、reference STRU及ensemble。
14份文件SHA256与235逐项匹配，归档于`PZT_ABACUS_pending/completed_strain003_minus`。

复用现有collect_abacus_stage、parse_pyatb_polarization和actual_strain，
确认原build e84abb4，32个连续离子步、32个force blocks、每步电子收敛，
最终ionic converged，最大力6.56661e-5 eV/Å，带隙1.835246723 eV，均满足生产门。
最后力评估之后没有坐标更新，其求力坐标与STRU_ION_D的周期分数坐标差≤5.1e-11；
原子顺序不变、有序三维Pb2TiZrO6、没有排序/标准化或人为修复结构。
实际工程应变[0,0,-0.004999999999999893,0,0,0]与序列化manifest一致，
原子弛豫保持固定应变晶胞，PYATB晶格与求力晶格一致。spglib仍固定symprec1e-3Å、angle5°。

单次PYATB输出a/b/c方向P=(-7.3171e-9,-3.1127e-8,1.113405545) C/m²，
量子(0.869852991,0.869852991,2.051528831) C/m²；这里只保留其报告方向和分支，
不将单点极化认定为自发极化或完整压电。ABACUS6045秒、PYATB15秒、cu26/40MPI×1OMP，
本点合计67.333333 rank-wall core-hours，不含参考优化、失败尝试及重叠调度成本。
本地pymatgen2025.10.7、NumPy1.23.5、spglib2.7.0；唯一警告为
“Set OLD_ERROR_HANDLING to false and catch the errors directly.”，保留在point_checks.json。

原ensemble的完成点增至7/12（001±、002±、003−、006±）。
003+、004±原任务仍继续；005−的HF CG重置结果仍单独保存，未混入235 ensemble，005+未完成。
PZT完整e/C/d、rank/residual及外部有序模型对照仍未完成，不能据单点验收宣称完整benchmark通过。
# 2026-09-19追加：004−终态与004+独立启动

235原build e84abb4的strain-004−已实际跑满100步，ABACUS返回0但未打印离子收敛；
只读解析得到末步最大原子力1.546371335e-4 eV/Å，高于固定1e-4门，不能进入PYATB或
完整张量。100个force block、每步SCF收敛，PBE间隙1.842048406 eV且绝缘；实际设置为
scf_thr1e-8、force_thr_ev1e-4、relax_nmax100、stress_thr0.5。耗时18498秒、cu25、
40MPI×1OMP，即205.5333 rank-wall core-hour。该点与既有005−(2.059390077e-4,
100步、18428秒)均保留为不合格证据，不因残差“小”而接受，也不放宽生产门。

004+此前因串行driver在004−失败后停止而从未启动；检查cu25一分钟负载0、无ABACUS/
VASP/PYATB进程，验证原始INPUT/STRU/KPT SHA和参考力/应力/绝缘门后，单独以40MPI×1OMP
启动原始004+，没有改输入、重复004−或自动恢复。启动回执SHA为
2c7a97db20f2450b9ebe3623a4fdc21560c797320902d6b494efd3bca89211aa，远程running_relax.log
已产生电子结构输出，结果待终态。失败点审计JSON SHA为
c09cc60d9345943554590539ba04db10d4789c5e1663f1609289faa8863cfacb。

004−后续若恢复，必须另设明确优化器假设的独立目录，不能在原目录盲目续跑；当前先完成
尚未计算的中心差分配对点。005−的HF不同build CG结果仍不得静默混入原build ensemble。

## 原235 build的新完成点：strain-003+（2026-09-19）

cu26原任务随后正常完成strain-003+并自动完成同节点PYATB；没有重新提交或修改输入。
14份小型输入、终态、日志、带隙、极化、运行记录及manifest文件从235收集到
`PZT_ABACUS_pending/completed_strain003_plus`，逐文件SHA256与远端一致；大CSR矩阵
保留在共享计算目录，不复制进Git工作区。

现有ABACUS/PYATB解析器确认原build `e84abb4`，26个连续离子步和26个力块均电子收敛，
离子弛豫收敛，最终最大原子力为6.78799e-5 eV/Å，occupation-manifold带隙为
1.845969674 eV。实际输入保持scf_thr=1e-8、force_thr_ev=1e-4、relax_nmax=100、
stress_thr=0.5；没有提高精度或放宽门槛。实际工程应变为
`[0,0,0.004999999999999893,0,0,0]`，与ensemble序列化向量一致；末步求力坐标与
`STRU_ION_D`周期分数坐标差不超过5.1e-11。

PYATB一次计算给出a/b/c极化
`(8.3453e-9,-7.3717e-9,1.135470714) C/m²`，对应量子
`(0.861197738,0.861197738,2.051528831) C/m²`。这里只验收单点原始分支，不把它
单独解释为自发极化；与003−的分支配对将在完整张量收集器中统一完成。ABACUS耗时
4918秒、PYATB16秒，cu26/40MPI×1OMP，本点54.822222 rank-wall core-hour。

原ensemble合格完成点因此增至8/12（001±、002±、003±、006±）。004+仍在原任务
运行；004−和005−仍为原build未收敛失败点，005+尚未完成。PZT完整e/C/d、rank和
residual仍未验收，且该10原子PZT50/50 [001]有序模型不代表随机合金、陶瓷或MPB。

## strain-005− 原构建兼容性闭环

HF CG-reset 终点随后在235的原ABACUS构建 `e84abb4` 上进行了独立、固定输入的
兼容性控制。控制目录与原100步失败目录分离；`INPUT`、`KPT`、赝势、轨道、
`scf_thr=1e-8`、`force_thr_ev=1e-4 eV/Å`、`relax_nmax=100` 和
`stress_thr=0.5 kbar` 均未改变。cu21采用40 MPI×1 OMP；ABACUS 220秒、PYATB 16秒，
共2.622222 rank-wall core-hour。

原构建在候选几何上1个离子步即打印离子收敛，最大原子力范数
`6.540253042e-5 eV/Å`，occupation-manifold带隙`1.842055711 eV`，所有SCF收敛。
随后同一原构建产生矩阵，并由一次PYATB计算得到a/b/c极化
`(-0.02144636021, 9.1355986e-8, 1.12433764331) C/m²`，极化量子分别为
`(0.86551184034, 0.86550913563, 2.05154806399) C/m²`。
实际工程应变为
`(-2.53e-11,-2.53e-11,-1.07e-11,0,-0.004999999993,0)`；微小非目标分量来自
结构文本序列化，收集器始终使用该实际向量，而非名义`-0.5%`。

额外结构审计显示，HF-reset终点与原235第100步终点晶胞完全相同，逐原子最大周期
笛卡尔差仅`7.8768e-5 Å`、RMS差`4.1198e-5 Å`。因此没有用一个不同相或不同局域
极小值替换原响应点；但来源仍明确保留，不把跨构建优化步骤隐藏。最终力、本征值、
稀疏矩阵和极化均由原构建重新计算，故该点可作为原构建ensemble的已验收替代点。
原失败目录及100步日志不覆盖、不删除。

本点的15份输入/输出/运行文件、原失败终态结构和逐文件SHA256归档在
`outputs/pbe_database_comparison_20260918/PZT_ABACUS_pending/`
`completed_strain005_minus_original_build_control`；`point_checks.json`记录实际应变、
力、带隙、极化、结构差异、资源及解析器警告。完整PZT计数增至9/12：
`001±、002±、003±、005−、006±`。单点通过仍不等于完整e/C/d通过。

## strain-004− 有界CG-history reset启动

原`004−`最后10个最大力在`1.1769e-4–1.6899e-4 eV/Å`之间往复，末值
`1.546371335e-4 eV/Å`；能量已稳定但100步内未越过固定`1e-4`门。由于`005−`已证明
同类CG历史重置可由原构建闭环验证，检查cu21一分钟负载为0且无ABACUS/PYATB/VASP
进程后，仅对保存终点启动一次独立CG-history reset。任务仍用原构建、40 MPI×1 OMP、
原输入和原阈值，目录为`continuations-original-build/strain-004-minus-cg-reset`；
启动回执为`pzt-strain004minus-original-build-cu21-20260919.json`。

该任务不是放宽收敛、不是从初始结构盲目重跑，也不会覆盖原100步失败证据。
只有在离子/电子收敛、最大力、绝缘性、实际应变、终态几何与PYATB三方向极化全部
通过后才可替代`004−`；否则保留为失败诊断且不再自动重投。
