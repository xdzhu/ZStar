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

## 证据状态

* 本阶段全量回归为 `447 passed, 1252 warnings`（包含当前未提交的 v1/声子谱改动以及
  v2 draft tests）；其中 Berry 定向测试为 `11 passed`。警告均为现有依赖的弃用提示，
  没有失败。
* v2 独立测试覆盖 schema round-trip、单位、Voigt、稳定性、实际扰动差分、
  intertwiner、rank/residual、relaxed-ion 代数、cubic/P1/molecule symmetry 和 restart store。
* 进入 Gate C 前没有提交 ABACUS/VASP/QE 任务；随后按用户授权在 cu24–cu26 直接完成
  一组三阶段 ABACUS smoke，详细记录见 [`v2_abacus_smoke_20260912.md`](v2_abacus_smoke_20260912.md)。

## 资源状态

PBS 检查显示 `cu24`、`cu25`、`cu26` 均为 `job-exclusive`，分别由当前用户的
40 核占位作业持有。用户已明确授权在这些节点上直接运行 v2；后续仍须每个节点不
超过 40 核、先做 smoke、记录 MPI/OpenMP/wall time，并避免修改占位作业本身。

## 当前门控

* **Gate A：**已满足。
* **Gate B：**进行中；需要 schema/failure contract 评审和完整 v2 synthetic failure matrix。
* **Gate C：**六分量/多幅度 force-stress/energy 数据收集已通过；完整 Gate C 仍未满足，
  尚需 stress sign/单位和能量曲率收敛确认、极化收集、relaxed-ion 和独立后端核对。

## 下一步

1. 评审并冻结 draft schema 的字段语义、单位注册表、边界条件和错误契约；
2. 补齐缺失 stage、金属、branch jump、backend failure、输入 hash 改变等 failure tests；
3. 完成 cubic BaTiO3 六分量、多幅度 clamped-ion 任务，记录输入哈希、SCF、wall time 和日志；
4. 通过 ABACUS 输出/文档和独立小算例确认 stress 符号/单位；随后增加带应变的
   Berry 阶段，再开始 relaxed-ion 应变任务；
5. 在 branch-matched 极化数据上验证 draft e 拟合，再以独立后端或高精度参考结果
   核对完整 C 矩阵和 proper e 张量，之后才进入正式压电/弹性 CLI 设计。
