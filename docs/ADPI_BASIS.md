# ADPI basis before criterion evaluation

The current terminal tool calculates bounded catalogue throw and T/L only. Its
ADPI_verified flag remains false. Numerical interpolation does not select an
applicable comfort criterion.

Review exact edition, product-to-category correspondence, cooling/heating mode,
room sensible-load meaning and range, ceiling/installation conditions, and the
geometric interpretation of L before evaluating an acceptance range. Distinguish
manufacturer chart conditions from generic handbook conditions and coursework
instructions; record conflicts rather than silently combining them. A coil allowance
multiplied by SHF does not establish the room sensible load.

Official source comparison on 2026-11-10 found different classification/load schemes
in [ASHRAE 2015 Tables 3/4](https://handbook.ashrae.org/Handbooks/A15/SI/a15_ch57/a15_ch57_si.aspx)
and [ASHRAE 2023 Tables 5/6A](https://handbook.ashrae.org/Handbooks/A23/SI/A23_Ch58/a23_ch58_si.aspx).
The latter distinguishes louvered blade details. Do not map a manufacturer's older
pattern terminology to a newer category without product evidence.

The actual private source snapshots and hashes are retained in the ADPI edition
review. No table has been automatically chosen for the coursework. Original course
method, actual room load and product/geometry correspondence remain unresolved.
Keep the reported allocation-cell lengths labelled diagnostic proxies; do not alter
geometry or invent loads merely to place ratios inside a preferred interval.
