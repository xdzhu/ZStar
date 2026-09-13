# 3D SiC VASP BEC 独立后端审计（2026-09-13）

## 目的和证据等级

本记录复用共享目录中已经完成的 VASP DFPT 结果，审计 v1 BEC 记录到 v2
calculator-neutral 量的轴约定、原子顺序、声学和以及数量级。没有提交新作业，
也没有把这组结果写成压电或弹性常数。由于 ABACUS 与 VASP 的晶格、k 点、截断能
和电子收敛设置不完全匹配，本记录是 **独立 parser/backend smoke**，不是 Gate C
所需的定量跨后端收敛证明。

## 输入和来源

| 项目 | ABACUS v1 参考 | VASP 已有参考 |
|---|---|---|
| 体系 | 3C-SiC，2 原子原胞，Si/C 顺序 | 3C-SiC，2 原子原胞，Si/C 顺序 |
| 晶格 | 由 `examples/3D_Bulk/SiC/results/shared/zstar_response.json` 读取；第一晶格长度约 3.10688 Å | `/home/zhuxd/vasp/zstar_vasp_validation_20260825/sic_dfpt/reference/POSCAR`；第一晶格长度约 3.09675 Å |
| 泛函/势 | PBE，SG15 ONCV | PAW-PBE，Si 05Jan2001、C 08Apr2002 |
| k 点 | Gamma-centered 13×13×13 | Monkhorst-Pack 15×15×15，K-spacing 0.030 |
| 截断 | 100 Ry | 520 eV |
| 电子阈值 | `scf_thr=1e-8` | `EDIFF=1e-6` |
| VASP 方法 | — | `LEPSILON=.TRUE.`，20 cores 历史结果 |

VASP 来源文件为：

```text
/home/zhuxd/vasp/zstar_vasp_validation_20260825/sic_dfpt/response/OUTCAR
/home/zhuxd/vasp/zstar_vasp_validation_20260825/sic_dfpt/vasp_bec.json
```

VASP 的 `vasp_bec.json` 已由现有 `zstar.vasp_bec.collect_vasp_bec` 生成；该
collector 将 VASP OUTCAR 的“行=电场/极化、列=力/位移”张量转置为 ZStar
约定的“行=位移、列=极化”。本次只读检查未改变这些文件。

## 数值结果

VASP DFPT（`sic_dfpt`）输出：

```text
epsilon_infinity = diag(6.996889, 6.996889, 6.996889)
Z*(Si) = diag( 2.68952,  2.68952,  2.68952)
Z*(C)  = diag(-2.68952, -2.68952, -2.68952)
sum_i Z*_i = 0 exactly in stored precision
```

对应的 ABACUS 记录为：

```text
epsilon_infinity ≈ diag(6.867069, 6.867069, 6.867069)
Z*(Si) ≈ diag( 2.7009406336,  2.7009406336,  2.7009406336)
Z*(C)  ≈ diag(-2.7009406336,-2.7009406336,-2.7009406336)
```

在未匹配计算设置的前提下，Si 对角 BEC 差为 `-0.0114206 e`（约 `-0.423%`），
电子介电常数差为 `+0.12982`（约 `+1.89%`）。非对角分量在两套记录中均为数值
零量级，且 VASP 声学和严格为零。

## 结论和后续动作

1. VASP 输出轴转置、Si/C 原子顺序、BEC 单位和声学和检查路径可作为 v2 独立
   后端适配的初步证据。
2. 这不是压电交叉验证：VASP 这组结果只含 BEC/介电，没有同一参考结构的应变
   极化、应变力、应力和内部弛豫 ensemble。
3. 这也不是精度 benchmark：VASP 的 PAW、晶格、`EDIFF=1e-6` 和 ABACUS 的
   ONCV、晶格、`scf_thr=1e-8` 不一致；不能把上述百分比当作后端误差上限。
4. Gate C 的下一项应是冻结同一个 3D `P4mm` 或非极性 SiC 结构、匹配离子顺序和
   物理设置，先完成一项 40 MPI × 1 OpenMP VASP reference smoke，再完成成对
   `+/-` 应变或内部位移，并把 OUTCAR/vasprun.xml 映射进 v2 `ResponseDocument`。
   在此之前不提升 VASP capability，也不写入正式材料压电值。

