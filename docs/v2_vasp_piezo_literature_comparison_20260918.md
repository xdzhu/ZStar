# VASP 文献压电对照（2026-09-18）

完整数值表、泛函层级、proper/improper 换算、PTO 独立 d33 对比、原始文献与复现条件见
[VASP 压电文献调研报告](../outputs/v2_vasp_piezo_literature_20260918.md)及
[来源核查记录](../outputs/v2_vasp_piezo_literature_20260918.provenance.md)。

优先结论：PTO 的 VASP/PBEsol `e33=4.95 C/m²`、`d33=208 pm/V` 已读原文与表图；
当前 ABACUS/PBEsol 为 `4.164278`、`128.748224`，幅值差异 `-15.87%`、`-38.10%`。
AlN 同泛函 VASP/PBEsol 三个 e 有参考；GaN VASP/PBE e33 与当前值相差 `-3.35%`，
但这是跨泛函次级对照，不能取代同泛函参考。ZnO/PZT 的严格同结构参考仍有缺口。
