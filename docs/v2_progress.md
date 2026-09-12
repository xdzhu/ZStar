# ZStar v2 阶段进度记录

**目标线程：**长期推进 ZStar v2；**工作分支：**`zstar-v2-development`
**更新时间：**2026-09-12（Asia/Shanghai）

## 已完成

1. 第一轮研究基线已提交为 `0c5fdf4`：v1 审计、文献/BibTeX、理论拆分、任意空间群约化、总体架构和测试计划。
2. draft-only v2 API 已提交为 `75c073f`：
   `zstar/v2/model.py`、`units.py`、`mechanical.py`、`symmetry.py`、`fit.py`、`algebra.py`。
   该 API 与 v1 `zstar-response` 1.0 隔离。
3. 当前工作树又加入结构级 `spglib` 表示、工程 Voigt 应变表示和
   `.zstar/v2` 原子替换状态/ensemble 原型；这些仍需评审后再冻结。
4. ABACUS force/stress 输出解析已接入 draft `ResponseDocument`，真实 smoke 结果已
   成功回读，见 [`v2_abacus_smoke_20260912.md`](v2_abacus_smoke_20260912.md)。
5. 已增加显式 stress-sign 转换和 `fit_elastic_response` draft API：未知的
   `backend-raw` 符号会被拒绝，拟合使用实际序列化应变并返回 rank/residual。
6. 已在 cu24–cu26 完成 cubic BaTiO₃ 六分量、两幅度 clamped-ion 试验（25 阶段），
   结果与审计限制见 [`v2_abacus_multiamp_20260912.md`](v2_abacus_multiamp_20260912.md)。
7. collector 已在日志存在 `FINAL_ETOT_IS` 时保存 stage energy；本轮能量二阶曲率与
   stress 拟合仍有幅度依赖，尚不能作为最终弹性结果。
8. 已加入 draft Berry 极化 parser、极化量子单位归一化、非正交/低维 branch matcher
   和路径展开诊断；已用 ABACUS NSCF `gdir=1,2,3` 参考结构 smoke 回读验证，详见
   [`v2_abacus_polarization_smoke_20260912.md`](v2_abacus_polarization_smoke_20260912.md)。
   这仍不是压电结果：尚未加入应变 Berry 对、proper 修正或独立后端核对。
9. 已加入 `fit_piezoelectric_response` draft API：只接受同一连续 Berry branch、
   C/m² 极化和实际工程 Voigt 应变，返回 e 矩阵及 rank/residual；proper/improper
   几何修正、relaxed-ion 贡献和张量单位封装仍未冻结。
10. 已加入严格的 `collect_abacus_polarization_triplet`：按 `gdir=1,2,3` 组织
    三个独立 NSCF 目录，拒绝缺方向、重复方向和重复目录，并保留 scalar 与
    Cartesian tuple 的区别，供后续应变路径组装。
11. 已加入 `match_polarization_ensemble` 和 `MatchedPolarizationEnsemble`，将
    非连续的 `reference, +η, -η` 样本相对于 reference 做 branch matching，保存
    实际应变、量子基底、branch shift 和 residual；尚未连接正式应变 Berry 生产任务。
12. 已加入 `fit_piezoelectric_ensemble` 薄封装，将 branch-matched ensemble 接到
    raw e 拟合；它检查零应变 reference，并允许用户显式设置 residual 阈值，不把
    合法的物理 ΔP 默认判为错误。
13. 已加入 `prepare_abacus_berry_stages` dry-run：从已完成的 SCF stage 复制
    `STRU/KPT/赝势/轨道/charge restart`，生成三个独立 NSCF `gdir` 目录和 manifest，
    明确写入 `init_chg/read_file_dir/berry_phase/symmetry`，但不执行 ABACUS。
14. 已将该 dry-run 生成的 `gdir-3` 目录在 cu26 做单阶段实跑：ABACUS 原始
    `exit_code=0`、wall time 57.40 s，Berry parser 回读成功；外层 Windows→SSH
    CRLF 包装返回码单独保留，未与 ABACUS 状态混淆。
15. 已修正 Berry preparation manifest 的可迁移性：JSON 只保存相对 `gdir-*` 路径，
    返回对象才提供当前机器的绝对路径；同时支持 `.upf/.orb` 及其 gzip 资产。
16. 已完成 cubic BaTiO₃ 的 reference、`strain-001±` 共 9 个 Berry NSCF 阶段，
    并用 triplet collection → reference branch matching → 对称性约束 e fit 串联审计；
    结果为 `Pm-3m` 禁止的零 e，完整记录见
    [`v2_abacus_strain_polarization_smoke_20260912.md`](v2_abacus_strain_polarization_smoke_20260912.md)。
17. 上述 9 阶段全量回归保持 `456 passed, 1252 warnings`；准备目录、远端原始日志、
    parser 输出和对称性 fit 诊断均已保留，尚未把该零响应提升为一般材料压电结论。
18. `collect_abacus_strain_response` 现支持显式 `polarization_stages` 映射，将
    triplet 的晶格方向标量、量子和可选 Cartesian directional tuple 写入 v2 schema；
    未提供映射时 force/stress/energy 旧行为保持不变。
19. 已加入低维安全门：`dimensionality < 3` 的 ABACUS Berry 极化不会被按三维
    `C/m^2` 静默收集；在 sheet/line 归一化、真空依赖和边界条件明确前，collector
    给出可操作的失败提示。对应 failure-matrix 测试已加入。
20. 已在人为构造的非中心对称 tetragonal BaTiO₃ (`P4mm`) 上完成 9 个 SCF + 27 个
    Berry NSCF 的算法完整性 smoke。补齐 `eta_xx/eta_yy/eta_zz/eta_xz` 正负对后，
    允许秩 3、拟合秩 3，`complete=True`，最大线性重建残差为 `5.5e-7 C/m²`，且
    `e15=e24`、`e31=e32` 满足 `P4mm` 约束。该单幅度、未弛豫人工结构结果只用于
    证明采样和重建链闭合，不作为材料压电值。详细输入哈希、节点计时和失败门见
    [`v2_abacus_tetragonal_piezo_smoke_20260912.md`](v2_abacus_tetragonal_piezo_smoke_20260912.md)。

21. 重新核对 v1 的 PYATB 实现后确认：一次 PYATB 运行会在内部完成 a/b/c 三个
    Berry loop，并在一个 polarization.dat 中写出三方向极化和量子。因此 v2 正式
    路径改为“每个几何一次 PYATB”，不再为三个方向分别启动 ABACUS NSCF；新增
    parse_pyatb_polarization、collect_pyatb_polarization 和非正交晶格的显式方向投影
    重建。ABACUS gdir=1,2,3 仅保留为可选交叉审计 backend。

22. 直接 PYATB writer 的六位小数不足以支撑本轮小应变差分；已改用 v1
    zstar.pyatb_precision writer 在 40 MPI × 1 OpenMP 上重跑三方向极化。该适配器
    保留六位小数原文件，另写 16 位 polarization.dat 与哈希证明，数值 kernel 未改。

23. 已在 cu24/cu25/cu26 以每任务 `40 MPI × 1 OpenMP` 完成 tetragonal `P4mm`
    fixture 的 1 个 reference + 36 个中心应变 SCF，并对每个几何各运行一次
    precision PYATB；37 个 PYATB 输出均包含 a/b/c 三个方向。SCF 串行 wall-time
    合计 4905 s，PYATB（含 reference）合计 882 s，所有任务 `exit_code=0`。

24. formal collector 已闭合：输入秩 6、P4mm 允许秩 3、拟合秩 3，最大重建残差
    `2.7885e-6 C/m²`，branch shift 最大值 0。当前 raw e 仅为固定离子算法验证，
    不作为材料数值；完整输入哈希、节点计时、命令和 Gate C 缺口见
    [`v2_abacus_tetragonal_formal40_20260912.md`](v2_abacus_tetragonal_formal40_20260912.md)。

25. 根据 Vanderbilt proper-piezoelectric 定义补齐研究 API
    `proper_piezoelectric_response`：对 normal 和 engineering-shear 列分别施加
    几何修正，并同时返回 raw、correction、proper 三个矩阵；新增测试明确拒绝未声明
    的 Voigt 剪切约定。该转换不选择 Berry branch，reference branch 仍由 collector
    和 ensemble matching 负责。

26. 为弹性拟合增加显式 `enforce_major_symmetry` 门，将空间群允许子空间与
    `C=C.T` 的热力学约束求交；P4mm 的 elastic basis 从 7 降为 6 个独立参数。
    formal tetragonal 数据在 compression-positive 假设下给出正特征值候选，但 sign、
    应变收敛和独立后端尚未核实，因此只写入案例诊断，不提升为正式 C。

27. 为 ABACUS 应变任务增加显式 `ion_relaxation` 研究选项。默认
    `clamped-ion` 保持原有 SCF 输入；选择 `relaxed-ion` 时，只有正负应变阶段切换
    到 `calculation relax` 并写入正的 `force_thr_ev`，reference 仍固定为参考结构的
    单点 SCF。collector 同时识别 `running_scf.log`、`running_relax.log` 和
    `running_cell-relax.log`，分别记录电荷与离子收敛状态。该接口尚未声称已完成
    relaxed-ion 实际计算或 `Lambda` 重建，后续仍需结构回读、内部应变拟合和独立核对。

28. collector 现在会读取固定晶胞 relax 输出中的唯一 `OUT.*/STRU_ION_D`，校验原子
    顺序和晶胞，并把 `wrapped(final_fractional-initial_fractional) @ initial_cell`
    保存为显式 `internal_displacement` 张量。新增 `fit_internal_strain_response` 将
    该张量拟合为 Cartesian Λ 的扁平化线性结果；不自动施加声学平移规范，也不把
    尚未实跑的 relaxed-ion 数据误标为正式响应。

29. 在独立远端 scratch `/home/zhuxd/zstar-v2-tbto-relaxed40-20260912` 启动真实
    `40 MPI × 1 OpenMP` relaxed-ion 应变任务。reference SCF 已完成；cu24、cu25、
    cu26 采用可恢复的 stage runner。早期手动 smoke 与批处理 runner 曾在
    `strain-001-` 发生同目录并发，已终止双方、把冲突输出移入
    `OUT.POLAR.duplicate-aborted-20260912-1130` 并安排干净重跑；该阶段及其冲突日志
    不会进入结果摘要。

30. 将 relaxed-ion 研究 runner 固化到 tetragonal 案例目录：每个 stage 使用原子
    `.zstar-stage.lock`，陈旧锁只移动到带时间戳的审计目录，不会静默删除；默认仍为
    `40 MPI × 1 OpenMP`，并要求 `STRU_ION_D` 与明确的 ionic-convergence 标记后才写入
    `.done40`。同时将 v2 测试改为使用仓库内可复现的 tetragonal 输入，不再依赖被忽略的
    v1 运行时生成目录。

31. strain preparation 现在为 reference 和每个 stage 保存输入哈希（INPUT、STRU/KPT
    及复制的 UPF/ORB 资产），collector 在解析输出前逐项校验；relaxed-ion 若由 PYATB
    临时替换 `STRU`，则以保留的 `STRU_INITIAL` 进行校验。新增输入被改写后的失败测试，
    防止不同输入生成的结果被静默混合。

32. backend capability contract 已接入 draft API；`BackendCapabilities.require` 显式
    检查功能、最大维度和金属 Berry 极化安全门，PYATB strain collector 也会在读取输出
    前拒绝 `metadata.insulating: false`。该字段仍需由独立 band-gap/后端审计提供，不把
    capability 声明冒充物理验证。

33. 增加显式 `remove_acoustic_translation` 规范工具：支持等权或用户提供的正权重，
    仅在调用者明确选择时移除整体平移，collector 和 Λ 拟合默认保留原始规范；对应
    理论说明和测试已补齐。

34. 远端 relaxed-ion 任务中，清理并重跑的 `strain-001-` 已在 cu25 以单一
    `40 MPI × 1 OpenMP` 于 11:57--12:20 完成，`STRU_ION_D` 和 ionic-convergence
    标记均存在；随后用原子锁定的 PYATB runner 于 12:41 完成一次三方向 precision
    极化。当前 `reference` 加 9 个无污染 strain stage 已有 PYATB 输出，其余 stage
    仍由 cu24/cu26 各一个 40-rank ABACUS runner 继续推进；relaxed-ion 全张量尚未
    收集完毕，不能提前写入材料结论。

35. 用户补充授权 `cu17` 后，先用 PBS/节点负载和进程检查确认该节点空闲，再在
    独立审计目录 `audit-cu17-001minus-20260912` 以 `40 MPI × 1 OpenMP` 对已完成的
    `strain-001-` 终态执行 `scf_thr=1e-8` 单点 SCF。ABACUS 运行约 123 s，能量为
    `-3729.322542166178 eV`；随后仅运行一次 PYATB `POLARIZATION`（一次得到 a/b/c
    三方向）并用 precision adapter 写出 16 位结果。相对于 formal stage 的
    `(-)` 极化 `(6.4571267012e-08, 5.9328896803e-08, 3.9502396831e-01) C/m²`，
    审计值为 `(6.4512617690e-08, 5.9154254935e-08, 3.9502397892e-01) C/m²`，
    差值约 `(-5.86e-11, -1.75e-10, +1.06e-8) C/m²`。该结果只作为独立数值审计，
    不替代 formal stage，也不把单点审计误写成完整 relaxed-ion 张量验证。

36. 为获得可解释的 clamped/relaxed 对照，又在 cu17 以 `40 MPI × 1 OpenMP` 对
    formal stage 保存的原始 `strain-001-/STRU_INITIAL` 做了固定离子 SCF（约 123 s，
    `scf_thr=1e-8`），并用一次 PYATB 得到三方向极化。有效 clamped-ion 值为
    `(6.4773256444e-08, 5.9616427567e-08, 3.4876883547e-01) C/m²`；与同一应变、
    同一收敛设置下的 relaxed 终态审计值相比，`ΔP_relaxed−clamped` 为
    `(-2.6064e-10, -4.6217e-10, 4.6255143e-02) C/m²`。该差异仅是单个应变点的
    内部弛豫审计，不能代替完整 Λ 或 relaxed-ion e 拟合；两次误复制终态的旧输出
    已整体归档并明确标注为 `wrong-final`，不进入数据收集。

37. 为充分使用新增的 `cu17` 而不产生同目录并发，先暂停 cu24/cu26 的旧批处理父进程，
    保留其当前 MPI 子作业继续收尾；随后在确认 `strain-013-` 完整收敛后手工补写其
    运行记录并结束旧父进程。现在由 cu24 收尾 `016+`、cu17 的原子 runner 接管
    `017+–018+`，cu26 的原子 runner 接管 `014-–018-`；cu25 的原子 PYATB runner
    扫描所有已完成 stage。每个节点最多一个 40-rank ABACUS/PYATB 作业，所有活动
    stage 通过 `.running40`/`.zstar-stage.lock` 可审计，未修改 PBS 占位或其他用户任务。

38. 资源审计随后发现 cu26 曾残留第二个旧 `run_relaxed_batch.sh`（40 ranks，工作于
    `strain-015-`），使节点短时出现 80 个 ABACUS 进程。通过独立 PGID/session 和
    工作目录确认其为本轮遗留后，仅终止该旧进程组；其部分输出与日志整体归档为
    `OUT.POLAR.duplicate-aborted-20260912-1835`，未纳入结果。cu26 的 atomic
    `strain-014-` 未被终止，清除残留 `.running40` 后将按序重跑 `015-`，并再次核验
    节点仅有一组 `mpirun -np 40`。

39. 按“先证明算法、再优化工程”的要求，补做了 `eta_xx=±2.5e-4` 并与已有
    `±5e-4`、`±1e-3` 极化审计比较。每个几何只运行一次 PYATB `POLARIZATION`，
    由同一输出取得 a/b/c 三个方向；实际应变从序列化晶格回算。中心差分的
    `dP_c/deta_xx` 依幅度分别为约 `0.0122`、`0.1145`、`0.0294 C/m^2`，明显不
    收敛；各弛豫对的中点相对单点 reference 还存在约 `0.0463 C/m^2` 的 c 方向
    偏移。完整数值、输入和命令见
    [`v2_abacus_multiamplitude_audit_20260912.md`](v2_abacus_multiamplitude_audit_20260912.md)。

40. 该不收敛不是 Berry 分支跳变：所有打印值均远离约 2.0/2.1 `C/m^2` 的分支
    量子；审计进一步发现 formal reference 的单点 SCF 残余力为约
    `0.36--0.67 eV/Angstrom`、对角应力为约 `41--75 kbar`，不满足 relaxed-ion
    响应的平衡参考条件。因此当前数据只能作为算法失败诊断，不能写成已验证的
    `e`、`Lambda` 或 relaxed-ion `C`。Gate C 暂停，已在 cu17 独立启动 reference
    relaxation，完成后须以该平衡结构重建应变点再继续。

41. 将上述物理前置条件落实为 collector 失败门：`relaxed-ion` ensemble 现在必须
    声明正的 `force_thr_ev`，并在解析任何响应张量前检查 reference 的最大离子力；
    超过阈值会给出“先弛豫 reference”的明确错误，而不是继续拟合。新增失败测试覆盖
    高力 reference；相关定向测试为 `38 passed`。这只收紧算法正确性契约，不改变
    v1 接口，也不引入 CLI 或集群调度逻辑。

42. 在 cu17 完成了独立 fixed-cell reference relaxation（40 MPI，约 1209 s）：最大
    力 `0.000488 eV/Angstrom`，达到 `force_thr_ev=0.0005`；最终能量
    `-3729.323887441615625 eV`，应力仍约 `(68.1855, 68.1855, 23.5694) kbar`。
    对该最终结构只运行一次 PYATB 得到
    `(6.9583213193e-08, 5.9093019978e-08, 3.9500998393e-01) C/m^2`，与旧 relaxed
    ±应变点的 c 分量对齐，确认旧偏移源于未平衡 reference。

43. 重建平衡 reference 周围的 ±`2.5e-4` 应变时，输入审计先发现一次错误：误用
    旧目录的零应变 `STRU_INITIAL`，使两项实际变成 zero-strain。两项 40-rank 任务
    已完成但整体移入 `OUT.POLAR_BAL_XX_{P025,M025}.wrong-cell-20260912`，明确排除；
    随后按保留旧 ±晶格、替换为平衡内部坐标的规则重新启动。该事件再次说明必须在
    SCF 前检查实际晶格和序列化结构，不能只相信目录名或 nominal amplitude。

44. 纠正输入后，平衡 reference 周围的 ±`2.5e-4` 两个 stage 各四个离子步收敛，
    并各自只运行一次 PYATB。用实际晶格分母得到
    `dP/deta_xx=(1.0859e-05, 8.61e-08, 5.8687e-02) C/m^2`，中点相对平衡 reference
    的 c 偏移降到 `1.69e-04 C/m^2`。这只说明 reference 前置条件已修正，仍需与
    平衡 reference 的 ±`5e-4`（当前在 cu24/cu25 计算）比较后才可判断线性收敛。

45. 平衡 reference 的 ±`5e-4` pair 随后分别五、六个离子步收敛；PYATB 给出中心
    `dP/deta_xx=(1.0969e-05, 2.68e-07, 8.0444e-03) C/m^2`，c 中点偏移约
    `1.807e-04 C/m^2`。与 ±`2.5e-4` 的 c 斜率仍相差约七倍，因此只能判定为
    “reference 已平衡、响应尚未幅度收敛”；平衡 ±`1e-3` 正在作为最后的截断误差
    诊断，Gate C 仍阻塞。

46. 进一步检查发现各 balanced stage 的最终最大力残差约为 `7.5e-5--3.6e-4
    eV/Angstrom`，不能把幅度差异直接归因于物理非线性。保持 `scf_thr=1e-8`，另建
    `force_thr_ev=1e-4` 的 ±`2.5e-4` tight audit（cu24/cu25，40 MPI）以分离离子
    收敛误差；在该审计结束前不接受任何材料响应常数。

47. tight ±`2.5e-4` pair 已达到最大力约 `6.9e-5`/`6.7e-5 eV/Angstrom`；其 c
    导数约 `0.02186 C/m^2`，介于先前松阈值 ±`2.5e-4` 与 ±`5e-4` 结果之间，说明
    离子收敛误差确实进入响应误差预算。当前用同一 `force_thr_ev=1e-4` 重算平衡
    ±`5e-4`，之后再判断是否需要更严格的物理模型或停止在审计阶段。

48. 对 balanced/tight 目录做字节级 provenance 复核后发现，其 `STRU_INITIAL` 原子
    坐标仍来自旧的应变弛豫结果，未严格等于平衡 reference；这些斜率全部降级为失败
    诊断，不再作为物理收敛证据。随后以 `force_thr_ev=1e-5` 重新弛豫 fixed-cell
    reference（cu17，40 MPI，639 s），最大力降至 `4e-6 eV/Angstrom`，极化为
    `P_c=0.39517389498898037 C/m^2`。

49. 使用该高精度 reference 坐标重建 `eta_xx=±5e-4`（cu24/cu25，40 MPI，663/668 s，
    `force_thr_ev=1e-4`）。最终最大力为 `4.1e-5/3.8e-5 eV/Angstrom`，中心斜率
    `dP_c/deta_xx=0.0159989367 C/m^2`，中点偏移 `2.409e-6 C/m^2`。

50. 同一 reference 的 `eta_xx=±2.5e-4`（cu24/cu25，40 MPI）最终最大力为
    `1.6e-5/1.5e-5 eV/Angstrom`，中心斜率 `dP_c/deta_xx=0.0156429208 C/m^2`，
    中点偏移 `7.785e-7 C/m^2`。两幅度斜率相差约 2.2%，说明该审计几何的
    `P(eta_xx)` 已达到初步幅度收敛，但仍不能代替完整张量验证。

51. 针对“SCF 精度是否限制离子力”的疑问，在完全相同的 tight-reference 几何上做
    了 `scf_thr=1e-8`（cu17，115 s）与 `1e-10`（cu26，129 s）单点对照，均为 40 MPI。
    最大力分别约 `2.34e-6` 与 `3.46e-6 eV/Angstrom`；PYATB 极化差为
    `(1.73e-14, 1.80e-14, 3.65e-9) C/m^2`，远小于当前应变差分误差。基于此，
    暂不把全部生产任务盲目提高到 `1e-10`；如后续体系出现 SCF 力噪声，再按同样的
    paired audit 决定。

52. 按用户授权在共享目录运行完整的 `P4mm` BaTiO3 六分量 `±1e-3` relaxed-ion
    API 验证（reference + 12 stages）。ABACUS 每阶段使用 `40 MPI x 1 OpenMP`，
    `scf_thr=1e-8`、`force_thr_ev=1e-4`；PYATB 每个几何只运行一次并输出 a/b/c
    三方向极化。13 个 stage 的 ABACUS wall-time 总和为 `10873.6 s`，所有离子
    阶段均有 `Relaxation is converged` 和 `STRU_ION_D`。详细输入、节点、SCF
    次数、张量、能量曲率和机械稳定性记录见
    `v2_abacus_sixstrain_api_audit_20260913.md`。

53. 完整 collector 回读成功：输入哈希、`STRU_INITIAL` 分数坐标、实际 cell 应变、
    force/stress/energy、内部位移和 13 次 PYATB 均通过。`P4mm` 允许子空间秩为
    3（压电）和 6（major-symmetric 弹性）；直接 relaxed-ion improper `e` 最大
    拟合残差 `1.94e-5 C/m^2`，弹性残差 `2.64e-2 kbar`，六个稳定性特征值均为
    正。该结果仍是单材料/单后端/单幅度审计，Gate C 不变。

54. 发现并修复 `STRU`→`STRU_INITIAL` 别名造成的输入哈希假失败：哈希现在对该别名
    使用逻辑名 `STRU`，同时保持真正内容变化的拒绝；新增回归测试后 v2 定向测试
    为 `86 passed`。修正提交为 `15c4fd6`，正负应变生成约定测试随后的提交补充。

55. 在同一 tight reference 上完成 `±2.5e-4` 和 `±5e-4` 两个六分量幅度 ensemble。
    两批各 12 个 ABACUS relaxed-ion stage 均收敛并完成一次 PYATB 三方向后处理。
    三种幅度下 `e31/e32` 展宽约 2.2%、`e15/e24` 约 2.1%、`e33` 约 0.5%；弹性
    张量变化小于约 0.4%，Lambda 残差保持 `10^-6 Å` 量级。完整数值、SCF 次数、
    40 核资源和一次中断重跑记录见 `v2_abacus_amplitude_audit_20260913.md`。

## 证据状态

* v2 独立 worktree 的完整回归为 `479 passed, 1124 warnings`（本地 editable install
  仅用于提供 distribution metadata，没有上传或发布）；v2 定向测试当前为 `86 passed`。
  警告均为 spglib/phonopy 等现有依赖的弃用提示，没有失败。
* v2 独立测试覆盖 schema round-trip、单位、Voigt、稳定性、实际扰动差分、
  intertwiner、rank/residual、relaxed-ion 代数、cubic/P1/molecule symmetry 和 restart store。
* 进入 Gate C 前没有提交 ABACUS/VASP/QE 任务；随后按用户授权在 cu24–cu26 直接完成
  一组三阶段 ABACUS smoke，详细记录见 [`v2_abacus_smoke_20260912.md`](v2_abacus_smoke_20260912.md)。

## 资源状态

PBS 检查显示 `cu24`、`cu25`、`cu26` 均为 `job-exclusive`，分别由当前用户的
40 核占位作业持有。用户已明确授权在这些节点上直接运行 v2；算法 smoke 已完成，
从下一批正式第一性原理任务起固定使用每任务 `40 MPI x 1 OpenMP`，记录节点、
MPI/OpenMP、wall time 和可复现实命令，并避免修改占位作业本身。
本轮另核对 `cu17` 的负载约 `0.16` 且无 ABACUS/MPI 进程；已用作上述独立审计，
审计目录与 formal scratch 分离，未抢占其他用户任务。

## 当前门控

* **Gate A：**已满足。
* **Gate B：**进行中；需要 schema/failure contract 评审和完整 v2 synthetic failure matrix。
* **Gate C：**仍阻塞。collector、单次 PYATB 三方向路径和内部位移拟合接口已接通；
  `P4mm` 六分量 `±1e-3` 审计已完成，允许子空间/秩、stress 符号与单位、能量曲率
  和 Λ 重建已有单后端证据。但在报告材料响应常数前，仍必须完成多幅度收敛、
  work-conjugacy 的独立复核和独立后端核对。

## 下一步

1. 评审并冻结 draft schema 的字段语义、单位注册表、边界条件和错误契约；
2. 补齐缺失 stage、金属、branch jump、backend failure、输入 hash 改变等 failure tests；
3. 对 tight reference 核对最终力、应力、空间群、能量和结构对应关系，并保留
   `1e-8`/`1e-10` SCF paired-audit 证据；
4. 将已通过的六分量 `±1e-3` 审计扩展到 `±2.5e-4`/`±5e-4`，逐 stage 检查 ionic
   convergence、`STRU_ION_D`、实际应变、分支残差和中点一致性；
5. 只有多幅度差分收敛后，才冻结 relaxed-ion `e`/`C`/Λ，并单独完成 stress
   work-conjugacy、单位和机械稳定性审计；
6. 在 `P4mm` 允许子空间完备的 branch-matched 极化数据上以独立后端或高精度
   参考结果核对，之后才进入正式压电/弹性 CLI 设计。
