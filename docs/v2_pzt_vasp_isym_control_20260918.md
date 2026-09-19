# PZT 原生 VASP：ISYM=0/1 单参数对照

## 原因审计

用户没有要求关闭 VASP 空间对称性。当前 campaign 调用的原生
`zstar/vasp_bec.py::prepare_vasp_bec` 在 reference_updates 与
response_updates 中硬编码 `ISYM=0`（同时设置 NCORE=4），覆盖输入设置。
因此这不是 PZT 的物理要求，也不是 VASP 弹性/压电计算的必要条件。
该默认值尚缺性能/正确性对照依据；本实验只检查和验证，不提前修改共享原生 API。

VASP 官方说明：ISYM=1/2 开启空间对称性；ISYM=0 关闭空间对称性，
但仍利用 k 与 -k 关系。IBRION=6 可利用对称性约化位移。
来源：[ISYM](https://vasp.at/wiki/index.php/ISYM)、
[IBRION](https://vasp.at/wiki/index.php/IBRION)。

## 单参数实验

- 模型：三维周期、10 原子有序 Pb2TiZrO6，PZT50/50 [001]；不是无序陶瓷。
- 原始作业：HF Slurm 27720985，保留运行和全部输出，不中断。
- 新目录：`/public/home/iai806/zstar-validation/pbe-native-piezo-20260918/results-pzt-native-isym1-control/pzt001`。
- 同一份已收敛 accepted-input/POSCAR；不重新优化、标准化、排序或修正坐标。
- **唯一 INCAR 参数变化：ISYM=0 → 1**。逐字段断言其余标签一致。
- 保留 PBE、原 PAW、ENCUT=1000 eV、EDIFF=1e-8、原 k 网格、NCORE=4。
- 保留 IBRION=6、ISIF=3、NFREE=2、POTIM=0.01、LEPSILON=True。
- 保留原 VASP SYMPREC（未指定时使用 VASP 默认）；spglib 检查固定 1e-3 Å。
  两者不是同一个参数；不扫描阈值，也不为了获得目标点数放宽 VASP 阈值。
- Slurm 请求 32 MPI × 1 OMP，单节点非独占，最长 6 h。
- 重新执行同设置下 reference SCF 与 native response；不重做离子优化。
- POSCAR/KPOINTS/POTCAR 两阶段逐文件哈希相同；INCAR 仅 ISYM 有差异。
- 不自动重试。若 NCORE=4 下的内部 k 点切换不兼容，保存失败日志，
  后续兼容性实验必须另立记录，不能把多参数改变的耗时归因于 ISYM。

准备时重新核查原参考优化电子/离子收敛、最大力 ≤1e-4 eV/Å、
最大应力 ≤0.5 kbar、绝缘性及固定 spglib 阈值下 SG99。
保留解析警告、软件版本、输入哈希及 Slurm 作业号。
沿用现有集群环境，不升级依赖；不是 skill 中新版环境快照的复现。

## 比较计划与状态边界

当前原任务 OUTCAR 明确报告 30 原子位移自由度与 6 额外应变自由度。
NFREE=2 对应 60+12=72 个扰动结构；参考结构另计。
新任务实际自由度和扰动数量必须从其 OUTCAR 核查，不能提前承诺缩减比例。

两任务完成后分别报告：

1. VASP 识别的对称操作、不可约 k 点、位移/应变自由度与实际扰动点数。
2. reference/response 各自 OUTCAR elapsed time、电子迭代次数、32-rank core-hours。
3. Slurm 分配 wall time 单列；排队时间、参考优化不计入原生响应加速比。
4. 完整 clamped/relaxed e、C、BEC、力常数及介电张量的最大绝对差和 Frobenius 相对差。
5. d33 单独列；仅在相应科学质量门通过时作为合格值，否则明确标记诊断/缺失。
6. 内应变两条导数路径、平移规范、机械稳定性、对称性违例与现有质量门。

不同节点的耗时包含硬件/负载因素；单次 wall-time 比不是纯算法加速证明。
不因点数减少或运行正常退出就声称结果一致，不改验收阈值以填充 d 表。
此文档创建时尚无 ISYM=1 的结果或耗时结论；提交与状态记录后续追加。

## 已提交记录

HF `sbatch --parsable` 已返回 **27721621**（`zv2-pzt-isym1`）。
原任务 27720985 保持运行，不改变其输入。
准备检查通过：原参考最大力 8.2590005e-5 eV/Å、最大应力 0.00862859 kbar、
PBE gap 1.8381 eV、固定 spglib 阈值 SG99、最短原子间距 1.75939 Å，解析警告零。
两个任务参考结构同一 SHA256：
`04636815007af358a93855b5415b1b98365bb525831fe5134615aa4826e8efa2`。
Python 语法检查及所有准备时字段/文件哈希断言通过；未改核心 API 或 CLI。

本地准备记录：
`outputs/pbe_database_comparison_20260918/PZT_VASP_ISYM1_control/control_prepare.json`。
Slurm 输出位于 campaign 根目录 `pzt_isym1_27721621.out/.err`。
尚不能给出加速比或张量一致性结论。

## 首次启动失败与有界恢复

27721621由sacct确认FAILED1:0，分配wall1m21s（32核约0.72 rank-wall core-hours）。
Slurm/MPI日志报告node317启动task0段错误，Hydra下游status139，
reference和response均没有OUTCAR，未产生可比较的DFT响应。
这与有明确MCE证据的235/cu20错误不同：不能据此认定node317硬件故障。
失败原目录完整保留，本地已保存failure.json与startup_failure_27721621.log。

在终止状态与无OUTCAR核查后，仅开展一次独立目录启动恢复，
`results-pzt-native-isym1-startup-recovery/pzt001`，排除node317和此前同类失败node378。
输入逐字段/逐文件核查通过，与首次对照相同；ISYM=1相对原任务仍是唯一数值标签变化。
没有复用失败现场的restart输出，不变更MPI启动器或其他并行参数，不自动重试。
准备档案`startup_recovery_prepare.json`保留首次终止账目、日志哈希及解释边界。

恢复提交 **27721638**（`zv2-pzt-isym1-r`），最新Slurm为RUNNING、node25、32核。
原27720985也在node25运行，分配由Slurm控制，非独占；不将节点相同当作负载完全相同。
此记录时尚未取得恢复任务的响应结果，仍无加速比或张量一致性结论。
随后复核27721638.0仍RUNNING，reference/vasp.log已出现实际DAV1–4电子迭代。
这次已越过首次失败的MPI启动环节，但参考/响应是否最终成功仍待验收。

## 实际对称性收益与响应兼容性失败

随后 sacct 确认 27721638 FAILED 1:0，分配 wall time 8m18s。
reference 成功且 gap=1.8382 eV；response 在有限电场线性响应期间退出。
vasp.log 与 OUTCAR 一致报告：内部要求改变 k 点集合，但当前带并行配置不支持。
输入未设置 NPAR，但 NCORE=4 导致此配置受到同类限制。
这是已取得明确日志的并行兼容性失败，不是对称性识别失败，也不是硬件失败。
原目录及失败日志保留；本地归档为
`PZT_VASP_ISYM1_control/response_compatibility_failure_27721638.json` 与
`response_compatibility_27721638.log`。

两份 reference OUTCAR 的实际结果（原数值设置相同、NCORE=4）：

| 项目 | ISYM=0 | ISYM=1 |
|---|---:|---:|
| 不可约 k 点 | 163 | 45 |
| 对照识别的空间群操作 | — | 8（C4v） |
| reference OUTCAR elapsed / s | 250.569 | 93.256 |

reference SCF 实测 wall time 降低约 62.78%，比例约 2.69；这不是完整
压电/弹性响应加速比。负载和运行时间不同，不能视为隔离硬件因素的普适结论。
ISYM=1 响应没有完成，尚无完整张量一致性结论；原 ISYM=0 作业仍运行。
VASP 官方 [IBRION](https://vasp.at/wiki/index.php/IBRION) 推荐利用对称性，
并说明 IBRION=6 的位移约化及 ISIF>=3 的弹性/内应变响应。

## 同一兼容并行配置下的配对实验

依据明确的 k 点切换错误，另建 NCORE=1 的 ISYM=0/1 配对，而非原样重试。
已有 GaN NCORE=1 原生响应完成记录作为此兼容配置的先例，不保证 PZT 必然成功。
两个配对目录之间唯一 INCAR 差异为 ISYM；与原任务相比还改变了 NCORE。
因此只有新配对可以将耗时差主要归于对称性，不能把旧 NCORE=4 与新 NCORE=1
之间的总差异全归于 ISYM。

- ISYM=0：Slurm **27721687**，目录 `results-pzt-native-isym0-ncore1-pair/pzt001`。
- ISYM=1：Slurm **27721688**，目录 `results-pzt-native-isym1-ncore1-pair/pzt001`。
- 两者均 32 MPI × 1 OMP、单节点非独占、NCORE=1、最长 6 h。
- 原 accepted 参考结构及 POSCAR/KPOINTS/POTCAR 哈希完全一致；所有其余 INCAR
  标签逐字段断言相同，保持 PBE/ENCUT1000/EDIFF1e-8/POTIM0.01/NFREE2。
- 不重新优化、不提升精度、不变更 VASP SYMPREC、不扫描 spglib 阈值。
- 复用已审计参考结构前重新核对 exact hash，不复用失败的 calculator restart。
- 准备解析警告零，Python 语法检查通过；提交前核查两阶段输入及工作流 manifest。
- ISYM=1 的初版准备脚本漏写 workflow manifest；在任何计算开始前补齐，并保存
  `preparation_completion.json`，所有计算输入未改。这不是 DFT 失败或重新计算。
- 保存 exclusive submission attempt 和每个作业 receipt；不自动重试或重复提交。

最新 Slurm 两者 RUNNING，分别在 node353 与 node363。硬件/节点负载因素须在
耗时对照中披露；实际 response 点数、e/C/d 和总耗时仍待完成后审计。
未修改共享后端默认值、CLI、main 或 v1 正式论文。

后续实际执行复核：27721687已有reference DAV电子迭代；27721688 reference完成，
native response已进入外电场RMM迭代，当前仍RUNNING。
此时尚未观察到NCORE=4时的k点切换终止，但不据此提前宣布响应完成或兼容性完全通过。
原27720985 OUTCAR推进到Iteration61(3)，迭代号不是已验收扰动点数量。

## NCORE=1 配对实际结果：参考 SCF 成功，ISYM=1 响应终止

后续调度器核查确认 27721688 FAILED 1:0，node363，分配 wall 14m03s；
27721687（ISYM=0，node353）及原 27720985 仍 RUNNING。不原样重投失败任务。
配对两组均 32 MPI × 1 OMP、NCORE=1，输入之间只改变 ISYM。

| reference OUTCAR 项目 | ISYM=0 | ISYM=1 |
|---|---:|---:|
| 不可约 k 点 | 163 | 45 |
| elapsed time / s | 608.798 | 210.136 |
| 完整 native response | 仍运行 | 失败，无完整张量 |

参考 SCF 实测 wall time 降低 65.48%，时间比 2.90。两组节点不同，
这是一次实测耗时，不是排除硬件/负载因素后的算法加速比；不外推至完整响应。
当前没有 ISYM=1 完整 e/C/d，因此结果一致性尚未验证。

新失败发生于响应中的扰动结构对称性重新识别：OUTCAR 已由 C4v（8 操作）
进入 C1h（2 操作），vasp.log 的终止信息是
`mkpoints_change.F:786 / GENERATE_KPOINTS_TRANS: number of G-vector changed in star 10255 10257`。
这不同于 NCORE=4 的带并行/k 点切换限制。此前的 LRF_COMMUTATOR 警告也保留，
但不能把它替代为此处已明确记录的终止原因。

VASP 官方说明此错误涉及从不可约 BZ 向完整 BZ 旋转轨道时，等价 k 点星
中的平面波数不一致；容差识别的近似对称性可能触发，建议结构对称化、
小幅改变 ENCUT 或关闭对称性。
来源：[官方错误说明](https://vasp.at/wiki/Number_of_G-vectors_changed_in_the_star)、
[官方支持回复](https://vasp.at/forum/viewtopic.php?t=19671)。
这支持定位到对称性/k 点星变换环节，但尚不能证明本例唯一诱因就是 POSCAR
微小偏差，更不能据此声称 ZStar 张量算法错误或所有 ISYM=1 都不适用。

保留所有 HF 输入/输出；本地归档 failure JSON 与完整 response/vasp.log：
`outputs/pbe_database_comparison_20260918/PZT_VASP_ISYM1_control/`。
本次失败分配成本 7.4933 core-hours（14m03s × 32），不是有效响应产出。
后续先核查晶胞/原子对称性的实际偏差及失败扰动，再选择有依据的有界恢复。
若对称化 POSCAR 或改变 ENCUT，必须对 ISYM=0/1 两组共同应用并重新检查输入，
不能与原组混用后宣称单参数一致性；不扫描 spglib 阈值、不盲目提高 SCF 精度。
默认值政策仍待完整对照决定：不能因本例失败就给所有体系强制 ISYM=0，
也不能把尚未成功的 ISYM=1 宣称为已验证生产默认。

## 配对 ISYM=0 的内存不足终止

再核查 sacct，27721687 已是 OUT_OF_MEMORY（显示截断为 OUT_OF_ME+），
ExitCode 0:125，node353，分配 wall 16m17s，ReqMem 59168M。
Slurm stderr 明确记录 batch 的两次 oom_kill；reference 成功，但 response
的 mpirun 非零退出。不能把此前 RUNNING 状态当成最终完成。
失败分配成本 8.6844 core-hours；并非正常响应耗时，不参与加速比。
本地保存 `isym0_ncore1_failure_27721687.json` 和
`isym0_ncore1_oom_27721687.log`，原 HF 全部现场保留。
两组 NCORE=1 全响应均失败，原因不同；已有 reference SCF 对照依旧有效，
但没有完整张量一致性证据。内存问题的恢复须显式申请足够内存，不改变物理精度，
且不能把失败后的多次分配成本隐藏。暂不再次提交整组。

原 NCORE=4 作业 27720985 仍由 Slurm 确认 RUNNING，VASP 日志明确显示
Finite differences progress 为 66/72（不是从电子迭代编号猜测）。
继续保留此作业取得原始模型完整响应，不重复运行同一组设置。

## 实际结构偏差与单次精确对称性电子响应测试

只读审计使用原 accepted POSCAR、pymatgen 2024.5.1、spglib 2.6.0，
固定 symprec=1e-3 Å、angle_tolerance=5°，得到 SG99、8 个操作。
保持 10 个有序原子、原子顺序和三维周期性，最小距离 1.7593933 Å。
最大同种原子对称映射偏差 1.64450e-6 Å；最大晶格度量不变性偏差
2.51963e-4 Å²；对应 Cartesian 旋转的非正交性最大 1.58496e-5。
原晶胞的 a/b 差约 1.486e-5 Å，xy 非对角分量约 1.580e-5 Å。
这明确量化了近似对称性，而不是只凭空间群编号认定严格相等。
原输入及全部失败输出哈希记录在 `structure_failure_symmetry_audit.json`。
旧 pymatgen/spglib 的 deprecated dict-interface 警告保留，不升级环境。
OUTCAR 最后打印晶胞尚与参考相同，不能据此恢复实际出错的完整扰动结构。
此前响应 log 有 228 次 LRF_COMMUTATOR 警告；仍以 k 点星错误为终止证据。

按官方建议检验精确对称结构假设：在新目录用原 fractional 操作对晶格度量、
同种原子匹配后的坐标作 Reynolds 平均，不标准化、不排序、不改变原点/模型。
单个副本最大晶格元素改变 1.57995e-5 Å、原子 Cartesian 坐标改变 1.23462e-5 Å；
副本对称映射残差 8.88178e-16 Å，写入后回读晶胞/坐标/组成断言通过。
原 POSCAR 字节与哈希未改；这些小改动仍是新科学输入，不与原组混用验收。

仅提交固定离子 LEPSILON 电子响应（IBRION=-1、NSW=0、新鲜 ISTART=0/ICHARG=2）。
保留 ISYM=1/NCORE=1、PBE、ENCUT1000、EDIFF1e-8、原 PAW 和 k 网格；
不提升精度，不提交完整 72 点。此测试能检查电子响应 k 点变换，
不证明后续原子/应变扰动全部兼容，且不用于完整响应加速比。
副本还需在计算后核查力、应力和绝缘性，当前不是验收 benchmark。

初次 sbatch 申请 32 MPI×1 OMP、128 GiB 被拒绝，未分配作业、未开展 DFT：
HF hfacnormal01 限制 requested memory/CPU ≤ DefMemPerCPU=1849 MiB。
保留 exclusive 原提交 attempt；确认无同名作业后，仅修正调度内存为
32×1849=59168 MiB，不增加 CPU、不独占、不改变计算输入哈希。
资源修正 attempt 与成功 receipt 分别保留，无自动重试。
成功提交 Slurm **27721760**（zv2-pzt-exactsym），最长 1 h；最新状态 PENDING/Priority。
准备/提交记录归档 `exact_symmetry_smoke_preparation.json`、
`exact_symmetry_smoke_submission.json`，不把拒绝的申请称为运行失败成本。

随后终态核查确认27721760 FAILED 127:0，node419，wall1s；
MPI/Hydra日志报告srun task0段错误及downstream status139，未生成任何OUTCAR。
这没有检验到精确对称结构假设，硬件故障亦未证实。现场及完整vasp.log保留，
分配成本仅1s×32=0.00889 core-hours，没有DFT响应产出。

依据终态和无OUTCAR证据，仅作一次独立目录启动恢复，复制四个输入并逐个校验哈希，
不复用失败计算输出、不重新投整组72点、不变更MPI/OMP或物理参数。
Slurm指定已确认原PZT持续执行DFT的node25，32×1、59168MiB、非独占1h；
不绕过调度器或抢占原作业。成功提交**27721772**，最新PENDING/Priority。
恢复receipt记录母任务账目、日志SHA、全部输入SHA与适用边界，
本地`exact_symmetry_smoke_startup_recovery_submission.json`。
原27720985日志已推进至71/72，尚未作为完整结果验收。

## 原ISYM0/NCORE4任务终态与收集

2026-09-19核查确认27720985 COMPLETED/0:0，node25、分配wall2h53m51s；
vasp.log明确72/72，native JSON/完整BEC/IFC及当前accepted结构已传回。
这替代此前RUNNING快照，不将已完成原任务误报为活动作业。
原生e33=2.99118 C/m²，Cmin9.514530 GPa；d仍被原生raw-Xi门拒绝。
新两路线收缩diagnostic d33=231.5118/246.9153 pm/V、差6.6534%，
同源重建不是独立准确性或ISYM一致性。完整模型和资源边界见
[PZT有序模型报告](v2_pzt_ordered_model_results_20260919.md)。
精确对称电子测试恢复27721772仍PENDING/Priority；其固定离子输出即使成功，
也不能替代完整ISYM1 e/C/d对照。目前依旧没有完整响应加速比。

## 2026-09-19 后续：解除单节点排队限制、MPI隔离诊断与实际SCF

27721772的node25请求将作业限制在128/128 CPU已分配的节点；Slurm曾预计
2026-09-21 21:52:37才开始。按
[Slurm scontrol官方说明](https://slurm.schedmd.com/scontrol.html)用`ReqNodeList=`
只更新同一PENDING作业、取消节点绑定，避开两处此前启动失败节点，
32×1/59168MiB/非独占/输入不变，无新的DFT作业由这次更新生成。
即时show一度仍显示旧请求，随后controller明确显示ReqNodeList null、node103，
证明更新生效；不能把即时观察延迟当作更新失败或据此重复提交。

27721772随后node103启动2s即FAILED，sacct最终127:0，step0 cancelled0:11；
controller瞬态曾显示255:0。srun task0段错误/Hydra downstream139，仍无OUTCAR。
现场run_started和vasp.log保留，INCAR/POSCAR/KPOINTS哈希仍与准备输入一致。
分配成本0.017778 core-hours，无SCF证据，未证明硬件故障或对称性假设失败。
失败日志与更新/账目保存在`startup_failure_27721772_and_mpi_probe.json`。

为了避免仅换节点盲目重跑，先提交一个无DFT的MPI_Init/Allreduce隔离测试
27721962：同一个32×1/4GiB/非独占allocation、同一个IntelMPI2021.3可执行程序，
各35s超时界限比较默认mpirun及I_MPI_HYDRA_BOOTSTRAP=ssh；
后者依据[Slurm MPI官方说明](https://slurm.schedmd.com/mpi_guide.html)。
node47上两种方式都实际通过world32/rank_sum528，作业COMPLETED/0:0、10s，
分配0.088889 core-hours。输出与源/二进制SHA保留，零DFT。
这没有复现先前故障，因此不能宣称全HF runtime损坏、SSH-bootstrap修好了VASP，
或已确定唯一启动失败根因。

据此准备一次输入完全相同的新独立固定离子诊断27721964，先校验母任务终态、
无OUTCAR、全部四个输入哈希与MPI测试二进制哈希；不复用任何calculator restart。
作业在自身32×1/59168MiB/非独占allocation上先运行相同MPI通信测试，
若默认失败才测试SSH-bootstrap；两者都失败则不调用VASP，整个任务最多调用
VASP一次，无自动calculator retry。node47实际default preflight world32/528成功，
step0 COMPLETED/0:0，随后OUTCAR存在并进入实际SCF，观察到Iteration1(11)。
这是已验证的启动与运行进展，不是固定离子响应已完成或完整e/C/d已验收。

receipt：`exact_symmetry_guarded_startup_submission.json`；原输入/旧失败目录不改，
原生主档案d门仍不改。启动调试只涉及运行诊断，非物理精度参数。
当前27721964在提交前启用了Hydra verbose，潜在全环境日志仅留私有远程诊断，
不显示/回传/提交/发布到案例；只收集OUTCAR等物理输出及白名单MPI字段。
发现这一日志范围问题时的取消操作仅对PENDING条件执行，而任务已RUNNING，
所以没有取消或重复当前实际SCF。旧verbose脚本snapshot哈希与receipt保留；
本地未来脚本源已改为仅I_MPI_DEBUG=5，不影响正在运行的已归档Slurm脚本。
该限制尚不是完整ISYM0/1响应耗时或张量比较结论。

## 2026-09-19 静态精确对称测试完成并进入完整响应对照

真实 Slurm27721964 已 COMPLETED/0:0，node47、32×1、job wall31m13s；
物理OUTCAR有完整timing footer，VASP自身elapsed1867.471s。
分配成本16.648889 core-hours，与VASP内部计时重叠，不相加。
前文RUNNING是保留的历史观察，本小节及terminal receipt明确替代其当前状态。
仅回传OUTCAR/vasprun.xml/POSCAR/INCAR/KPOINTS；未读取/回传可能带环境的verbose log，
未回传或提交POTCAR。所有已有现场和科学输入不改。

使用独立native worktree现有 `parse_vasp_outcar` / `parse_native_tensors`，
不复制parser、不调用collector写回既有结果；pymatgen受限XML/POSCAR解析捕获警告。
10个有序原子、3D PBC、SG99、固定symprec1e-3 Å/angle5°，无氧化态猜测、重排或标准化。
实际本地pymatgen2025.10.7/spglib2.7.0；保留OLD_ERROR_HANDLING弃用警告，未升级环境。

| 检查 | 结果 | 判断 |
|---|---:|---|
| reference 最大原子力向量范数 eV/Å | 8.986e-5 | 满足1e-4生产门 |
| reference 最大stress kbar | 0.02064881 | 满足0.5生产门 |
| PBE gap eV | 1.8382 | 绝缘 |
| clamped e 对原ISYM0主档案最大差 C/m² | 0.00042 | 电子响应相近 |
| clamped e 完整张量Frobenius相对差 % | 0.082872 | 不是总e或d误差 |
| 全原子BEC最大差 e | 0.00135 | 仅本次电子导数比较 |
| epsilon infinity 最大差（relative单位） | 0.000057 | 不是ionic/static总epsilon |

完整3×6 e、10×3×3 BEC、3×3 epsilon及全部差值/输入输出/parser/code哈希记录在
`exact_symmetry_static_diagnostic_27721964.json`；科学原始文件目录
`exact_symmetry_guarded_completed_27721964/`。BEC按native既定转置约定
`[atom, displacement/force, polarization/electric field]`，不与BORN转置混用；
e按工程Voigt `[xx,yy,zz,yz,xz,xy]`，clamped ions/fixed E，未作第二次proper correction。
单位技能促使显式保留这些边界和cost重叠；静态单位审计0 findings/0 suppressions。
沿用现有单位层，不安装Pint，不从确定性差值编造置信区间或standard uncertainty。

依据 [VASP IBRION官方说明](https://vasp.at/wiki/IBRION)，6采用对称有限差分，
ISIF≥3可获得内部应变/弹性，结合LEPSILON得到Born/压电/ionic dielectric；
[LEPSILON官方说明](https://vasp.at/wiki/LEPSILON)本身只给clamped电子量。
因此本次静态成功不等于所有原子/应变扰动已验证、full e/C/d一致或加速比已得到。

在terminal/input SHA、生产reference门及clamped电子比较通过后，**仅一项**完整原生
ISYM1测试成功提交 Slurm **27722088**，最新 PENDING/Priority、32×1非独占，
59168MiB、最长4h、不绑单节点/不抢占。维持exact POSCAR、PBE PAW原字节、k mesh、
ENCUT1000、EDIFF1e-8、POTIM0.01/NFREE2/ISIF3/LEPSILON、ISYM1/NCORE1；
相对完成的静态输入仅把IBRION−1→6、NSW0→1，恢复原生有限差分模式。
不复用输出restart；在自身allocation先过同一MPI通信门，最多一次VASP invocation，
没有自动calculator retry。未来脚本明确unset Hydra verbose，避免全环境日志。
实际独立点数必须从native progress测量，不预称72、40或某个加速比。

提交及四输入哈希保存在 `exact_symmetry_full_isym1_submission.json`。
原ISYM0主档案还存在near-symmetric geometry/NCORE4的差别，不能把新旧总时间差
严格归因于单独ISYM；前次同NCORE1配对失败历史继续保留。
未改变任何native d门、核心API/CLI/main/v1论文，完整目标仍active。

## 2026-09-19 实际几何审计兼容对称性约化

真实 HF27722088 最新为 RUNNING，node47、32核、elapsed1:04:41，
OUTCAR推进至Iteration19(7)。内部迭代标签不是已完成扰动计数，也不是terminal证据。
未新增提交、重复运行或更改活动输入。

原研究几何审计硬编码全部3N方向正负位移和六应变正负点；
不能拿这一全采样条件否决 IBRION6/ISYM1 的合法约化采样。
已保留旧脚本快照 `audit_native_perturbation_geometry_fullsampling_20260919_snapshot.py`，
为 `.codex-output/audit_native_perturbation_geometry.py` 增加显式模式，默认仍为 `full`。
全采样模式继续要求完整点数、正负配对，并新增原始方向矩阵满秩检查，拒绝重复方向冒充完备采样。

`--sampling symmetry-reduced --incar PATH` 仅在读取实际、受限大小的 INCAR 后启用，
要求 IBRION6、ISYM1/2/3、NFREE2、ISIF>=3；来源输入哈希和解析警告单列。
此模式报告实际原子/应变点数、实际工程应变和非仿射位移、未展开采样秩、
未显式配对负点的记录索引，不要求一定72点，也不将缺失负点直接视为对称性已恢复。
`symmetry_reconstruction_completeness_verified=false` 明确保留：
实际采样记录本身不是响应重建完备或误差阶数的证明。
两模式均拒绝非terminal OUTCAR、缺参考/原子/应变或混合扰动的异常记录。

本次采用 pymatgen 技能保留坐标/PBC、解析警告、输入输出/算法哈希和软件版本；
3D ordered Structure、Cartesian OUTCAR 与输入原子顺序不改，
固定 symprec1e-3 Å/angle5°，不按技能通用建议扫描容差，遵循用户固定阈值。
OUTCAR分类容差仍为3e-5 Å/3e-6 strain，非物理收敛门或空间群识别阈值。

六项三维控制测试通过，涵盖全采样、约化计数、显式负点缺失报告、
运行中输出拒绝、不兼容实际ISYM输入拒绝、足够点数但重复方向拒绝。
对真实已完成GaN/ISYM0档案重新执行默认全采样审计，仍得reference1/atomic24/strain12/mixed0；
新独立输出为 `GaN_native_actual_geometry_audit_full_mode_20260919.json`，历史审计不覆盖。
待27722088终态后使用约化模式，配合原生进度/张量输出核查，不提前发布点数或加速比。

```powershell
$env:PYTHONPATH='D:/Work/Code/zstar-v2-development'
python .codex-output/audit_native_perturbation_geometry.py --outcar OUTCAR --poscar POSCAR --incar INCAR --sampling symmetry-reduced --output NEW_geometry_audit.json
python -m pytest tests/test_v2_native_geometry_sampling.py -q
```

## 2026-09-19 运行中输出明确给出的约化计划

只读核查真实 HF27722088 的 OUTCAR，非内部Iteration标签推断：
输出在 `finite differences with symmetry` 模式下明确报告
`Found 18 degrees of freedom`，`Strain: 6 additional degrees of freedom`，
总 `DOF=24`；最新有限差分进度块为
`Degree of freedom: 11/24`、`Displacement: 1/2`、`Total: 21/48`。
同次调度器核查作业 RUNNING/node47/32核，elapsed1:10:38，
实际force几何块已有22个，但不在运行中冻结或声称终态几何审计完成。

因此本次**计划**原子扰动36点、应变扰动12点、总扰动48点，参考几何另计。
原已完成ISYM0主档案实测为原子60点、应变12点、总72点，参考几何另计。
原子点数计划减少40%，总扰动点数计划减少33.3%；
本次计划未减少应变点数。不能把这些百分比写成实际wall/core-hour加速比：
参考电子响应、各点SCF成本、节点以及NCORE/参考几何差别仍影响总时间。
完整结果是否一致、最终实际点数及消耗，必须待terminal/完整张量后另行核查。
本次读取不改活动输入、不重投、不改native d门。

## 2026-09-19：明确的终态后处理入口

核对实际 Slurm 脚本发现 HF27722088 只执行 VASP，不自动收集张量。
因此准备研究目录中的 `.codex-output/collect_pzt_exactsym_full.py`，
复用原生 `parse_native_tensors`、`parse_vasp_outcar` 和现有 XML IFC 解析器，
不重写物理算法、不调用计算器、不修改原生 d 验收门。
脚本 SHA256 为 `99237ffed525850a80c5307b1527a823d13d324ec85f1e87d558858487a3c936`；
已传到 HF 同名任务根下的 `collect_pzt_exactsym_full_20260919.py`，远端哈希一致。

收集前必须核实唯一主作业 `COMPLETED/0:0/32 ranks`、终态 OUTCAR、
输入与提交记录哈希、静态参考门及完全相同的参考 POSCAR。
参考力/应力/gap 来源明确使用已完成静态父任务，不能拿最后一个扰动几何冒充参考。
完整 e/C、两条原生内应变路线及原生 d 通过/拒绝信息均原样保留；
不在原生拒绝时暗中用代数 d 替代。输出 IFC、全原子 BEC 和带单位/警告/来源的研究 JSON，
不调用采用默认 1e-5 的 Phonopy 对称性或生成已验收响应记录。
实际几何、张量对称性、光学子空间及两路线审计仍是后续必要检查。

九项保护测试通过；与六项实际几何采样测试合计 `15 passed`。
加入这些保护测试后的本地全量回归为 `660 passed, 4345 warnings in 31.42s`；
警告来自已有依赖弃用接口，不用本地通过代替最低依赖版本或真实计算验收。
远端 CLI 可用。对仍为 RUNNING 的真实27722088调用时，按预期在解析科学输出前拒绝，
且未创建目标结果目录；这是收集保护测试，不是 DFT 失败。
该次最后核查任务仍为 RUNNING，有限差分 `40/48`；不冻结活动输出、不新增 DFT。

终态后使用（若目标已存在，先检查其来源/完整性，不覆盖或重复执行）：

```bash
/public/home/iai806/zstar-validation/vasp-native-20260918/venv/bin/python \
  /public/home/iai806/zstar-validation/pbe-native-piezo-20260918/collect_pzt_exactsym_full_20260919.py \
  --source /public/home/iai806/zstar-validation/pbe-native-piezo-20260918/results-pzt-exactsym-full-isym1-20260919/pzt001/native-response \
  --baseline /public/home/iai806/zstar-validation/pbe-native-piezo-20260918/results/pzt001/native-elastic \
  --native-code /public/home/iai806/zstar-validation/vasp-native-20260918/code \
  --static-gate /public/home/iai806/zstar-validation/pbe-native-piezo-20260918/exact_symmetry_static_diagnostic_27721964.json \
  --destination /public/home/iai806/zstar-validation/pbe-native-piezo-20260918/pzt_exactsym_full_intake_27722088
```

按 pymatgen/单位核查技能保留有序三维结构、固定 symprec=1e-3 Å、角度5°、
解析警告、来源哈希及明确单位；确定性对照差异不伪装成标准不确定度。
收集器保护测试不是完整科学验收。精确对称性结构和 NCORE 与原任务不同，
即便结果收齐也不能称为严格单参数 ISYM 加速实验。

## 最新终态：27722088已完成

后续核查已确认为COMPLETED/0:0，48/48扰动完成，终态收集与本地归档已执行。
实际36原子+12应变；已有v2空间群表示的轨道补全输入秩30/30、6/6。
完整e/C相对原任务变化0.384%/0.216%，response elapsed实测降低19.464%，
但节点/NCORE/几何不同，不能称为ISYM单独加速。
原生d仍拒绝，位移/应变路线诊断d33=232.397456/250.678969 pm/V，差7.8665%。
上文运行中进度属于历史记录；
详见[完整终态报告、实际计时和质量限制](v2_pzt_isym_completed_comparison_20260919.md)。
