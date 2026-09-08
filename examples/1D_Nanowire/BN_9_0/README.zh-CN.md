# BN(9,0) nanotube：BEC 与 Gamma 点声子

采用 PBE，结构位于 xy 真空中心，z 为周期方向。统一位移框架从同一组
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
不重复 Raman 任务。[完整谱学案例](../../IR_Raman_Spectra/Nanotube_BN_9_0/README.zh-CN.md)
以及新旧框架对照保留在原谱学目录中。

## 独立 VASP BEC 对照

已附上[完成的对照和原始证据](results/vasp_validation/README.md)：轴向相差
0.3%，径向仍相差约 0.08 e，保留该差异，不通过归一化或投影将其隐藏。

使用相同的已优化结构、PBE、PAW-PBE-54 B/N 赝势、500 eV 截断能和
1x1x12 Gamma 中心网格。先做参考态 SCF，再用 `LEPSILON` 执行含局域场
的原生 DFPT；不重复结构优化，也不额外计算声子。

```bash
bash run_vasp.sh --dry-run
export VASP_POTENTIAL_DIR=/path/to/POT_GGA_PAW_PBE_54
export VASP_COMMAND="mpirun -np 40 vasp_std"
bash run_vasp.sh
```

赝势目录需要有 `B/POTCAR` 和 `N/POTCAR`，仓库不分发 VASP 授权赝势。
新计算写入 `work-vasp/`，完成的阶段可断点续算。准备清单保留一维物理维度，
但 VASP 求解器仍采用含真空的三维周期超胞，不施加孤立管横向镜像修正。
对比时使用同一几何下的局域径向、切向和轴向 BEC；不要将含真空的介电张量
直接解释为纳米线的本征介电常数。
