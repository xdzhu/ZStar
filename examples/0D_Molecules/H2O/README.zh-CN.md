# 水分子（H2O）HSE APT 记录

本目录保存精简的 HSE 分子 APT 验证记录。完整的 ABACUS 位移
临时目录和 cube 文件有意不放入公开案例库。可运行的 CP2K H2O 工作流位于
`examples/backend_examples/cp2k_bec/H2O`；ABACUS/PYATB 的输入几何也保存在
随案例提供的 `structure.vasp` 中。

无需计算器即可检查记录：

```bash
python -m json.tool results/hse_apt_summary.json
```
