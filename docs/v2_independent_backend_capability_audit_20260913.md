# v2 独立后端能力审计（2026-09-13）

## 目的

Gate C 要求至少一个独立计算后端的交叉验证。本记录只审计共享节点上的
可执行程序和运行时，不把“程序存在”误写成物理结果，也不提交作业、不改变
任何节点状态。

## 审计范围和方法

通过 235 逐节点执行只读检查：

```text
cu17 cu24 cu25 cu26
```

检查项目为 hostname、ABACUS、VASP、Phonopy、Python，以及 `pw.x`（Quantum
ESPRESSO）和 `cp2k.popt` 是否在 `PATH` 中。检查命令没有启动 MPI、SCF 或
后处理任务；因此本审计的 CPU core-hours 为 0。

## 结果

| 节点 | ABACUS | VASP | Phonopy | Python | QE `pw.x` | CP2K `cp2k.popt` |
|---|---|---|---|---|---|---|
| cu17 | 3.10.0-LTS | 6.3.2 | `/home/zhuxd/Software/anaconda3/envs/icu/bin/phonopy` | 3.10.9 | 未在 PATH | 未在 PATH |
| cu24 | 3.10.0-LTS | 6.3.2 | `/home/zhuxd/Software/anaconda3/envs/icu/bin/phonopy` | 3.10.9 | 未在 PATH | 未在 PATH |
| cu25 | 3.10.0-LTS | 6.3.2 | `/home/zhuxd/Software/anaconda3/envs/icu/bin/phonopy` | 3.10.9 | 未在 PATH | 未在 PATH |
| cu26 | 3.10.0-LTS | 6.3.2 | `/home/zhuxd/Software/anaconda3/envs/icu/bin/phonopy` | 3.10.9 | 未在 PATH | 未在 PATH |

确认到的绝对路径为：

```text
ABACUS: /home/zhuxd/Software/abacus/INSTALL/3.10.0-LTS/bin/abacus
VASP:   /home/zhuxd/Software/src/vasp/6.3.2/bin/vasp_std
```

所有节点均可见上述 ABACUS/VASP 可执行文件和同一 `icu` Python 运行时。QE
和 CP2K 没有通过当前 `PATH` 发现；在没有进一步模块/环境核查前，不假设它们
可用。

## 科学含义和限制

VASP 可执行文件的存在只说明潜在的独立后端路径可用，尚未证明：

1. POTCAR 的来源、版本和元素映射与 ABACUS 案例具有可比性；
2. 现有 v2 collector 能稳定读取 VASP 的能量、力、应力、结构和极化相关输出；
3. VASP 与 ABACUS 使用相同的晶胞、坐标、应变/位移序列和边界条件；
4. VASP 结果在 `scf_thr`、离子力阈值、应力符号和单位上满足交叉验证要求。

因此本记录不提升 Gate C，也不产生材料响应常数。下一步应先在本地完成
calculator-neutral VASP reference collector 和输入/POTCAR provenance 检查，
再在一个已冻结的 P4mm 小胞上做一项 40 MPI × 1 OpenMP 的 reference smoke，
随后做一个明确的 `+/-` 应变 pair。只有该 pair 的应变、力/应力、极化和单位
映射全部通过审计，才可扩展到完整张量。

## 与数值精度门控的关系

本项目当前将 `scf_thr=1e-8` 作为生产基线，并把 `force_thr`、最大位移、应力
和离子收敛标志分开记录。更严格的 SCF 阈值会减小电子自洽引起的力噪声，使离子
优化在给定 `force_thr` 下更容易达到目标；它不会替代离子力阈值，也不能单独证明
响应斜率或结构已经收敛。VASP 交叉验证必须使用成对输入，分别记录 SCF 阈值、
离子阈值、最终最大力、应力和差分斜率，避免把单次能量差异当作收敛证据。

## 可复现信息

- 跳转主机：235（用户授权的共享目录环境）。
- 节点：cu17、cu24、cu25、cu26。
- 检查类型：只读 executable/runtime discovery。
- MPI/OMP：未启动任务；资源消耗 0 core-hours。
- 结论日期：2026-09-13。
