# Molecule CH4：IR 与 Raman

默认 `bash run.sh` 使用 Unified 框架；`bash run.sh --post-only` 从已校验的
归档响应离线重建 IR/Raman，输出至 `work-unified-post/`，无需 DFT。
`bash run.sh --method mode --work mode_control` 保留独立模式位移对照。

`run/` 已对齐优化后的 Unified 基准结构，PBE、`scf_thr=1e-8`，
`gamma_only=0` 用于 PYATB 矩阵导出。脚本从给定的优化结构开始，不再次优化。
旧快速示例输入保存在 `legacy/before_acceptance_20260906/`，不作为当前基准结构。

本甲烷案例使用大周期盒和 `dim=0`，提供 ABACUS + PYATB 分子 IR/Raman 快速
上手流程。这里的响应是分子响应，不是体材料介电函数。

```bash
bash run.sh --dry-run
ABACUS_COMMAND="mpirun -np 20 abacus" PYATB_COMMAND="pyatb" bash run.sh
```

干净的 PBE 输入、赝势和轨道位于 `run/`。模式表与谱线位于 `results/`，
生成的声子和响应中间阶段写入 `work/`。
