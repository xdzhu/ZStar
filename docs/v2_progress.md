# ZStar v2 阶段进度记录

**目标线程：**长期推进 ZStar v2；**工作分支：**`zstar-v2-development`
**更新时间：**2026-09-13（Asia/Shanghai）

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

56. 在同一 tight reference 和同一 `±1e-3` 六分量序列上完成 clamped-ion
    `P4mm` BaTiO3 审计（13 个 ABACUS single-point + 13 个一次性 PYATB 三方向
    后处理）。每个 ABACUS 任务固定为 `40 MPI x 1 OpenMP`、`scf_thr=1e-8`；
    总 wall-time `1658.4 s`、约 `18.43` 个 40 核 core-hours、190 个 SCF
    迭代。clamped/relaxed 的 `e`、`C`、rank/residual 和机械稳定性均在同一
    calculator-neutral collector 中回读成功，详情见
    `v2_abacus_clamped_ion_audit_20260913.md`。

57. clamped-ion 结果显示 `e33=-0.449975`、`e15=e24=-0.003945`
    `C/m^2`，而 relaxed-ion 对应为 `3.890919`、`5.076478 C/m^2`；
    `C33` 从 `3194.04` 降至 `1420.08 kbar`。这只证明边界条件分离和内部弛豫
    软化的数值链路，尚不等于最终 `Z*/Omega · Lambda` 规范已经冻结。

58. 在同一 tight P4mm BaTiO3 reference 上完成 v1 Unified symmetry-adapted BEC
    审计：4 个独立 site、8 个中心差分 stage，实际位移范数全部为 `0.010000 Å`；
    9 个几何各运行一次 PYATB 并得到 a/b/c 三方向极化。投影 BEC 的声学和最大
    误差为 `8.9e-16 e`，site 位移秩均为 3；ABACUS wall-time `1246.922 s`
    （约 `13.855` 个 40 核 core-hours），详情见
    `v2_abacus_bec_audit_20260913.md`。

59. BEC 与同一 relaxed-ion 六分量应变 ensemble 的 `Lambda` 做了实测重建。发现
    algebra API 原先会把 Å 数值直接代入 `q/Omega`，造成 `1e10` 的单位错误；现已
    增加显式 `internal_strain_unit` 转换，新增回归测试覆盖 `angstrom -> m` 和
    非法单位拒绝。该修正只在 v2 algebra 层，未改变 v1 入口。

60. 使用 `internal_strain_unit="angstrom"` 后，BEC/`Lambda` 重建的 relaxed-ion
    `e` 与直接应变拟合最大差为 `6.32e-4 C/m^2`（单材料、单后端、不同响应
    ensemble 的有限步长误差量级）；该结果支持单位一致的 `Z*Lambda` 链路，但
    Gate C 仍需 acoustic gauge、Gamma/IFC 和独立后端复核。

61. 在 algebra 层增加 `acoustic_sum_rule_diagnostics`：对归一化刚性平移基检查
    `Phi` 的左右平移零模和 `T^T Gamma` 的净力兼容性，返回绝对/相对残差及兼容性
    标志；`internal_strain_response(..., check_acoustic=True)` 可在超出容差时明确
    拒绝输入，默认不改变历史合成代数行为。新增兼容/不兼容矩阵测试，避免用伪逆
    静默掩盖错误原子索引或边界条件。

62. 应用户反馈把 SCF 与离子收敛的关系落实到准备接口：
    `prepare_abacus_strain_ensemble(..., scf_thr=...)` 会把同一阈值写入 reference
    和全部应变阶段，并在 ensemble metadata/convergence 中保留 `scf_thr` 与
    `force_thr_ev`。较小 `scf_thr` 可降低力噪声、帮助达到给定离子力阈值；是否
    采用 `1e-10` 仍通过 paired force/response audit 判定，而不是把它误当成单独的
    物理收敛证明。collector 现同时保存每个阶段的最大力和最大应力诊断。

63. 用 BEC ensemble 已保存的投影 `FORCE_CONSTANTS` 和同一应变拟合的 `Lambda`
    做了新 acoustic 诊断的实数值闭环：`Phi@T`/`T.T@Phi` 最大残差
    `9.99e-16 eV/Angstrom^2`，`T.T@Gamma` 最大残差 `3.55e-15 eV/Angstrom`，
    `Phi-Phi.T` 最大残差 `1.78e-15 eV/Angstrom^2`。这是同一 `Phi/Lambda` 构造的
    代数一致性证据，不是独立 Gamma 第一性原理验证；详情写入
    `v2_abacus_bec_audit_20260913.md`。

64. 将任意空间群的响应秩选样落到 draft API：新增
    `symmetry_adapted_input_plan`/`SymmetryInputPlan`，对 polarization、strain/stress
    和 relaxed-ion displacement 的 intertwiner 基做联合 block-rank 贪心选择；不再
    把六个应变分量固定写成“约化”。`prepare_abacus_strain_ensemble` 新增显式
    `symmetry_reduce=True`，P4mm BaTiO3 的统一计划由 6 个分量降为 4 个 canonical
    directions（8 个正负 stage），P1 保留全部 6 个。计划的向量、允许秩、identified
    rank 和 complete 标志写入 ensemble metadata，all-six control 仍可用于内部审计。

65. 补齐 rank 不足的 failure contract：`LinearFitResult` 现在在约束设计矩阵不完备
    时返回 `suggested_input_indices`，按实际已序列化输入向量推荐能增加秩的 canonical
    方向；它不生成缺失观测，也不零填充张量。新增 rank-deficiency 回归断言，并在
    对称性文档中记录“推荐方向仍须成对重算”的恢复动作。

66. 新增 calculator-neutral `normalize_polarization`/`NormalizedPolarization`：2D 使用
    周期面垂直高度 `Omega/A` 和面内投影，输出 `C/m`；1D 使用横截面积
    `Omega/|a_parallel|` 和轴向投影，输出 `C`；0D 明确拒绝把体积 `C/m^2` 当作分子
    极化。合成真空扫描和 wire 归一化测试通过。该层只解决几何/单位，不开放尚未
    验证的低维压电、弹性或开放方向响应。

67. 将显式低维归一化接入 PYATB strain collector 的可选路径：默认仍要求 3D bulk
    语义；`normalize_low_dimensional=True` 时才追加 `polarization_intrinsic`，并把
    `C/m`/`C` 单位、周期轴、投影、几何因子和边界标签写入 provenance。新增 2D
    collector 回归，确认单次 PYATB 三方向输出可直接复用，且不会悄然开启低维
    压电或弹性结论。

68. 修复联合 symmetry input plan 在某一输出允许秩为零时的空 block 边界：Pmmm
    正交 fixture 现在可以保留 12 个弹性允许参数，同时把 polarization 的秩 0
    作为严格的 symmetry-forbidden 分支处理；新增 P-6m2 hBN 2D fixture，确认
    六方边界兼容操作与 `1+6` 联合秩计划。

69. 将低维周期轴写入 `ResponseEnsemble` schema，并在 ABACUS strain preparation
    中显式计算 intrinsic periodic strain indices：2D 默认只生成面内 `xx/yy/xy`，
    1D 只生成轴向 normal strain；open-direction components 会给出可操作错误，
    未验证的低维 symmetry-reduced bulk 计划保持禁用。

70. 将空间群操作的原子映射从贪心最近邻改为 species-preserving 二分图匹配，并用
    近简并位点的合成操作回归；即使某个候选原子同时接近多个目标，仍优先寻找完整
    双射，避免把合法操作误判为不等价。

71. 为 `relaxed_elastic` 增加显式 unit-aware 模式：声明能量、长度、体积和目标弹性
    单位后，将 `Gamma.T @ Phi^+ @ Gamma / Omega` 从 eV/Angstrom³ 等能量密度转换到
    Pa/GPa/kbar；缺少任一单位或体积不是长度三次方时拒绝输入。旧的无单位调用仅
    保留给合成代数测试，不能直接作为真实材料常数。

72. 明确分子 `dimensionality=0` 的机械边界：`periodic_strain_indices(())` 现在给出
    “均匀周期应变未定义”的可操作错误，要求转用分子极化率或显式有限团簇边界模型；
    新增回归测试。该契约不改变 1D/2D intrinsic strain 规则，也不把分子体系静默
    扩展为周期弹性响应。

73. schema 层强制每个 `TensorQuantity.periodic_axes` 与顶层 `DimensionSpec` 一致；
    dim2/1/0 文档若漏写物理周期轴会在构造时失败，而不是默认为三维 bulk。新增
    dim2 拒绝和 dim0 合法 round-trip 测试，v2 schema 仍与 v1 `zstar-response` 1.0
    完全隔离。

74. collector 现在拒绝 manifest 中明确标记为 `failed` 或 `skipped` 的终态 stage，
    错误信息分别给出重跑失败 stage、移除 skipped stage 或重新生成 ensemble 的
    最小动作；不会因为目录中残留输出而把失败/跳过状态静默提升为可收集结果。新增
    两个 failure-matrix 回归测试。

75. `ResponseEnsemble` 现在显式校验 `zstar-v2-ensemble` 的 schema version；未知版本
    在读取时拒绝，并提示重新生成 manifest，避免未来不兼容字段被静默解释为当前语义。
    schema 名称和版本常量从 v2 API 导出，新增 forward-version failure 测试。

76. 对周期空间群分析补齐依赖/数据集失败契约：缺失 `spglib` 时明确终止；spglib
    在所有容差下返回空 dataset 时返回 `symmetry_untrusted` 且不允许建立约化计划。
    新增两条 monkeypatch synthetic 测试，保留分子 `dim=0` 的非周期特殊路径。

77. ABACUS collector 现在解析并保留每个日志的全部 `TOTAL-FORCE` 块：末块继续用于
    离子收敛，首块以 `forces_initial` 显式保存，附带块数和首末最大力诊断；relaxed-ion
    文档额外写入该 quantity，但不自动宣称 Gamma 已完成。新增多块日志和 schema
    回归，避免用弛豫终态零力替代应变—力耦合。

78. 新增 calculator-neutral `fit_strain_force_coupling`：消费首块固定离子力和实际
    序列化的 engineering-Voigt 应变，按 `Gamma = -dF/deta` 拟合 `(atom, cartesian)`
    行顺序，支持 `(stage, atom, cartesian)`/展平输入、零应变参考力、rank/residual
    诊断和 shape/finite 失败门。该 API 仅完成数值拟合，不绕过 `STRU_INITIAL` 对应性、
    acoustic-SR、正负扰动和独立 IFC/后端验证。

79. 用已有共享目录结果完成 `±5e-4` 与 `±2.5e-4` 的离线 Gamma 多幅度审计：两组
    拟合矩阵最大差 `1.36580e-3 eV/Å`、RMS `1.85499e-4 eV/Å`；与已有
    `-Phi@Lambda` 代数重建的差异约 `6.97e-2 eV/Å`。该结果支持幅度斜率已趋稳，
    但仍是同一 ABACUS 后端链路，不能替代首块对应性、独立 IFC/后端和 acoustic gauge
    闭合；完整数值与块数记录见 [`v2_gamma_force_audit_20260913.md`](v2_gamma_force_audit_20260913.md)。

80. 修正 unified strain symmetry plan 的输出表示契约：`force` 显式复用 Cartesian
    displacement 表示，`stress` 使用不加倍剪切的 tensorial-Voigt 表示，不再错误复用
    engineering-strain 表示。P4mm 的 `(polarization, force, stress, displacement)`
    联合计划达到允许秩 `3+14+7+14=38`，并保持四个 canonical 应变方向。

81. 在空间群分析中加入 Cartesian rotation 正交性与 `|det R|=1` 检查，并把被拒绝
    操作的原因写入 symmetry diagnostics；非标准晶胞或轻微异常操作不再静默进入
    intertwiner basis。

82. 新增 `fit_response_document` calculator-neutral 结果封装层：从已收集的
    `ResponseDocument` 读取实际应变和存在的 polarization/stress/force/displacement
    观测，追加带 units、axes、boundary、provenance 和 rank/residual diagnostics 的
    `piezoelectric_raw`、`elastic`、`strain_force_coupling`、`internal_strain`；stress
    sign 必须显式提供，缺失观测不补零，重复拟合会被拒绝。该层仍不宣称 proper、
    relaxed-ion 或独立后端验证完成。

83. 加强 Gamma 安全门：若响应文档声明 `relaxed-ion` 但缺少 `forces_initial`，结果
    封装层现在明确拒绝使用最终近零 `forces`，要求重新收集可识别首个
    `TOTAL-FORCE` 块；clamped-ion 文档仍可使用其唯一固定离子力块。

84. 对 cu17、cu24、cu25、cu26 做只读独立后端能力审计：四个节点均可见
    ABACUS 3.10.0-LTS、VASP 6.3.2、Phonopy 和 Python 3.10.9；`pw.x` 与
    `cp2k.popt` 未在当前 PATH 中发现。该结果只证明 VASP 交叉验证在软件层面
    具有候选路径，不等于 POTCAR、collector 或物理结果已经验证；未提交作业，
    资源消耗为 0 core-hours。详细路径、限制和下一步 Gate C 入口见
    [`v2_independent_backend_capability_audit_20260913.md`](v2_independent_backend_capability_audit_20260913.md)。

85. 澄清 v1/v2 边界：BEC、Gamma 声子/IFC、已有 acoustic-SR、PYATB 三方向极化
    属于继承基线，不在 v2 重新发明。v2 当前所做的是把这些已有结果接入应变—力/
    应力响应、显式单位/Voigt/边界条件和 calculator-neutral schema；`Z*Lambda`
    与 relaxed-ion 高层装配在当前仓库中尚无 v1 可调用实现，因此是 v2 新增装配层，
    不是重复计算 BEC/IFC。Gate C 中的 Gamma/IFC/acoustic 项应读作接口兼容性与
    独立证据审计；若用户已有仓库外 v1 装配证据，应直接接入并回归，不保留两套等价
    实现。

86. 新增 [`v2_v1_baseline_mapping.md`](v2_v1_baseline_mapping.md)，逐项标记 v1
    能力的继承、v2 适配、新增响应块和待核验后端；特别区分 v1 Gamma phonon/IFC
    与 v2 的应变—力耦合 `Gamma_{uη}`。后续 Gate C 只追踪 provenance 映射、
    单位/表示兼容性和真正缺失的后端/边界证据，不再把 v1 物理算法列为待重做任务。

87. 新增 `zstar.v2.legacy.adapt_v1_response_record`：将稳定的 v1
    `ResponseRecord` 显式适配为 v2 `ResponseDocument`，保留原始 schema、quantity
    convention、metadata 和 provenance。已知 BEC/介电量只使用无歧义边界默认值；
    未知量必须显式提供 `boundary_conditions` 与 `ion_relaxation`，避免 stress 符号
    或离子状态被猜测。适配真实 3D SiC v1 记录时发现 `force_constants` 的 v1
    重复轴名，现映射为唯一的 `atom_row/atom_column` 并保留原始轴语义；新增文件级
    迁移 API 和 5 项适配器测试，完整回归更新为 `513 passed`。

88. 新增 calculator-neutral `convert_piezoelectric_forms` 与
    `ElectromechanicalForms`：输入必须显式声明 proper、engineering-Voigt、
    \(e\) 的 C/m²、\(C^E\) 的压力单位和绝对/相对介电单位；在 SI 中构造
    \(d=e s^E\)、\(\epsilon^T=\epsilon^S+e s^E e^T\)、
    \(g=(\epsilon^T)^{-1}d\)、\(h=(\epsilon^S)^{-1}e\) 以及
    \(C^D=C^E+e^T(\epsilon^S)^{-1}e\)，并返回 reciprocal-identity 残差和条件数。
    raw Berry derivative、tensorial-Voigt 和非对称 \(C/\epsilon\) 均显式拒绝；31 项
    定向测试通过。这是热力学转换的研究 API，不代表任何后端已完成 \(d/g/h\) 实测
    交叉验证。

89. 复用共享目录中已经完成的 3D SiC VASP `LEPSILON` 结果做只读 BEC backend
    smoke：VASP stored `Z*(Si)=2.68952 e`、`Z*(C)=-2.68952 e`、
    `epsilon_inf=6.996889 I`，声学和严格为零；与 ABACUS v1 SiC 记录的 Si
    `2.7009406 e` 和 `6.867069 I` 相比，当前未匹配 PAW/ONCV、晶格、k 点、cutoff、
    `EDIFF` 设置下分别约 `0.423%` 和 `1.89%`。该证据只验证 VASP parser/轴转置和
    数量级，不提升 Gate C，也不涉及压电张量；详细来源和限制见
    [`v2_vasp_sic_bec_audit_20260913.md`](v2_vasp_sic_bec_audit_20260913.md)。

90. `ElectromechanicalForms.to_tensor_quantities` 将上述热力学转换结果物化为
    12 个带完整物理语义的 v2 `TensorQuantity`：分别标记 (e/d/g/h) 的电学与
    机械边界、(C^E/C^D)、(s^E/s^D)、\(\epsilon^S/\epsilon^T\) 和
    \(\beta^S/\beta^T\) 的单位、坐标轴、Voigt 约定、离子状态、周期轴、后端和
    provenance。它不创建顶层 `ResponseDocument`，避免猜测结构维度；调用者必须
   将其放入轴一致的文档。对应 schema 注释和测试已通过。

91. 新增 calculator-neutral `zstar.v2.vasp.parse_vasp_outcar_observations`：从
    VASP OUTCAR 读取实际 `TOTEN`、最后一个 `in kB` 六分量应力、全部
    `TOTAL-FORCE (eV/Angst)` 块和最后一个 direct-lattice block；原始应力明确标记
    为 `vasp-raw`，缺少力块时允许只做 stress/energy 审计，要求力块时给出失败。
    三项 synthetic parser/failure 测试通过。该模块不执行 VASP、不转换 stress sign，
    后续结果仍必须经 v2 的实际应变、单位和边界条件拟合。

92. 新增 `collect_vasp_strain_response`：将 VASP `reference + strain-*` 的
    POSCAR/OUTCAR 观测包装为与 ABACUS 同构的 `ResponseDocument`，提供实际序列化
    应变、原始应力、总能量、末力/首力块和 fixed-cell `CONTCAR` 内部位移；检查
    阶段状态、POSCAR/OUTCAR 晶胞一致性、原子顺序、reference 力阈值和 3D 边界。
    应力始终保留 `vasp-raw`，极化字段不补零，故只能进入弹性/内应变独立审计，
    不能被误当作 VASP 压电 workflow。clamped/relaxed/failure 三项 collector
    测试通过。

93. 用新 parser 对共享目录真实 3D SiC VASP `response/OUTCAR` 做只读回读：2 原子、
    1 个 force block、非正交晶胞成功解析；该 `ISIF=0` BEC-only 输出没有应力行，
    因而 parser 在显式 `require_stress=False` 下返回 `stress=None`，而 strain
    collector 仍拒绝无应力数据。该边界使 BEC 审计和弹性审计不会相互冒充，细节已
    补入 [`v2_vasp_sic_bec_audit_20260913.md`](v2_vasp_sic_bec_audit_20260913.md)。

## 证据状态

* v2 独立 worktree 的完整回归为 `528 passed, 1158 warnings`；新增首/末力块
  解析后，本次全量回归已重新执行（本地 editable install
  仅用于提供 distribution metadata，没有上传或发布）；加入终态失败契约后，v2 定向
  测试当前为 `120+ passed`（本轮新增 electromechanical 形式转换测试）。
  警告均为 spglib/phonopy 等现有依赖的弃用提示，没有失败。
* v2 独立测试（当前收集 120 项）覆盖 schema round-trip、单位、Voigt、稳定性、实际
  扰动差分、intertwiner、rank/residual、acoustic-SR、relaxed-ion 代数、cubic/P1/
  molecule symmetry 和 restart store。
* 进入 Gate C 前没有提交 ABACUS/VASP/QE 任务；随后按用户授权在 cu24–cu26 直接完成
  一组三阶段 ABACUS smoke，详细记录见 [`v2_abacus_smoke_20260912.md`](v2_abacus_smoke_20260912.md)。
  之后只读复用了已有六分量、多幅度输出；没有为 Gamma 审计重复提交大任务。

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
  work-conjugacy 的独立复核和独立后端核对。当前节点审计表明 VASP 是候选独立
  后端；已有 SiC BEC parser smoke，但尚未完成同结构输入、赝势、应变响应和
  quantitative collector 验证。

## 下一步

1. 评审并冻结 draft schema 的字段语义、单位注册表、边界条件和错误契约；
2. 补齐缺失 stage、金属、branch jump、backend failure、输入 hash 改变等 failure tests；
3. 对 tight reference 核对最终力、应力、空间群、能量和结构对应关系，并保留
   `1e-8`/`1e-10` SCF paired-audit 证据；
4. 将 clamped/relaxed 两组结果接入 `Z*`、`Lambda` 和体积/声学规范的显式代数，
   已完成合成数据、单位转换和 exact-geometry BEC 链路；下一步仍需独立 Born/IFC
   结果和 acoustic gauge 约定后才考虑冻结 relaxed-ion 公式；
5. 独立复核 ABACUS stress work-conjugacy、单位和能量曲率，并记录
   `scf_thr=1e-8`/`1e-10` 对最终力、离子步数和响应斜率的 paired audit；更高 SCF
   精度应视为降低力噪声、帮助满足 `force_thr_ev` 的收敛设置，同时仍须检查离子
   收敛标记、最大力、应力和多幅度稳定性，不能只比较总能量；
6. 在至少一个非 `P4mm` 低对称材料、一个独立后端和一个合适的二维边界条件案例
   上复现相同的 branch/rank/residual 检查，之后才进入正式压电/弹性 CLI 设计。
7. 先完成 VASP 输入/POTCAR provenance 与 calculator-neutral collector 的本地
   synthetic tests，再提交一项 40 MPI × 1 OpenMP reference smoke 和一对
   `+/-` 应变任务；不要把可执行文件探测结果直接升级为 Gate C 科学证据。
8. 使用 `ElectromechanicalForms` 对已经通过单位/边界审计的 proper `e`、
   \(C^E\) 和 \(\epsilon^S\) 做 schema 级派生量检查；先在合成矩阵验证
   reciprocal identities，再把同一流程接入 3D `P4mm` 审计。未完成独立后端
   定量核对前，不把派生 \(d/g/h\) 写成材料最终值。

## 2026-09-13 代数闭环增量

新增 `solve_internal_strain_response` 研究 API。它与既有
`internal_strain_response` 使用相同的 SVD 截断和最小范数解，但额外返回
`Phi @ Lambda + Gamma` 平衡残差、相对残差、刚性平移规范残差、奇异值和有效秩；
可用 `residual_tolerance` 明确拒绝含有未被 `Phi` 支持的非平移零模分量。这样
伪逆不再被误当作力平衡证明，且旧 API 保持只返回 `Lambda` 的兼容行为。

新增两项代数测试：平移兼容的 3D 两原子模型通过严格残差门；含额外零模且不可平衡
的 `Gamma` 被明确拒绝。定向响应代数测试结果为 `25 passed`。该改动只增强 v2
研究层，不改变 v1 入口或任何发布文件。

随后新增 `fit_energy_elastic_response` 研究函数和 `EnergyElasticFitResult`。该函数
按 `E=E0+Omega*sigma0·eta+1/2 Omega eta·C·eta` 对实际工程 Voigt 应变做独立二次
曲率拟合，显式处理 eV/Å³、J/m³ 与目标压力单位，返回参考应力、对称弹性矩阵、
设计秩、条件数和能量残差。新增满秩 3D 合成模型及单轴秩不足测试；响应代数定向
测试增至 `27 passed`，随后全量回归为 `517 passed, 1158 warnings`。该结果用于后续 ABACUS
stress-vs-energy work-conjugacy 对照，尚未作为材料常数发布。

## 2026-09-13 VASP 3D SiC 应变 smoke

在 `cu17` 上以 `40 MPI × 1 OpenMP` 完成 VASP reference、`eta_xx=+0.001`
和 `eta_xx=-0.001` 三个 3D SiC 阶段。首次手工只修改一条非正交晶格矢量时，
collector 反推出额外剪切并正确拒绝；随后按 `L' = L(I+eta)^T` 对三条晶格矢量
统一变换后重跑，几何、OUTCAR 晶格、力和应力均通过 collector 检查。raw VASP
应力导数为 `-5193.73 kbar`，显式转为 tension-positive 后为 `519.373 GPa`；
中心能量曲率为 `524.31 GPa`。这只是单方向 work-conjugacy/collector smoke，
不是完整 `C_ij` 或 Gate C 定量通过；详见
`docs/v2_vasp_sic_strain_smoke_20260913.md`。

随后加入非正交晶胞笛卡尔单轴应变回归测试，锁定 `L' = L(I+eta)^T` 约定，
避免只修改一条晶格矢量而产生伪剪切。全量回归现为 `529 passed, 1158 warnings`。

## 2026-09-13 3D SiC 完整中心应变审计

在 cu17/cu24/cu26 上完成六个工程 Voigt 应变分量的正负中心差分（12 个阶段，
每阶段 `40 MPI × 1 OpenMP`）。VASP collector 收集到 13 个完整观察；`F-43m`
空间群的弹性响应基降为 3 个自由度。显式采用 VASP raw stress 的
compression-positive 约定后，stress 拟合 rank 为 `6 -> 3/3`，残差
`0.0231 kbar`；同一 3 参数基上的 energy 拟合 rank `10 -> 3/3`，最大能量残差
`6.54e-8 eV`，两种曲率最大差 `4.67 GPa`。这通过了 3D 几何、对称基、collector
和 reduced energy fitter 的研究审计，但因后端设置未完全匹配，Gate C 仍未通过；
后续优先做同一后端的第二应变幅度和文献锚点映射，不把 ABINIT/QE 作为必做条件。
详见 `docs/v2_vasp_sic_fullstrain_20260913.md`。

随后修正了带空间群弹性基的 major-symmetry 数值交集：spglib 旋转的约 `1e-11`
舍入噪声不再把 cubic/F-43m 的三参数基错误压缩为一维；`fit_energy_elastic_response`
也支持同一 major-symmetric reduced basis，使仅采样独立应变方向时能正确报告
energy Hessian 的有效秩。新增 cubic stress/energy reduced-fit 回归；全量测试现为
`531 passed, 1164 warnings`。

## 2026-09-13 ABACUS 3D SiC 完整中心应变审计

在 cu25 以 `40 MPI × 1 OpenMP` 完成现有 v1 3D SiC primitive cell 的 ABACUS
六分量 `±0.005` clamped-ion 中心差分（reference + 12 stages）。collector 通过
输入哈希、实际序列化应变、力、应力和能量完整性检查；空间群在三档 `symprec`
下稳定为 `F-43m`/Hall 512，stress symmetry basis 为 3 维。压缩正应力转换后的
C 拟合秩为 3/3，最大残差 `0.4889 kbar`；能量曲率拟合秩为 3/3，最大能量残差
`6.14e-8 eV`，两者最大 C 分量差 `0.358 GPa`。所有阶段均达到 SCF 收敛并输出
`TOTAL-STRESS (KBAR)`；总耗时 448.56 s（约 4.984 core-hours）。这证明了
ABACUS 后端的 3D stress/energy 重建链闭合，但不是最终材料常数；仍需
`symmetry=0` 复核和第二应变幅度，Gate C 继续阻塞。若目标材料没有定义匹配的
文献/数据库锚点，再考虑 ABINIT/QE 独立高精度基准。
详见 [`v2_abacus_sic_fullstrain_20260913.md`](v2_abacus_sic_fullstrain_20260913.md)。

## 2026-09-13 ABACUS `symmetry=0` follow-up

为排除自动对称化影响，另准备了完全相同的 SiC `±0.005` 3D ensemble，仅将
`symmetry` 改为 0。reference 和前两个 stage 可完成，但 `strain-002+` 在
`DONE : INIT SCF` 后超过 10 分钟没有进入 `E_Harris`/SCF/stress 输出；确认工作目录
只属于本轮 scratch 后停止该进程组，部分日志保留为失败审计，不进入拟合。该结果说明
当前 ABACUS LCAO + 40 MPI 的 symmetry-off 组合存在运行阻塞，不能据此判定物理响应；
后续若需 symmetry-off 对照，应先做受控的小 rank smoke 或采用已验证的并行分解。

随后将阻塞的 `strain-002+` 输入复制为独立 diagnostic stage，以 `4 MPI × 1 OpenMP`
重跑；32.12 s 内得到 SCF 收敛、stress 和最终能量，证明问题来自 `symmetry=0` 的
40-rank 并行分解/扩展性，而不是应变序列化或输入文件损坏。该 diagnostic 输出仍不
进入正式 ensemble 或材料结果。

基于 ABACUS/cu25 与既有 VASP/cu17/cu24/cu26 的两个 3D SiC ensemble，补充了同一
`F-43m` 3 参数基下的 backend comparison：两者均为 rank 3/3，最大 stress residual
分别为 `0.4889` 与 `0.0231 kbar`，energy residual 均约 `6e-8 eV`，stress/energy
曲率差分别为 `0.358` 与 `3.45 GPa`；stress-derived 矩阵最大差 `32.73 GPa`
（5.80%）。进一步将两个 primitive-cell 张量旋转到 IEEE cubic 轴，得到
ABACUS `(363.40, 110.63, 252.79)` GPa、VASP `(383.49, 126.74, 264.27)` GPa，
并与文献实验锚点 `(390, 142, 256)` GPa 比较。由于 PAW-PBE 与 ONCV-LCAO 设置未
匹配，这仍是 collector/表示审计和文献锚定 benchmark，不是最终材料常数；不再为
形式上的“第三后端”启动 ABINIT/QE。只有后续材料缺少定义匹配的外部锚点时，才考虑
它们作为可选 oracle。详见 [`v2_sic_backend_comparison_20260913.md`](v2_sic_backend_comparison_20260913.md)。

随后在 cu25 对同一 3D SiC 输入完成第二个 `±0.0025` clamped-ion 中心应变
ensemble（仍为 `40 MPI × 1 OpenMP`、PBE、100 Ry、13×13×13、`scf_thr=1e-8`）。
13 个阶段全部通过 SCF/force/stress/energy 收集，`F-43m` stress basis rank 为
3/3；stress residual 为 `0.1214 kbar`，energy residual 为 `7.18e-8 eV`。旋转到
IEEE cubic 轴后，stress `(C11,C12,C44)=(363.24,110.57,252.73)` GPa，相对原
`±0.005` stress 结果最大变化 `0.16 GPa (0.054%)`；energy 结果最大变化
`0.54 GPa (0.20%)`。这完成了该 3D SiC 设置的幅度稳定性审计；仍属于单一泛函、
单一 ABACUS 后端的 clamped-ion 证据，不直接升级为普适材料常数。详见
[`v2_abacus_sic_fullstrain_20260913.md`](v2_abacus_sic_fullstrain_20260913.md)。

该第二幅度 ensemble 的阶段 wall time 总和为 `446.79 s`，按 40 MPI 计约
`4.964 core-hours`；单阶段范围 `21.74--46.33 s`，并已将计时来源写入审计文档。

新增 `zstar.v2.rotate_elastic_tensor`：在明确的 engineering-Voigt 约定下，将
6×6 stiffness 展开为 Cartesian 四阶张量，执行给定右手正交旋转，再压回同一 Voigt
约定。函数不自动对称化或投影晶体点群，保留坐标变换前后的残差语义；新增任意旋转
往返、非法旋转和 SiC primitive→IEEE cubic 回归测试。全量回归为 `534 passed,
1164 warnings`。
