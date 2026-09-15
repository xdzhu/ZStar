# 2026-09 qNEP compatibility decision record

`metrics.json` reports all completed 100k qNEP trials against the same fixed
167-frame cubic-BaTiO3 dataset.  The cubic-only model had the best E/F values.
Adding other phases slightly improved sparse-BEC fitting but worsened cubic
energy and force errors.  The `C+T` output has a documented MPI concurrent
tail-write artifact and is diagnostic only.

Result: the data interface is retained; qNEP model development, qNEP phonons,
NAC comparison, and all finite-temperature claims are paused.
