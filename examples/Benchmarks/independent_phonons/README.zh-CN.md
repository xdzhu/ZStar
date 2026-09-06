# Separate/Unified 独立声子基准

这里保存新增的 30 个独立力计算 SCF，不是复用 BEC 的力后重新命名。
`results/` 保留输入、SCF 日志、力、实测计时、验证与哈希；`run/` 提供便携运行器。
赝势与轨道取自相邻材料案例的 `run/`，运行时普通复制到新工作目录。

```bash
# 只验证档案，不运行 DFT、不修改 results
bash run.sh

# 从输入重新计算一个材料的独立声子任务
bash run.sh --calculate t_HfO2 --command "mpirun -np 1 abacus" --omp 40
```

力计算从原子电荷开始，关闭不需要的矩阵和电荷导出。原 Cartesian 参考态提供
参考力，因此不另外计一个参考 SCF。Separate 的 BEC 计时本身含有力输出，
这部分开销没有被人为扣除，不能将本表称为最优 force-free BEC 实现的基准。
成功任务的墙钟秒数乘 40 核即核时；失败的资源文件定位尝试保留记录但不混入成功核时。

在仓库根目录执行 `python tools/shared_response/build_separate_efficiency.py`
重新生成效率 JSON/CSV。原 Cartesian 共同响应控制仍独立保留，勿与这里的力混用。
