# 2D MoS2：IR 与 Raman

本单层 MoS2 案例采用 PBE+D3(BJ)。输入和匹配的 ABACUS 资产位于 `run/`；
`results/` 保存 IR/Raman 模式表和谱线，其中 Raman 响应采用二维片层约定。

```bash
bash run.sh --dry-run
ABACUS_COMMAND="mpirun -np 20 abacus" PYATB_COMMAND="pyatb" bash run.sh
```

面外 BEC 仍采用基于 cube 空间积分的二维方法。光谱响应应按片层响应报告，
不能解释为依赖真空厚度的三维体介电张量。

## 原生 VASP 交叉验证

`results/native_vasp/` 保存精简的原生 VASP/PBE-D3(BJ) 验证数据。四个光学
模式频率为 283.626、384.260、406.272 和 469.712 cm^-1，与采用相同泛函和
色散修正的文献结果相比，平均绝对偏差为 2.542 cm^-1。归档包含弛豫结构、
模式表、谱线和来源信息，但不分发受许可限制的 PAW 数据及大型重启文件。
