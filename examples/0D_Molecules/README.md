# Molecular APT examples / 分子原子极化张量

| Case | Purpose / 用途 |
|---|---|
| [H2O](H2O/) | Polar molecule, PBE and HSE APT evidence / 极性分子及 HSE 对照 |
| [CH4](CH4/) | Nonpolar molecule, PBE and HSE APT evidence / 非极性分子及 HSE 对照 |
| [CO2](CO2/) | Linear-molecule workflow / 线性分子 |
| [H2O_unified](H2O_unified/) | Matched unified/Cartesian PBE benchmark / PBE 效率对照 |
| [CH4_unified](CH4_unified/) | Matched unified/Cartesian PBE benchmark / PBE 效率对照 |

Use each case's README and `run.sh`; `run/` contains clean inputs and `results/`
contains retained outputs. HSE APTs use ABACUS charge-density cube integration,
not PYATB evaluation of a semilocal Hamiltonian. HSE timings do not enter the PBE
unified-framework benchmark.
HSE 张量通过 ABACUS cube 积分得到，不借用半局域 PYATB 哈密顿量；HSE 机时不计入 PBE 效率对照。
