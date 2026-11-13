# Pinned upstream contraction data probe

This is a data-only numerical crosscheck, not a python-hvac package integration
or an adopted physical correlation. The full package and removed interp2d API
are not executed. No upstream code or coefficient grids are redistributed.

The inspected candidate is Tom Christiaens' MIT-licensed python-hvac,
commit94247560a667905bfbf67e45a58965a58254fce8, class ConvergingTransitionA9B:
https://github.com/TomLXXVI/python-hvac/tree/94247560a667905bfbf67e45a58965a58254fce8
The upstream source and full MIT notice must have exact recorded SHA256 values.
AST literal-array reading executes no upstream code. Existing SciPy1.18.1
RegularGridInterpolator and bounded one-dimensional area-factor interpolation
supply numerical evaluation. SciPy's official transition guide describes modern
regular-grid alternatives and orientation requirements:
https://docs.scipy.org/doc/scipy/tutorial/interpolate/interp_transition_guide.html

```
python -m bsa.contraction_candidate run FITTING_ANALYSIS PINNED_SOURCE MIT_NOTICE --out FRESH_STUDY
python -m bsa.contraction_candidate verify STUDY
```

Use explicit host BSA_PROJECT_ROOT. Each study replays the original source/native
fitting analysis, pins method/source/license bytes, and preserves all formal
records. No candidate values enter production paths. The actual taper length,
small downstream hydraulic diameter and area ratio are read from saved native
quantities. One equal positive wall angle is a screening choice only; equality
within1e-6 degrees is a software bound, not a published construction tolerance
or proof of original correlation applicability. Unequal/one-plane wall angles
are not collapsed to their maximum; all axes must be bounded without clamping.
Small downstream reference velocity pressure remains explicit. Existing inlet
reference coefficients are not directly compared as if their references matched.

Four tests across candidate interpolation and pressure ledger pass with durable
receipt verification. Synthetic checks establish axis orientation, bilinear
arithmetic, area factor, out-of-bounds/NaN rejection and unequal-angle exclusion.
Protected source data, actual point values and runtime records remain private.
No full package, source transcription, physical applicability, fitting friction,
interaction or fan duty acceptance is claimed. CLI exit2 retains that scope.

Actual source/native generation and saved-probe reconstruction both pass across
all 31 native transitions: 4 bounded numerical crosschecks, 4 outside-axis
queries and 23 excluded unequal/one-plane cases. All four bounded candidate
signed contributions differ numerically from the existing conditional source
values. This is not a demonstrated source error or a selection/acceptance
criterion: original correlation applicability, station and friction scope must
be resolved before either method can establish full pressure. The original
formal fitting record remains byte-identical; no new formal loss is added.
