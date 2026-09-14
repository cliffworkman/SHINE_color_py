# Octave nonfinite rescaling correction — 2026-09-14

The independently demonstrated rescaling fidelity bug is repaired. The change
is confined to `shine_color/rescale.py`. NumPy remains the runtime FFT backend;
pyFFTW remains optional diagnostic tooling. No new zero-phase or zero-energy
rule, wider tolerance, modified golden output, xfail, or Gate 3 work was added.

## Empirical semantics

`reference/octave/probe_rescale_extrema.m` calls the unmodified repaired reference
at `870e058fe8bf1e4090baf2401ff0e127d1c0237a`. Octave 11.1.0 on
`x86_64-w64-mingw32` was probed with 12 cases and both rescaling options.
Each case records inputs, per-image nested extrema, global extrema, means of
extrema, both outputs, warnings and errors. MAT arrays retain NaN/Inf exactly;
the companion JSON uses strings for nonfinite values.

For these real, nonempty arrays:

- `max(max(image))` and `min(min(image))` omit NaNs when other values exist.
  An all-NaN image has NaN extrema. An all-NaN column does not poison other
  columns. Infinities remain legitimate extrema, rather than being omitted.
- Option 1's global extrema follow the same NaN omission rule. A NaN-only
  member does not poison a set containing finite images. If the entire set is
  NaN, the scaling parameters remain NaN and terminal uint8 outputs are zero.
- Option 2 uses ordinary means of the per-image extrema. An all-NaN member
  therefore propagates NaN to both means and all output images become zero.
  Partial NaNs still allow finite per-image extrema, so both options can scale
  the other pixels normally. NaN pixels themselves map to zero only at the
  already-established terminal uint8 cast.
- +Inf is the maximum when present and -Inf the minimum. For the probed
  arrangements, infinite ranges, Inf-Inf and opposing infinite means produce
  zero outputs after IEEE arithmetic and the final cast under both options.
  These outcomes do not amount to a general rule that all infinities should
  be replaced or all nonfinite image sets should be blacked out.
- No extrema/rescale execution warnings or errors were observed in these cases.
  The unrelated toolbox `rescale` path-shadow warning occurs during setup and
  remains visible. The probe warms function parsing before capturing execution
  warnings.

The cases are: finite; partial NaN; all NaN; positive Inf; negative Inf; both
infinities in one image; NaN-only member with two finite images; partial-NaN
member; NaN column; all-NaN set; positive-Inf-only member; and opposing-Inf-only
members alongside a finite image.

## Narrow Python correction and regression evidence

A private `_extreme(values, maximum)` helper removes NaNs from the *reduction
operands only*, retains infinities, and returns NaN without a warning when no
non-NaN operand remains. It is used for per-image extrema and option 1's global
extrema. Option 2 retains ordinary means. No input pixel is cleaned or replaced.
Invalid-operation warning suppression is extended only to the probed ordinary
means and span subtraction, matching Octave's warning-free behavior; this does
not suppress warnings elsewhere or change the arithmetic results.

There are 36 new Octave-reference tests: 24 output/warning/input-preservation
checks (12 cases × 2 options), plus 12 direct per-image/global/mean extrema
checks. Before the fix, 9 of the 24 output/warning tests failed: seven incorrect
output cases and two extra NumPy invalid-operation warnings. Afterward, all
36 pass. All original finite tests and all 58 Phase 1 tests remain green.

For the simple proven case `[all-NaN 2x2, [[0,10],[20,30]]]`, option 1 now returns
`[all-zero 2x2, [[0,85],[170,255]]]`, matching Octave. Previously both images
were zero. Option 2 still returns two zero images, correctly. The new three-image
NaN-member probe additionally demonstrates global scaling across *both* finite
members rather than special-casing the original example.

## Inverse-transform / rescaling separation

All paths below receive the same Octave-derived phase/magnitude arrays, followed
by the existing Python frequency operations. Captured identical inverse inputs
are evaluated by the two runtimes; option 0 bypasses rescaling and uses that
runtime's uint8 conversion. Both options 1/2 and the bypass are included in
the 90 outputs. Octave inverse runs use estimate planning and one thread.

| Path | Inverse FFT | Rescale | Exact outputs | Maximum / mean uint8 difference |
| --- | --- | --- | --- | --- |
| A | Python | Corrected Python | 90/90 | 0 / 0 |
| B | Octave | Corrected Python | 90/90 | 0 / 0 |
| C | Python | Octave | 90/90 | 0 / 0 |
| D | Octave | Octave | 90/90 | 0 / 0 |

The prior 88/90 downstream result was caused by Python rescaling alone on this
corpus. The corrected measurements show no inverse-transform rounding-boundary
failure or interaction. This is not a claim that inverse FFTs are bit-identical
or guaranteed equivalent for all possible data. Raw inverse differences and
nonfinite-pattern comparisons are retained in `corrected_summary.json`.

## Updated execution comparisons

The same five fixture sets, three images, two operations and three rescaling
settings give 90 outputs. The original Octave arrays are unchanged. A fresh
Octave forward/frequency run and a fresh inverse/rescale replay reproduced the
reference outputs; saved replay inputs match the refreshed forward-derived
inputs exactly. Original
planner-run evidence and ordinary-pyFFTW results are preserved under
`reference/diagnostics/fft/`. New evidence is under
`reference/diagnostics/nonfinite_rescale/`.

| Execution | Exact before → after | Maximum absolute uint8 error after | Pixel-weighted MAE after | Equal-image-weight MAE after |
| --- | --- | --- | --- | --- |
| Octave reference | 90 → 90 | 0 | 0 | 0 |
| NumPy/pocketfft | 51 → 51 | 255 | 5.773343187977335 | 12.93369708994709 |
| Matched-orientation pyFFTW | 83 → 85 | 12 | 0.06282335550628233 | 0.1619047619047619 |

MAE includes all pixels/outputs, not only mismatches. Matched orientation means
transposing before a contiguous FFT and transposing back; estimate, one thread,
pyFFTW 0.15.1 / bundled FFTW 3.3.5. Both complex and real-Hermitian variants
give the reported pyFFTW result. Ordinary-orientation pyFFTW remains 51/90.
The optional Octave DLL comparison reaches 85/90, with maximum error 13.
No FFT backend was selected or added to runtime dependencies.

The two newly exact matched-FFTW outputs are sources 1 and 2 of 5x8 sfMatch,
rescale option 1. Their previous maximum errors were 232 and 255 respectively;
both are now zero. Those finite members were poisoned by the third member's
NaN extrema. NumPy's forward transform instead gives a tiny finite radial
energy and finite reconstruction in that case; its outputs and all comparison
rows are unchanged. Thus none of the original 18 NumPy reference test failures
becomes green from this fix alone.

## Remaining failures by mechanism

Source numbers are one-based. Each table cell lists failing source outputs
for the indicated rescaling option. A = forward phase degeneracy;
B = radial-energy degeneracy. Other images can inherit the resulting error
through correctly implemented set-wide rescaling; that is not category D.

| Backend | Fixture | Operation | Option 0 | Option 1 | Option 2 | Root category |
| --- | --- | --- | --- | --- | --- | --- |
| NumPy | 5x7 | specMatch | 3 | 3 | 1,2,3 | A (source 3) |
| NumPy | 5x8 | specMatch | 3 | 3 | 1,2,3 | A (source 3) |
| NumPy | 6x8 | specMatch | 2,3 | 1,2,3 | 1,2,3 | A (sources 2,3) |
| NumPy | 8x5 | specMatch | 3 | 1,2,3 | 1,2,3 | A (source 3) |
| NumPy | 5x8 | sfMatch | 3 | 1,2,3 | 1,2,3 | B (source 3) |
| NumPy | 8x5 | sfMatch | 3 | 1,2,3 | 1,2,3 | B (source 3) |
| Matched pyFFTW | 5x7 | specMatch | 3 | 3 | 1,2,3 | A (source 3) |

This is 39 NumPy image-output mismatches across 18 test configurations, and
five matched-pyFFTW mismatches across three configurations. The full per-output
table, errors and direct-versus-propagated attribution are in
`remaining_failures.csv`; the real and complex pyFFTW variants are listed
separately. No category C (inverse), D (rescale), or E (unexplained) remains
in these controls. No unexplained well-conditioned-input mismatch was found.
The four small additive source patterns have mathematically zero mixed
frequencies; the additional 6x8 source has numerically cancelling coefficients.
This distinction and the numerical thresholds are preserved, not generalized
into proof about every tested frequency.

## Backend decision remains open

FFTW materially improves measured fidelity to this Octave executable. Remaining
disagreements are rooted in degenerate spectra in this corpus; some otherwise
nondegenerate images differ only because their set also contains such a source.
NumPy is exact on all 18 outputs of the 16x18 set, where the troublesome phase
promotion/retained-bin singularity is absent. Other source-level finite FFT
differences remain machine-near. This compact corpus does not establish
universal equivalence on all well-conditioned images.

pyFFTW adds a compiled platform-dependent dependency, explicit planning/thread
configuration, memory-orientation conversion, and potentially Hermitian
completion. The observed 3.3.5 versus 3.3.10 build difference and residual
5x7 disagreement show that merely specifying FFTW does not ensure exact parity.
Using it to match undefined source phase more closely would reproduce aspects
of Octave execution, not establish a scientifically unique phase at zero.

The corrected evidence is sufficient for an informed human backend review,
but not a claim that FFTW is required or universally faithful. It does not
warrant automatically introducing a new zero-phase/zero-energy algorithmic
rule. Recommended next bounded step: review whether to prioritize closer
Octave execution fidelity or define an explicit policy for degenerate spectra;
only then authorize a backend or zero-handling implementation decision.

MATLAB numerical parity remains untested. GNU Octave is the current executable
reference; MATLAB remains a future secondary target. Gate 2 is not green and
Gate 3 has not begun. Full suite: **133 passed, 18 failed**, including all
original 58 passing tests and all 36 new semantic checks. Existing reference
tests, expected outputs and tolerances are unchanged.

## Reproduce

1. In Octave, add `reference/octave` to the path; run
   `probe_rescale_extrema(toolbox, fullfile(pwd,'reference/diagnostics/nonfinite_rescale'))`
   with the pinned unmodified reference toolbox path.
2. In Octave, run
   `probe_fft_stability(toolbox, fullfile(pwd,'tests/reference/fixtures'), fullfile(pwd,'reference/diagnostics/nonfinite_rescale'))`
   to refresh the Octave reference into the new directory, preserving history.
3. Run `python -m reference.compare_fft_backends --destination reference/diagnostics/nonfinite_rescale --reference-destination reference/diagnostics/nonfinite_rescale`.
4. In Octave, run
   `replay_fft_stages(toolbox, fullfile(pwd,'reference/diagnostics/nonfinite_rescale'))`.
5. Run `python -m reference.measure_rescale_correction`, then
   `python -m pytest -q -p no:cacheprovider --tb=no`.

Use a new destination when preserving an additional historical run. The
existing optional pyFFTW installation instructions in `FFT_DIAGNOSTICS.md`
still apply. All artifacts and commits remain local; the canonical fork is
unchanged, and no remote, publication or public license was added.
