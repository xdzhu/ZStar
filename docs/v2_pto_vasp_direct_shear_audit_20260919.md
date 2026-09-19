# PTO/PBE：独立直接剪切响应验证（运行中，不是验收结果）

## 科学问题和范围

现有PTO原生VASP完整e/C已完成，但原生d被displaced-atoms内应变平移力平衡门拒绝。
已有同源双路线收缩和声学规范测试不能代替独立导数验证。本次在**原生结果的同一
平衡结构、PAW、泛函、cutoff和k网格**上，用固定应变晶胞的真实离子弛豫及Berry
极化有限差分核查e15，同时保留应力供C55检查。这是不同响应路线，而非独立软件。
不重跑整个材料系列、不改native验收门，不以这一个应变方向验证完整e/C/d或d33。

PTO为三维极性P4mm体相、5原子；沿用原始原子顺序、极化畴和晶胞，
没有标准化、排序、晶格对称化或对称阈值扫描。
原生平衡结构SHA256：`93cb6fb3210d1ce963175dbf5f89dfb489d3cddab19b2a6fefe12c6bd894ddf8`。
参考接受记录：力6.99700007e-5 eV/Å、应力0.00585573 kbar、gap1.9272 eV、SG99。
本次另算参考静态极化，用于分支匹配，不重新优化参考结构。

## 扰动、坐标和单位

工程Voigt为`[xx,yy,zz,2yz,2xz,2xy]`，仅第五列η5=±0.005。
复用已有`zstar.v2.strain.apply_strain`和`actual_strain`：
对称Cartesian应变εxz=εzx=η5/2，F=I+ε，行晶格H'=H Fᵀ。
16位POSCAR序列化回读后实际η5为±0.005000000000000011；
其余应变为约2.22e-16以下的序列化误差，正负配对检查通过。
后处理必须再次读取实际执行POSCAR和最终cell，不仅使用名义0.005。

[VASP官方LCALCPOL说明](https://vasp.at/wiki/index.php/LCALCPOL)明确一次计算包含三个
倒易晶格方向；OUTCAR的p[ion]/p[elc]为电子电荷Å单位，官方定义电子电荷为负。
不得将原始偶极数值直接当C/m²，或凭与参考值接近调整符号。
应保留原始ionic/electronic dipole、晶格、体积、极化量子和branch整数；
采用显式电荷/长度/体积单位转换，再按现有v2分支与proper-piezo定义处理。
v2 VASP strain collector目前**没有已验证的Berry极化读取器**，本试验不伪造该接口
已稳定；输出先留作研究数据，只有解析及控制测试完成后才能报告压电差分。

对于固定晶胞离子弛豫，采用[官方ISIF=2](https://vasp.at/wiki/index.php/ISIF)，
只允许原子移动，不让施加的剪切应变被晶格弛豫消除。VASP应力保持raw标记，
转换至拉伸为正的物理约定后才能拟合C；不能用参考零应力0.5kbar门拒绝应变响应应力。

## 五个串行阶段及固定设置

1. reference：同一平衡结构，静态LCALCPOL；
2. minus-relax：−0.5%剪切，固定cell离子弛豫；
3. minus-static：以上CONTCAR，静态LCALCPOL；
4. plus-relax：+0.5%剪切，固定cell离子弛豫；
5. plus-static：以上CONTCAR，静态LCALCPOL。

沿用PBE/PAW、ENCUT1000eV、Gamma 9×9×8、EDIFF1e-8、EDIFFG−1e-4eV/Å、
NELM200、NSW100（弛豫）、IBRION1/POTIM0.1（原优化器）、NCORE4、ISYM0。
这里保留ISYM0是为了与原PTO父计算保持设置一致，不是新的默认策略或ISYM速度对照。
从原accepted-input仅改变ISIF=2；静态阶段另设IBRION−1/NSW0/LCALCPOL=true。
继承的NFREE5在上述弛豫/静态模式不是“五点压电差分”；实际应变点只有正负一对。
不提高精度，不重用未验证的CHGCAR/WAVECAR；原LCHARG/LWAVE=false保持不变。

每个阶段须电子收敛、最大原子力范数≤1e-4eV/Å、gap≥0.01eV、原子序列不变和cell
不变；弛豫阶段还须ionic convergence。保留实际执行输入哈希、日志、每阶段计时，
任何失败停止并保存证据，没有自动重试。参考静态阶段另核查SG99和应力≤0.5kbar。
最终分支/差分/proper校正与原生完整e/C对照尚未执行，不声明恢复或方法验收成功。

## 实际提交与验证

HF Slurm **27722611**，已观察RUNNING、node72、32MPI×1OMP、非独占；
首个观察elapsed00:00:13仅证明调度已开始，不证明VASP已进入SCF或成功完成。
目录：`/public/home/iai806/zstar-validation/pbe-native-piezo-20260918/pto-direct-shear-20260919`。
PAW仅在已授权HF目录内复制，不下载、发布或提交POTCAR到Git。
提交claim和执行标记禁止重复尝试；排除先前记录MPI启动失败的node317/node378，
不把该排除称为硬件故障已经证实。

本地输入准备回读、实际应变、正负配对和原子顺序检查通过，无parser warnings。
既有应变测试实测33 passed、14 warnings、1.46s；不是完整v1/v2回归或DFT准确性证明。
生成/运行脚本单位静态审计分别0 findings/0 suppressions；语法检查通过。
预检修正了Incar复制须保留Incar类型以及stress JSON须显式转列表的问题，
修正在提交前完成，没有因此重投DFT。
实际本地pymatgen2025.10.7、NumPy1.23.5、spglib2.7.0，不为技能的新版本快照升级环境。
单位技能的Python/Pint快照不匹配，使用已有显式单位层及静态审计，不伪造统计不确定度。

脚本SHA256：`71d84e717c68bbce2b065ba2c1e2806f62ab4c1e7475061db73423e65e646a26`；
Slurm脚本SHA256：`b244f558b8f72ea581b65c1cc465cfd201fc838524df3103eae2cb0a50372f72`。
资源成本待每阶段runtime/终态Slurm accounting收齐，不以分配时间伪造已完成core-hours。
PZT/HF27722565同期仍运行（已至第五离子步）；本次不更改原235采样计数。

## 初始尝试终态：PEAD 与 NCORE 的兼容条件漏检

上文RUNNING为初次观察，随后27722611终态为FAILED1:0，node72/32核/84秒。
VASP运行14.74190452秒后返回1；电子迭代行0、force blocks0，五阶段均未完成。
实际致命信息明确要求PEAD的NCORE=1；即使LPEAD未显式启用，LCALCPOL仍调用PEAD。
预检误以为能保留父参考静态计算NCORE4，这是本次设置错误，不是力或SCF精度不足。
原生父参考未启用LCALCPOL，所以其成功不证明新增LCALCPOL兼容同样的NCORE。

6个失败小文件已下载并逐项核查SHA256，目录
`outputs/pbe_database_comparison_20260918/PTO_VASP_direct_shear_failed_27722611`。
没有在原目录重跑、覆盖日志或把Slurm子step COMPLETED误写成主job成功。
84秒Slurm时间与14.74秒VASP启动时间重叠，不相加；本次SCF次数为0。
PSMAXN警告同时保留，但明确的终止条件为NCORE/PEAD，不将警告误写为本次失败根因。

一次有因修正准备在新`pto-direct-shear-ncore1-20260919`目录进行：
仅三个静态极化阶段NCORE=1，两个离子弛豫阶段仍NCORE4；32MPI×1OMP不变。
PAW、cell、网格、泛函、1000eV、EDIFF1e-8、力1e-4/100步不变，
不改变ISYM、不提高精度，不自动重复失败尝试。新尝试实际提交状态另记录，
本段不能当作已经运行或恢复成功的证明。

随后修正尝试已实际提交HF Slurm **27722618**：已观察RUNNING、node96、32核，
elapsed00:00:17。新目录的五阶段POSCAR/KPOINTS/POTCAR逐字节与旧尝试一致；
五个INCAR比对确认仅三个静态阶段NCORE4→1，其余设置（含两弛豫的NCORE4）完全一致。
新版runner SHA256为`a8f0fce2b1371bf41a4d6a16c5add800dd01f683431db74a24bdc07139bb8da2`，
Slurm脚本SHA256为`0a0f9a9784fdad9027a7e04715cb4cdf63f262f44eadc908b57e2caba33aa2cf`。
独立回执为`PTO_VASP_direct_shear_ncore1_submission_27722618.json`，保留旧提交回执和失败终态。
首次观察仅证明新job已获分配，不代表已进入SCF、极化解析成功或已通过响应验收。

后续已观察真正进入VASP SCF：27722618仍RUNNING、node96，elapsed00:01:52，
reference/vasp.log含`entering main loop`及DAV1、DAV2。
实际binary SHA256=`f0a61b17bb1d5668b510bec97b52188f96882ea73bd8299512c820e41a984b60`，
与失败父尝试一致；因此NCORE1已通过此次明确的PEAD启动兼容检查。
不将启动通过解释为电子收敛、极化分支通过或科学结果验收。
HF实际环境pymatgen2024.5.1/NumPy1.26.4/spglib2.6.0，与本地环境不同，均保留记录。
证据回执：`PTO_VASP_direct_shear_ncore1_startup_27722618.json`。

## 修正尝试终态：静态参考力检查未通过

27722618随后终态为FAILED1:0，node96、32核、Slurm348秒。
VASP自身返回0，运行271.0503073秒，19次电子迭代且电子收敛；
失败发生在后处理参考力检查，不是VASP运行崩溃或再次出现PEAD/NCORE错误。
只读pymatgen复核无warnings：最大原子力范数0.0001248900004 eV/Å，
超过统一1e-4门；gap1.9273 eV和最大raw应力0.03162954 kbar均合格。
没有完成正负应变阶段，也没有取得此次独立e15/C55或d33验证结果。

父continuation记录的优化末步力为6.997000071e-5 eV/Å，但同一几何的
父native-elastic/reference静态OUTCAR已显示约1.07e-4 eV/Å。
因此不能把优化末步的合格力自动转移为每一次独立静态SCF的合格力；
目前证据不支持把差异唯一归因于LCALCPOL、NCORE或电子噪声。
保持EDIFF1e-8、力1e-4、原生d门及源几何不变，未自动重投。
原ABACUS完整PBE响应不受本次独立VASP试验停止影响。

四个失败小文件已归档并与远程SHA256逐项一致：
`PTO_VASP_direct_shear_ncore1_failed_27722618`；终态详情见其中terminal_receipt.json。
Slurm348秒与VASP271.05秒重叠，分配成本3.093333 core-hours，
VASP阶段成本2.409336 core-hours，二者不能相加。

原始OUTCAR另发现本版本偶极单位为`|e| Angst`，不是官方旧NaF示例的
`electrons Angst`。前者是正的基本电荷量，后者的电子电荷为负；
尚未写新的极化解析器，禁止把旧示例的负号无条件用于本版本输出。
后续必须保留实际单位标签并依据对应版本单位验证转换，不能按匹配结果调符号。

## 研究读取工具与三维控制（后续进展）

新增`tools/read_v2_vasp_lcalcpol.py`，仅为研究后处理，不接入正式CLI或原生d验收。
正基本电荷标签`|e| Angst`的转换为正e，旧`electrons Angst`转换为负e；
读取离子与电子的完整配对并保留原字符串、数值、行号和单位。
模型为p_SI=q_label Å_to_m (p_ion+p_elc)，P=p_SI/Ω；
Ω由同次OUTCAR实际Cartesian lattice rows的正行列式确定。
三维极化量子为e H^T/Ω（H按行存晶格），其列向量直接兼容已有v2分支API。
不存在根据文献或native结果选择符号、把缺失方向补零或默认取铁电极化分支的行为。

完整配对后的最后记录才可读取；末尾截断、不完整、混合单位、非有限值、
不支持的单位、错误晶格及非3D归一化均明确拒绝，不静默复用旧配对。
该工具不检查电子收敛、带隙、力验收或DFT误差，调用者必须独立完成这些检查。
输出的standard_uncertainty为null；印刷位数不是SCF误差或统计标准不确定度。

新增22项控制均为三维模型：旧NaF官方文档数值的负BEC符号检验
（不是本次新算NaF）、正负单位区别、非正交极化量子列、
复用既有三维分支匹配、通用三维Cartesian旋转，以及上述失败条件。
与既有polarization控制联合44 passed/0.43s；完整本地回归696 passed、
4347 warnings、33.66s、exit0。单位技能静态审计0 findings/0 suppressions；
没有安装Pint或升级现有科学环境。这些控制证明研究读取算法，不证明压电DFT准确性。

已下载失败参考OUTCAR（不含POTCAR），SHA256与原远程档案一致：
8b6746fef781415a7fa4fb1dd866466d124ea8773882b2ca0f0f317d3f132bd4。
实际原始离子偶极为[19.18740,19.18788,10.53088]，
电子偶极为[-3.83748,-3.83758,4.47728]，单位均为`|e| Angst`。
完整原始转换与量子矩阵见失败目录`reference_raw_dipole_audit.json`。
该静态极化代表仍含任意晶格量子分支，不将其z分量当自发极化，不产生e15/C55/d。
研究算法SHA256为b467a2b1d6035985100050312135246f6b75803a3dbf026ee3907747e71c3b7a。
本轮新增DFT任务/SCF/集群core-hours均为0；HF/PZT27722565同期仍RUNNING，
已观察第9离子步，cu25/cu26原40MPI任务仍活跃，未加重叠任务。

## 四个原未执行应变阶段的诊断性续算

后续独立提交HF **27722637**，目录`pto-direct-shear-tail-20260919`。
目的不是将参考点的力门改为通过，而是完成尚无实际数据的正负剪切方向，
以判断native两Xi路线差异在直接响应中的表现。参考几何、参考SCF和原生门均不改。
参考力1.248900004e-4 eV/Å仍判失败；即使四阶段完成，整个试验仍
`benchmark_eligible=false/accepted_full_tensor=false`，不能悄悄填入合格论文主表。
此控制的平衡参考近似本身是限制，不能据一次差分宣称得到独立精度证明。

仅执行minus-relax/minus-static/plus-relax/plus-static；没有重复参考SCF。
各阶段开始前确认原目录不存在OUTCAR/runtime/vasp.log，故不是重试失败应变点。
16个INCAR/POSCAR/KPOINTS/POTCAR与原准备文件逐字节一致，
继承EDIFF1e-8、EDIFFG−1e-4、NSW100/PBE/PAW/1000eV/9×9×8/ISYM0；
弛豫NCORE4、静态LCALCPOL NCORE1，非独占32MPI×1OMP。
所有新阶段仍复用原严格电子/离子、力范数1e-4、带隙0.01及cell/原子顺序检查；
没有扩张力门、提升SCF精度或更改生产算法。

薄包装器通过哈希固定父runner和参考输出，复用既有运行及检查逻辑，
不复制新的计算器收敛算法。所有输出在新目录exclusive创建，无自动重投。
准备程序实际返回0；Slurm语法、Python编译和16文件同一性检查通过。
已有研究极化/应变定向回归55 passed、14 warnings、1.62s；
它不是包装器的全覆盖测试或新一轮完整回归（上次完整回归仍为696项快照）。

实际观察27722637 RUNNING、node96、32核、elapsed48秒，
minus-relax/vasp.log已有DAV4/5/6，证明真实SCF启动，不证明收敛。
启动binary hash与旧试验一致，HF包版本仍为pymatgen2024.5.1/NumPy1.26.4/spglib2.6.0。
prepared与started已收集，前者远程/本地SHA一致；详见
`PTO_VASP_direct_shear_tail_27722637/submission_receipt.json`。
参考输出仍在原目录只读使用，未下载或发布任何POTCAR。
本轮新增Slurm提交1个，计划新SCF数不能当实际完成数，费用待真实终态runtime收集。
同期HF/PZT27722565仍RUNNING，elapsed46:05，无抢占或235重叠提交。

## 实际应变量子与完整响应读取链的缺失控制补齐

既有分支测试主要采用固定量子；后续在同一研究测试中新增0.5%与1%的
三维非正交晶胞控制，包含零应变和六方向正负扰动（13几何）。
逐晶胞16位序列化回读，复用actual_strain计算实际工程应变，
将给定线性Cartesian响应加上任意整数倍的**该阶段**晶格量子，
转换为合成VASP原始偶极文本，再通过读取器、既有分支匹配和既有fit重建。
没有新增分支算法、proper校正公式或稳定CLI。

两种步长均完整恢复18个raw导数分量，fit/allowed rank18/18，
最大拟合残差<1e-12 C/m²；负例复用零应变晶胞量子导致
至少一个raw导数分量错误>0.1 C/m²。该负例检验流程错误，不是材料误差估计。
这证明读取链必须传递逐阶段量子；不证明某个真实材料的步长收敛、
proper/relaxed-ion精度或SCF噪声已满足要求。

定向读取/分支/差分测试58 passed/0.66s，随后强化rank断言后全套回归
698 passed、4347 warnings、30.86s、exit0；单位静态审计0 findings/0 suppressions。
测试SHA256与冻结回执见local_full_regression_deformed_lcalcpol_quanta_20260919.json。
单位技能影响为明确原始偶极、SI极化、逐晶胞体积/量子和无统计误差条；
没有安装Pint或升级科学环境。
新增真实DFT提交/SCF/core-hours均为0；PTO27722637仍RUNNING并观察第17离子步，
PZT27722565仍RUNNING并观察第14步，没有以合成控制替代目标中的真实计算验收。

## 四阶段诊断续算的实际终态

27722637随后为FAILED1:0，node96、32MPI×1OMP、Slurm1139秒。
负剪切弛豫28步收敛，最大原子力范数7.755169953e-5 eV/Å，带隙1.9276 eV。
其后minus-static自身返回0，运行270.1014375秒、19次电子迭代并电子收敛；
实际XML只读复核最大原子力范数1.553594007e-4 eV/Å，超过1e-4门，
带隙仍1.9276 eV且合格。根因定位为**静态阶段力验收失败**，不是带隙或电子收敛失败。
检查使用合并assert导致原failure.json的error为空，不能用空字符串或栈末尾
`gap >= .01`猜测是金属化；原始证据已保留，未修改运行中的检查器。

minus-static输入POSCAR SHA与minus-relax CONTCAR逐字节一致；
负剪切优化合格力不能直接继承给新独立SCF。此次观测还不能唯一归因于
LCALCPOL/NCORE差异或SCF噪声。正剪切两个阶段未执行，没有中心差分e15/C55结果，
也没有新d33结果；参考点原先未通过力门的限制继续保留，不提升为benchmark。
没有提高既定精度、放宽力门、修改原生d门或自动重投。

6份小型原始文件保存在`PTO_VASP_direct_shear_tail_27722637/terminal_raw`，
数值、检查和哈希见同目录上级的`minus_static_terminal_audit.json`，本地XML解析warnings为空。
远程只读Python解析观察60秒超时后改为收集小型XML/OUTCAR在本地解析；
这不代表VASP任务重启，任务失败终态由sacct及原始failure独立核实。
Slurm分配为10.124444 core-hours；minus-relax实测862.0204151秒、
minus-static270.1014375秒，阶段合计10.063305 rank-wall core-hours，二者重叠，不相加。
原ABACUS/PBE完整PTO e/C/d不受此补充诊断失败影响。

## 实际几何、网格与隐藏带数差异的定位

随后收集负剪切弛豫XML/OUTCAR、CONTCAR及两阶段INCAR，原始哈希逐项匹配。
复用pymatgen只读解析，核查五原子三维有序结构、身份映射和周期最近距离，
未排序、标准化、改动坐标或扫描对称阈值。两个实际末步求力XML的晶格/分数坐标
完全相同（在XML输出精度内）；CONTCAR与XML的约2.55e-8 Å差仅是序列化诊断。
两者粗FFT网格40×40×50、细网格80×80×100相同；PREC Accurate、ADDGRID=true、
LREAL=false、EDIFF1e-8、展宽0.02 eV、NELECT32相同，原输入ENCUT1000 eV相同。

**新发现：实际NBANDS分别24和32。** INPUT都未指定NBANDS，
NCORE4→1同时改变了默认带数；INCAR相似不等于实际数值设置完全一致。
[官方NBANDS说明](https://vasp.at/wiki/index.php/NBANDS)确认并行分组会自动调整带数，
空带数也影响迭代求解收敛。本证据确定了一个隐藏混杂因素，但没有证明力差异唯一由它造成。
另一个差异为弛豫末步仅3次电子迭代，而新静态SCF19次；不将这些差异定量当作SCF噪声预算。
两者XML打印自由能均-37.9770396 eV，打印相同不证明力相同或能量误差为零。
完整记录为`PTO_VASP_direct_shear_tail_27722637/relax_static_pair_audit.json`，warnings为空。

基于此证据准备一个有界单点控制：同失败minus-static的几何、PAW、NCORE1、
SCF与其他输入，仅LCALCPOL true→false。控制必须确认实际NBANDS仍32，
以先分离极化开关效应，不再一次同时改变带数、并行与极化设置。
控制本身不是新的压电结果、不是精度升级、不放宽既定力门，不自动重跑整个材料。
实际提交和结果须由独立回执记录，准备工作不能当作已提交或控制通过。

该单点控制随后已实际提交HF Slurm **27722676**，首次观察RUNNING、node43、
elapsed16秒、32MPI×1OMP、非独占。Python编译和Slurm bash语法检查通过，
准备阶段核查仅LCALCPOL不同，POSCAR/KPOINTS/PAW哈希与失败静态点一致。
预检使用同一远程进程等待完成，没有因读取延迟重启或重复提交。
独立prepared及提交回执保存在`PTO_VASP_lcalcpol_off_27722676`，prepared远程/本地哈希一致。
实际NBANDS32、力、电子/绝缘性和资源消耗待终态核实，不以RUNNING代替控制结果。

随后同一27722676仍RUNNING，node43，elapsed1:41；已确认实际VASP二进制哈希与
失败点一致，static/vasp.log进入`entering main loop`，started.json已收集。
没有因观察等待重复提交；此时仍无电子收敛或最终力结果。

## LCALCPOL 单开关控制终态：排除极化开关为本例力超限原因

27722676已COMPLETED0:0，node43、32MPI×1OMP非独占、Slurm369秒。
实际VASP282.6926032秒，电子收敛19次迭代，NBANDS32，gap1.9276 eV。
最大原子力范数仍1.553594007e-4 eV/Å，全部15个XML打印力分量与27722637
minus-static逐一完全一致，打印分量差0，不是仅比较一个最大值。
实际INCAR diff只有LCALCPOL True→False；POSCAR/KPOINTS/PAW输入哈希不变。
因此，在该固定几何、实际NBANDS32/NCORE1下，**极化开关不是本次静态力超限原因**。
这个结论不外推为所有体系所有VASP版本的无误差证明；打印差为0不等于真实DFT误差为0。

diagnostic/runtime/OUTCAR/XML已收集、4项SHA256与远程一致，warnings为空。
证据和控制边界见`PTO_VASP_lcalcpol_off_27722676/terminal_receipt.json`。
控制成本2.512823 rank-wall core-hours，调度分配3.28 core-hours，二者不相加。
控制成功退出仅表示科学对照执行成功，力门仍未通过，不作为压电benchmark或原生d验收。

下一步优先核查固定带数下的电子初始化与并行对照，再采用一致实际数值设置的
弛豫/响应阶段；不能直接把默认NBANDS变化写成已证明的唯一根因，
也不能用提高EDIFF精度、放宽力标准或重跑全部材料代替该定位。
本轮无新提交；235/cu25 PID17896、cu26 PID64871实测仍活跃，各40个ABACUS进程，
驱动日志没有新的完成点，未加重叠计算。完整PBE双后端e/C/d目标仍未完成。

## 固定并行下的实际带数对照：27722695

为分离已观测到的混杂因素，在同一失败minus-static几何、同一PBE PAW、
同一9×9×8网格、同一VASP二进制下，实际提交HF Slurm27722695。
固定NCORE4、LCALCPOL=false、冷启动，两个静态点显式NBANDS24/32串行执行；
二者INCAR语义只差NBANDS。它们相对27722676控制只改NCORE及显式带数，
SCF EDIFF1e-8、force1e-4、其他生产数值设置均不变。32/NCORE4结果将与
已完成32/NCORE1对照比较；不是材料系列重算、步长扫描、CLI修改或门槛放宽。

预检核查四输入源哈希、三维有序五原子及原子身份映射，无WAVECAR/CHGCAR；
Python编译与Slurm bash语法检查通过。pymatgen2024.5.1/NumPy1.26.4环境保留，
prepare warnings为空；未升级依赖、排序或标准化结构。作业node43、32MPI×1OMP非独占，
最新观察RUNNING/4:06。准备/提交/started回执保存在`PTO_VASP_fixed_bands_27722695`。

24条带点已实际完成：返回0、20电子迭代且电子收敛，NBANDS24、ISTART0/ICHARG2，
带隙1.9276 eV；最大力1.559503552e-4 eV/Å，仍高于1e-4。
运行145.9557868秒，1.2973848 rank-wall core-hours。32条带点已进入电子迭代，
尚无终态。本次24条带冷启动仍超限，说明仅恢复旧弛豫的带数/NCORE不能恢复
其打印合格力；不能宣布默认带数是唯一根因，也不能宣称尚未完成的并行对照一致。
完整raw文件及逐分量差待两个点终态收齐后记录，控制不提升为完整e/C/d结果。

### 固定带数/并行对照已完成，原始数据核验通过

随后27722695由sacct确认COMPLETED0:0、node43、Slurm380秒。
32带点21次电子迭代、SCF收敛、带隙1.9276 eV，最大力1.573486886e-4 eV/Å，仍未过力门。
两点实际NBANDS24/32、ISTART0/ICHARG2由XML复核；OUTCAR明确记录每条带NCORE4、8组，
不是只根据INCAR猜测实际并行。两XML的初/末几何与源求力几何/CONTCAR一致，
五原子顺序不变。13份新增原始/诊断/运行文件哈希与远程一致，warnings为空。

| 有界对照（全部为同一三维PTO求力几何） | 最大力分量差(eV/Å) | 最大原子力矢量差(eV/Å) |
|---|---:|---:|
| NBANDS24−32，固定NCORE4、冷启动 | 9.3000e-6 | 9.300005e-6 |
| NCORE4−1，固定NBANDS32、冷启动 | 4.1890e-5 | 4.189000e-5 |
| 新24/NCORE4冷启动−原24/NCORE4弛豫末步 | 8.3250e-5 | 8.390331e-5 |

因此带数与并行确实影响部分打印力，但三种冷启动单点的max force均约1.55–1.57e-4；
没有一个消除与旧弛豫7.75517e-5的差异。可以排除“仅恢复带数或NCORE即可修复”的建议，
但不能把剩余差异唯一归为某个优化器错误、SCF噪声或确定的冷/热初始化机制。
上述三组差异来自单点控制，不是独立统计重复或力不确定度标定，不累加为误差预算。

两点运行145.9557868/182.9365793秒，合计2.9234877 rank-wall core-hours；
Slurm分配3.3777778 core-hours，与阶段成本重叠，不相加。
`PTO_VASP_fixed_bands_27722695/terminal_receipt.json`包含原始哈希、全15分量差、实际并行与边界。
38项既有终态/坐标配对/LCALCPOL读取测试通过（0.64s）；没有新增核心算法，
本轮未重跑全项目回归。native worktree仍clean、vasp_response.py SHA不变，d门未改。

下一步应在明确且一致的实际带数/电子设置下取得相同几何的弛豫与响应观测，并验证
独立静态求力的可复现性；不能继续沿用旧合格力替代新静态力，也不能自动重跑完整材料系列。
补充剪切中心差分和原生d的质量验收尚未闭环；原ABACUS完整PBE结果保持不变。

### PTO全中心应变独立验证准备：一致电子设置与病态约化采样检查

按用户继续计算PTO的要求，不重跑已完成的ABACUS十三几何结果。
新的HF独立验证使用相同PBE、Pb/Ti_pv/O PAW、1000 eV、Gamma 9×9×8网格；
全程ISYM1、NCORE1、显式NBANDS32、LCALCPOL=true、ISTART0/ICHARG2，
EDIFF1e-8、EDIFFG=-1e-4、IBRION1/POTIM0.1/NFREE5、NSW100。
参考固定晶胞弛豫及冷启动静态检查均通过后，才生成实际参考上的±0.005工程应变；
每个应变弛豫后还要通过同设置静态力/绝缘性检查，失败保留日志、停止、不盲目重投。
参考要求SG99及最大应力≤0.5 kbar，应变点不要求零应力。
这是独立科学验证路线，不替换VASP原生优先接口，不改原生d门、不将诊断d升级为验收值。

预检在真实五原子三维PTO父结构上复现一个采样问题：spglib symprec仍为1e-3 Å，
识别P4mm，但优化晶胞约1e-9 Å的非对角元使当前采样器只选xx、zz就报告24/24满秩。
这并不意味着剪切响应可稳定恢复。通过现有allowed_response_basis构造每种输出的
系数设计矩阵，两个方向的最小奇异值约0.77–1.43e-9，e/C/Lambda设计条件数约
6.98e8/1.29e9/6.98e8；完整六方向相应条件数均约1。
本次因此明确禁用此约化采样，采用完整六分量±应变（参考加12应变，共13观测几何）；
另计参考及应变弛豫，不声称约化任务数或加速收益。
未改变结构、对称阈值或正式采样算法；病态非理想晶胞的采样判据是后续算法整改项。

只读审计脚本`.codex-output/audit_pto_reduced_sampling_condition.py`及
`pto_consistent_lcalcpol_20260919/sampling_condition_audit.json`保留完整奇异值和警告。
初次仅预检目录`pto-consistent-lcalcpol-20260919`没有提交DFT，作为历史预检保留；
完整采样的新目录为HF campaign下`pto-consistent-fullstrain-20260919`。
新runner使用独立zstar源码快照（SHA256 d2461efb8cc71733db35da6ae5a66e5d88b632b90fd961082ab9cab13274c5af），
复用apply_strain、actual_strain；Python编译、Slurm bash语法通过。
既有对称性/LCALCPOL读取测试46 passed，15个spglib弃用警告保留，没有升级依赖。
截至此准备记录尚未报告新DFT结果；原ABACUS d33=49.084674 pC/N保持不变。

预检随后完成（warnings=[]），源/runner/Slurm哈希核对通过，独占提交标记防止重复sbatch；
已提交作业27722725，squeue/sacct显示RUNNING、node43、32核、10秒的初始分配观察。
这是Slurm分配证据，不能据此声称VASP计算或参考结构已经通过。
提交回执`.codex-output/pto_consistent_lcalcpol_20260919/submission_receipt.json`保留
实际采样范围、SHA、设置、资源及未验收边界；完整采样prepared.json已回收。
新完整采样只读设计审计JSON的SHA为2d3d12d8ca91afb0084d0a515f7487c9546b065ee1c8aea3645e06d28ed6cde4。
初次病态采样预检目录没有DFT提交；native worktree clean、HEAD bbaf059a，d门未改。
后续55秒观察确认runner在node43进入`START reference-relax`，远程started.json记录实际
pymatgen2024.5.1/NumPy1.26.4/spglib2.6.0；这证明计算器已启动，仍不代表参考门通过。

### ISYM1初次失败与严格P4mm结构的一次有界重试

作业27722725终态FAILED/1:0，Slurm64秒；VASP实际14.1668秒、0.125927 rank-wall
core-hour，在reference-relax进入SCF前报内部错误
`GENERATE_KPOINTS_TRANS: number of G-vector changed in star 5015 5017`。
因此它不是电子或离子不收敛，更没有产生可用响应；原目录、vasp.log、OUTCAR和failure.json保留。

对父结构在固定symprec=1e-3 Å、angle_tolerance=5度下识别的P4mm八个操作进行Reynolds
平均：在原分数坐标基、原点和原子顺序内，对度量张量和同元素原子轨道投影。
父结构操作匹配最大距离1.59065e-5 Å；子结构最大晶格变化4.86466e-5 Å、最大原子
笛卡尔变化3.43961e-5 Å，严格子结构操作残差3.14e-16 Å。没有标准晶胞变换、原子排序、
极化畴翻转、精度提高或阈值放宽。投影元数据与POSCAR SHA保存在本地exact_projection.json。

严格结构重新预检得到稳定的四方向约化候选(0,2,3,5)，但本次仍采用六方向完整采样。
新目录`pto-consistent-fullstrain-exactsym-v2-20260919`，作业27722735初始观察
RUNNING/node43/32MPI×1OMP非独占。它是针对已识别VASP对称星输入不一致的一次有依据
重试，未覆盖27722725、无自动重试；当前尚无参考门或张量结果。
结构投影脚本及失败/重试回执保存在`.codex-output/pto_consistent_lcalcpol_20260919`。

后续5:58观察已取得参考门结果：reference-relax两离子步、电子和离子均收敛，
最大原子力9.282e-5 eV/Å；冷启动reference-static电子收敛，最大力9.368e-5 eV/Å；
两者实际NBANDS32。PBE间隙1.9273 eV、SG99，参考应力对角量
(-0.00521,-0.00521,-0.01845) kbar，均通过既定门。runner随后进入strain-001-minus-relax。
这同时表明严格P4mm+ISYM1的一致设置解决了初次G-star启动失败，并使弛豫/静态力均
在生产阈值内；仍需全部正负应变、实际向量、polarization/stress和张量拟合才能验收d。

真实PTO/ZnO父结构的系数设计审计还促成核心修复：task-selection秩现在采用
`max(1e-10,1e-8*s_max)`，不再把1e-9轴泄漏当作独立信息；相对阈值记录进plan schema。
新增近似P4mm和hexagonal回归，全套699 passed；提交6b8ec161已推送v2分支。

后续完整采样取得首个中心应变配对：strain-001-minus的relax/static最大力为
`5.796e-5/9.665e-5 eV/Å`，strain-001-plus为
`8.861e-5/1.678e-5 eV/Å`，均通过既定门。runner随后进入strain-002-minus。
这些是已完成阶段的数值证据，不是完整e/C/d终态；作业27722735保持单实例运行，
未因等待而重复提交。
