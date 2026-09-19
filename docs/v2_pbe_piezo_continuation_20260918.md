# PBE 双后端压电续算，2026-09-18

## PTO/ZnO/GaN完整中心应变独立验证（2026-09-19）

为独立核查原生VASP路线尚未验收的`d`，三套任务均使用完整六个Voigt工程应变方向、
每方向`±0.005`，而不是把对称约化候选直接当作全张量证据。统一设置为PBE、
1000 eV、32 MPI×1 OMP、`EDIFF=1e-8`、`EDIFFG=-1e-4 eV/Å`、`NSW=100`、
`NCORE=1`、显式`NBANDS=32`、`LCALCPOL=true`；实际序列化应变写入ensemble plan。
PTO采用精确P4mm/`ISYM=1`，ZnO和GaN采用精确P6_3mc/`ISYM=2`，三者
`SYMPREC=1e-3 Å`。严格投影只移除远小于1e-3 Å的序列化/弛豫噪声，保持原点、
原子顺序和极化畴；原父结构及父/子SHA均保留。

PTO作业27722735在node43实际运行：reference-relax/static和
strain-001-minus/plus的relax/static均通过。两负应变阶段最大力分别为
`5.796e-5/9.665e-5 eV/Å`，两正应变阶段为`8.861e-5/1.678e-5 eV/Å`；
随后进入strain-002-minus。ZnO名义24带被VASP补齐为32的协议不一致已单独停止，
全阶段显式32带的新作业27722789在node47实际运行；reference-relax/static最大力
`9.259e-5/9.389e-5 eV/Å`，strain-001-minus-relax为`2.185e-5 eV/Å`，
随后进入对应静态阶段。两者均尚未生成或验收完整张量。

GaN来源审计确认四原子P6_3mc父结构、PBE/1000 eV/Gamma 8×8×6、参考实际
NBANDS32、gap1.71 eV、最大力`1.531e-5 eV/Å`、最大残余应力0.01499 kbar。
Reynolds投影的父操作匹配最大`6.893e-6 Å`，晶格/原子最大变化
`3.159e-7/3.489e-6 Å`，严格子结构操作残差`8.882e-16 Å`；稳定约化候选为
`(xx,zz,2yz)`，但计算仍使用完整六方向。一次预检通过后提交HF作业27722871，
随后在node21以32 MPI×1 OMP实际启动并进入reference-relax；未自动重试、
未修改原生d门或生产精度。提交、started、prepared回执及哈希均已回收。

PZT50/50 [001]仍为单独的有序模型研究：003+和004+日志持续更新；004−/005−
各在100步停止且未过`1e-4 eV/Å`力门，不能混入已验收张量。该边界不影响四原子
AlN/GaN/ZnO或五原子PTO的完整ABACUS结果。

## 最新PTO追加验证：HF 27722725（2026-09-19）

按用户要求继续PTO计算，保留已完成ABACUS/PBE e/C/d（d33=49.084674 pC/N）。
新增同PAW/PBE/1000eV/Gamma9×9×8的独立完整中心应变验证，
ISYM1、NCORE1、NBANDS32、LCALCPOL=true贯穿参考/应变弛豫及静态，
力1e-4、SCF1e-8、NSW100不变；HF Slurm32×1非独占。
参考冷启动力/应力/绝缘性/SG99检查通过后才计算±0.5%全六工程应变方向。
真实非理想PTO父晶胞的原约化采样报告两法向方向满秩，但系数设计条件数约1e9，
不采用该采样；完整六方向系数设计条件数约1，明确不声称约化加速。
已提交27722725，初始Slurm观察RUNNING/node43；尚无新张量或验收d结果。
预检及提交回执、病态设计矩阵审计见PTO direct-shear audit末节。
46项既有对称性/极化读取测试通过，保留15个spglib弃用警告；main/v1论文及CLI未动。

随后27722725在VASP建立ISYM1对称k点星时失败，错误为G向量数在同一star内变化；
14.1668秒计算器成本已记录，不误写成SCF或离子失败。固定1e-3 Å的P4mm操作投影只移动
晶格/原子最多4.865e-5/3.440e-5 Å，保持原点、顺序和畴，严格操作残差3.14e-16 Å。
一次有根因依据的新目录重试27722735已提交并初始RUNNING；仍使用完整六方向采样和原阈值。

27722735随后通过reference-relax/static：最大力9.282e-5/9.368e-5 eV/Å、
gap1.9273 eV、SG99、最大参考应力0.01845 kbar、实际NBANDS32，现进入首个负应变弛豫。
对称采样相对秩门修复经699项全回归通过，提交6b8ec161已推送v2分支；张量仍待全点完成。

并行核查PZT原build：003+仍在运行；004−已100步终止但最大力1.54637e-4未过门，
005−既有失败为2.05939e-4。004+是driver因前点失败而未执行的独立配对点；cu25核实空闲后
以原输入40×1单独启动，不重跑004−。完整PZT e/C/d仍未完成或验收。

PTO首个strain-001-minus随后通过弛豫/冷启动静态力门：5.796e-5/9.665e-5 eV/Å，
进入plus配对点。ZnO使用已验收P6_3mc源结构、PBE/1000eV/Gamma8×8×6、ISYM2、
NCORE1/NBANDS24/LCALCPOL=true准备完整六方向±0.5%独立验证；新相对秩算法给出稳定
`(xx,zz,2yz)`三方向候选计划、联合17/17，但本次仍不约化。作业27722771
初始RUNNING/node47/32×1非独占；尚无ZnO新参考门或张量结果。

27722771随后在reference-relax进入SCF前复现VASP G-star内部错误
`number of G-vector changed in star 3564 3565`；计算器15.8959秒、0.141297
rank-wall core-hour，原目录保留且不原地重投。P6_3mc十二操作Reynolds投影保持原点和
Zn/Zn/O/O顺序，父操作匹配最大5.729e-5 Å，晶格/原子最大变化6.586e-5/6.920e-5 Å，
严格子结构残差1.91e-15 Å。它与PTO独立复现同一近似对称晶胞+VASP symmetry-star问题；
新严格结构目录只进行一次有根因依据的ISYM2重试，不切换ISYM0或提高精度。

严格ZnO重试27722781已在node47实际进入VASP电子主循环，越过原G-star失败点；
32MPI×1OMP、ISYM2/NCORE1/NBANDS24不变。此时只能确认启动问题消除，reference力/应力/
绝缘门及完整e/C/d仍待实际终态。

27722781随后两离子步收敛，力9.259e-5 eV/Å、最大应力0.05558 kbar、gap0.7195 eV、
SG186均过门；但VASP在NCORE1/32MPI下把显式NBANDS24实际补齐为32，runner按实际参数
一致性门停止，未生成应变任务。该结果是物理参考通过但数值协议不一致，不能把后续32带
应变与24带名义参考混用。新目录将全阶段显式NBANDS32后仅做一次有依据的重启；不改阈值。

## 最新证据：PZT新增003−、PTO固定带数科学对照（2026-09-19）

上一目标轮只核查并展示已有PTO值，没有新增完成证据。本轮重新检查实际集群状态，
原cu25/cu26驱动仍活跃，各40个ABACUS进程，未启动重叠任务。
新strain-003-完成并经14文件远程/本地哈希、既有收集器、力/绝缘性/实际应变核查：
32离子步均SCF收敛，max force6.56661e-5 eV/Å、gap1.835246723 eV、实际η3=-0.005，
一次PYATB得到三方向极化；原PZT有序模型完成点增至7/12。该点成本67.333333 core-hours。
小型原始文件及point_checks.json保存在`PZT_ABACUS_pending/completed_strain003_minus`，
保留一个spglib既有弃用提示；没有升级环境或把HF build混入原ensemble。

PTO已排除LCALCPOL开关本身后，本轮实际提交27722695，HF node43/32MPI×1OMP非独占，
同失败静态几何、PAW及精度，固定NCORE4/LCALCPOL=false，串行比较NBANDS24/32。
24带冷启动点已经电子收敛但max force1.559503552e-4 eV/Å仍超生产门；
这直接否定“只恢复原弛豫默认带数/NCORE即可消除超限”的简单修复，
不能把未确定根因写成带数的唯一影响。32带点仍在实际电子迭代，完整并行对照待终态。
准备/提交/started回执见`PTO_VASP_fixed_bands_27722695`，两新INCAR只差NBANDS，
脚本编译/Slurm bash预检通过；不提高EDIFF、放宽force/d门或自动重跑材料系列。

两项工作均为科研控制及结果收集，不新增稳定API/CLI、修改main/v1论文、合并或发布。
完整ABACUS四材料e/C/d仍已完成；GaN/ZnO/PTO原生VASP d仍未验收，PZT完整张量未完成。
目标继续active，不能用单点或内部测试代替完整双后端验收。

随后27722695已COMPLETED0:0，13份新增文件SHA匹配、实际求力几何和原子顺序一致，
32带点21电子迭代、gap1.9276 eV、max force1.573486886e-4仍未通过；
两点合计2.9234877 rank-wall core-hours。固定NCORE4下24/32的max分量差9.30e-6，
固定32条带下NCORE4/1为4.189e-5，冷24−暖末步24为8.325e-5 eV/Å。
因此带数/并行不能单独解释并修复全部差异，剩余电子初始化/历史影响未唯一定位。
终态回执保留全分量、原始哈希、warnings=[]；没有把诊断控制成功退出提升为force或d验收。
本轮定向既有测试38 passed/0.64s，三个研究脚本编译及diff检查通过；native worktree clean。
下一步完成一致实际设置下的PTO响应观测和剩余PZT点，仍不改生产精度或正式接口。

## 本轮范围与原则

响应算法不重写：ABACUS 复用 v2 有限应变与 PYATB 全精度输出，VASP 只读复用
独立 `codex/vasp-native-response` 分支及 HF 上已有代码。
不改变正式 CLI，不合并 main 或原生分支，不修改 v1 论文，不发布。

生产设置：力 1e-4 eV/Å、电子收敛 1e-8（各后端量定义不同）、最大优化步数 100；
ABACUS stress_thr 保持 0.5 kbar，结构识别使用 spglib symprec=1e-3 Å。
VASP 保持本轮 PBE、1000 eV 与原 k 网格及 POTCAR，不把旧 600 eV AlN 结果
伪装成新的 1000 eV 计算。已验收旧 AlN/VASP 原生结果直接复用外部对比。

## 实际启动记录

235 检查：cu24 运行其他 ABACUS 任务，不使用；cu26 运行 PZT/ABACUS 原参考优化，
不重叠；cu25 空闲，于其上启动单一串行队列，40 MPI × 1 OMP。

ABACUS 目录：
`/home/zhuxd/abacus/agent-runs/20260918-v2-pbe-dual-backend/piezo-abacus`。
日志：同一 campaign 的 `piezo_dispatch_cu25.log`。
顺序：AlN → GaN → ZnO → PTO。
每个体系使用已收敛 PBE R1 的真实末态，固定晶胞内部弛豫 R2r 验收后，
生成参考 SCF 与 ±0.5% 六个工程应变方向（共 13 个几何，完整采样审计）。
先完成真实参考 SCF/PYATB smoke 并核查力与带隙，再执行其余应变。
每个几何只运行一次 PYATB 得到全部三方向极化，不做三个 NSCF。
最后复用现有收集器进行实际应变差分、proper e、C、d 及对称性/残差分析。
这是完整采样验证，不声称具有对称约化任务数收益。

HF 目录：`/public/home/iai806/zstar-validation/pbe-native-piezo-20260918`。
已提交的独立非独占 Slurm 作业，每个 32 MPI × 1 OMP：

| 作业 ID | 材料 | 首次确认状态 | 分配节点 |
|---|---|---|---|
| 27720982 | GaN | RUNNING | node363 |
| 27720983 | ZnO | RUNNING | node117 |
| 27720984 | PTO | RUNNING | node378 |
| 27720985 | PZT50/50 [001] | RUNNING | node25 |

随后 PTO 作业 27720984 在 node378 的 MPI/Slurm 启动阶段失败：
`srun task 0: Segmentation fault`、Hydra 代理状态 139；没有生成 OUTCAR。
其日志与执行记录完整保留，Slurm 显示耗时 79 秒、32 核。
这是启动故障证据，不是 VASP 优化或物理响应不收敛。
已在新输出目录 `results-node-recovery` 做一次有依据的独立重提交，
作业 **27720995**，`--exclude=node378`；其他物理与并行参数不变。
未覆盖或删除失败作业，也没有反复自动重投。

VASP 6.3.2。原 GaN/ZnO/PTO 在 CG 优化中报 ZBRENT bracketing 失败；
PZT 达到 100 步而力不达标。它们都不是合格参考。
本轮从原 CONTCAR 复制到新目录，重置优化历史，采用 IBRION=1、POTIM=0.1、
NFREE=5；力、电子阈值、泛函、赝势、截断能、k 网格不放宽。
这是针对失败 line-search 的一次明确续算，不宣称已证明失败完全源于优化器。
算法定义见 [VASP 官方 IBRION 文档](https://vasp.at/wiki/index.php/IBRION)。
新优化必须满足电子/离子收敛、最大力、最大应力、绝缘性与目标空间群后，才自动
进入现有原生 `--elastic` API 的参考 SCF 与 IBRION=6/ISIF=3 响应；
不另建外部应变极化差分路线，不额外跑 Raman。

## 科学验收与恢复

每个 VASP 结果由原生收集器保留钳制/离子/总 e 与 C；只有通过原生 d 质量门才
输出 d。不因作业返回零而接受未优化收敛的结构，也不忽略金属化、弹性不稳定或
内部应变平衡警告。PZT 无数据库同模型记录，不能与任意陶瓷实验 d33 冒充同条件复现。

每个失败保留 `failure.json`、输入、日志与执行标记，不自动反复重投。
ABACUS 队列会继续其他独立材料；HF 每个材料为独立作业，失败不影响其他材料。
既有计算目录和已有已验收结果不覆盖。
各执行记录包含命令、节点、MPI/OMP、返回码、耗时、core-hours；HF 另记录 Slurm ID。

处理完成后更新 [数据库完整张量对比报告](v2_pbe_database_comparison_20260918.md)，
单列 e31/e33/e15 和 d33；数据库未直接提供 d33 的位置留空。

## 代码与检查

研究辅助脚本 `tools/continue_v2_pbe_piezo.py` 只组合已有 Python API 和驱动，
`tools/stage_v2_pbe_vasp_sources.py` 只转移小输入并记录哈希。
用户许可的 POTCAR 只留在本人的计算目录和仓库外临时传输目录，不进入 Git。
两套启动脚本通过 bash 语法检查，Python 编译检查通过；
续算、相/固定 symprec、失败保留/防盲目重试、差分及已有响应回归合计 **54 passed**。
后续检查已见 AlN/ABACUS 的 R2r 与参考 SCF/PYATB 完成，参考力与带隙门通过，
进入 12 个正负应变任务；GaN/ZnO/PZT 的 HF 日志已出现实际 VASP DAV 电子迭代。
这些是运行与阶段验收证据，不是全体系压电完成声明。

## 首次目标续推检查

确认 cu25 的队列进程仍在运行，AlN 的 `strain-001-` 已完成 ABACUS/PYATB。
HF 四个有效作业 27720982、27720983、27720985、27720995 仍为 RUNNING；
PTO 恢复作业分配到 node203，已进入实际电子/离子迭代，启动故障没有复现。
从正在运行的 OUTCAR 提取最近一个完整力块（仅状态观察，不提升为最终结果）：

| 材料 | 已打印力块数 | 最大原子力 eV/Å | 当前资格 |
|---|---:|---:|---|
| GaN | 29 | 1.8110e-4 | 仍需达到 1e-4 和优化收敛标记 |
| ZnO | 31 | 2.0212e-4 | 仍需达到 1e-4 和优化收敛标记 |
| PZT50/50 | 8 | 3.0800e-4 | 仍在优化，单独模型验证 |
| PTO | 5 | 2.7890e-3 | 仍在优化，不提前启动原生响应 |

原生压电响应必须等待参考结构通过门限；不因为初始能量变化已很小而跳过力验收。
没有提高 SCF 精度、增加优化步数或修改现有作业。

等待期间扩展内部 `tools/compare_v2_pbe_database.py`，可读取两套实际结果 schema，
逐一保留完整 18 分量差值、C/d、闭合、相和质量诊断。
必须给出明确坐标/极性畴核对证据，拒绝 PBEsol 混入和低维超胞冒充 Bulk；
缺少可靠 d 仍展示原始 e，但结果状态为科学门待验，d33 数据库栏保持空白。
新增完整张量/d33 独立报告、缺失 d 不提升、泛函及坐标畴拒绝测试；
相关回归合计 **57 passed**（14 个 spglib 弃用提示）。

## 第二次目标续推检查

cu25 AlN 参考计算与 `strain-001±`、`strain-002±` 已完成，共四个应变点；
其余应变继续由同一队列执行，后续 GaN/ZnO/PTO 尚未启动。
cu26 原 PZT/ABACUS 参考优化仍在运行，未观察到结束记录。
HF 四个有效作业仍 RUNNING，无新的 `vasp_native_response.json` 或完成记录；
先前 PTO/node378 的失败文件保留，node203 恢复作业继续运行。
没有重复提交、改变生产精度、抢占其他任务或启动新材料。

等待期间完成四个 ABACUS/PBE R1 的坐标与极性畴审计，固定 symprec=1e-3 Å。
结果见数据库比较报告；PTO 的 c 晶格差异 +4.367% 必须作为外部比较限制报告。
没有据此翻转任何张量符号。最终响应参考结构仍需独立核对。
加入三项诊断测试，相关差分、收集、机电与数据库回归合计 **60 passed**，
14 个 spglib 弃用提示，无失败。这是测试与结构诊断进展，不是全材料计算完成。

## 第三次目标续推：GaN/VASP 进入原生响应

HF 27720982 的 GaN 续优化已出现 required-accuracy 与计时结束标记，
61 个完整力块，最终最大力 6.8272e-5 eV/Å。实际流水线已通过
电子/离子、应力、带隙和 SG186 门，参考 SCF 完成，原生 response 正在运行。
本节不将原生响应的单个力块当成完整 e/C/d。

GaN 的实际 accepted-input/POSCAR 重新通过坐标/极性畴审计：
与 mp-804 同 SG186、同 c 极性畴；内部坐标 RMS 0.000120 Å，
反畴 RMS 0.645893 Å；a、c 晶格差值分别 +0.0994%、+0.1071%。
证据保存在 `outputs/pbe_database_comparison_20260918/GaN_VASP_reference_domain_audit.json`，
包含真实参考结构 SHA256。没有自动变更结构、张量方向或符号。

其他 HF 作业仍运行：ZnO 第 88 个完整力块为 1.2510e-4 eV/Å，
最近八步在 7.98e-5 到 1.38e-4 范围波动，尚无离子结束标记；
PTO 第 19 个力块 4.38e-4，PZT 第 27 个力块 1.21e-4 eV/Å。
均未重投或改变优化上限、收敛阈值。235 两个队列 PID250102/PID50888
与各自 40 个 ABACUS rank 已再次核实存活。

## ZnO/VASP 终止诊断与一次对称性恢复

27720983 已由 Slurm 确认 FAILED，原因是工作程序拒绝了未离子收敛的
100 步参考结构；不是电子迭代失败。完整 XML 的最终数据为：
最大原子力 **2.00624e-4 eV/Å**，最大绝对应力 **0.143529 kbar**，
带隙 **0.7195 eV**，电子收敛 true、离子收敛 false。
最近十步的力在 5.215e-5–2.610e-4 eV/Å 范围往复；不能挑选其中
单个较小力的步而提升最后结构为已收敛 benchmark。

关闭空间对称性的 IBRION=1 续算产生了约 1e-5–1e-4 Å 量级的
非目标剪切/坐标漂移；最终结构在明确 symprec=1e-3 Å、angle_tolerance=5°
下仍识别为 SG186。恢复试验假设是启用已有目标相对称性，抑制数值
电荷/力/应力的非目标方向漂移；**尚未证明这是唯一失败根因**。
[VASP ISYM 官方文档](https://vasp.at/wiki/index.php/ISYM)说明启用对称性时
会对称化电荷、力、应力；[SYMPREC](https://vasp.at/wiki/index.php/SYMPREC)
控制 VASP 的位置等价识别。这里只调整 VASP，不写入 ABACUS 禁用参数。

从终止 CONTCAR 创建新目录 `results-zno-symmetry-recovery/zno`，
仅调整 ISYM=0→2 并明确 SYMPREC=1e-3；不重新标准化原子坐标，
不改变 PBE/PAW、ENCUT=1000、k 网格、EDIFF=1e-8、EDIFFG=-1e-4、
NSW=100、IBRION=1、POTIM=0.1、NFREE=5、32 MPI×1 OMP。
原目录与失败日志完整保留；这是依据已终止作业的单次恢复试验，非自动重试。

新作业 **27721213** 已实际 RUNNING 于 **node294**，Slurm 非独占资源。
准备脚本拒绝覆盖已有目录，并记录父结构/XML/INCAR、全部实际输入的哈希；
证据：`outputs/pbe_database_comparison_20260918/ZnO_VASP_symmetry_recovery_prepare.json`。
准备时出现旧版本 pymatgen dict-interface 弃用提示，非解析失败。
原失败作业 VASP wall=1189.752 s（32 rank-wall 合计 10.576 h），
Slurm 分配 wall=1282 s（32 核分配时长 11.396 core-hours）；
两者不冒充逐 rank 实测 CPU 时间。

其他三项 HF 作业与 cu25 队列仍运行，没有新的完整响应张量。
恢复成功仍需原有力/应力/带隙/空间群门、最终参考坐标畴审计及原生 e/C/d 验收。

## 第四次续推：ZnO/VASP 原生响应与 PZT/ABACUS 内部坐标恢复

ZnO 的恢复作业 27721213 已通过参考优化验收，日志进入
`START zno native e/C/d`；GaN 与 ZnO 原生响应仍计算中。
PTO、PZT 的 HF 作业继续运行；尚无新的完整张量文件。
cu25 的 AlN 已完成七个正负应变任务，仍使用原队列和设置。

cu26 原 PZT/ABACUS 正常退出但未收敛：100 步、最终最大力
2.727704e-4 eV/Å，应力 0.0193502 kbar；最近十步力从
4.636e-4 降至约 2.73e-4，不能因退出码零而验收。
原计算 wall=4 h 44 min 5 s，40 核分配时长约 **189.389 core-hours**。
耗时记录显示 `cal_r_overlap_R::init` 累计 14623.96 s，约占总 wall 的 85.8%，
来自优化每步重复生成位置矩阵。此例的计时比例不是所有材料的通用加速比。

仅在 v2 的纯几何 R1/R2r 准备 API 中明确 `out_mat_hs2=0`、`out_mat_r=0`，
防止模板泄漏不需要的中间矩阵输出；力/应力输出、生产精度不变。
正式 strain/polarization ensemble 仍显式启用两类矩阵，现有测试核对其输出合同。
这不是删除 PYATB 路线或改变极化算法。两项现有几何准备测试追加该约束，
相关回归仍 **60 passed**，14 个 spglib 弃用提示，无失败。
cu25 活跃 runtime 没有替换；PZT 使用单独 `runtime-pzt-recovery`，
避免改变正在运行任务的代码和输入。

PZT 在应力已合格的最终晶胞上，从最终结构创建
`pzt-fixed-reference-recovery/R2r`，进行固定晶胞内部坐标恢复，
仍为 SCF1e-8、力1e-4 eV/Å、100步、ABACUS默认对称性设置。
已核对 cu26 没有其他实际计算进程后启动；恢复进程 PID **62069**，
已确认实际 **40 MPI×1 OMP** 运行，未重跑原目录。
新的收敛标记、力、应力≤0.5 kbar、SG99 与晶胞不变检查通过后，
才进入参考 SCF/PYATB 绝缘性验收及中央 ±0.005 应变响应。
若固定晶胞后的应力不再合格，保留失败，不继续响应或自动重试。
原 R1 仍明确标为未收敛；恢复后合格参考不等于原 R1 已收敛。
PZT 始终是有序10原子模型，不能与无同模型的数据库/陶瓷 d33 作严格复现比较。

## 新增 cu17/cu21：已启动独立材料，不重复串行队列

用户新增授权 cu17、cu21。启动前实际 calculator 进程为空，负载分别
0.08/0.03/0.05、0.14/0.05/0.05；PBS 占位不视为资源冲突。
新任务沿用生产 SCF1e-8、力1e-4 eV/Å、relax_nmax100、默认应力0.5 kbar、
中心工程应变±0.005，spglib symprec1e-3 Å，不写 ABACUS 专用 symmetry_prec。

| 节点 | 材料 | 已核实状态 |
|---|---|---|
| cu17 | GaN/PBE | controller108047，实际40个ABACUS rank；R2r完成，参考SCF/PYATB运行 |
| cu21 | ZnO/PBE | controller299564，实际40个ABACUS rank；R2r完成，参考SCF/PYATB运行 |
| cu25 | AlN/PBE，之后PTO/PBE | 原AlN ensemble252014保持运行，10/12应变完成；实际40 rank |
| cu26 | PZT001/PBE | 固定参考恢复门已通过，原参考SCF/PYATB完成，进入12个应变；实际40 rank |

原 cu25 controller250102 的参数包含尚未启动的 gan/zno/pto。
核实其子进程252014只负责当前AlN ensemble，三个后续材料目录尚不存在后，
仅终止串行controller，不发送进程组信号、不终止driver或MPI。
交接协调进程261881等待原driver退出，再用成功断点收集AlN并推进PTO。
这不是重新计算已完成点。远端 `queue_handoff.json` 记录该一次性队列交接。

使用独立 `runtime-expanded-nodes`，仅扩展授权节点列表并采用已测试的纯几何
矩阵输出约束；既有AlN与PZT运行时未替换。
本次相关回归36 passed，14个spglib弃用提示；bash语法检查通过。
尚无新增完整e/C/d结果，节点启动或参考验收不能替代最终张量验收。

## 完整结果收集：AlN/ABACUS 与 GaN/ZnO 原生结果

原AlN ensemble已正常完成12个应变点；交接协调进程复用成功标记，
完成收集后启动PTO，未重算已完成SCF/PYATB点。
AlN/ABACUS完整summary、response_document、continuation已同步到
`outputs/pbe_database_comparison_20260918/AlN_ABACUS/`。
proper e31=-0.568977944、e33=1.387955736、e15=-0.297343483 C/m²，
d33=4.975410402 pm/V；rank完整、每阶段绝缘、C稳定、对称性及闭合检查通过。
PTO已通过reference SCF/PYATB，进入12个应变。
cu17/GaN与cu21/ZnO各完成第一个负应变，cu26/PZT继续应变，均不重投。

HF27720982/GaN、27721213/ZnO均 COMPLETED0:0，完整原生JSON已回读。
但displaced-atom内应变force-balance relative分别0.0122345、0.0151523，
原collector保留警告并拒绝发布d；这是科学验收未通过，不是SCF进程崩溃。
e仍逐分量对比，但JSON均为scientific_gate_pending，不提升为合格论文benchmark。
匹配PBE数据库完整对比和单列d33见 `docs/v2_pbe_database_comparison_20260918.md`。

复用实际R2r参考结构重做AlN/GaN/ZnO ABACUS坐标畴审计，均为同相同畴。
ZnO/VASP有微小晶胞轴向漂移，显式正交坐标变换处理，保留全部实际剪切和原始e，
不改结构、阈值或张量符号；对d使用普通应力表示而非e的工程应变表示。
新测试覆盖旋转前后e=dC闭合与原结构不被更改。
比较脚本从spglib已定义Hall空间群类型核对collector输出的Hermann-Mauguin符号，
避免把P6_3mc字符串和数字186误报成物理相不匹配，同时独立核对continuation门。

GaN单次新native对照作业27721360已RUNNING于HF node272。
32MPI×1OMP非独占；实际vasp.log显示32 total cores。
ISYM2/SYMPREC1e-3/NCORE1仅用于有界对照，不替换其他活跃runtime或已完成结果。
生产SCF1e-8、ENCUT1000、原平衡POSCAR、POTIM0.01/NFREE2与k点/PAW均不变，
不重跑relax；新的reference SCF已完成，gap1.71eV，原生response正在运行。
兼容依据：https://vasp.at/forum/viewtopic.php?t=19315 。
`GaN_VASP_native_symmetry_control_prepare.json`记录全部实际输入哈希、父结果哈希与假说。
这是检验对称性保留是否改善应力位移导数的对照，不声称根因已经确定。
无自动重试；其他PTO/PZT HF作业仍在Slurm运行。

当前相关回归64 passed，3196个spglib弃用提示（多数来自Hall类型枚举），无失败。
警告没有静默过滤；不声称全项目回归已经完成。
main、v1正式论文、已发布接口未变，未发布/合并。
本轮属于实际结果处理及有界科学对照推进，目标保持active。

## 原生内应变警告的光学子空间敏感度：未修改验收门

三个HF作业27721360/27720985/27720995仍由Slurm确认RUNNING。
PTO参考续优化已完成并通过门，作业已进入native response，并非仍停在relax。
ABACUS各材料原driver继续工作，没有因观测超时重启。

回读GaN/ZnO实际native BORN和FORCE_CONSTANTS，使用已验收的平衡POSCAR，
而非IBRION6 XML末帧结构。复用v1 `project_response` 和v2
`remove_acoustic_translation`/`solve_internal_strain_response`/`relaxed_piezoelectric`，
在诊断副本上拆分两条原生Gamma导数之差为平移和光学部分，
保留原始native e/C与gate，不将投影结果替换为正式结果。
投影Phi的光学秩均为9且光学本征值正；分解重建、净光学力与正交性均核验。

| 材料 | Gamma差最大 eV/Å | 光学部分最大 eV/Å | 光学平方范数占比 | 对e33的固定Phi/BEC线性敏感度 C/m² |
|---|---:|---:|---:|---:|
| GaN | 0.06785 | 0.0435875 | 76.77% | 0.00700721 |
| ZnO | 0.06894 | 0.0525825 | 55.82% | 0.00612198 |

纯共同平移对该投影后极化响应的敏感度分别约5.1e-19、2.35e-18 C/m²；
因此不能把全部Gamma路线差都描述成声学gauge，更不能只去均值就消除所有数值问题。
上述e33敏感度相对当前总e33约1.67%与0.589%；
它不是统计标准不确定度、置信区间或误差上界，也不能证明原生总e/C/d绝对准确。
全局Gamma符号不改变所报敏感度绝对值；没有按文献匹配符号。
GaN对数据库e33差0.04456 C/m²，大于该固定Phi/BEC模型路线差敏感度；
不能声称当前外部差异全部由这一内应变残差造成。

本地Pint未安装，未新建或改变科学环境；使用已有显式单位层完成
eV/Å²×Å与eV/Å的边界、BEC(e)、参考volume(m³)、Lambda(Å)与P(C/m²)转换。
输入误差分布及自由度未知，未编造GUM或Monte Carlo置信度。
证据：`outputs/pbe_database_comparison_20260918/native_internal_strain_optical_sensitivity.json`，
保留源native/BORN/FC/平衡结构哈希、投影幅度、秩和残差。
这些检查属于对既有声学规范的复用和当前数据审计，不重新发明v1的BEC/IFC规范。

## 旧AlN/PBEsol残差复检：暂缓论文主验证，不重跑

回读20260917归档原始`response_document.json`，未改归档、拟合或验收阈值。
旧proper diagnostics继承raw polarization fit的残差；其`residual_relative`
是相对参考点增量的线性拟合残差范数比，不是proper张量相对误差。
对每对实际正负向量定义`odd=(Y+−Y−)/2`、
`even=(Y++Y−)/2−Y0`，完整保留各对数值。

旧AlN/PBEsol的极化偶分量范数比0.548538501与旧拟合残差精确一致。
六对Pz中点共同偏移平均+0.00493198 C/m²，围绕均值最大变化0.00030159 C/m²。
内部位移中点也存在共同光学偏移：前两原子z约+0.0012814 Å、
后两原子约−0.0012814 Å；不是共同刚性平移。
应力中点平均偏移xx/yy/zz约−1.85171/−1.72026/−0.94261 kbar。
应力偶分量比0.172127，旧elastic residual 0.178298另含major-symmetric拟合影响。
因此存在参考态与应变弛豫态的一致性风险，不能将旧54.85%写成张量误差，
也不能因为中心差分消去共同偏置就直接认定旧参考态合格。

归档实际INPUT显示reference `symmetry=1`，strain `symmetry=0`，
二者均写过` symmetry_prec=0.001`。这属于历史设置，不符合现已统一的
ABACUS输入协议；单凭这些观测尚不能严格证明全部偏移由该设置造成。
新AlN/PBE同类Pz偏移均值−2.79936e−5 C/m²，原子z中点平均偏移仅数e−6 Å，
其极化偶分量比0.0193597，明显没有旧档案的共同参考偏置。
不同泛函之间不将此差异当作严格控制实验。

证据`outputs/pbe_database_comparison_20260918/historical_aln_residual_parity_audit.json`
含原始文档SHA256、单位、实际应变、全部奇偶分量。
已告知独立0918论文副本负责人暂缓旧AlN/PBEsol主验证，优先使用新PBE档案；
未改任何正式论文、未因该复检提交新的计算。
另v1 shared-response与v2 relaxed/electromechanical复用测试69 passed；
与前述64项集合有重叠，不相加、不声称全项目回归完成。

## PTO现参考结构及历史拟合残差的补充审计

从两个后端的实际已验收平衡结构回读：ABACUS fixed-cell R2r末态与
VASP `results-node-recovery/pto/accepted-input/POSCAR`，不使用响应末位移帧。
按pymatgen skill保留原件、周期性、分数坐标、Å单位、无序检查、最小距离、
源哈希、软件版本与解析警告；按项目约定固定symprec=1e-3 Å、angle=5°，不扫描。
二者均SG99且同数据库mp-20459的+c极化畴，无符号修改或晶胞标准化。
相对数据库a/b/c长度差分别为ABACUS −0.92367/−0.92367/+4.36658%，
VASP −0.90053/−0.89802/+3.54670%。这些结构差异必须和后续张量差异一起披露，
不能将外部偏差全归结为赝势，也不把同空间群等同于同一几何状态。
证据`PTO_current_reference_domain_audit.json`，两个平衡结构最小周期距离
分别1.73623与1.74988 Å，原子有序、三维全周期，警告原样保留。

旧PTO/PBEsol完整响应文档也完成奇偶审计，未重新计算。
在工程Voigt六维应力空间，残差平方严格分解为偶分量平方与奇分量拟合残差平方：
`r_total² = r_even² + r_odd-fit²`，所有量使用同一参考增量范数归一化。
PTO的total=0.100080597、even=0.100078329、odd-fit=0.000673708，
故旧10%残差几乎全部是偶分量，不是中心差分导数的10%误差。
旧PTO极化偶分量比0.0119902，Pz中点均值1.41311e-5 C/m²，
不具有旧AlN那样六对点的明显共同大参考偏置。
偶分量来源可能包括有限应变非线性、数值噪声与参考一致性；仅凭单步长不能分离。
奇分量小也不能提供O(h²)截断误差上界，不改变现验收门或增加参数扫描。
证据`historical_pto_residual_parity_audit.json`含完整奇偶分量和源文档哈希。

修正前节应力矩阵范数与工程Voigt范数的混用解释：旧AlN的0.172127是3×3
矩阵观测的偶分量比，不应直接与六维Voigt拟合比0.178298相减。
改用同一Voigt范数后，旧AlNtotal=0.178298004、even=0.178297978、
odd-fit=9.68387e-5，major-symmetric奇分量拟合贡献很小；
新AlN/PBEtotal=0.009153936、even=0.009153480、odd-fit=9.13707e-5。
此补充明确区分张量对称性残差、观测偶分量及中心导数拟合残差，不改历史数值。

最新HF日志显示GaN对称性控制已完成20/20原子有限位移点，仍待完整响应收集；
PTO响应10/42附近、PZT仍执行SCF，均是当前进程实际输出而非仅凭状态文件判断。
本次结构域、差分及重建相关测试22 passed（2个spglib弃用提示）；
研究审计脚本的实际正负配对、残差平方加和断言均通过。
未修改核心响应算法、生产输入、正式CLI或论文。

## GaN VASP对称性控制完成，保留未通过状态

27721360由sacct确认COMPLETED/0:0，响应与收集完整，非观察超时重试。
native内应变相对平移残差由1.22345%降至0.330385%，
互易最大差由0.06785降至0.03129 eV/Å，但仍未过原生1e-3门，d未发出。
控制e31/e33/e15为−0.26445/0.42286/−0.14618 C/m²；
同相PBE数据库差8.7537/8.9664/4.9277%，全e对原任务变化0.9834%、全C变化0.2138%。
独立source manifest与比较目录保留父结果，`scientific_gate_pending`不改；
记录输入哈希与平衡结构哈希一致。不盲目复制控制、不调整精度或验收门。
成本分配9.44 core-hours，native阶段计时9.0625 rank-wall core-hours。
详细表与限制见`v2_pbe_database_comparison_20260918.md`，已告知独立论文任务负责人。
235 cu17/cu21/cu25/cu26实查均40个ABACUS进程：
GaN前三个应变点完成，ZnO第一对±点完成，PTO/PZT继续；无节点任务重叠。
HF PTO/PZT仍RUNNING且其vasp.log有实际SCF推进。
本轮科学控制结果已改变后续动作：单凭对称性/并行组合不能完整修复问题，
后续先审计既有BORN/IFC与两路线内部贡献，而非再提交相同目标的重复原生计算。

## 原生内部贡献完整重建完成：不修改待验收状态

新增科学审计`v2_vasp_native_internal_strain_audit_20260918.md`与完整矩阵证据
`native_ionic_contribution_reconstruction_audit.json`。
四档案（已验收AlN、GaN原任务/控制、ZnO）使用v1光学/charge-neutral投影和v2既有代数，
displaced-route重现native e_ion最大差不超过6.56e-6 C/m²、C_ion不超过7.67e-5 GPa。
strained-route/mixed-route的差明显更大，验证当前native contraction来源，
也验证Xi_VASP=-Gamma_ZStar的声明符号及eV/Å³到GPa、Å³到m³的转换。
所有光学rank9、正性、声学兼容、内部平衡及诊断e/d/C闭合检查通过。
AlN BORN是2不等价原子compact文件，改读四原子all_atoms档案且显式转置，
没有简单复制或把compact匿名数组当full tensor。

仅研究诊断d33（pm/V）displaced/strained route：
AlN5.324398/5.355360、GaN原1.577099/1.600457、GaN控制1.583040/1.601599、
ZnO9.714688/9.779863。它们没有替换native门下缺失的d，也不写入验收主表。
原始Gamma平移残差不是最终张量误差的直接估计；
同源内部重建也不是独立DFT验收，等待ABACUS完整中心应变结果。
依uncertainty-and-units skill区分确定性敏感度与统计不确定度；
输入分布未知，不编造误差条。静态审计0 findings，实际断言全部通过。
相关v1/v2复用测试本轮69 passed，868个已有弃用提示，非全项目回归。
新增DFT任务0、新增集群core-hours0（既有计算继续消耗独立记录）。

独立0918论文任务确认已冻结稿件、未采用诊断GaN/ZnO d；
后续仅在一批已验收结果形成时统一交付资格/档案，不以每次内部诊断触发论文修改。
latest HF核查PTO native进度21/42附近，PZT仍SCF；235四材料继续实际stage执行。
本轮属科学重建证据推进，目标仍active，不宣称全部材料e/C/d完成。

## 235 普通 PBS 加速未启动的末尾应变点

按用户新增授权，检查 gold6248 队列、pbsnodes 和实际计算进程后，
cu15/cu16/cu20 均为空闲、无计算器进程。仅提交已经准备且无输出/锁的
ZnO、PTO、PZT001 的 strain-005±、strain-006±；逆序执行末尾分量以减少
与原有正序串行派发相遇。作业714456/714457/714458分别申请cu15/cu16/cu20，
均为普通PBS、单节点40 MPI × 1 OMP、12小时上限，qstat确认RUNNING。
没有新增应变幅度、修改输入、提高精度或重新运行已完成点。

提交前核查13几何集合的参考SCF/PYATB已完成；所选点的INPUT/KPT/STRU、
赝势和轨道存在，scf_thr=1e-8、force_thr_ev=1e-4、relax_nmax=100，
没有ABACUS symmetry_prec/symmetry_autoclose。输入哈希、节点检查、
qsub命令与作业号保存在outputs/pbe_database_comparison_20260918/PBS_tail_submission.json。
每点仍由原有ABACUS+单次三方向PYATB驱动执行，沿用原始目录及排他锁。
若原串行驱动赶上正在运行的PBS点，其锁检查会安全停止派发（exit10），
这是调度互锁而非DFT不收敛；必须确认所属PBS成功终止后再续接和收集，
不清除活跃锁、不盲目重投。运行成本由各点runtime记录累计，不以12小时上限充当实际成本。

## PBS 与串行应变互锁核查、文献历史快照资格纠正

提交后实际确认cu15/cu16/cu20各40个ABACUS进程；PBS分配exec_host均为对应节点0-39。
逐目录确认ZnO/PTO/PZT串行活动点分别为strain-002+、strain-001+、strain-001-，
三个PBS活动点均为各自strain-006-；不同点使用各自canonical排他锁，无相同点并写。
GaN串行已完成10/12应变点，仍在strain-006-，未有results/summary.json。
Slurm27720995与27720985持续RUNNING，其OUTCAR结构迭代从38/25推进到41/27，
但PTO/PZT完整vasp_native_response.json仍未生成；不将结构迭代号冒充已完成扰动数。

早期outputs/v2_vasp_piezo_literature_20260918.md及provenance侧车增加同日资格更新，
保留原始文献核查和Dryad403/401访问记录，但明确后来取得941条完整e数据。
重新核对gzip SHA256与冻结manifest一致；旧AlN/PBEsol表为隔离历史快照，
当前PBE表独立，不能将GGA/LDA的d33参考冒充同泛函PBE数据库d。
新增DFT作业0（上节三个PBS继续运行），未修改生产数值输入、核心算法、CLI或论文。
本轮完成数据资格纠正并核实具体作业实际推进，目标保持active。

## PTO/VASP收集、实际扰动审计及cu20硬件失败恢复

上一目标轮完成数据资格纠正及具体活跃作业核查，分类为progress。
本轮Slurm27720995由sacct确认COMPLETED/0:0，完整PTO/VASP结果已传回
PTO_VASP目录并加入completed_calculations.json及18分量数据库CSV。
e31/e33/e15=1.66857/2.43823/2.79621 C/m²，对同相PBE差1.5161/12.6746/14.2238%，
C最小特征值26.5624 GPa为正；raw内应变平移相对残差0.00106288793，d仍未输出。
不把这项raw残差当最终d误差、不为填表改变门槛，待复用内部贡献审计及ABACUS对照。

已完成GaN/PTO原生OUTCAR实际几何审计及正负配对：GaN参考1/原子位移24/应变12，
PTO参考1/原子位移30/应变12。两者实际工程应变±1%、原子位移±0.01 Å，先应变后位移。
这与ABACUS的±0.5%不同，已在对照文档披露，不能将跨后端差异全归于赝势。
复用v2实际应变恢复函数；pymatgen解析原始POSCAR，不重排/标准化/扫阈值。
OUTCAR五位小数坐标导致序列化分类容差3e-5 Å，不改变任何物理收敛或对称性门。
实际向量、晶胞、软件版本、输入输出哈希保存在两个*_native_actual_geometry_audit.json。

PBS714458在cu20第一个PZT strain-006-失败，runtime returncode255、449秒。
内核明确记录不可纠正内存硬件错误，杀死abacus:229630，与MPI rank39 Bus error对应；
其他rank9号信号为随后的MPI退出。现场内存和/dev/shm充足，无提高精度或修改混合参数依据。
qstat C/exit_status255以及随后tracejob state COMPLETE/Exit_status255确认终止。
cu20无残留ABACUS进程，排除该节点；未修改系统节点状态或其他用户作业。

失败目录完整移至response/failed-hardware-cu20-714458/strain-006-，包括锁/日志/输出，
没有删除任何证据。canonical strain-006-仅复制原始INPUT/STRU/KPT及赝势/轨道，
逐项匹配提交前哈希；不复用硬件错误现场的电荷、弛豫结构或检查点。
证据驱动恢复作业714459申请cu15、40 MPI×1 OMP，afterok:714456.mu01依赖，
避免与ZnO在该节点重叠；没有盲目重投到cu20。硬件及PBS终止证据、归档路径、
不变参数和qsub命令保存在PZT_PBS_hardware_recovery.json。
GaN/ABACUS最新11/12应变点完成；PZT/VASP仍RUNNING，其余PBS继续。
相关数据库和极化畴测试12 passed（3182个spglib已有弃用提示），非全项目回归。
目标仍active；新计算只有已查明原因的PBS硬件恢复，未增加精度扫描或修改正式接口/论文。

## GaN/ABACUS完整收集及PZT单参数ISYM对照

上一目标轮完成PZT ISYM=1单参数实验准备并提交27721621，属于progress。
本轮核实GaN/cu17全部12应变完成与收集END，13几何数据已下载，
参考几何hash与现有SG186/同+c畴审计一致，已加入completed_calculations.json。
完整e/C/d通过现有内部检查；e31/e33/e15为−0.30384652/0.52506936/−0.18817385 C/m²，
d33=1.87223918 pm/V。对同相de Jong/PBE差4.83973/13.03726/35.07078%，
全e差14.4173%，不把大剪切差异隐藏或宣称严格外部复现。
独立全张量比较ABACUS与原GaN/VASP，e/C差21.6406/3.89412%，不能仅归因于赝势。
VASP d门仍未通过，不以诊断d代替合格值。

读取13个已完成runtime及SCF日志：3967s ABACUS、130s PYATB，
40 MPI×1 OMP累计45.5222 rank-wall core-hours，不含初始优化/历史失败。
96次SCF循环与726条电子迭代分开记录；每个PYATB同时输出三方向。
结果、CSV、诊断、成本档案及案例索引更新；无新增ABACUS计算。

PZT27721621在node317实际开始，但sacct FAILED1:0；MPI/Hydra启动status139，
reference/response均无OUTCAR。证据不足以认定硬件原因，且没有响应计算可比较。
失败目录与日志保持完整，不自动重试。另立启动恢复目录与准备记录，
数值和并行设置均不变，排除node317与此前同类启动失败node378。
这与cu20有明确MCE证据的硬件故障不是同一类因果判断。
原PZT27720985继续运行；235 ZnO/PTO串行及PBS尾部仍有实际输出推进，
恢复714459仍依赖ZnO PBS成功后运行，不能仅凭已有锁/state宣称运行完成。

PTO内部贡献审计也已复用v1投影和v2求解：满12光学rank，
displacement/strain路线诊断d33分别63.82975/63.34978，差−0.75194%；
明确为诊断代数结果，不是通过原生门的d或误差条，未修改质量门或API。
目标保持active，主分支、v1正式论文与发布状态未改变。

恢复准备断言通过，Slurm27721638已提交且核实RUNNING于node25、32核；
原27720985继续实际DAV电子迭代。失败27721621单列成本约0.72 rank-wall core-hours。
本轮数据库比较与极化畴相关测试12 passed、3182个既有spglib弃用警告，
不是全v1/v2回归。没有提交、推送、发布或修改正式论文。

最新复核27721638.0 RUNNING且已有实际DAV电子迭代，已越过首次启动失败环节。
ZnO/cu21完成strain-004+后安全跳过PBS已完成005-，在PBS仍运行的005+锁处
按设计exit10停止串行分发。原failure.json完整保留，这是已预期的并发互锁，
不是新的SCF/离子失败。714456/cu15尾部仍在运行，不能删除锁或再投005+。
下一步须确认该PBS成功及全部13几何完成后，仅调用收集器并记录互锁解释，
不需要重新计算已完成的应变结构。PTO/PZT的实际计算仍推进。

## ZnO收集完成与完整native路线审计

上一目标回合取得实质进展：PZT ISYM-only执行失败被明确定位为NCORE=4
内部k点切换限制，随后另提交同NCORE=1的ISYM=0/1配对，不原样盲目重试。
本回合进一步由tracejob确认ZnO PBS714456 Exit_status=0、wall00:38:58，
尾部四点全部DONE；仅执行collect_v2_piezo_case，取得13几何完整结果。
保留原prepared continuation及driver exit10互锁failure.json，另存
continuation_collected.json及源哈希，已同步共享目录；没有新增ABACUS运行。

ZnO/PBE proper e31=-0.5216729841、e33=1.0474817095、e15=-0.3840075476 C/m²；
同相de Jong PBE差2.94637%、1.02928%、0.25778%，全e差1.72734%。
d33=9.666371551 pm/V，数据库无配对d，不填参考百分差。
直接e/C/d的rank、绝缘性、C正定与闭合检查通过；Lambda独立对称门失败，
最大0.008119229 Å/strain，不将全部内应变功能描述成已验收。
原始禁戒e16=0.002185528 C/m²也保留，不宣称所有零分量小于1e-3。
资源13 ABACUS+13 PYATB：7278+138s，40×1累计82.4 rank-wall core-hours；
154次SCF循环、1119条电子迭代；不含参考优化/历史失败。

只分析既有native数据得到五档案完整总e/C/d双路线敏感度。
GaN/ZnO的d最大差分别0.02336/0.06517 pm/V；PTO为3.87329 pm/V。
PTO d33仅−0.75194%，但d15/d24约−3.78/−3.87 pm/V，说明不能仅靠d33
的小变化解除全部张量警告。既有生产幅度目标只用作说明性尺度，未更改native门。
全部原生诊断d仍不进入验收表；新增DFT为0。结果见native_total_route_sensitivity.json。

Python语法检查、单位静态审计0 findings/0 suppressions；比较/极性畴测试12 passed，
3182条既有spglib弃用提示，非完整v1/v2回归。
文档、完整CSV、单列d33表与案例索引更新。分支zstar-v2-development；
未修改main/v1正式论文、共享native后端或CLI，未提交/推送/发布。

最新实际运行：HF27720985原PZT仍有OUTCAR Iteration61(3)，不将其当成61个完成点；
27721688 ISYM1/NCORE1已完成reference并进入电场响应，27721687配对reference
仍有实际DAV迭代；PBS714457 PTO尾部与714459 PZT恢复仍RUNNING。
235/PTO串行已完成001±、002±，PZT串行与PBS恢复继续，未观察到新终止证据。
目标active：PTO/PZT计算与native完整e/C/d科学门仍未全部完成。

## 2026-09-19 继续：实际 ISYM 对照失败分类与三维算法控制

上一目标轮取得 NCORE1 单参数 reference SCF 对照与 ISYM1 k 点星终止证据，
属于 progress。本轮确认 ISYM0 配对也终止，原因是 Slurm OUT_OF_MEMORY，
不是正常响应完成。两组 reference elapsed 为 608.798/210.136 s，
实测降低65.48%，但没有全响应耗时/张量一致性结论。
保留失败 JSON/stderr/response log，不把两次失败消耗作为有效加速产出。

实际 PZT 结构偏差已通过固定 spglib1e-3 Å 的同种原子映射与晶格度量审计量化；
新副本保持原模型/原子顺序/原点，写入回读通过，原结构不改。
单个固定离子 LEPSILON/ISYM1/NCORE1 诊断提交27721760，32×1，未重新优化，
未提高ENCUT/EDIFF/改变PAW/k网格。128GiB申请因每核内存限制被拒，未运行；
确认无重复作业后按32×1849=59168MiB仅修正调度申请。
完整准备/attempt/receipt和适用边界在PZT ISYM对照文档与本地JSON中保留。
此项尚不能替代完整72点或证明两组tensor一致，后续必须核查实际终态。

复用v1 project_response及现有v2求解新增6项三维声学/光学控制：
纯translation Γ不改变e/C/d、raw诊断保留、optical Γ误差确实改变响应、
额外optical零模被rank/residual拒绝、BEC中性是刚体规范不变的条件。
定向六文件111测试通过，4051已有依赖弃用警告，无核心API/CLI/native质量门改变。
不是完整v1/v2回归或外部DFT精度证明，详细条件在native内应变审计报告。

原27720985仍RUNNING，实际日志已推进至70/72；不重复提交。
235 PTO已完成串行001±、002±、003−及PBS006±、005−；
PZT恢复PBS006−完成，其余仍有已确认运行作业。目标保持active。

随后27721760在node419启动1s即FAILED127:0，MPI/Hydra status139且无OUTCAR，
不是精确对称副本的DFT失败，也未证明节点硬件原因。
保留日志/账目；只作一次独立目录输入完全一致的启动恢复27721772，
由Slurm请求已有成功DFT运行证据的node25、32×1/59168MiB/非独占，PENDING/Priority。
原27720985仍运行，实际71/72。没有盲目重复整组响应，也未改变v1/main。

## 2026-09-19 PZT/VASP正式结束并完整收集

上一目标轮完成三维算法控制和精确对称诊断准备/启动恢复，属于progress。
本轮sacct确认27720985 COMPLETED/0:0，日志72/72；收集native JSON、all-atom BEC、
BORN、IFC、当前accepted POSCAR、continuation及终态OUTCAR，未增加DFT。
实际几何审计参考1/原子60/应变12/mixed0、正负配对通过，原子约±0.01 Å、应变±1%。
native e31/e33/e15=1.11308/2.99118/6.63810 C/m²，Cmin9.514530 GPa。

复用v1投影/v2求解完成27维几何光学子空间审计及两路线完整e/C/d敏感度：
diagnostic d33=231.5118/246.9153 pm/V，变化6.6534%；全d变化6.76352%，
不提升为验收结果。精确delta_d分解中d33的e项0.893757/C项14.509703 pm/V，
说明柔顺性放大两路线差异；不是独立精度/唯一误差源证明。
冻结941条PBE数据库无Pb/Ti/Zr候选，单独模型表不制造文献/实验匹配。

新模型结果文档/model_summary具备units、axes、哈希、原source R1字段历史说明及成本。
分配92.72 core-hours/native-driver79.52898，范围重叠；本轮只收集，零新增PZT整组DFT。
55定向测试通过/3183弃用警告；三份新输出重复审计与冻结JSON完整一致；
单位静态审计0 findings/0 suppression，不编造uncertainty，不改生产精度或native门。
精确对称电子测试恢复27721772仍PENDING/Priority，235 PTO/PZT仍有实际运行作业。
总体goal active：PTO/PZT ABACUS、native d完整科学验收与ISYM一致性尚未完成。

## 2026-09-19 本地全套回归与正在运行的弛豫点核查

上一轮通过cu25真实MPI/ABACUS进程确认PTO仍在运行，属于verified wait，
不是计算结束。本轮新增全套本地回归证据：`python -m pytest -q`实际终态
619 passed、4341 warnings、47.48 s，exit code 0；范围为本worktree配置的全部
`tests/`，包含v1 Unified/BEC/谱学留存案例与v2研究测试，而非另一个native
VASP worktree的全部测试，也不是集群DFT或外部精度证明。
记录与三个关键源文件SHA256在
`outputs/pbe_database_comparison_20260918/local_full_regression_20260919.json`。

环境实测Python3.10.9、NumPy1.23.5、SciPy1.10.1、spglib2.7.0、Phonopy2.21.0、
pytest7.1.2。NumPy/Phonopy低于pyproject声明的1.26/2.36最低版本，
因此不能把这次通过称为支持安装环境或发布审查通过；未升级用户环境，
未改依赖约束。4341项提示主要来自既有依赖弃用，未以忽略警告改变测试结论。

实际PBS714457/cu16与714459/cu15均R；HF27721772仍PENDING/Priority。
嵌套SSH分别核查cu25、cu26、cu16、cu15，每节点当前有40个ABACUS进程，
没有这四个节点上重复40-rank任务的迹象；这不等于完整节点负载审计。
PTO003+日志到离子步14、最新打印最大力1.31e-4 eV/Å；005+到步21、
3.90e-4 eV/Å。PZT001+到步12、3.382e-3 eV/Å；PBS005−到步3、
1.9054e-2 eV/Å。均为运行中快照，不是接受结果或单调收敛保证。
固定晶胞应变点的非零应力是待求响应，不拿参考cell-relax的0.5 kbar阈值
去强制消除应变应力。仍按SCF1e-8、力1e-4 eV/Å、relax_nmax100运行。

本轮未提交新DFT或重跑已完成点；仅本地测试与只读集群核查，新增DFT消耗0。
未修改核心算法、CLI、main、v1正式论文、native门，未提交/推送/发布。
下一步待实际弛豫完成后收集PTO/PZT中心应变张量；继续保留native d科学门
与ISYM全响应比较的未完成状态。目标保持active。

本轮末再次读取driver日志：PTO003+已DONE，因此12个应变点已有9个完成
（001±、002±、003±、006±、005−），尚缺004±和005+；这是runner完成记录，
完整张量拟合、rank/residual及质量验收仍须全部收齐后执行。
PBS714457/714459仍R，未把刚完成的003+重复提交。

## 2026-09-19 原生完整张量空间群审计与PTO尾部完成

上一轮补齐全套619项本地回归并确认PTO003+完成，属于progress。
本轮六组冻结原生档案e/C/d完整空间群审计完成；严格区分工程应变与
work-conjugate stress表示，复用v2 SVD/major symmetry而不重写Unified框架。
完整原始/投影/残差、群操作、rank、source与算法哈希、警告保留。
PZT诊断d最大对称性偏离7.118926/2.290662 pm/V，两路线分别1.61755%/0.59050%；
这是全矩阵对称残差，不是d33准确度或解除native门的理由。
详见`v2_vasp_native_internal_strain_audit_20260918.md`新增小节。

新增3项三维测试通过，之后全本worktree622 passed/4345 warnings/43.68 s。
单位静态审计零finding/零suppression；原结构/张量/native门不改。
仍使用原本本地环境，NumPy/Phonopy最低依赖问题如上，不能宣称发布验证完成。
新增DFT为0，未提交/推送/发布，目标active。

集群末次实际核查：714457进入C，cu16 runner已记录005+ DONE和
V2_PIEZO_CASE_COMPLETE，尾部006±/005±全部完成；PTO目前10/12应变点完成，
剩004±由原cu25 driver继续，无重复提交。714459 PZT/cu15仍R，已DONE006±；
cu26原PZT driver已DONE001−。HF27721772仍PENDING/Priority。
待PTO全部完成才做统一收集、rank/residual与同相PBE全张量比较。

科学审计工具最终修订只延迟导入optional pymatgen；六组全矩阵审计重复结果
逐项一致，显式禁止pymatgen导入时3个三维代数测试仍通过。
最终全本worktree再次622 passed/4345 warnings/40.12 s，历史receipt保留前次
43.68 s记录并追加本次工具SHA与结果，不把一次修订后的测试说成旧源文件测试。

## 2026-09-19 启动故障隔离并恢复精确对称固定离子实际SCF

上一轮完成六组全张量空间群审计、三个新三维控制及622全本地测试，属于progress。
本轮只读核查native worktree当前仍bbaf059a、clean，raw-Xi平移relative>1e-3
仍为d拒绝条件；没有假定旧警告已被别的任务解除，也未修改共享native代码。

发现HF27721772此前绑定node25造成预计9月21日晚间排队；只更新同一个queued
作业取消绑定，参数/input不变，不抢占他人。随后node103在2s启动失败，无OUTCAR。
追加完整失败证据而不继续仅换节点重投。先单个32×1非独占allocation做无DFT
MPI_Init/Allreduce默认/SSH-bootstrap隔离测试27721962，两者node47都通过，
10s/0.088889分配core-hours，失败27721772另0.017778；总0.106667，非DFT产出。
未证明唯一根因或全HF runtime问题。

新单次固定离子诊断27721964先通过自身allocation MPI通信门，再调用VASP；
node47实际RUNNING/OUTCAR存在，观测到SCF1(11)，32×1非独占。
四个科学输入逐个哈希相同，无restart reuse，无calculator retry或生产精度提高。
该项只检验exact-symmetry/ISYM1静态电子响应可行性，非72点/full e/C/d结果。
Hydra可能含环境的verbose日志不进入本地/案例；只收集物理OUTCAR及白名单字段，
未来本地脚本源已去除该verbose开关，未取消或改动已运行作业。
细节及receipts见PZT ISYM对照文档新增小节。

235/cu25和cu26实际各40个ABACUS进程；PTO仍10/12，原driver继续004±；
PZT恢复PBS714459仍R，006± DONE，原cu26已有001− DONE。没有重复ABACUS提交。
本轮核心算法/API/CLI未改，未提交/推送/发布/main/v1论文修改。目标仍active，
等待PTO/PZT收齐以及新诊断真实终态，native完整d科学验收仍未完成。

## 2026-09-19 光学谱块定位：从残差检查进入响应误差归因

上一轮最后核查为 verified wait：HF27721964有真实RUNNING handle及持续变化的
物理OUTCAR；235原ABACUS driver及PZT714459仍在运行。本轮没有重复提交计算。
新增研究工具 `tools/audit_v2_native_optical_route_modes.py`，只读取冻结六组档案，
复用v1 IFC/BEC投影，按几何光学子空间的正力常数谱块分解两条Xi路线的
完整e/C及精确有限delta d；不改核心API/CLI/native gate或已验收张量。

新证据纠正过于笼统的软模归因：PZT delta d33=+15.403460 pm/V，最大的
单块贡献为光学力常数编号26的+8.770294，其中经C路径+8.544474；
该曲率38.293532 eV/Å²，不是最小曲率。软compliance放大不等于最低光学模
必然是错误来源。PTO总delta d33=−0.479963，编号8/12贡献−1.648560/+1.135420，
正负抵消意味着总d33差小不能代替逐项/完整张量审计。
这是同源诊断归因，不是唯一DFT故障根因或独立误差上界；质量未加权曲率不称THz。

完整数值、公式、模式表、适用边界和重现说明见
`docs/v2_native_optical_route_attribution_20260919.md` 与 exclusive 输出
`native_optical_route_mode_attribution_strict_20260919.json`。
两版calculations通过完整JSON比较一致，最大完整d块和闭合9.06e-13 pm/V。
新三维测试包括简并基不变、六应变完整有限变化闭合、非稳定光学拒绝，以及
近简并不平均的敏感负控制；严格JSON拒绝重复键/NaN。
没有安装Pint或改变依赖，使用既有单位层；静态单位审计0 findings/0 suppressions。

终态已观察的本地全worktree回归630 passed、4345 warnings、31.54s；
随后仅强化近简并负控制，最终修订测试结果另存
`local_full_regression_native_optical_modes_20260919.json`，不能用旧源哈希冒充新测试。
既有本地NumPy/Phonopy低于声明minima的限制仍在；不是发布安装环境验收，
也不是独立native worktree完整测试或DFT正确性证明。

235最新只读检查cu25/cu26均40个ABACUS进程，PTO仍DONE001±/002±/003±，
结合已完成PBS尾部005±/006±共10/12；PZT原cu26已DONE001−，714459/cu15仍R。
HF27721964/node47/32×1非独占仍RUNNING，allocation MPI门已通过，实际电场迭代继续；
未读取可能含环境的verbose vasp.log。本轮新增DFT/SCF/集群core-hours为0，
正在运行任务费用留给其终态provenance记录。
目标保持active：AB PTO/PZT收集和native完整d验收仍未完成，
没有把诊断d33或模式归因当成最终成功，也未提交/推送/发布或改main/v1论文。

## 2026-09-19 01:10 CST：统一生产阈值与活动离子步复核

上一轮完成光学模式归因和630全本地回归，属于实质progress；本轮为verified wait，
通过真实Slurm27721964、PBS714459和持续变化的活动relax日志确认任务仍在执行。
不是仅凭旧lock/DONE状态推测活动，也不把未结束的电子迭代称为合格结果。

按ABACUS技能读取当前生成INPUT和对应日志，PTO004−、PZT001+/005−均为
固定晶胞relax、force_thr_ev1e-4、scf_thr1e-8、relax_nmax100、stress_thr0.5、
PBE/symmetry0。没有误用1e-6力阈值/1e-10 SCF或在ABACUS加入spglib专用设置。
固定应变任务不弛豫晶胞，stress_thr不替代其离子力收敛判据；应变保持不变。

PTO活动离子步25，最近完整步24的日志最大gradient0.000279 eV/Å；
步21–24为0.000361/0.000233/0.000306/0.000279，尚未达到既定1e-4。
PZT001+活动步26，完整步25为0.000234；005−活动步16，完整步15为0.007027。
这些都是native打印的largest-gradient值，不冒充已独立解析的全力矩阵。
有局部往复但仍远未到100步，电子收敛明确；当前证据不足以宣称最终不收敛或失败，
继续原任务，不提高精度、修改活动INPUT或盲目重投。PTO仍10/12，PZT仍未收齐。

HF27721964/node47/32×1继续RUNNING，作业elapsed23m01s；
MPI preflight已通过，物理OUTCAR从Iteration2(1)推进到2(6)，此前一个电场响应loop
达到EDIFF，但整项LEPSILON未结束。场扰动中INISYM子群为2操作并不自动意味着
输入SG99结构识别错误；完整结束后再核对reference和张量，暂不提交完整ISYM1 ensemble。
pymatgen技能用于准备受限结构/输出验收，遵守用户固定symprec1e-3，不开展阈值扫描，
不升级实际运行环境、不改科学门；verbose环境日志未读或回传。

观测receipt为`live_convergence_observation_20260919_011002.json`，保存每个具体
stage/input/log、当前步与最后完整力步的区别、资源规格和未完成标记。
本轮新计算提交为0；活动任务终态成本待实际完成后归档，不从PBS CPU Time Use
编造wall time。无新增代码变更，因此不重复跑完整回归。
没有新的最终e/C/d、数据库误差或加速比结论，完整目标仍active。

补充：本次cu25/cu26的只读nested SSH pgrep各12s观测超时，timeout发送signal15
给查询连接；未取消任何科学任务。这不是ABACUS终止证据，不据此重启，
也不把上轮40进程数冒充本轮测量。HF/PBS真实RUNNING/R及已读取的具体阶段日志
分别记录，远程观测失败与计算终态严格区分。

### 01:13 CST 新增完成点与进程重新核实

本轮复核发现PTO driver新写入`DONE strain-004-`，结合既有完成点为11/12，
仅剩004+。这是新完成阶段证据，但尚未执行不完整采样的最终重建，
仍待12/12和全部收敛/绝缘/序列化几何核查后收集完整e/C/d。
重新只读节点查询采用每节点30s观测界限，session5526已正常exit0，
cu25/cu26各实际40个ABACUS进程；不把先前12s超时当作任务死亡，未重新投计算。
HF27721964依旧RUNNING/node47/32×1，elapsed26m16s，真实OUTCAR从2(13)到2(16)，
PZT714459仍R。现有continuation会在全应变完成后调用既有collector，
不另起第二个collector/driver来抢锁，也不重新执行完成阶段。
上述后续观察追加在已有live convergence receipt，保留前次10/12和超时历史。
本轮无新DFT提交/精度调整/代码或CLI修改，不重复完整回归，目标active。

## 2026-09-19 静态测试真实终态与有条件的完整ISYM1响应推进

上一轮为verified wait，本轮取得新科学证据并提交下一项有前置条件的实验，属于progress。
HF27721964 COMPLETED/0:0、node47、32×1、wall31m13s。完整OUTCAR/XML与三输入回传，
无POTCAR/环境verbose日志；借用native既有parser和受限pymatgen校验，
SG99、reference force8.986e-5 eV/Å、stress0.02064881 kbar、gap1.8382eV均过生产门。
clamped e对原档案完整张量最大差0.00042 C/m²/Frobenius差0.082872%，
BEC最大差0.00135e、epsilon infinity最大差5.7e-5。不是总e/C/d或最终d验收证据。
诊断成本16.648889分配core-hours，不与VASP elapsed重复相加。

在真实完成/科学输入SHA/production reference/clamped比较均验证之后，
完整exact-symmetry ISYM1/NCORE1 native测试27722088提交成功，最新PENDING/Priority。
32×1非独占、59168MiB/4h，维持PBE/PAW/k/ENCUT/EDIFF/POTIM/NFREE/几何；
仅恢复IBRION6/NSW1的有限差分模式，自身allocation MPI门先行且最多一个VASP invocation。
不是换节点盲目重投原72点，不改变生产精度或native d拒绝门。
原ISYM0/NCORE4和微小几何投影不同仍明确披露，不提前声称单参数完整加速。

source、全张量、解析器/算法哈希和Slurm receipt详见PZT ISYM对照文档新小节；
新collector只做这一个实际数据集的研究解析/断言，单位静态审计0 findings/0 suppressions，
没有改核心源码或宣称稳定CLI，未以先前630测试冒充本次新研究脚本的测试。
提前一次scp查询发生在preparer仍运行时未找到receipt；仅等待原session8446完成，
没有重新调用preparer。现已取得27722088唯一receipt并由squeue验证真实PENDING。
235的原PTO/PZT继续，不重跑AlN/GaN/ZnO或已完成阶段；PTO最终全张量仍待收齐。
未修改main/v1正式论文或发布，目标保持active。

## 2026-09-19 PTO收集完成与跨档案C/d参考完善

上一轮实际完成PTO/ABACUS结果收集、几何/逐点收敛/实际应变与完整e/C/d审计，属于progress。
PTO为SG99同+c畴，13个几何全部完成，中心工程应变±0.005；
d33=49.084674 pm/V，e33=2.114819 C/m²，最小C特征值28.440409 GPa。
全部应变点离子收敛且力≤1e-4，SCF1e-8/relax100保持不变；13点均绝缘。
e33对同相PBE数据库差24.2576%，不声称严格复现；VASP native d门仍保留。
文件哈希、reference STRU与R2r几何等价核查、实际应变、阶段节点/费用见
PTO_ABACUS/completed_response_audit.json；数据未重算，新增提交0。
费用220.0778 rank-wall core-hours，仅本轮13个响应几何及PYATB，不含参考优化/历史失败。

本轮核对既有941条e与1181条C冻结档案及官方元数据，
补齐[跨档案PBE C/d参考说明](v2_pbe_cross_archive_d_reference_20260919.md)。
AlN/GaN/ZnO跨档案d33为5.342677/1.720637/9.273189 pm/V；
ABACUS有符号差−6.87%/+8.81%/+4.24%，已验收AlN/VASP差−0.34%。
这是有条件跨档案推导，非数据库直接报告的d；体积、内部坐标、设置差异完整披露。
GaN/ZnO来源结构反演后更接近，保持压电档案e的原始畴与符号，四阶C反演偶；
不把接近当完全同几何，不改变对称阈值或native d门。
PTO没有匹配C，外部d参考仍空；未验收native d仍空，不拿诊断值填表。

实际测试638 passed/4345 warnings/32.92 s，含8项参考审计测试；
单位静态审计0 findings/0 suppressed。该本地环境不是最低声明依赖的发布资格验证。
只更新研究审计、文档与来源，未改核心接口/main/v1正式论文或发布。

最新只读核查HF27722088 RUNNING、node47、32×1，elapsed00:50:48，
OUTCAR从Iteration11推进到12(7)，真实有限差分仍执行，不提前解释为已完成12个扰动。
235/PZT PBS714459.mu01 RUNNING、cu15、40×1、wall02:43:02，
cu26串行日志已DONE001±、PBS已DONE006±；完整响应尚未收齐。
没有新计算提交、盲目重投或活动输入修改。目标active：PZT两后端及native完整d验收仍未完成。

本轮末按真实进程再查cu26/cu15：各40个abacus rank，CPU约98.9–99.7%/rank，
进程elapsed分别约1559 s/7116 s，与既有串行/PBS计算相符；没有据占位PBS或旧lock推断运行。
native只读worktree仍bbaf059a、git status clean，未在参考审计期间修改或合并其代码。

## 2026-09-19 已完成双后端完整张量审计

本轮属于 progress：新增 research-only 完整 e/C/d 双后端比较工具和七项三维测试，
冻结数据实际执行成功；来源哈希、原始质量警告和 null native d 均保留。
新增报告 [完整双后端比较](v2_completed_backend_pair_audit_20260919.md)，
四体系 AB−V 的 d33 有符号差依次 −6.55%、+18.71%、−0.50%、−23.10%。
除 AlN 外 VASP d 仅为完整 e/C 诊断代数值，不是已验收数据。
ZnO d33 接近但完整 d 范数差为 11.79%；PTO 为 14.86%，不能仅据 d33 验证全部张量。
同源内应变路线敏感度单列，不能作为独立误差范围或替代跨后端验证。
沿用单位审计约束，差值不宣称为标准不确定度；未改 native 门、核心接口或精度。

完整回归实际结果 645 passed/4345 warnings/32.12 s，新增七项测试 7 passed/0.37 s。
本轮 DFT 新提交 0、新增计算资源消耗 0；实际已有任务继续计入各自 provenance。
末次只读检查 HF27722088 RUNNING、node47、32核、elapsed59:54，
OUTCAR推进至Iteration17(5)，未将此内部迭代号解释成已完成17个扰动。
235/PZT PBS714459.mu01仍R；cu26 DONE001±、PBS DONE006±，完整12应变尚未收齐。
一次 HF run.log 路径不存在只是观察路径错误，改查实际 OUTCAR 后确认推进，非计算失败。
未重复提交或修改活动输入，目标仍 active。

## 2026-09-19 对称性约化实际几何审计修正

上一目标轮为 progress（完成四体系完整张量比较）；本轮亦为 progress：
修正研究几何审计将全采样点数硬套于ISYM约化采样的问题，默认全采样检查保持，
新增显式约化模式及六项三维测试。要求实际INCAR匹配，报告未配对负点和未展开采样秩，
不自动认定对称重建完备、不改变native d门。
真实GaN已完成输出复核仍为reference1/atomic24/strain12/mixed0；
新输出与旧脚本快照保留，未覆盖历史数据。
完整回归最新实际结果651 passed/4345 warnings/33.67 s；六项新增测试6 passed/2.17 s。
具体语义、技能影响和可复现命令见
[ISYM对照审计](v2_pzt_vasp_isym_control_20260918.md)。

已确认HF27722088仍RUNNING/node47/32核，elapsed1:04:41，实际OUTCAR推进至19(7)。
235 PBS714459.mu01仍R，qstat-f wall02:56:33、cu15/0-39；
另查cu26实际40个abacus进程，elapsed约36m16s、CPU98.8–99.7%/rank。
cu26已DONE001±、PBS已DONE006±；PZT全响应未完成，未凭旧锁文件认定活跃。
一次嵌套SSH引号命令未正确传参，改用无awk的ps白名单列后取得真实进程证据；
此观察错误不是任务终态或重投依据。
本轮新DFT提交0、新增计算成本0，未修改main/v1论文或核心接口；目标保持active。

## 2026-09-19 PZT/ISYM1 有限差分计划得到实际输出证据

上一轮为 verified wait，本轮实际输出提供新科学/任务数量证据：
HF27722088 OUTCAR明确报告原子DOF18、应变DOF6、总DOF24、正负总48点，
最新原生progress为21/48，不依据Iteration标签判断完成点数。
相对原ISYM0完成档案原子60+应变12=72点，本次计划原子36+应变12=48点；
原子/总扰动计划分别减少40%/33.3%，应变点数未减少。
这是计划数量，不是终态实测加速比或完整张量一致证明，
参考几何/NCORE/节点差异继续披露，详见ISYM对照报告新小节。
作业当前RUNNING/node47/32核/elapsed1:10:38；235/PZT PBS714459仍R，
cu26串行DONE001±、PBS DONE006±，全应变未收齐。
无新DFT提交、无活动输入变更、无native d提升；目标仍active。

## 2026-09-19 使用已核实空闲 cu25 运行未启动的 PZT 004±

上一轮为 progress（原生48点计划证据），本轮为 progress（新增未启动点的真实执行）。
按 jobs/ABACUS 技能核查实际资源：cu24已有10个高线程CPU的abacus进程、load约34，
所以不使用或碰该节点任务；cu25无计算器进程、load0，pbsnodes显示40核，
占位701443.mu01的Job_Owner为zhuxd、R、exec_host=cu25/0-39。
遵循用户直接使用自己占位节点的授权，不把job-exclusive误判为不可用，亦不抢占其他任务。

当前原活动目录明确为cu26 strain002−、cu15 strain005−。
004−和004+检查时仅有生成输入/伪势/轨道，没有OUT、runtime执行记录、done或阶段锁。
新增只运行这两个点的独立启动脚本，复用既有driver
`runtime-expanded-nodes/tools/v2_piezo_235_direct.sh`（SHA256
22a0023e14e9d81eda1305f07300ce3f1dd73d280c82a14da7024859865e089b），
不改算法、输入、CLI或活动程序。节点fcntl锁和已有逐阶段锁防止重复执行；
主遍历若将来碰到活动阶段锁会停止而非重跑，待所有点结束后统一收集。
004−先运行、004+后串行，均40MPI×1OMP，PBE/100Ry/SCF1e−8/力1e−4/relax100，
参考stress门0.5；INPUT kspacing0表示采用已生成显式KPT Gamma9×9×4，非不采样。
现有reference已通过force/stress/SG99/绝缘性及精确极化输出检查，作为完整SCF/PYATB smoke复用。

首次新脚本在写receipt前因digest(__file__)的str/Path类型错误终止；
实查calculator数0、无receipt/阶段输出，故并未重跑DFT。
原远程脚本/失败log保留，新_v2脚本改用digest(Path(__file__))，重新执行全部pristine/空闲门。
本地py_compile与远程bash-n检查完成；真实新启动PID17896，
运行日志明确START，cu25实查40个abacus进程、elapsed约25s、CPU98.2–99.1%/rank。
这是实际执行证据，不把nohup PID、占位PBS或锁文件独自作为SCF运行证明。

source输入/四元素伪势/四轨道/driver/adapter/launcher哈希及reference门记录于
远程`pzt-unstarted-strain004-cu25-20260919.json`；本地运行中快照为
`outputs/pbe_database_comparison_20260918/PZT_ABACUS_pending/strain004_cu25_launch_20260919.json`。
快照为guarded_launch，不是完成结果；最终逐阶段节点/核数/秒数由runtime_abacus/runtime_pyatb文件记录，
成本尚未结算，不写成0，也不将已有PBS占位时间混作DFT core-hours。
本次技能影响是复用真实reference smoke、查用户占位/实际负载、保持科学参数与输入哈希，
不按通用技能默认改去cu08/09或降低用户40MPI要求；生产协议不提高精度。

最新HF27722088仍RUNNING/node47/32，elapsed1:18:53、原生progress26/48。
PZT完整两后端结果仍待完成，原生d门不改；未动main/v1论文或发布，目标active。

## 后续当前状态：HF对照已终态，ABACUS增加一个完成点

上文HF运行中记录是历史快照。27722088现已COMPLETED/0:0并完成收集，
36原子+12应变扰动，轨道输入覆盖完整；两路线诊断d33仍差7.8665%。
完整终态、对称性、光学与协变审计见
[PZT ISYM完整对照](v2_pzt_isym_completed_comparison_20260919.md)，不改变原生d门。

本轮235现有cu26驱动新增 `DONE strain-002-`：ABACUS在第36步显示弛豫收敛，
日志最大力8.7e-5 eV/Å；该点ABACUS/PYATB均returncode0。
独立计时receipt已保存至
`outputs/pbe_database_comparison_20260918/PZT_ABACUS_pending/completed_strain002_minus/`。
cu26、40MPI×1OMP：ABACUS6771秒、PYATB15秒，共75.4 rank-wall core-hours。
这是单应变点成本，不含参考、其他点、历史失败或PBS占位时间。
已完成应变点为001±、002−、006±（5/12），参考另计；尚不执行完整中心差分张量重建。
PBS714459仍R，cu25/cu26实际40个ABACUS进程及驱动存活均已核查；
剩余计算继续用现有生产阈值，不重投、不提高精度。本轮没有新增源码修改或DFT提交。

## 后续终态：PZT strain-005- 达到100步，离子未收敛

PBS `714459.mu01` 已实查为 `C`，`exec_host=cu15/0-39`。
其 driver 明确停止于 `ionic relaxation did not converge: strain-005-`，
不是观察超时或作业失联。ABACUS runtime returncode为0；
第100步日志最大梯度为1.61e-4 eV/Å，日志明确 `Relaxation is not converged yet!`。
输入仍为relax_nmax100、force_thr_ev1e-4、scf_thr1e-8、stress_thr0.5，未改精度。
日志有100条charge-density convergence记录；这不等于离子收敛，
也不是最终力向量范数的独立复算。

原始INPUT/STRU/KPT、最终STRU_ION_D、完整running_relax.log、
ABACUS runtime与driver日志已另存至
`outputs/pbe_database_comparison_20260918/PZT_ABACUS_pending/terminal_strain005_minus_714459_20260919/`。
七个原始文件逐一核对远程SHA256一致；终态及哈希写入terminal_receipt.json。
不覆盖旧快照，不收集为合格极化点，不执行完整中心差分重建，不重投。

已证实的停止条件是既定步数上限内离子未收敛；
优化器收敛缓慢与电子力噪声尚未区分，不能仅由最终力值归咎于SCF或对称性。
下一步须分析保存的能量、力和结构轨迹，再决定有依据的恢复方式；
其余原作业继续核查，PZT完整ABACUS响应仍未完成。
本点ABACUS计时18428秒；PBS整作业walltime05:56:23、cput236:52:10包含006±，
两种口径重叠，不能相加或将PBS时间全归于005−。scheduler exit_status本次查询未返回，保留null。
本次jobs技能用于区分真实终态、计算器返回码与科学收敛状态，并保存可审计原始证据。

随后完成逐步力/能量审计：100步电子均收敛，末步最大力分量1.609807e-4、
最大原子力范数2.05939008e-4 eV/Å，均不达标；实际有效优化器是新式CG。
末段能量近乎不变不能代替力收敛，SCF噪声与优化器原因仍未区分。
完整证据、单位/测试及恢复前置条件见
[PZT终态轨迹审计](v2_pzt_relaxation_failure_audit_20260919.md)。
下一步优先独立同精度终点SCF检查，而非原样重跑100步；本轮尚未提交恢复计算。

后续推进：核对原ABACUS日志commit=e84abb4及匹配源码，证实失败末步力先于
最后坐标更新，必须另算最终序列化几何。独立终点SCF已提交HF27722541，
实际RUNNING node43、32MPI×1OMP、非独占，PP/8au轨道与235源hash全匹配。
HF实际commit=f7cb1d3，与235构建不同，故仅为跨构建诊断，
不估计原构建SCF噪声、不自动填入中心差分ensemble；尚未重投弛豫。
详见上述失败审计更新及`endpoint_scf_HF_submission_27722541.json`。
cu25 PID17896和cu26 PID64871仍有真实40-rank ABACUS进程，无新增235重叠任务。
本地完整回归重新实测669 passed、4347 warnings、31.54秒，exit0。

后续HF27722541正常完成：实际终点绝缘（gap1.84202768eV），
最大力分量1.442751e-4、最大原子力范数1.56940693e-4 eV/Å，均未达1e-4。
11个原始文件hash及完整力/应力/能量/gap再解析一致，未提升为合格中心差分点。
仅SCF312秒×32核=2.77333333 rank-wall core-hours，不能与Slurm313秒口径相加。
三维原构建坐标—力配对实证末20步仍是下降方向的小更新（2e-6–1.42e-5Å），
不是已证明的严格两点循环，也尚未证实电子力噪声根因；新增配对测试5 passed。
详细证据见失败审计更新及`endpoint_scf_HF_27722541/completed_diagnostic.json`。
235 driver新增DONE strain-002+，cu26 PID64871仍有40-rank原进程并开始003−；
新增点仍需按原v2完整门核查，不能仅凭DONE就称已验收。

新增002+复用远程`collect_abacus_stage`实际核查：39个力块、电子与离子收敛，
最大原子力范数9.85787e-5 eV/Å达标，gap1.84221513eV绝缘，
一个PYATB输出包含a/b/c三方向极化，16位序列化hash匹配precision记录。
输入/初末结构/KPT/两个计时/极化与precision小文件已归档，6个源hash与远程一致。
见`PZT_ABACUS_pending/completed_strain002_plus/point_checks.json`。
该点ABACUS7251秒、PYATB16秒、40×1，合计80.74444444 rank-wall core-hours；
这是新增单点口径，不与PBS整作业或历史点耗时相加。
原计划已有6/12个完成点（001±、002±、006±）；完整张量和rank/residual仍未重建，
003−正在cu26原进程内继续，004−在cu25原进程内继续；005−未恢复、005+未开始。

新5项配对测试纳入后完整回归实测674 passed、4347 warnings、31.51秒、exit0；
新快照`local_full_regression_pzt_pairing_20260919.json`保留原669项历史记录。
原生VASP d门未修改；GaN/ZnO/PTO/PZT的诊断d仍不伪装成原生验收d。

后续实际推进：保存的005−终点已开展单次CG历史重置试验，HF Slurm27722565，
实际RUNNING/node43/32MPI×1OMP/非独占，观察elapsed00:03:48。
生产INPUT字节不变，只有STRU改为保存终点；SCF1e-8、力1e-4、100步不变，
PP/8au轨道/KPT保持哈希。构建f7cb1d3与HF27722541一致、不同于235 e84abb4，
不自动作为原235合格点、不运行PYATB、不覆盖日志、不盲目重试；原计划计数仍6/12。
回执见`PZT_ABACUS_pending/endpoint_cg_reset_HF_submission_27722565.json`；
终态力、绝缘性和恢复成功与否待实际输出核查。

本轮同时只读核查原生VASP源码：d=e(C^E)^-1路径仍受raw internal-strain
force-balance门约束。现有v2热力学转换和三维acoustic invariance测试已覆盖相关定义，
不重新实现、不绕开原生门、不把诊断d提升为原生验收d；native工作树保持干净。

后续案例整理实质更新：`v2_piezoelectric_case_matrix.md`前置当前AlN/GaN/ZnO/PTO
PBE e31/e33/e15与同相数据库及百分比，另列d33理论参考和原生/诊断资格。
历史PBEsol表保留并明确改为历史快照，防止PTO历史128.75与当前PBE49.08混写。
案例README同步指出旧`results/benchmark_comparison.json`仅为2026-09-17历史快照，
旧资格不能沿用；当前源为冻结comparison.json（SHA25613e6333e...c2815）。
四种材料12组e/参考/差值单元及4个d33逐项匹配冻结数值和六位显示精度，
`tests/test_v2_completed_backend_pairs.py`及`tests/test_v2_pbe_database_comparison.py`
联合实测15 passed、3180 warnings、0.41秒、exit0；不是新的完整回归。
没有新增DFT作业、改阈值、改native门或重算PTO；原PZT计算继续。

后续科学验证已实际提交：PTO同一VASP平衡结构的独立直接剪切试验HF27722611，
已观察RUNNING/node72/32MPI×1OMP/非独占。正负工程η5=±0.005，
固定cell离子弛豫各一次、静态LCALCPOL各一次，另一个参考静态极化，共5串行阶段。
与父计算保持PAW/PBE/1000eV/9×9×8/EDIFF1e-8/力1e-4/100步；
这是有针对性的独立e15/C55响应路线核查，不是整套重算或完整d验收。
输入准备回读及现有应变测试33 passed；静态单位审计0 findings。
新VASP Berry读取/branch/proper差分仍须验证，不能把调度运行等同结果。
详见`v2_pto_vasp_direct_shear_audit_20260919.md`及提交回执27722611。
同期HF27722565仍真实运行，已至第5离子步；没有新增235重叠任务。

随后27722611确认FAILED1:0：LCALCPOL内部PEAD不支持继承的NCORE4，
在SCF前退出；电子迭代0、力块0。六个失败小文件归档hash与远程全匹配。
这是新增模式的并行兼容条件漏检，不是生产精度不足，也不是原native d门的根因。
单次有因修正已提交新HF27722618，实际RUNNING/node96/32核/非独占。
五阶段逐文件比对，只把3个静态LCALCPOL阶段改为NCORE1，其余全部设置和文件不变。
新版脚本编译检查通过，不复用失败输出、不覆盖旧日志、不自动重试或改科学门。
详细终态和修正回执见PTO直接剪切审计；仍需实际SCF/力/gap/branch/proper检查。

随后27722618停止于静态参考验收：VASP rc0且19次电子迭代收敛，
最大力范数1.248900004e-4 eV/Å略超统一1e-4门；gap1.9273 eV、
应力0.03162954 kbar合格。无应变阶段完成，未声称独立e15/C55或d验证成功。
只读解析无warnings，四个失败日志小文件归档后hash与远程一致。
父同几何静态参考力也约1.07e-4，不能把优化末步合格力自动继承至静态SCF；
未提高精度、更改力门、修改native gate或自动重投。
实际OUTCAR偶极单位为正基本电荷`|e| Angst`，旧文档示例`electrons Angst`
负电子电荷转换不能无条件套用。研究解析器暂未编写，先保留版本单位证据。
原ABACUS/PBE PTO完整结果d33=49.084674 pC/N保持不变。

后续实质进展：研究LCALCPOL读取工具完成实际单位区分、严格完整dipole配对和
三维Cartesian/量子转换，复用已有v2分支API而非重写分支或proper算法。
22项新三维控制及已有polarization联合44 passed；完整回归696 passed、
4347 warnings、33.66s、exit0；单位静态审计0 findings/0 suppressions。
失败PTO参考OUTCAR已下载且hash与远程一致，原始偶极转换冻结为
reference_raw_dipole_audit.json，明确force gate失败、branch未匹配、
自发极化未计算、完整响应未验收；没有以读取成功替代native d验收。
新增DFT/SCF/集群core-hours为0；PZT/HF27722565实时RUNNING/node43/32核，
已观察第9离子步、elapsed38:04；235两个原驱动PID17896/64871均实际存活且各40个AB进程。
jobs技能的/jobs命令当前未提供，使用真实Slurm与PID回退核查，不宣称已安装命令。
总体目标继续active，四材料原生d资格和PZT完整AB响应仍未全部完成。

后续实质进展：PTO四个从未执行的正负剪切阶段已提交HF27722637，
RUNNING/node96/32MPI×1OMP/非独占，48秒观察有实际DAV4/5/6。
参考SCF没有重复运行；其力门失败明确保留，整体仅用于研究诊断，不合格benchmark。
16个输入与原准备字节一致，新阶段复用原力/带隙/收敛检查；
没有提高精度、放宽阈值、更改native d门或覆盖失败日志。
薄包装器固定父runner/reference hashes，复用既有算法，所有新输出exclusive。
prepared/started已收集；本地Python编译/Slurm语法及输入同一性检查通过；
既有极化/应变定向回归55 passed、14 warnings、1.62s（不代表包装器全覆盖）。
实际新增提交1个，完成阶段和资源费用待终态核查，不能按计划造SCF次数。
PZT/HF27722565同期真实RUNNING/46:05，不从旧锁或等待超时重投。

后续实质进展：补齐实际应变晶胞量子→原始VASP偶极文本→既有分支匹配→
完整18分量raw响应fit的三维控制，0.5%/1%各13几何，fit/allowed rank18/18。
错误复用参考晶胞量子的负例可检测，不把合成模型当作真实材料或proper响应验证。
完整回归698 passed、4347 warnings、30.86s、exit0；单位审计0 findings/0 suppressions。
算法/API/CLI未改，新增DFT提交0；PTO27722637真实RUNNING/第17步，
PZT27722565真实RUNNING/第14步，完整目标仍active而非完成。
# 2026-09-19 后续终态收集

HF27722676单开关对照随后已COMPLETED0:0，实际NBANDS32、19次电子迭代、
电子收敛且gap1.9276 eV，全部15个打印力分量与LCALCPOL开启点完全一致。
因此排除LCALCPOL开关是本例静态力超限的原因；最大力仍1.553594007e-4 eV/Å，
力门不通过。4份原始结果哈希匹配，详见PTO审计最新终态节及
`PTO_VASP_lcalcpol_off_27722676/terminal_receipt.json`。下一步仍需分离
默认带数/并行与电子初始化历史因素，不能因此提升原生d或独立剪切benchmark。

后续PTO实际XML配对核实末步求力几何完全一致、FFT网格一致，但默认NBANDS
由弛豫24变为静态32，存在未锁定的数值设置混杂。单点LCALCPOL-off控制
已提交HF27722676，首次观察RUNNING/node43/32MPI×1OMP非独占；仅改极化开关，
SCF/力门/PAW/几何不变，实际NBANDS32仍须终态核查。见PTO直接剪切审计及
`PTO_VASP_lcalcpol_off_27722676/submission_receipt.json`。这不代表完整原生d验收。

PZT/HF27722565 CG重置诊断已COMPLETED0:0，14步、最大原子力范数
6.549119033e-5 eV/Å、gap1.842055684 eV；满足既定力与绝缘性门，
但极化未计算、跨235构建兼容性未验证，不能加入原235完整响应点计数。
10份原始文件哈希匹配，见PZT失败审计的最新终态节和terminal_intake.json。

PTO/HF27722637已FAILED1:0；负剪切弛豫成功，后续静态LCALCPOL电子收敛，
但最大原子力范数1.553594007e-4 eV/Å超过1e-4门；gap1.9276 eV合格。
正剪切阶段未执行，无独立中心差分e15/C55结果；完整原生d验收仍待解决。
见PTO直接剪切审计最新终态节和minus_static_terminal_audit.json。
本次无新提交、无精度提升、无主分支/原生backend gate修改；完整目标保持active。

## 2026-09-19：PTO/ZnO独立中心应变续算与PZT 003+收集

PTO独立VASP中心应变作业27722735在`strain-002-plus-static`停止：弛豫末步力
9.725e-5 eV/Å通过，但独立冷静态复核为1.0091e-4 eV/Å；ZnO作业27722789同样
从7.27214e-5变为1.03248e-4 eV/Å。两者电子收敛、绝缘且并非物理响应失败。
分别提交一次有证据的复核结构再弛豫续算27723065和27723070，均保持PBE、1000 eV、
32MPI×1OMP、EDIFF1e-8、力门1e-4、100步和原应变，不放宽门槛、不重复已通过点。
PTO修正弛豫/静态已以7.275e-5/6.497e-5通过并继续003−；ZnO修正弛豫以
9.70303e-5通过，独立静态复核仍在运行。GaN原独立中心应变作业27722871继续运行。

235原build PZT strain-003+同时完成：26步、最终力6.78799e-5 eV/Å、带隙
1.845969674 eV，ABACUS/PYATB分别4918/16秒；实际+0.5% zz应变和三方向极化已核验，
14份小型证据与远端SHA256匹配并归档。原PZT合格点增至8/12；004+仍运行，
004−/005−仍未过固定力门，005+未完成。因此PZT完整e/C/d仍不得宣称验收。

## 2026-09-19：PZT strain-004+ 原任务验收

cu25上的原始`004+`任务在第97个离子步达到ABACUS实际最大分量力门：
`9.88795e-5 < 1e-4 eV/Å`，SCF/离子收敛标记完整，带隙`1.842042964 eV`。
40 MPI×1 OMP的ABACUS/PYATB分别耗时17979/16秒；PYATB一次运行得到a/b/c极化
`(5.347895385e-8, 2.140382068e-2, 1.124337660908) C/m²`，精确文件哈希与适配器
清单一致。独立收据`pzt-strain004plus-accepted-20260919.json`冻结全部输入、运行、
结构、带隙和极化证据。PZT当前11/12点通过，仅`005+`仍运行；未重投、未改变
`scf_thr=1e-8`、`force_thr_ev=1e-4`、`relax_nmax=100`或`stress_thr=0.5`。
