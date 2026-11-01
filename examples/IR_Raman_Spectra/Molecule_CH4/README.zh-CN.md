# Molecule CH4：IR 与 Raman

默认 `bash run.sh` 使用 Unified 框架。分子位置矩阵 APT 路线目前为实验性；
请阅读[验证记录与限制](../../Benchmarks/Molecular_APT_Safety/README.md)。
归档 IR 采用旧分子响应，缺少匹配的 APT 凭据，仅作历史记录，不作为当前已验证
的 IR 结果；此归档的 `--post-only` 已禁用。历史 Raman 谱也有独立的响应和强度限制。

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
