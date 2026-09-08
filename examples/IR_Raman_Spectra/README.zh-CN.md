# IR 与 Raman 光谱案例

这里单独整理光谱计算案例，与极化/BEC 案例分开。每个材料都包含干净的
`run/` 输入目录、已有计算结果 `results/`、中英文说明和根目录 `run.sh`。

| 案例 | 体系 | 计算器 | 已保存结果 |
|---|---|---|---|
| `Bulk_HfO2` | 四方 HfO2 | ABACUS + PYATB | IR 与 Raman |
| `2D_MoS2` | 单层 MoS2 | ABACUS + PYATB | IR 与 Raman |
| `Molecule_CH4` | 甲烷 | ABACUS + PYATB | IR 与 Raman |
| `Nanowire_GaAs` | 周期性 GaAs 纳米线 | ABACUS + PYATB | IR 与 Raman |
| `Nanotube_BN_6_0` | 无需钝化的 BN(6,0)，PBE | ABACUS + PYATB | BEC、Gamma 声子、完整光学模 IR/Raman |
| `Nanotube_BN_9_0` | 无需钝化的 BN(9,0)，PBE | ABACUS + PYATB | BEC、Gamma 声子、完整光学模 IR/Raman |
| `Nanowire_Sb2S3` | 孤立 Sb2S3 链，PBE-D3(BJ) | ABACUS + PYATB | BEC、Gamma 声子、完整光学模 IR/Raman |

真实计算前先执行 `bash run.sh --dry-run`。脚本从 `run/` 读取输入，在同级
`work/` 写入中间结果，不修改已经保存的 `results/`。

这里的结果是科学与接口验证所需的精简记录；用户仍需针对泛函、轨道、k 点、
位移和展宽参数自行进行收敛性检查。

新增三个案例均包含原始结构优化输入及带文件哈希的紧凑证据包，默认从优化后、
横向居中的结构复算。与文献的比较明确区分泛函、电子响应和去极化近似；
计算流程完成不等于 Raman 相对强度已经通过定量文献验证。
