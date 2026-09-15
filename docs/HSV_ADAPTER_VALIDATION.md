# Octave-compatible HSV: Gate 4 resolution and Gate 3 revalidation

Both HSV directions now use a small vectorized float64 NumPy adapter,
`shine_color/_hsv_octave.py`, behind the existing color API. It reproduces
the nominated Octave arithmetic on all recorded probes. No epsilon, rounding
adjustment, per-color exception, or native RGB clipping was introduced.
Working V and the terminal `to_uint8` function are unchanged. Lab is unchanged.

## Specification and implementation sequence

The independently expressed [behavioral specification](OCTAVE_HSV_SPEC.md)
was written after inspecting the installed Octave 11.1.0 core conversions and
probing modulo behavior around zero and one. Its SHA-256 is bound into the
candidate manifest. The independent inputs and reference-selected boundaries
were exported before implementing or comparing the adapter. The implementation
uses max-priority selection and piecewise weights derived from the specification;
it does not reproduce the source program's control structure.

For uint8 RGB, normalize by binary64 division by 255. Let M=max(R,G,B),
m=min(R,G,B), d=M-m. V=M; gray gives H=S=0; otherwise S=1-m/M.
Select the maximum with R before G before B on ties. Hue is:

| Maximum | Ordered expression |
| --- | --- |
| R | ((1/6)*(G-B))/d |
| G | 1/3 + ((1/6)*(B-R))/d |
| B | 2/3 + ((1/6)*(R-G))/d |

Subtract, multiply by the binary64 constant, divide by d, then add the
sector offset. Add 1 only to negative hue. The saturation expression and
operation order matter at binary64 precision.

For inverse HSV, shift and wrap hue independently for R/G/B:
u=mod([H-2/3,H,H-1/3],1). The corresponding weights are 6u for
0<=u<1/6, 1 for 1/6<=u<1/2, 4-6u for 1/2<=u<2/3, and 0 otherwise.
Compute base=V*(1-S), chroma=S*V, and RGB=base+chroma*weight, with separate
float64 operations. There is no floor(6H) sector index or p/q/t computation
in the reference arithmetic. H=1 wraps like H=0; S=0 reconstructs V;
exact sector boundaries use the stated intervals. Native output is unclipped,
including probes with finite S/V outside [0,1]. Terminal conversion remains
the separate shared saturating cast of RGB*255. Nonfinite HSV, huge arbitrary
hues, and Octave's complete dtype API are outside this acceptance scope.

## Frozen reference corpus

The new `tests/reference/fixtures/hsv_adapter` corpus has **97,990 records**
across four strata. Repeated RGB/V pairs and repeated regression occurrences
are intentionally retained; these counts are records, not unique colors.

| Stratum | Records | Selection |
| --- | ---: | --- |
| Forward | 76,337 | 65,536 random RGB, 256 grays, 4,096 dark cube, 4,913 coarse cube, 1,536 near-grays |
| Processed-V boundaries | 9,363 | Entire eligible subset of independent Octave search |
| Native inverse | 11,832 | 3,640 sector/saturation/value probes + 8,192 mixed HSV |
| Gate 4 occurrences | 458 | Every previously recorded scalar boundary occurrence, reconstructed as a triplet |

The independent search evaluates all 131,072 PCG64(2026091409) RGB colors at
each working V in {0,1,2,31,64,127,128,254,255}: **1,179,648 RGB/V pairs**.
Octave alone selects every pair for which any RGB*255 component is within
the predeclared inclusive **1e-10** distance of floor(component)+0.5.
The 9,363 selected pairs include exact ties and both sides of boundaries.
The threshold is a corpus-selection rule, never an output tolerance or
runtime adjustment. No Python disagreement was used to select these inputs.

Inverse probes span H=k/6, k=-3..9, with offsets -1e-12, -eps, 0, eps,
1e-12; S={0,1e-12,1/255,.5,254/255,1,-.1,1.1}; and
V={0,1/255,.5,254/255,1,-.1,1.1}. They exercise wrapping, exact sector
endpoints, gray, low/high saturation and value, and unclipped output.
Seeds 2026091408 and 2026091410 generate the independent forward and mixed
inverse samples. Full construction and counts are in the frozen specification.

The 458 old scalar occurrences retain their original group, configuration,
source, pixel/channel identity, original RGB, reference terminal value and
processed V. Reconstructing all three components of these occurrence records
counts 480 old scikit-image mismatches because the same triplet can appear
for multiple originally failing components. That is not a revision of the
original 458 distinct scalar-output findings in the pipeline matrix.

## Stage-separated evidence and adapter decision

The following native maxima and terminal disagreement counts concern the
independent 9,363-record boundary stratum. The reference baseline always uses
Octave H/S with identical processed V. The cross-reference exporter evaluates
Octave inverse on the exact serialized scikit-image H/S, not an approximation.

| Comparison | Maximum native difference | Unequal terminal components |
| --- | ---: | ---: |
| scikit-image inverse, identical Octave HSV | 9.43689570931383e-16 | 1,522 |
| Octave inverse, scikit-image H/S | 1.27675647831893e-15 | 2,201 |
| scikit-image forward + inverse | 1.2212453270876722e-15 | 3,050 |
| Both inverses on identical scikit-image H/S | 9.43689570931383e-16 | 1,289 |
| Adapter inverse, identical Octave HSV | 0 | 0 |
| Adapter forward + inverse | 0 | 0 |

The 76,337-record forward stratum's old scikit-image H/S/V maxima are
[1.1657341758564144e-15, 2.6020852139652106e-16, 1.1102230246251565e-16].
The adapter's maxima are **[0,0,0]**. Working-V mismatches are zero for both
implementations there. Adapter H/S is also exactly equal on the boundary and
captured strata, and inverse native/terminal differences are zero on all four
strata. The inverse stratum includes out-of-range hue/S/V probes; the old
scikit-image maximum of 1.2100000000000002 there reflects additional wrap/range
semantics, not just the roundoff mechanism of valid pipeline HSV.

Keeping scikit-image forward with an Octave inverse leaves 2,201 unequal
terminal components in the independent boundary stratum. Both directions
therefore need replacement. No hybrid path was retained.

## Gate 3 and pipeline revalidation

All **102,193 Gate 3 forward HSV records** now match exactly in H/S/V.
Unequal working-V values: **0**. Native inverse and terminal outputs are
exact for original, working-channel roundtrip, and processed-V variants,
both with identical reference inputs and through the adapter forward path.
Measured native maxima are zero throughout these HSV comparisons.
The original Gate 3 tests and their previous bounds remain unchanged;
six additional tests require exact native HSV parity on this entire corpus.
All 318 pre-pipeline tests pass, including every Lab test.

On the unchanged 480-run pipeline corpus, all **160 HSV configurations**
have exact working V, native reconstructed RGB and terminal uint8 RGB:
**zero unequal terminal scalar values**, including all previously failing
458 occurrences. The other two spectral cases use the separate approved
degeneracy policy; no HSV adapter change is involved in those cases.

## Dependencies, tests and provenance

Production imports no scikit-image or SciPy. NumPy is the only runtime
dependency. The normal `dev` extra remains pytest/SciPy for fixtures and tests.
The optional `reference` extra retains scikit-image==0.25.2 and SciPy solely
to reproduce historical converter comparisons and external reference tools.
`reference/check_numpy_runtime.py` exercises all 24 mode/colorspace pairs
with two iterations while rejecting SciPy and scikit-image imports.

The full suite reports **1,412 passed in 29.07 seconds**, zero failures,
skips or xfails. Sixteen new HSV tests verify exact native and terminal
results, source identities, frozen selection/specification, wrapping,
unclipped output, and Gate 3 revalidation. Existing tests were not weakened.

Environment: Python 3.12.10, NumPy 2.1.3, SciPy 1.15.1, diagnostic
scikit-image 0.25.2; Windows 11 x86-64. Reference: Octave 11.1.0 with image
2.18.2, estimate planner and three FFTW threads. The HSV functions are Octave
core functions. Manifests include source paths/hashes, specification/input
hashes and generation provenance; measurements include all MAT-file hashes.

For existing committed reference arrays:

```text
python -m reference.measure_hsv_adapter
python -m reference.pipeline.measure_completion
python -m pytest -q -p no:cacheprovider
```

The comparison command needs the optional `reference` extra. Pytest does not
need scikit-image or a live Octave installation. To reproduce new HSV reference
data, first preserve the existing corpus, run `reference.build_hsv_corpus`,
then Octave `export_hsv_corpus(destination)`; prepare the old converter's
cross-inputs with `reference.measure_hsv_adapter --prepare`, then Octave
`export_hsv_cross(destination)`, and finally measure. These tools do not
regenerate the existing randomized pipeline references.

Claims are bounded to this recorded corpus/runtime. MATLAB numerical parity
has not been established and remains a future secondary validation target.
Gate 5, masks, file I/O, CLI, video and SSIM optimization were not begun.
No remote, push or publication occurred.
