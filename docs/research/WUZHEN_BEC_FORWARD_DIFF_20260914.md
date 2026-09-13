# Wuzhen BEC forward-difference correction (2026-09-14)

The first 40-atom supercell BEC attempt used ZStar's `auto` finite-difference
policy.  Because both rattled candidates are effectively P1, that policy
created a central-difference pair for every Cartesian degree of freedom:

\[
2(3N)=2(3\times40)=240
\]

stages per frame, or 480 stages for the two-frame pair.  This was unnecessary
for the CPC compatibility demonstration.  The partial central-difference
directories were retained remotely under
`bec_supercell_pair/abandoned_central_partial_20260914` and the jobs were
cancelled; no output was treated as a BEC result.

The replacement batch explicitly invokes
`zstar bec pre --method forward --ensemble phonopy`.  It produces one positive
displacement per Cartesian degree of freedom, 120 stages per 40-atom frame and
240 stages in total.  The generated manifests were checked before submission:

```text
frame-supp_003: method=forward, displacement_scheme=phonopy, stages=120
frame-supp_005: method=forward, displacement_scheme=phonopy, stages=120
```

The two completed `0.no-move` reference calculations are reused.  The Wuzhen
Slurm driver runs 32 MPI ranks with one OpenMP thread per rank, excludes
`j10r2n12`, keeps ABACUS on automatic `kspacing=0.1`, and uses `pyatb_input
--polar --mp 0.08`.  During the first retry, ABACUS was found to read
`init_chg=file` from `OUT.SCF` even though the POLAR suffix writes response
files to `OUT.POLAR`; the driver now copies the reference charge cube and
restart into both locations.  This avoids a false early exit before PyATB.

The first replacement arrays are Slurm jobs `44250977`--`44250981`, covering
stage-list indices 0--199 in five 40-task arrays.  The final 40 stages are
submitted only after one array releases its accounting quota, because Wuzhen
enforces a 200-element group submit limit.

One slow-node exception was handled without duplicating the full campaign:
array element `44250980_139` (`supp_005/disp-020`) was cancelled after about
40 minutes because `j11r2n24` had a load average near 69 and an unrelated CFX
job occupied the node; its ABACUS log had not advanced beyond SCF
initialization.  The partial directory is retained under
`abandoned_slow_j11r2n24_20260914/`.  The pristine stage inputs were rebuilt
and the same stage index was resubmitted as `44253559_139` with both
`j10r2n12` and `j11r2n24` excluded.  No other array element was cancelled.

The first retry also exposed two separate issues: `44253559_139` hit an
ABACUS/MPI segmentation fault on `j10r3n39`, and the rebuilt retry initially
omitted the six stage-local UPF/orbital symlinks.  Those outputs were archived,
the original symlinks restored, and `44253862_139` was started on the
previously successful `j10r3n19` node.  A missing-output audit found nine
earlier elements (60, 61, 63, 64, 66, 67, 68, 89, 90) killed on the
oversubscribed node; they were submitted once as array `44253895` with the
same node exclusions.  These retries replace only incomplete stages and do
not increase the 240-stage target.

After `44253895` finished, the stage-level audit reduced the remaining gap to
`disp-060`, `disp-063`, and `disp-066` in `supp_003`, plus `disp-089` and
`disp-090` in `supp_005`.  Their zero-based stage-list indices are 59, 62, 65,
208, and 209; they were submitted exactly once as array `44254274` with the
same quarantine list.  This index audit prevents completed stages from being
recomputed.

## Cost-controlled execution record

The final stage-level audit at 2026-09-14 01:41 CST found all 240
`pyatb/Out/Polarization/polarization.dat` files (120 per parent frame), with
no missing output and an empty Wuzhen queue.  The five tasks in `44254274`
were exact replacements for zero-based stage-list indices 59, 62, 65, 208,
and 209; no completed stage was recomputed.  The old central-difference
attempt and all failed/oversubscribed-node directories are archived and
excluded from labels.

The completed outputs were compacted to a 373-KB transport archive containing
only `STRU`, `INPUT-scf`, optional original `KPT`, response manifests,
polarization files, and final energy/force snippets.  For the two reference
`0.no-move` stages, the compact archive records the already-existing parent
DFT energy/force labels because the BEC reference log contains no force block;
no second SCF was launched and no zero force was inserted.  Local collection
now reports 2 BEC-labelled parent frames and 242 force-only family rows.
