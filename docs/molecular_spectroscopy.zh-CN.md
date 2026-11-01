# 分子 IR 与 Raman 光谱

ABACUS 推荐使用 [Unified 位移工作流](unified_spectroscopy.zh-CN.md)，复用同一套
SCF 完成 APT、Gamma 模式、IR 与 Raman。分子位置矩阵 APT 路线目前为实验性，
仅适用于中性、非磁性闭壳层且只采样 Γ 点的分子。APT 求和通过不能替代独立
精度和真空收敛性验证。

## 适用范围与物理约定

将分子放入具有足够真空的超胞，以消除周期镜像相互作用。ZStar 使用单位为
`angstrom * sqrt(amu)` 的质量加权 Gamma 点简正坐标 `Q`。分子 IR 使用 APT
得到的偶极矩导数，而不是周期 Berry 极化分支。分子 Raman 使用
`dalpha/dQ = V/(4*pi) * d(epsilon_r)/dQ`，将稀释超胞介电导数转换为分子极化率导数。

展示谱按最大强度归一化。CSV 保留偶极矩和极化率导数，但归一化曲线不被宣称为气相
积分截面。

## 完整计算链

先在足够大的固定真空超胞中优化分子，并在响应计算时释放全部原子。然后准备、
运行并检查共同位移集合：

```bash
zstar bec pre --stru STRU --dim 0
zstar bec run
zstar bec post
zstar phonon inspect --dim 0 --qpoints qpoints.yaml --json gamma_review.json
zstar spectra pre --response . --root spectra
zstar spectra run --root spectra
zstar spectra post --root spectra
```

原有简正模式 Raman 单独工作流仍可用，但旧的 Berry 分子 IR 路线已禁用。没有
兼容 APT 来源记录的历史分子 IR 应视为待核验。复用旧 SCF 结果前请阅读
[诊断说明](workflow_diagnostics.zh-CN.md)。

## 输出文件

| 路径 | 内容 |
| --- | --- |
| `BEC.raw.dat`、`BEC.dat` | 投影前后原子极化张量。 |
| `.zstar/molecular_apt_diagnostic.json` | 原始 APT 求和与投影诊断。 |
| `.zstar/molecular_apt_validation.json` | 方法、检查以及来源和结果指纹。 |
| `spectra/ir/ir_modes.csv` | 频率、偶极矩导数与 IR 活性。 |
| `spectra/raman/raman_modes.csv` | 频率、Placzek 活性与 Raman 张量。 |
| `spectra/spectra_result.json` | 响应方法、模式筛选及谱线设置。 |

## 必须完成的收敛检查

- 优化到力和分子几何稳定；
- 确认振动子空间没有显著虚频；
- 增大真空，直到换算后的 `dmu/dQ` 和 `dalpha/dQ` 稳定；
- 检查通常为 `0.01-0.03 angstrom * sqrt(amu)` 的简正坐标位移在线性响应区；
- 检查 LCAO 基组、截断能和 PYATB 响应网格收敛；
- 保持足够严格的分子对称性，使禁戒活性和简并模式劈裂接近数值零。

## 历史 Benchmark

以下频率和选择定则对照来自历史计算；其中旧 Berry 分子 IR 强度尚未由实验性的
位置矩阵路线验证，不能作为当前分子 APT 的精度证明。

甲烷是非中心对称主 benchmark。ABACUS/PBE 谐频率为 1287.93、1516.62、
2968.29 和 3088.05 cm-1，与 NIST 基频误差为 1.13%-2.29%。计算振动表示为
`A1 + E + 2 T2`：四组基频均具有 Raman 活性，只有两组 `T2` 具有 IR 活性。
参考频率与归属来自
[NIST Chemistry WebBook](https://webbook.nist.gov/cgi/cbook.cgi?ID=C74828&Mask=887)；
独立理论对照见
[PCCP 2016, DOI 10.1039/C6CP03463B](https://doi.org/10.1039/C6CP03463B)。

二氧化碳是中心对称互补 benchmark。已在专用计算节点上使用 20 核直接完成全流程，采用
ABACUS 3.10.0 LTS、PBE、100 Ry 截断能、20 Angstrom 超胞且不使用经验频率缩放。
接受的线性结构 C-O 键长为 1.17042 Angstrom，最大残余力为 0.00623 eV/Angstrom，
参考结构带隙为 8.618 eV。

| 基频 | 对称性 | ZStar/ABACUS (cm-1) | NIST (cm-1) | 误差 | IR | Raman |
| --- | --- | ---: | ---: | ---: | --- | --- |
| 二重简并弯曲 | Eu | 635.64 | 667 | -4.70% | 活性 | 禁戒 |
| 对称伸缩 | A1g | 1331.99 | 1333 | -0.08% | 禁戒 | 活性 |
| 非对称伸缩 | A2u | 2381.04 | 2349 | +1.36% | 活性 | 禁戒 |

禁戒 Raman 活性低于最强谱线的 `2.5e-15`，禁戒 IR 活性为数值零，因此计算同时
恢复了弯曲简并度和中心对称互斥定则。对称伸缩实验 Raman 区域受 Fermi 共振影响，
谐性计算应与未扰动基频比较。实验数据来自
[NIST CCCBDB](https://cccbdb.nist.gov/exp2x.asp?casno=124389&charge=0)。

CH4 与 CO2 分别检验非中心对称活性和严格的中心对称互斥定则。下图把频率一致性、
逐模式误差、允许活性和计算光谱整合为一条可追溯的验证证据链。

![分子 IR 与 Raman 验证总览](paper_figures/molecular_validation_overview.png)
