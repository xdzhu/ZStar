# 三维压电响应

ZStar 支持绝缘三维晶体的 proper 压电应力系数 `e`、含离子弛豫的弹性系数
`C` 以及应变系数 `d = e C^-1`。工程 Voigt 顺序为
`(xx, yy, zz, 2yz, 2xz, 2xy)`；`e`、`C`、`d` 的单位分别为 C/m2、GPa、
pm/V（等价于 pC/N）。

## ABACUS + PYATB 有限应变路线

公开 Python API 生成一个参考结构及六个 Voigt 方向的 `+-0.5%` 中心应变，
收集应力、力、弛豫后的内部坐标和分支匹配后的极化，并采用实际写出的应变向量
完成拟合。响应记录保留 proper 修正、点群残差、声学平移、弹性稳定性及
`e = d C` 闭合诊断。

```python
from zstar.piezoelectric import prepare_abacus_strain_ensemble

prepare_abacus_strain_ensemble(
    "work",
    structure="run/STRU",
    input_template="run/INPUT",
    kpt_template="run/KPT",
    pp_dir="run",
    orb_dir="run",
    amplitude=0.005,
    ion_relaxation="relaxed-ion",
)
```

仓库案例可直接使用 `tools/prepare_piezoelectric_case.py`、
`tools/run_piezoelectric_ensemble.sh` 和 `tools/collect_piezoelectric_case.py`。
计算器执行与响应分析保持分离，队列 header、module 与资源申请仍由计算环境控制。

## VASP 原生路线

对于 LDA/GGA，ZStar 保持 VASP 原生电子和离子响应的定义。独立的命令族为：

```bash
zstar piezo pre --calculator vasp --input-dir input --root response
zstar piezo run --root response
zstar piezo post --root response
```

该命令获取含离子弛豫的 `e`、三维弹性矩阵并推导 `d`。旧的
`zstar bec ... --piezo [--elastic]` 仍作为兼容接口保留。VASP 授权的
`POTCAR` 不随仓库分发。求解器与对称性细节见
[VASP 原生响应](vasp_native_response.zh-CN.md)。

## 可复现案例

[纤锌矿 AlN](../examples/Piezoelectric_Response/AlN)与
[纤锌矿 ZnO](../examples/Piezoelectric_Response/ZnO)提供干净 ABACUS 输入及资产、
ABACUS + PYATB 与原生 VASP 的完整张量、文献参照和可自检的 `run.sh`。
两者均采用 PBE，并保留全部张量分量，而不是只列 `d33`。

当前实现面向三维本征响应。含真空的 slab 和 wire 需要线/面机电响应定义及明确的
电学边界条件；ZStar 不会把真空超胞导数静默解释成三维压电系数。
