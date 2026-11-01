# 工作流日志与故障定位

ABACUS + PYATB 的 BEC 和 Raman 工作流实时打印阶段信息，并将外部程序的
stdout、stderr 同时输出到终端和阶段日志。生成的 Shell、Slurm、PBS 驱动脚本
通过 `tee` 保留到调度日志和 `.zstar/workflow.log`。升级后，可重新执行
`zstar bec job --system slurm`，使已有脚本获得无缓冲环境和失败定位提示。

```text
[time] [disp-002] [stage-start] [START] index=3; total=7; path=...
[time] [disp-002] [ABACUS SCF] [START] cwd=...; log=...; command=...
... ABACUS 的标准输出与错误输出 ...
[time] [disp-002] [ABACUS SCF] [PASS] exit=0; elapsed=42.1s; log=...
[time] [disp-002] [INSULATION] [PASS] SCF-mesh gap=1.234000 eV; ...
[time] [disp-002] [PYATB polarization/dielectric] [START] ...
```

## 查看最后执行位置

```bash
zstar bec stat
zstar bec stat --json
tail -n 80 .zstar/workflow.log
```

状态表的 `last_step` 显示最后保存的步骤。失败或运行中记录会给出更新时间和
日志路径；JSON 输出便于高通量脚本收集状态。`running` 表示最后保存的状态，
若任务被强制终止或超时，应结合 Slurm/PBS 状态判断，进程未必有机会写入最终错误。
已记录完成但必要文件缺失的阶段会显示为 `stale`；状态查询不会改写历史记录。
只有至少两个已完成位移提供了耗时样本时，才显示串行剩余墙钟时间的粗略估计；
该估计不包含排队时间。

Slurm 用户可选用 `sacct` 查询一个作业的实际分配核数和运行时间：

```bash
zstar bec stat --job-id 123456 --budget-core-hours 100
zstar bec stat --job-id 123456 --budget-core-hours 100 --json
```

核时按**单个作业**的分配 CPU 数乘以墙钟时间计算，并非 CPU 实际利用率、
计费账单或多作业总额。预算比较仅用于监测提醒，不会取消作业或实施硬上限；
应另行设置调度器的时间与资源限制。若 `sacct` 不可用或尚未记录该作业，程序
会明确报错，不会编造机时。

| 文件 | 用途 |
| --- | --- |
| `.zstar/logs/<stage>.log` | 命令、工作目录、外部程序输出、退出码及耗时 |
| `.zstar/progress.log` | 简洁的阶段事件、错误和续算提示 |
| `.zstar/workflow.jsonl` | 结构化事件，便于批量分析 |
| `.zstar/stages/*.json` | 各组件状态、最后步骤、错误和日志路径 |
| `.zstar/symmetry.json` | 实际对称容差、旋转正交性及原子映射检查 |
| `<stage>/zstar_insulation.json` | 参考态或位移结构的绝缘性判据 |
| `.zstar/gamma_modes.json` | Γ 点本征模式分类及谐近似响应是否允许计算 |
| `.zstar/force_constants_diagnostics.json` | 原始及投影后力常数的残差和刚体—内部耦合 |
| `.zstar/molecular_apt_diagnostic.json` | 分子原始 APT 和电荷求和诊断 |
| `.zstar/molecular_apt_validation.json` | 实验性分子 APT 的来源及结果指纹 |

修正原因后重复 `zstar bec run` 即可续算。已完成输出会重新检查并复用，以
`SKIP` 标明。Unified Raman 的私有 `static/<stage>/run.log` 保存 PYATB 输出，
捕获的错误还写入 `failed.json`。若用户在自定义计算命令中主动写入
`abacus > other.log`，程序输出仍会进入该文件，无法同时出现在 stdout 中。

## 如何读检查结果

**绝缘性。** 参考态同时报告 PYATB 路径/MP 诊断和 ABACUS SCF 网格的能隙、
判定阈值、分数占据数和占据能带数。位移结构检查其 SCF 网格与参考占据子空间的
一致性。`PASS`、`FAIL`、`SKIP` 和 `DRY-RUN` 分开显示；试运行不能证明体系绝缘。
孤立分子改为检查实际 Γ 点的 SCF 占据和能隙，不使用晶体能带路径。

**对称性。** 准备、运行及收集时报告实际 `--symmprec`、操作数量、笛卡尔旋转
的最大 `|R^T R-I|` 以及原子映射误差。不自动改变容差，也不静默正交化被拒绝的
操作。失败时给出实测误差，提示使用更严格的 `--symmprec` 或修整结构。较小容差
可能降低对称性、增加位移数量，应在新目录重新 `pre`，避免混用不同位移集合。

**Γ 点稳定性。** `zstar bec post` 在输出 BEC 和力常数的同时保存本征模式报告。
分类依据是质量加权本征矢与整体平移子空间的重叠；分子还检查刚体转动。
默认 20 cm^-1 的虚频容差用于小幅平移漂移，不用于忽略小的光学虚频。
刚体重叠的经验分类阈值为 0.99；简并子空间内单个模式的投影依赖所选基。
一维体系的轴向转动只标为候选，负频时不会自动放行。混合模、非平移负频模式
及过大的负频平移漂移都需要检查。力常数报告还给出互易性、平移残差和
刚体—内部耦合；内部子块为正不等于整个 Hessian 或全布里渊区稳定。

以下命令只检查已有结果，不自动新增计算：

```bash
zstar phonon inspect --dim 1 --qpoints qpoints.yaml \
  --force-constants FORCE_CONSTANTS.raw \
  --projected-force-constants FORCE_CONSTANTS --json gamma_review.json
zstar phonon compare --dim 1 --reference abacus/qpoints.yaml \
  --candidate vasp/qpoints.yaml --json mode_comparison.json
zstar phonon translation-check --calculator abacus --dim 1 \
  --reference reference_scf --translated translated_scf --json translation_check.json
```

`compare` 要求两端晶胞、原子顺序、质量和几何一致，允许整体平移；近简并模式
按本征矢子空间重叠匹配。几何和简并容差应根据问题明确选择。
`translation-check` 读取已有的 ABACUS 或 VASP 静态计算，不生成也不运行
计算；它报告打印的逐原子力差和可用的输入指纹，但不能推断计算器是否已扣除净力漂移。
这些检查不证明全波矢稳定性，也不能单凭振型重叠验证谱线强度。

**分子 APT。** 实验性的 ABACUS Unified 零维路径使用 Γ 点闭壳层位置矩阵，
投影前检查原始 APT 求和，并记录来源哈希和修正幅度。求和通过只是必要的
一致性检查，不是独立精度或真空收敛性的证明。没有匹配验收记录的旧零维
Berry `BEC.dat` 不会被 Unified IR 静默复用；如原始矩阵可用，可保留 SCF 数据
重新收集。目前位置矩阵路线不支持带电、自旋极化或非 Γ 点体系。

## 已有 BEC，但没有介电结果目录

`bec run` 和 `bec post` 不直接计算谐近似下的总介电响应。完成后还需运行：

```bash
zstar dielectric static
# 或：
zstar dielectric freq
```

`BORN` 中的电子介电背景也不等于总静态介电张量。介电命令失败时，即使尚未创建
输出目录，仍会保存 `.zstar/stages/dielectric-static.json` 或 `dielectric-freq.json`。
在同一工作目录中执行的介电步骤，也会出现在 `zstar bec stat` 中。按错误信息查看
Γ 点报告，或执行：

```bash
zstar phonon inspect --qpoints qpoints.yaml --json gamma_review.json
```

`BLOCKED` 会明确说明为何拒绝稳定相的谐近似介电响应，同时保留已算出的 BEC。
`--allow-imaginary` 仅用于主动分析不稳定相中的指定稳定模式；它不能修复结构
不稳定性，也不能将这种结果解释为经过验证的平衡态静态介电常数。
