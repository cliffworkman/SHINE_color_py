# Gate 4 whole-image pipeline — implemented, acceptance blocked

The whole-image pipeline is implemented and the operation-order regressions
pass, but **Gate 4 is not complete**. The full suite reports **1,244 passed,
150 failed**, with no skips or xfails. All prior 318 tests and all 116 new
orchestration/API tests pass. The 150 ordinary failures preserve two newly
exposed boundaries: HSV native roundoff surviving terminal quantization, and
post-histogram spectral degeneracy. No prior numeric/color algorithms or
tolerances have been changed to suppress them.

## Public API and architecture

```python
from shine_color.pipeline import run
result = run(images, colorspace, mode, iterations=1, rescale_option=1)
```

Input is a sequence of at least two same-size, nonempty `(H,W,3)` NumPy uint8
RGB images. Strings, paths, stacked batch arrays, floating images, mismatched
dimensions, empty sets and malformed shapes are rejected. Colorspace accepts
RGB, HSV, CIELab case-insensitively, with Lab as an alias. Mode is an explicit
integer 1..8; iteration count is a positive integer; rescale option is 0/1/2.
Booleans and floating parameter values are not silently treated as integers.

Output is a list of terminal RGB uint8 arrays. The function has no filesystem
side effects. Source arrays are not mutated. RGB channels are processed
independently; HSV processes only working V, Lab only working L. Conversion
happens once before iterations and reconstruction once afterwards. Original
H/S or a*/b* remains untouched. Lab inverse remains unclipped until the one
explicit terminal `to_uint8(native_rgb*255)` boundary. RGB working channels
are already uint8 and are recombined directly.

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

The function-oriented `_process_channel` calls existing primitives without
duplicating their algorithms. Every second stage consumes the first stage's
output; iteration n+1 consumes iteration n's output. It reproduces the
**repaired** semantics, not upstream 0.0.5's broken combined-mode and iteration
behavior. RGB channels are independent; the Python implementation completes
all iterations of a channel before advancing to the next channel, while the
reference shell interleaves channels per iteration. Histogram randomness is
not shared across runtimes, so this does not establish matched random draws.
The replay tool explicitly indexes captured stages by channel and iteration.

Rescale options are forwarded only to spectral primitives. Option 0 never
calls rescale() through the orchestration layer. Modes 1/2 ignore valid rescale
options. Default histogram behavior remains unseeded. A private channel-level
RNG hook and scoped monkeypatching support controlled tests; the public run
API does not silently seed randomness.

All channel-level statistics must compare original/transformed uint8 working
arrays on the same 0..255 scale, before inverse scaling. Representation tests
check this boundary; no diagnostic subsystem was added to production.

## Independent corpus and actual reference dispatcher

The predeclared rules are in `reference/pipeline/CRITERIA.md`, hashed into the
input manifest. Four sets contain three synthetic RGB images each, at 17x19,
17x20,20x17,20x20: full-range noise, heterogeneous smooth texture with fine
noise, and structured multichannel sinusoids with bounded integer perturbations.
PCG64 seeds are 2026091404..2026091407. These are synthetic workflow probes,
not a real experimental stimulus sample. No candidate was discarded or
regenerated based on agreement.

Each set covers all 8 modes, all 3 color spaces, iterations 1/2, and rescale
0/1/2 for modes 3..8. Modes 1/2 are measured at option 1; independent tests
verify their irrelevance to rescale choice. There are 120 configurations per
set, **480 configurations total** (168 deterministic, 312 histogram-containing).

The external Octave harness calls the actual repaired `processImage` function.
Thin external primitive wrappers delegate to function handles verified to
resolve to the pinned toolbox, recording stage input/output without changing
the primitive. Wrapper paths are removed after the run. The harness supplies
the documented color split/reconstruction and iteration loop externally.
It does **not** invoke the SHINE_color filesystem/wizard/plotting shell; claims
are limited to in-memory processing and the actual dispatcher it calls.

Reference: Octave 11.1.0, FFTW 3.3.10, image package 2.18.2 in the recorded
environment, toolbox commit 870e058fe8bf1e4090baf2401ff0e127d1c0237a. Runtime
FFT planner/thread/wisdom, dispatcher hash and delegate paths are recorded.
The canonical reference checkout is unchanged. All sources, per-stage arrays,
native RGB and terminal uint8 outputs are durable MAT fixtures. Python version
information and fixture hashes are in measurements.json. No ignored cache is
needed by the tests.

## Validation matrix

The complete **48-row mode/colorspace/iteration matrix**, with rescale variants
and all four sets aggregated per row, is `acceptance_matrix.csv`. The table
below reports configurations passing every strict full-chain assertion,
including input parity at injected histogram boundaries. Histogram rows use
captured-stage replay, not independent random-run pixel comparison.

| Mode | RGB | HSV | CIELab | Comparison |
| --- | ---: | ---: | ---: | --- |
| 1 | 8/8 | 0/8 | 8/8 | Deterministic exact working/terminal |
| 2 | 8/8 | 2/8 | 8/8 | Histogram invariant + captured replay |
| 3 | 24/24 | 0/24 | 24/24 | Deterministic exact working/terminal |
| 4 | 24/24 | 4/24 | 24/24 | Deterministic exact working/terminal |
| 5 | 24/24 | 0/24 | 24/24 | Histogram invariant + spectral/full replay |
| 6 | 23/24 | 3/24 | 23/24 | Histogram invariant + spectral/full replay |
| 7 | 24/24 | 1/24 | 24/24 | Spectral replay + terminal histogram invariant |
| 8 | 24/24 | 2/24 | 24/24 | Spectral replay + terminal histogram invariant |

Deterministic strict totals: RGB 56/56, HSV 4/56, Lab 56/56 (116/168 overall).
Histogram strict replay totals: RGB 103/104, HSV 8/104, Lab 103/104
(214/312 overall). Thus 330 configurations pass strict full-chain assertions.
The remaining 150 are ordinary failing tests, not accepted divergences.
The measurement JSON lists 152 failed checks: these 150 full-chain checks
plus separate spectral-stage checks for the same two generated-degeneracy
cases. It does not represent 152 distinct failed configurations.

All **780 histogram-stage checks pass**: exact rounded target histogram and
exact output intensity histogram, plus dimensions/dtype and mean/sample-SD
implied by sorted output values. Mode 2 contributes 60 stages; modes 5/6/7/8
each contribute 180. Target histograms need not themselves sum to pixel count:
the existing histogram primitive expands/resamples the target. Tests compare
the actual Octave output distributions, not an unjustified raw target equality.

Modes 5/6 replay their actual captured randomized first-stage images into
Python spectral primitives. Mode 5 is 180/180 exact; mode 6 is 178/180 exact,
with the two exceptions below. Modes 7/8 each have 180/180 exact spectral
replays and 180 passing histogram-stage checks. At iteration 2, prior random
arrangement can affect a spectral stage and its next histogram target; therefore
independent final histograms are not required to match across runtimes there.
The comparisons are stage-specific on identical captured input. No spectral
invariant is incorrectly asserted after uint8 clipping or histogram replacement.

## Spectral conditioning and the two post-histogram exceptions

Every captured spectral input is screened in Octave-exported and NumPy
decompositions using the unchanged Gate 2 threshold:
all magnitudes and occupied retained radial sums >1e-10*max(1,max magnitude).
Of **1,080 spectral stages**, 1,074 pass the screen and all 1,074 replay exactly.
Six captured stages fail the screen. Four still replay exactly; two do not.
They are retained separately and their per-source phase localization is saved.

Both mismatches occur in the 20x20 set, mode 6, after randomized histogram
matching: RGB (the iterations=2, rescale=1 run, green channel, first iteration)
and Lab (iterations=1, rescale=0). The former has 343 differing scalar working
pixels, maximum difference 1; the latter has one, maximum difference 1.
All six degenerate cases replay exactly after injecting the same recorded
Octave forward phase/magnitude. This localizes them to the known FFT phase
degeneracy class, not the pipeline dispatcher or Lab converter.

The RGB run happens to end with exact terminal images after a later histogram
replay, but its next histogram input was already nonexact; that is still a
strict full-chain failure. The Lab difference propagates to three RGB scalar
components, each differing by 1, with native RGB maximum difference
0.004087255706704207. This is not evidence of a new Lab algorithm defect.

The gate's strict full-replay assertions remain ordinary failures for these
two configurations. Separate stage tests positively exercise the approved
degeneracy mechanism using common-forward replay. Human review must decide
how to reflect dynamically introduced degeneracy in the pipeline contract;
no epsilon denominator, phase normalization or backend switch was introduced.

## New HSV terminal-quantization boundary

**148 HSV configurations have 458 unequal scalar terminal outputs**, each
differing by one uint8 level. Their working V channels agree exactly. Native
HSV reconstruction differs by at most 8.326672684688674e-16 over this corpus;
every changed scaled RGB value is within 1.2789769243681803e-13 of a
half-integer casting boundary.

A deterministic mode-1 example, source RGB [61,60,122], produces scaled R:

| | Scaled reconstructed R | Terminal R |
| --- | ---: | ---: |
| Python/scikit-image | 62.49999999999997 | 62 |
| Octave | 62.5 | 63 |

Python to_uint8 applied to **the same Octave native RGB** reproduces every
Octave terminal value in all 148 failing runs: zero cast-only mismatches.
Injecting original Octave H/S still leaves 124 failing configurations, so
inverse HSV arithmetic contributes independently of the forward chroma
roundoff. Every differing location and both scaled values are in diagnosis.json.
No numeric.py change is justified by this probe.

Gate 3's original assertions remain green; they did not cover these processed-V
values. Its corpus-bound claim therefore remains accurate, but it cannot be
extended to universal terminal HSV parity. This is a new explicit acceptance
boundary, not permission to introduce a one-level pixel tolerance or snap
values near .5. The previously validated color code is unchanged.

## Regression tests and stopping condition

116 orchestration/API tests pass. They include all modes/color spaces at one
and two passes against explicit manual Python composition with controlled test
randomness; combined-mode bypass regressions for modes 5..8; two-pass cases
that demonstrably differ from restarting (mode 3 and modes 5..8); exact stage
receiver tests; working-scale protection; rescale forwarding; a terminal Lab
cast probe; contract errors and source immutability.

480 reference stage tests pass, checking the captured repaired operation order
and iteration dataflow, histogram invariants and spectral replay. 480 strict
full-chain tests give 330 passes and 150 failures. Combined with 318 prior
tests and 116 new regression/API tests, the full command
`python -m pytest -q -p no:cacheprovider --tb=no` reports
**1,244 passed, 150 failed in 22.74 seconds**, no skips/xfails.
No existing tests, fixture arrays or numerical bounds were weakened.

Supported claim: the recorded evidence verifies repaired operation ordering,
iteration chaining, independent RGB processing, preserved HSV/Lab chroma and
working-scale plumbing. Deterministic RGB/Lab modes match exactly on this
corpus. Histogram stages and well-conditioned spectral replays agree under
the documented stage-specific comparisons. Full whole-image Octave parity is
not established because the above terminal HSV and generated-degeneracy
cases remain open. This is **not** a Gate 4 completion checkpoint.

MATLAB numerical parity has not been established and remains a future secondary
validation target. There is no claim for masking, background detection,
templates, optimized histograms, diagnostic plotting, wizard, CLI, file I/O,
video, upscaling, universal Octave parity or public release.

Next human decision: authorize a bounded study of Octave-compatible HSV
reconstruction at terminal cast boundaries, and decide the pipeline-level
policy for histogram-generated degenerate spectra. Preserve the distinction
between a faithful native conversion and terminal quantization. No next-gate
or excluded-feature work should begin from this checkpoint.

## Artifacts and reproduction

Production addition: `shine_color/pipeline.py`; no lower-level algorithm edits.
Tooling: `reference/pipeline/{build,measure,diagnose,report_matrix}.py`, the
predeclared criteria and external `export_pipeline.m`/delegating wrappers.
Tests: `tests/test_pipeline.py`, `tests/reference/test_octave_pipeline.py`.
Fixtures: `tests/reference/fixtures/pipeline`, including input and reference
MATs, provenance, compact measurement records, diagnosis and acceptance matrix.

With committed references available:

```text
python -m reference.pipeline.measure
python -m reference.pipeline.diagnose
python -m reference.pipeline.report_matrix
python -m pytest tests/test_pipeline.py -q -p no:cacheprovider
python -m pytest -q -p no:cacheprovider
```

To regenerate the reference, first preserve this run (histogram spatial
arrangements are intentionally random), run `python -m reference.pipeline.build`,
then add reference/octave to the Octave path and call
`export_pipeline(pinned_toolbox, tests/reference/fixtures/pipeline)` with absolute
paths. Regeneration creates a new random-stage corpus and needs new measurement;
old report counts are not promised for new draws. No fixture was regenerated
to hide an observed mismatch. All work is local; no remote, push or publication.
