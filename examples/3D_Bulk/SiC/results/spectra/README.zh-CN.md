# Unified IR 与 Raman 保留结果

这些文件与 `../shared/` 中的 BEC 和 Gamma 点力常数来自同一套两个对称性适配
3C-SiC 位移。谱学阶段没有新增 ABACUS SCF；PYATB 复用已保留的 Hamiltonian、
overlap 和 position matrices，计算 Raman 所需的静态介电导数。

三个光学模式简并于 772.645 cm^-1，具有相同的 IR 强度和归一化 Raman 活性，
符合立方对称性。归档包含数据表、响应张量以及 PNG、PDF 和 SVG 谱图，不包含
体积较大的矩阵副本与临时 PYATB 工作目录。

在案例根目录执行 `bash run.sh --with-spectra`，可在 `work/` 中重新完成全部计算。
