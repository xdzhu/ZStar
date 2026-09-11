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

## 证据状态

* v1 与现有工作区测试：`420 passed`（包含当前未提交的 v1/声子谱改动以及 v2 draft tests）。
* v2 独立测试覆盖 schema round-trip、单位、Voigt、稳定性、实际扰动差分、
  intertwiner、rank/residual、relaxed-ion 代数、cubic/P1/molecule symmetry 和 restart store。
* 进入 Gate C 前没有提交 ABACUS/VASP/QE 任务；随后按用户授权在 cu24–cu26 直接完成
  一组三阶段 ABACUS smoke，详细记录见 [`v2_abacus_smoke_20260912.md`](v2_abacus_smoke_20260912.md)。

## 资源状态

PBS 只读检查显示 `cu24`、`cu25`、`cu26` 均为 `job-exclusive`，分别被当前用户的
40 核长时任务占用，节点负载接近空闲但不能视为可随意复用。未在这些作业中注入新计算，
避免破坏既有作业的资源/计费边界。

## 当前门控

* **Gate A：**已满足。
* **Gate B：**进行中；需要 schema/failure contract 评审和完整 v2 synthetic failure matrix。
* **Gate C：**前置 smoke 已通过；完整 Gate C 仍未满足，尚需多分量/多幅度、极化收集、
  relaxed-ion 和独立后端核对。

## 下一步

1. 评审并冻结 draft schema 的字段语义、单位注册表、边界条件和错误契约；
2. 补齐缺失 stage、金属、branch jump、backend failure、输入 hash 改变等 failure tests；
3. 检查 `cu24–cu26` 既有作业是否结束或由用户明确释放一个作业环境；
4. 完成 cubic BaTiO3 六分量、多幅度 clamped-ion 任务，记录输入哈希、SCF、wall time 和日志；
5. 先解析 ABACUS stress 符号/单位，再开始 relaxed-ion 应变任务和独立后端对照。
