# 点群 IR 与 Raman 活性规则核验记录

## 核验范围

ZStar 依据 32 个晶体学点群对区中心振动模式进行分类。本记录说明对
`zstar/group_modesDB.py` 中活性数据库以及 ZStar 论文表 D.1 所做的独立核验。

该表给出的是对称性允许的不可约表示，而不是某个具体结构中各类模式的数目。
具体模式及其重数仍需由结构的机械表示分解得到。

## 权威依据

主要依据为
[Bilbao Crystallographic Server 的 POINT 服务](https://www.cryst.ehu.eus/rep/point.html)。
该服务给出了全部 32 个晶体学点群的特征标表、表示分解以及 IR/Raman 选择定则：

- M. I. Aroyo, A. Kirov, C. Capillas, J. M. Perez-Mato, and
  H. Wondratschek, *Bilbao Crystallographic Server. II. Representations of
  crystallographic point groups and space groups*, Acta Crystallographica A
  **62**, 115-128 (2006),
  [doi:10.1107/S0108767305040286](https://doi.org/10.1107/S0108767305040286)。

光谱学解释同时与以下资料交叉核对：

- D. L. Rousseau, R. P. Bauman, and S. P. S. Porto, *Normal mode
  determination in crystals*, Journal of Raman Spectroscopy **10**, 253-290
  (1981),
  [doi:10.1002/jrs.1250100152](https://doi.org/10.1002/jrs.1250100152)。
- *International Tables for Crystallography*, Vol. D, Sec. 2.3.3，
  [First-order scattering by phonons](https://onlinelibrary.wiley.com/iucr/itc/Db/ch2o3v0001/sec2o3o3/)。

## ZStar 采用的选择定则

电偶极 IR 活性要求模式的不可约表示包含在极性矢量表示 `V` 中。ZStar 当前实现的
静态非共振 Raman 处理中，模式表示必须包含在对称平方 `[V^2]` 中，对应对称极化率
导数。

这一范围不包括可能出现反对称 Raman 张量分量的共振或磁性 Raman 过程。

## 核验方法与结果

2026-09-08，逐页提取 Bilbao POINT 中全部点群的 `V` 与 `[V^2]` 分解，并独立地与
ZStar 数据库比较；随后再将论文表 D.1 与代码数据库逐行比较。

| 晶系 | 核验点群数 | Bilbao 与数据库一致 | 论文与数据库一致 |
| --- | ---: | ---: | ---: |
| 三斜 | 2 | 2/2 | 2/2 |
| 单斜 | 3 | 3/3 | 3/3 |
| 正交 | 3 | 3/3 | 3/3 |
| 四方 | 7 | 7/7 | 7/7 |
| 三方 | 5 | 5/5 | 5/5 |
| 六方 | 7 | 7/7 | 7/7 |
| 立方 | 5 | 5/5 | 5/5 |
| **合计** | **32** | **32/32** | **32/32** |

全部 IR 与 Raman 活性表示均未发现不一致。

## 符号约定

- Bilbao 对晶体学点群 `-3` 使用 `C3i`，而 `S6` 是等价的 Schoenflies 名称；同时
  面向晶体学和分子光谱学读者时写作 `C3i (S6)`。
- Bilbao 分别列出 `1E` 与 `2E` 等互为复共轭的表示。ZStar 将共轭对合并为振动
  光谱学中常用的实二维简并表示 `E`。
- 对于中心对称点群，电偶极 IR 活性表示具有奇宇称，一阶对称 Raman 活性表示具有
  偶宇称。宇称只是必要条件，并不意味着所有 `u` 或 `g` 表示都具有相应活性。

## 运行时保护

当所选对称性容差下的模式流形无法被可靠解析时，Phonopy 可能输出空的
`ir_label`。ZStar 将此类非声学模式标记为 `Unresolved`，不再推断其为静默模式。
只有已被识别、且同时不属于 IR 与 Raman 活性集合的不可约表示才标记为 `Silent`。

离线的权威来源快照可通过以下测试复核：

```bash
pytest tests/test_point_group_activity.py
```

该测试覆盖全部 32 个点群、真正静默表示的保留，以及空标签保护。权威网址和 DOI
也作为元数据记录在 `zstar.group_modesDB` 中。
