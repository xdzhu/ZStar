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

## 证据状态

* v2 独立 worktree 的完整回归为 `474 passed, 1122 warnings`（本地 editable install
  仅用于提供 distribution metadata，没有上传或发布）；v2 定向测试当前为 `81 passed`。
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
* **Gate C：**六分量/多幅度 force-stress/energy 数据收集、单次 PYATB 三方向极化
  collector 和内部位移拟合接口已接通；真实 relaxed-ion runner 已启动但尚未完成，
  完整 Gate C 仍未满足，尚需 stress sign/单位和能量曲率收敛确认、允许子空间完备的
  非零 e、无并发污染的 relaxed-ion Λ 数据和独立后端核对。

## 下一步

1. 评审并冻结 draft schema 的字段语义、单位注册表、边界条件和错误契约；
2. 补齐缺失 stage、金属、branch jump、backend failure、输入 hash 改变等 failure tests；
3. 完成当前 P4mm relaxed-ion 六分量、多幅度任务，逐 stage 检查 ionic convergence、
   `STRU_ION_D` 和无并发污染，并记录输入哈希、SCF、wall time 和日志；
4. 在同一批最终结构上运行每几何一次的 PYATB 三方向极化，执行 branch matching，
   拟合内部位移 Λ 和 relaxed-ion `e`，并单独审计 stress 符号/单位；
5. 在 `P4mm` 允许子空间完备的 branch-matched 极化数据上验证 draft e 拟合，再以
   独立后端或高精度参考结果核对完整 C 矩阵和 proper e 张量，之后才进入正式
   压电/弹性 CLI 设计。
