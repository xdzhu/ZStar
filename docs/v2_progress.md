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

## 证据状态

* 本阶段全量回归为 `470 passed, 1318 warnings`（包含当前工作树的 v1/声子谱改动以及
    v2 draft tests）；v2 极化/ABACUS collector 定向测试为 `35 passed`。警告均为现有依赖的
  弃用提示，
  没有失败。
* v2 独立测试覆盖 schema round-trip、单位、Voigt、稳定性、实际扰动差分、
  intertwiner、rank/residual、relaxed-ion 代数、cubic/P1/molecule symmetry 和 restart store。
* 进入 Gate C 前没有提交 ABACUS/VASP/QE 任务；随后按用户授权在 cu24–cu26 直接完成
  一组三阶段 ABACUS smoke，详细记录见 [`v2_abacus_smoke_20260912.md`](v2_abacus_smoke_20260912.md)。

## 资源状态

PBS 检查显示 `cu24`、`cu25`、`cu26` 均为 `job-exclusive`，分别由当前用户的
40 核占位作业持有。用户已明确授权在这些节点上直接运行 v2；算法 smoke 已完成，
从下一批正式第一性原理任务起固定使用每任务 `40 MPI x 1 OpenMP`，记录节点、
MPI/OpenMP、wall time 和可复现实命令，并避免修改占位作业本身。

## 当前门控

* **Gate A：**已满足。
* **Gate B：**进行中；需要 schema/failure contract 评审和完整 v2 synthetic failure matrix。
* **Gate C：**六分量/多幅度 force-stress/energy 数据收集已通过；极化 collector 和
  非中心对称 smoke 已接通，但完整 Gate C 仍未满足，尚需 stress sign/单位和能量
  曲率收敛确认、允许子空间完备的非零 e、relaxed-ion 和独立后端核对。

## 下一步

1. 评审并冻结 draft schema 的字段语义、单位注册表、边界条件和错误契约；
2. 补齐缺失 stage、金属、branch jump、backend failure、输入 hash 改变等 failure tests；
3. 完成 cubic BaTiO3 六分量、多幅度 clamped-ion 任务，记录输入哈希、SCF、wall time 和日志；
4. 通过 ABACUS 输出/文档和独立小算例确认 stress 符号/单位；随后增加带应变的
   Berry 阶段，再开始 relaxed-ion 应变任务；
5. 在 `P4mm` 允许子空间完备的 branch-matched 极化数据上验证 draft e 拟合，再以
   独立后端或高精度参考结果核对完整 C 矩阵和 proper e 张量，之后才进入正式
   压电/弹性 CLI 设计。
