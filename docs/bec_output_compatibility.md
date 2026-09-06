# BEC outputs and historical archives

New calculations write `BEC.dat` (full projected tensors), `BEC.raw.dat`
(full raw tensors), `BEC.rep.dat` and `BEC.rep.raw.dat` (representative atoms).
Reports use `BEC_symmetry.json` and `BEC_symmetry.txt`. Tensor axes and stored
precision are unchanged. Command names such as `zstar bec` remain lowercase.

Readers accept earlier lowercase names and `Z-BORN-symm.out` / `Z-BORN-all.out`
without modifying the archive. An explicit input path wins. Automatic discovery
rejects different-content aliases rather than selecting silently; provide the
intended `--born PATH` or move the unrelated result to a separate directory.
Identical canonical/legacy copies are accepted, including on case-sensitive Linux.

Cases keep `run/` inputs separate from `results/`. Native compressed evidence
is immutable; canonical copies retain the original numerical contents.

# BEC 输出与旧档案兼容

新计算采用大写 `BEC` 前缀，后缀保持小写；`BEC.dat` 为全原胞投影张量，
`BEC.raw.dat` 为原始张量，`BEC.rep.*` 为代表原子的张量。报告文件为
`BEC_symmetry.json` 和 `BEC_symmetry.txt`，命令行、张量轴序与精度不变。

旧小写及 `Z-BORN-*` 文件仍可读取，不会回写历史档案。显式指定路径优先；
自动发现遇到内容不同的新旧文件会报错并要求选择 `--born PATH`。
相同内容的规范副本与历史文件可以共存。新工作写入独立的 `work/`。
