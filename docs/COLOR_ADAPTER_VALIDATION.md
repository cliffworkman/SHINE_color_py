# Gate 3: Octave-compatible color conversion

The accepted color layer uses scikit-image 0.25.2 for HSV and a project-owned
NumPy adapter for Octave-compatible Lab. The adapter resolves the previously
documented working-L discrepancy without changing casting, adding epsilon
adjustments, or patching individual colors. NumPy remains the reference FFT
backend. **Gate 3 is complete: the full suite reports 318 passed in 12.67
seconds, with zero failures, skips or xfails.** Gate 4 has not begun.

The independently written [Lab behavioral specification](OCTAVE_LAB_SPEC.md)
and all expanded Octave outputs existed before adapter implementation. Its
hash is recorded in the candidate manifest. The old scikit-image Lab results
are preserved in [COLOR_VALIDATION.md](COLOR_VALIDATION.md) and the original
color fixture directory; they have not been overwritten or reclassified.

## Conventions implemented

Forward uint8 sRGB is normalized by 255 in float64, inverse-companded using
breakpoint 0.04045, and converted with Octave's recorded RGB-to-XYZ matrix.
XYZ is normalized by D65 [0.95047,1,1.08883]. Lab uses the rational breakpoint
(6/29)^3 and slope (29/3)^3/116, with the linear branch at equality. Native
L*,a*,b* are preserved in float64. Working L uses to_uint8(L*2.55).

Inverse Lab recovers XYZ with the corresponding piecewise inverse, including
negative auxiliary coordinates, then uses the specified rounded XYZ-to-RGB
matrix. It does not invert the forward matrix numerically. Forward companding
uses breakpoint 0.0031308; negative linear values remain on the linear branch.
Native output is **unclipped**, including values outside [0,1]. Only explicit
terminal to_uint8(rgb*255) saturates. The full matrices, equations, branch
equalities and scope exclusions are in the specification.

The implementation is derived from the mathematical specification and empirical
conventions. It is not a mechanical translation of Octave source. There are
no copied source comments, color-science framework, OpenCV dependency, special
handling for [0,1,0], or changes to numeric.py. No public license decision is
made. MATLAB numerical parity remains unestablished.

## Expanded reference corpus

| Forward class | Pixels / records | Selection |
| --- | ---: | --- |
| Original palette, structured image, gray ramp | 383 | Existing exact inputs retained |
| Dark lattice | 35,937 | Every R,G,B in 0..32 |
| Full-range sample | 65,536 | PCG64 seed 2026091401 |
| Cast-boundary records | 337 | Octave-derived, both sides of half integers |
| Total forward records | 102,193 | No exclusions based on Python results |

Boundary selection used 298,337 candidates: a separate 262,144-sample full-range
PCG64 draw (seed 2026091402), the dark cube and 256 grays. For each k=0..254,
Octave selected the nearest color strictly on each side of k+0.5 within 0.001
in scaled L. Ties in distance use first candidate order. There are 165 below
and 172 above records, no exact-half ties, and 173 missing k/side slots. Missing
sides were recorded, not filled using a changed selection rule. The nearest
distance is 1.067538129118084e-6 and farthest 0.0009991930740227417. These
are records, not a claim that all are distinct RGB values or every possible
cast boundary was covered.

The independent inverse set has 544 Lab probes: a 343-point L/a/b lattice,
192 original-palette Lab values with L offsets -0.001,0,+0.001, and nine
neutral values around L=0,8,100. It includes negative L, extreme chroma,
near-gamut values and negative inverse auxiliary coordinates. Additional
Octave stage probes bracket RGB companding, Lab branching and inverse
companding thresholds; they are archived separately in conventions.mat.
No new public conversion-stage APIs are introduced for those probes.

Each forward fixture exports native Lab/HSV, exact working channels, native
round-trips, working-quantized recombinations, and the processed working-channel
floor of 128. Native and terminal uint8 inverse results are retained separately.
The original H/S or a*/b* is preserved for every recombination.

## Lab results

There are **zero unequal working-L values across 102,193 records**. The
mismatch list in measurements.json is empty, including the former [0,1,0]
failure, which now produces working L=1 as Octave does.

| Forward native component | Maximum absolute difference | Mean absolute difference |
| --- | ---: | ---: |
| L* | 1.4210854715202004e-14 | 5.373239127879653e-16 |
| a* | 1.1368683772161603e-13 | 4.1116156348156e-15 |
| b* | 5.684341886080802e-14 | 1.1160200460056814e-15 |

Aggregate native Lab MAE is 1.921653197869749e-15. Native differences are
roundoff-scale and do not change any measured SHINE working value. This is
empirical corpus evidence, not a bitwise or universal conversion guarantee.

| Inverse path | Maximum native RGB difference | Terminal uint8 differences |
| --- | ---: | ---: |
| Same Octave native Lab | 7.167877402736167e-15 | 0 |
| Same Octave working-quantized Lab | 7.17134684968812e-15 | 0 |
| Same Octave processed-L Lab | 7.17134684968812e-15 | 0 |
| RGB -> adapter Lab -> native RGB | 1.0217521273503394e-14 | 0 |
| RGB -> working-L quantization -> RGB | 1.111610803405938e-14 | 0 |
| RGB -> processed working L -> RGB | 1.111610803405938e-14 | 0 |
| Dedicated 544-point inverse set | 5.329070518200751e-15 | 0 |

Each of the six forward-based inverse paths compares 306,579 RGB scalar
components; the dedicated inverse set compares 1,632. Native round-trip
terminal uint8 also equals the original input RGB across the full corpus.
Working reconstruction is compared to the quantized reference, not incorrectly
required to reproduce the pre-quantization source RGB.

The dedicated inverse outputs range from **-36.57452262131871 to
2.07080383109337** in both implementations. There are 422 scalar values below
zero and 242 above one. All out-of-range classifications agree, and all
terminal uint8 outputs agree. This explicitly tests the absence of hidden
clipping. The extreme lower value comes from a deliberately extreme Lab
probe and is not a range expected for ordinary source images.

Per-fixture/per-channel maxima, means, unequal counts and difference
distributions are in `tests/reference/fixtures/color_adapter/measurements.json`.

## HSV adoption and public layer

Expanded HSV maximum native difference is 8.881784197001252e-16 and MAE is
2.025685486295394e-17. Working V is exact across all 102,193 records. All
tested native-round-trip, working-V and processed-V terminal uint8 RGB values
are exact. Maximum native end-to-end RGB difference is 1.2490009027033011e-15.
The original 383-pixel results remain valid; the expanded native maximum is
a separately measured bound, not a widened working-channel tolerance.

scikit-image is adopted **only for HSV**, pinned to the tested version 0.25.2
in runtime dependencies. Its installed metadata supports Python >=3.10,
matching the project floor. It brings its declared transitive dependencies;
this is no longer a NumPy-only runtime, although FFT and Lab use NumPy.
scikit-image's Lab converter is rejected for this compatibility contract.
The documented HSV API is used directly, without private-library patches.
[scikit-image 0.25.2 color API](https://scikit-image.org/docs/0.25.x/api/skimage.color.html).

`shine_color/_lab_octave.py` contains two transparent vectorized transforms:
rgb_to_lab_octave and lab_to_rgb_octave. `shine_color/color.py` exposes them
alongside rgb_to_hsv/hsv_to_rgb, v_to_working/working_to_v,
l_to_working/working_to_l, and explicit split/merge helpers for RGB, HSV and
Lab. RGB channels remain uint8; HSV/Lab inverse returns native float64 RGB.
Splits return independent channels. Merges preserve chroma and do not mutate
caller arrays. No generic mode dispatch, iterations, image I/O or pipeline
orchestration is implemented.

## Acceptance bounds, tests and provenance

`tests/reference/test_octave_color.py` contains 113 acceptance tests. They cover
all six forward groups, direct and isolated inverse paths, working scaling in
both directions, RGB channels, chroma preservation, source immutability,
original boundary regression, gamut behavior, input contracts and independent
fixture-selection rules. All 113 pass alongside all prior 205 tests in the
green full-suite run.

Float bounds are the **fixed measured per-component maxima** from this run,
copied explicitly into test constants after measurement. Every such comparison
uses rtol=0. The measurement tool never edits test bounds, and pytest never
derives tolerances from current output. Integer working/terminal assertions
are exact. Existing kernel tolerances, tests and fixtures are unchanged.
No working-L mismatch was approved, skipped or hidden.

Reference environment: Octave 11.1.0/image 2.18.2, x86_64-w64-mingw32, repaired
toolbox commit 870e058fe8bf1e4090baf2401ff0e127d1c0237a. Python environment:
3.12.10, NumPy 2.1.3, scikit-image 0.25.2, Windows 11 x86-64. Fixtures record
generator versions/hashes, Octave library source hashes, source arrays and
MAT hashes. Ordinary acceptance tests require neither Octave nor ignored
cache files. MAT headers may change on regeneration; hashes identify the
recorded run. Platform/version changes require revalidation; the tested
float maxima are not promises for other builds.

## Supported claim and review boundary

In the recorded Windows/Python and GNU Octave 11.1.0/image 2.18.2 environments,
the color layer matches SHINE uint8 L and V exactly on 102,193 forward records,
and matches tested terminal uint8 round-trip, working-channel and processed-
channel reconstructions exactly. The dedicated 544-probe Lab inverse set
matches terminal uint8 and preserves Octave's unclipped out-of-gamut behavior.
Native floating differences are measured and bounded on this corpus.

This does not establish universal Octave parity, MATLAB parity, fidelity for
all possible processed Lab/HSV values, or pipeline/mode/iteration behavior.
MATLAB numerical parity has not yet been established and remains a future
secondary validation target. Gate 4 requires human review of these results;
no Gate 4 implementation has begun.

## Reproduction

From the repository root, the committed references support:

```text
python -m reference.measure_lab_adapter
python -m pytest tests/reference/test_octave_color.py -q -p no:cacheprovider
python -m pytest -q -p no:cacheprovider
```

To regenerate references, first preserve the historical run, then run
`python -m reference.build_lab_corpus` and invoke the external Octave function
`export_lab_corpus(toolbox, destination, original)` after adding
`reference/octave` to its path. Use the pinned toolbox snapshot as toolbox,
`tests/reference/fixtures/color_adapter` as destination and
`tests/reference/fixtures/color` as original. This order keeps selection entirely
reference-derived. The harness's initial uint8 candidate-matrix shape error
was corrected to a three-channel image before successful export; no colors
were changed or excluded. The successful CLI run emitted Octave's exit-time
execution_exception message with process exit code zero; all expected files
were produced and subsequently verified by acceptance checks.
