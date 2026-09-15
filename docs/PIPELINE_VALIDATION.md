# Gate 4: whole-image pipeline validated against GNU Octave

**Gate 4 is complete under the documented per-stage contract.** All 480
recorded configurations are accepted: 478 strict deterministic or captured
histogram replays, plus two positive dynamic spectral-degeneracy cases with
exact common-forward replay through the remaining pipeline. The complete suite
reports **1,412 passed in 29.07 seconds**, zero failures, skips or xfails.
All 318 pre-pipeline tests and 116 orchestration/API regressions remain green.

The earlier diagnostic checkpoint `792bb0701f33f0cfb695ef5d8b6ed1319ed885ea`
and its original measurement/diagnosis files are preserved. Its 150 failures
were resolved by reproducing Octave HSV arithmetic and applying the previously
approved Gate 2 degeneracy policy at each actual spectral-stage input.
No original pipeline MAT file or randomized histogram fixture was regenerated.

## Public API and orchestration

```python
from shine_color.pipeline import run
result = run(images, colorspace, mode, iterations=1, rescale_option=1)
```

Input is a sequence of at least two same-size, nonempty `(H,W,3)` NumPy uint8
RGB images. Paths, strings, stacked batches, floats, mismatched dimensions and
malformed images are rejected. Colorspace accepts RGB, HSV, CIELab
case-insensitively, with Lab as an alias. Mode is an explicit integer 1..8;
iterations is a positive integer; rescale option is 0/1/2. Boolean/floating
parameter values are not silently treated as integers.

The output is a list of terminal RGB uint8 arrays. Input images are not
mutated. There are no filesystem side effects. RGB channels are processed
independently; HSV processes only working V, Lab only working L. Color split
occurs once before iterations and reconstruction once afterwards. Original
H/S or a*/b* remains unchanged. Working values are uint8 on 0..255 throughout
kernel processing. HSV/Lab reconstruction returns native unclipped float64
RGB, then one terminal `to_uint8(native_rgb*255)` occurs. RGB channels are
already uint8 and are merged directly.

| Mode | Ordered operations |
| --- | --- |
| 1 | lumMatch |
| 2 | histMatch |
| 3 | sfMatch |
| 4 | specMatch |
| 5 | histMatch -> sfMatch |
| 6 | histMatch -> specMatch |
| 7 | sfMatch -> histMatch |
| 8 | specMatch -> histMatch |

The existing function-oriented dispatcher invokes the established primitives;
no kernel algorithm is duplicated. The second stage receives the first stage's
output, and iteration n+1 receives iteration n's output. This implements the
repaired semantics rather than upstream 0.0.5's broken combined-mode/iteration
behavior. Python completes iterations per RGB channel; the external reference
loop interleaves channels per iteration. Channels are independent. Captured
histogram replay indexes stages by channel/iteration and does not claim shared
random draws between runtimes.

Rescale options are forwarded to spectral primitives only. Modes 1/2 ignore
valid rescale choices. Default histogram processing remains unseeded; scoped
test instrumentation controls randomness without adding a public RNG option.
Working-scale tests protect statistics/comparisons before inverse scaling;
no production diagnostics framework was introduced.

## Recorded reference corpus

The predeclared `reference/pipeline/CRITERIA.md` is hashed into the manifest.
Four sets of three RGB images have dimensions 17x19, 17x20, 20x17 and 20x20:
full-range noise, smooth heterogeneous texture with fine noise, and structured
multichannel sinusoids with bounded integer perturbations. PCG64 seeds are
2026091404..2026091407. No candidate was discarded based on agreement. These
are synthetic workflow probes, not a real experimental stimulus sample.

Each set covers all 8 modes, 3 color spaces, iterations 1/2, and rescale 0/1/2
for modes 3..8. Modes 1/2 are measured at rescale 1, with independent regressions
verifying rescale irrelevance. There are 120 configurations per set, 480 total:
168 deterministic and 312 containing histogram matching.

The external Octave harness calls the actual repaired `processImage` dispatcher.
Thin external capture wrappers call verified original primitive handles and
record stage input/output. The harness supplies color splitting/reconstruction
and iteration wiring. It does not invoke the SHINE_color filesystem/wizard/
plotting shell. Wrapper paths are removed afterwards. The canonical reference
checkout remains unchanged.

Reference: GNU Octave 11.1.0, image 2.18.2, FFTW 3.3.10, pinned toolbox main
`870e058fe8bf1e4090baf2401ff0e127d1c0237a`. Original manifests record FFTW
planner/threads/wisdom, dispatcher hash, delegate paths and platform. Stage
arrays, native RGB and terminal outputs are durable MAT fixtures. Completion
measurement verifies every MAT hash against the original diagnostic record.
Tests need neither Octave nor ignored caches.

## Completed matrix

Cells give strict ordinary/captured-histogram replays, plus any positive
backend-sensitive configuration. Every listed configuration passes its stated
contract. The full 48-row mode/colorspace/iteration breakdown, including the
rescale variants, is `tests/reference/fixtures/pipeline/completion_matrix.csv`.

| Mode | RGB | HSV | CIELab | Comparison |
| --- | ---: | ---: | ---: | --- |
| 1 | 8 exact | 8 exact | 8 exact | Deterministic |
| 2 | 8 exact | 8 exact | 8 exact | Histogram invariant + captured replay |
| 3 | 24 exact | 24 exact | 24 exact | Deterministic |
| 4 | 24 exact | 24 exact | 24 exact | Deterministic |
| 5 | 24 exact | 24 exact | 24 exact | Histogram invariant + spectral/full replay |
| 6 | 23 exact + 1 degeneracy | 24 exact | 23 exact + 1 degeneracy | Histogram invariant + per-stage spectral contract |
| 7 | 24 exact | 24 exact | 24 exact | Spectral replay + histogram invariant |
| 8 | 24 exact | 24 exact | 24 exact | Spectral replay + histogram invariant |

All 168 deterministic configurations are exact at working and terminal levels:
56/56 each for RGB, HSV and Lab. Of 312 histogram configurations, 310 strict
captured-stage replays are exact; two use positive degeneracy/common-forward
replay. This does not claim independently randomized whole images are identical.

All **780 histogram stages** pass exact target/output histogram comparisons,
shape/dtype checks and mean/sample-SD invariants implied by sorted outputs.
Mode 2 contributes 60 stages; modes 5/6/7/8 each contribute 180. The target
histogram need not sum to pixel count; output distributions are compared to
actual reference outputs after the established expansion/resampling algorithm.

All **1,074 well-conditioned spectral stages** require and achieve exact
ordinary replay. Of 1,080 total stages, six fail the unchanged screen. Four
still produce exact ordinary results, two differ; all six become exact with
common Octave forward phase/magnitude. Mode 5 has 180/180 exact ordinary
spectral replays; mode 6 has 178/180 ordinary exact plus two positive mechanism
cases. Modes 7 and 8 each have 180 exact spectral replays and 180 passing
histogram-stage invariant checks.

At later iterations, previous random spatial arrangement affects the next
spectrum and potentially its histogram target. Consequently stage comparisons
use identical captured input, rather than requiring independent random-run
final histogram or pixel equality. No spectral invariant is incorrectly
asserted after terminal clipping or histogram replacement.

## HSV reconstruction resolution

The new NumPy HSV adapter reproduces Octave's actual forward/inverse arithmetic.
It does not change `to_uint8`, working V, or rounding. Both directions are
required: keeping scikit-image H/S with Octave inverse still yields 2,201
unequal terminal components on the independently selected boundary corpus.

The frozen mathematical specification is `docs/OCTAVE_HSV_SPEC.md`. The study
covers 76,337 forward colors, 9,363 independently selected processed-V boundary
pairs, 11,832 inverse probes, and all 458 historical Gate 4 occurrences. Every
adapter native/terminal comparison is exact. All 102,193 Gate 3 HSV records
are revalidated with zero native, working-V or terminal differences. All prior
Lab tests remain unchanged and green. Full measurements and selection rules
are in [HSV_ADAPTER_VALIDATION.md](HSV_ADAPTER_VALIDATION.md).

All 160 HSV pipeline configurations now have **zero native RGB difference
and zero unequal terminal uint8 values**. The old 148 failing configurations
and 458 scalar differences remain documented in the original diagnosis.json.
The cast was not the source and remains untouched.

Production dependencies return to **NumPy only**. scikit-image==0.25.2 remains
in the optional reference extra solely for historical comparison tooling.
The 24 space/mode dependency smoke runs succeed with SciPy/scikit-image imports
blocked. The normal pytest suite does not require scikit-image.

## Dynamic spectral degeneracy contract

Conditioning is applied to the **actual input of each spectral stage** using
the unchanged Gate 2 rule: every magnitude and occupied retained radial
amplitude sum must exceed `1e-10*max(1,max magnitude)`. Both NumPy and recorded
Octave decompositions are checked. This is a classification criterion, not an
output tolerance.

Histogram matching can change the spatial arrangement of intensities and
create mathematically/numerically degenerate Fourier components even when
the original input was well-conditioned. This matters especially for modes
5/6 and later iterations of combined modes. Screening the initial stimulus
alone cannot guarantee subsequent spectral conditioning.

The two nonexact captured stages remain unchanged:

| Set / configuration | Affected stage | Ordinary working differences |
| --- | --- | ---: |
| 20x20 / RGB / mode 6 / iterations 2 / rescale 1 | Green, first-iteration specMatch after histMatch | 343 scalar pixels, max 1 |
| 20x20 / CIELab / mode 6 / iterations 1 / rescale 0 | Working L specMatch after histMatch | 1 scalar pixel, max 1 |

Positive tests assert original working inputs pass the screen, captured
histogram output equals spectral input, actual stage spectra fail the screen
with near-zero coefficients, phase disagreement concentrates there, ordinary
output divergence remains observable, and common-forward replay is exact.
No arbitrary minimum phase angle is required: even a small phase difference
can promote a near-zero residual to a finite component.

Complete-chain tests then inject only the recorded forward quantities at
screen-failing stages, require their incoming pixels to match exactly, and
require subsequent histogram inputs, final working arrays and terminal RGB
to match exactly. They continue running the actual Python primitives and
pipeline. Well-conditioned stages are never granted relaxed parity. All
stage-order and iteration-chain assertions remain mandatory.

The ordinary RGB run ends with exact terminal images after a later captured
histogram output but has a nonexact intermediate histogram input; it is still
classified as backend-sensitive. The ordinary Lab run has three terminal RGB
component differences of one level. These ordinary results have not been
hidden or described as pixel-exact. Common-forward reconstruction has maximum
native RGB difference 1.1546319456101628e-14 in Lab, zero in RGB/HSV, and zero
terminal differences. This measured native maximum is not a new tolerance.

There is no runtime zero handling, phase normalization, denominator adjustment,
FFT backend switch or SHINE algorithm change. NumPy/pocketfft remains the
production backend. Classification and common-forward injection are validation
tooling only.

## Tests, scope and reproduction

The full result is **1,412 passed in 29.07 seconds**, no failures/skips/xfails:
318 prior tests, 116 orchestration/API regressions, 480 stage-contract tests,
480 complete-configuration tests, 16 additional HSV tests and two explicit
dynamic-degeneracy mechanism tests. Combined-mode bypass regressions for modes
5..8 pass; iteration chaining regressions for mode 3 and modes 5..8 pass;
12 stage/iteration receiver regressions cover all spaces and combined modes.
No prior numeric/color test bounds were widened and no fixture was removed.

Supported claim: the recorded whole-image in-memory pipeline is validated
against GNU Octave for repaired operation ordering, iteration chaining,
RGB/HSV/Lab working/reconstruction semantics, deterministic working/terminal
parity, histogram invariants with captured replay, strict well-conditioned
spectral parity, and explicitly tested backend-sensitive degeneracy with exact
common-forward downstream replay. This is the completed Gate 4 contract.

MATLAB numerical parity has not been established and remains a future secondary
validation target. Universal Octave pixel parity, independent random spatial
histogram assignment parity, other runtime builds, masking, background detection,
templates, SSIM optimization, file I/O, CLI, wizard, diagnostic plotting, video,
upscaling and public release are not established. Gate 5 and excluded features
were not begun. No remote, push or publication occurred.

Production changes in this completion are `_hsv_octave.py`, the color wrappers
and dependency metadata; the pipeline dispatcher, numerical kernel and Lab
adapter are unchanged. New evidence is in `hsv_adapter/`,
`pipeline/completion_measurements.json` and `pipeline/completion_matrix.csv`.
Original pipeline measurement/diagnosis files retain the stopping checkpoint.

```text
python -m reference.measure_hsv_adapter
python -m reference.pipeline.measure_completion
python -m reference.check_numpy_runtime
python -m pytest -q -p no:cacheprovider
```

Only the first command needs the diagnostic scikit-image reference extra.
Do not regenerate the frozen randomized Octave pipeline fixtures for these
checks. A new reference export would be a distinct corpus requiring its own
measurement and acceptance record.
