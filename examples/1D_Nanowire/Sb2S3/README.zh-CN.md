# Sb2S3 nanowire：BEC 与 Gamma 点声子

采用 PBE+D3(BJ)，结构位于 xy 真空中心，z 为周期方向。统一位移框架从同一组
Phonopy 位移的极化和力响应得到 BEC 与 Gamma 点力常数；z 用 PYATB Berry 相，
x/y 用电荷密度偶极积分。

- `run/`：干净输入，附带赝势与轨道。
- `results/`：已有结果和紧凑原始证据；`source_evidence.json` 记录复制来源与哈希。
- `work/`：执行时建立，不覆盖原始结果。

```bash
bash run.sh --dry-run
bash run.sh --abacus-command "mpirun -np 40 abacus" --pyatb-command pyatb
```

需要预先安装 ZStar、PYATB 和外部 ABACUS。此入口默认只计算 BEC 与 Gamma 模式，
不重复 Raman 任务。[完整谱学案例](../../IR_Raman_Spectra/Nanowire_Sb2S3/README.zh-CN.md)
以及新旧框架对照保留在原谱学目录中。
