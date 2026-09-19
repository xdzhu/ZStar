# VASP 原生响应：3C-SiC

本例采用 PBE，先优化两原子原胞，再验证 VASP 原生电场 DFPT、Γ 点声子
DFPT、原生应变有限差分，以及基于介电响应导数的 Raman 混合路线。

`run/` 仅包含干净输入；验证完成后，紧凑结果放入 `results/`。大文件保留
在不提交的 `.work/` 中。VASP 和具有许可限制的 POTCAR 不随例子分发。
运行脚本按 POSCAR 元素顺序，从 `$VASP_PSEUDO_ROOT/PBE/Si/POTCAR` 和
`$VASP_PSEUDO_ROOT/PBE/C/POTCAR` 组装计算需要的 POTCAR。

安装 `zstar[vasp]` 并加载 VASP 环境。在 hf 上执行 `sbatch run_hf.slurm`，
申请 64 MPI × 1 OMP，不指定节点、不排它。脚本保留完成阶段，支持继续运行。
逐步命令见同目录英文 README。
可通过 `MPI_TASKS` 和 `VASP_COMMAND` 覆盖并行数与启动命令。

保留的原生响应与 Raman 三重简并模检查已通过，IR 和频率介电后处理无需
额外 DFT 调用。原生 DFPT 的内部应变平衡警告仍保留；d 来自通过质量检查的
原生应变有限差分路线。结果细节与 `validation.json` 见 `results/`。

`--phonons` 请求原生 Γ 点声子；`--elastic` 请求完整 Bulk 弹性响应，其离子
和应变扰动采用 VASP 原生有限差分，电场响应仍采用 DFPT。后处理分别记录
电子/声子介电、钳制/离子/总压电贡献、弹性张量与可用的 d 系数。
未完成数值收敛及文献核对前，本例不被表述为材料精度 benchmark。
