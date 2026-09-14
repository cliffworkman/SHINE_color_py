# Gate 2 FFT diagnostic arc — 2026-09-14

**The evidence supports a mixture of backend-sensitive amplification and a
specific Python rescaling discrepancy. Gate 2 remains blocked.** No kernel
code, test tolerance, existing fixture or failing test was changed. No zero
handling, color conversion or pipeline was added.

## Findings

1. **Using FFTW helps substantially only with appropriate transform orientation.**
   Ordinary pyFFTW complex transforms in NumPy's orientation give no improvement.
   Transposing the data to reproduce Octave's column-major orientation improves
   exact image agreement from 51/90 to 83/90. Both full complex transforms and
   real transforms with Hermitian completion give that result. Calling Octave's
   own FFTW DLL gives 83/90 too; the library name/version alone does not specify
   the full execution plan, memory layout or floating-point evaluation behavior.
2. **The large original errors are concentrated at numerically unresolved source
   components.** For the five source images with large phase discrepancies,
   coefficients below 1e-14 account for at least 99.999999999991% of the L1
   discrepancy in the spectrum after full magnitude replacement. Phase error
   outside that set is at most 1.199040866595169e-14 radians for those images.
   The thresholds 1e-15, 1e-14, 1e-13 and 1e-12 classify diagnostic observations;
   none was made a tolerance or used to alter coefficients. Four images are
   exactly additive row-plus-column patterns in integer arithmetic, proving
   their mixed-frequency coefficients vanish mathematically. The data support
   the hypothesized ill-conditioning, not a general policy for arbitrary images.
3. **There is a concrete Python discrepancy in nonfinite rescaling.** The third
   5x8 source has a retained radial bin with zero Octave energy versus
   4.1174489003860687e-16 NumPy energy. With Octave's decomposition, the Python
   frequency operation also produces nonfinite reconstruction values. Given
   the *same* raw arrays, Octave rescale option 1 ignores the NaN image when
   choosing the global extrema and scales the finite images; Python's extrema
   reduction propagates NaN and outputs black images for the entire set.
   This is a reproducible behavioral error relative to the current reference,
   separate from the FFT difference. It is documented, not fixed in this arc.

For scale, the retained bin-4 target energy is 0.37604937799454324 in the
5x8 example: its Python multiplier is about 9.13e14, while Octave's is infinite.
In the 8x5 third image, the retained bin has energies 1.716587549445839e-16
(Python) and 2.482534153247273e-16 (Octave), producing multipliers about
1.90e15 and 1.31e15. Both are finite, but amplify different residual structure.

## Controlled Octave comparison

Reference source: unmodified snapshot of repaired main
`870e058fe8bf1e4090baf2401ff0e127d1c0237a`. The canonical sibling checkout was
left untouched. Environment: Octave 11.1.0, image 2.18.2, FFTW 3.3.10,
`x86_64-w64-mingw32`. The original fixture manifest did not record planning
state; the new default probe reproduces its arrays and outputs exactly, but
does not retrospectively prove its historical planner settings.

| Configuration | Wisdom at start | Current saved FFT difference from frozen fixtures | Exact final outputs |
| --- | --- | --- | --- |
| Default: estimate, 3 threads | Nonempty 71-character header; no plan entries | 0 | 90/90 |
| Estimate, 1 thread | Cleared, header only | 0 | 90/90 |
| Measure, 1 thread | Cleared, header only | 0 | 90/90 |

Within each saved run, repeated FFTs and repeated final outputs are identical.
An earlier harness-development measure run produced maximum complex error
3.66205343881779e-15 and phase error 1.4432899320127035e-15 radians, also with
90/90 exact uint8 outputs. Its raw arrays were overwritten during cleanup
corrections; the observed values and this limitation are retained in
`reference/diagnostics/fft/prior_attempts.json`. Thus small planning-related
roundoff variability was observed, **but no within-Octave final-output
instability was demonstrated by these configurations**. The evidence does
not justify claiming the reference outputs themselves changed with threading.

The successful probe verifies restoration of the initial planner, thread count
and double-precision wisdom, including its hash. Single-precision wisdom was
incidentally different after the planner/thread calls; it is recorded separately
and was not used for these double-precision computations. Initial attempts to
re-import that wisdom failed. All probes ran in disposable Octave processes;
no persistent wisdom files or canonical reference source were written.

## Backend and stage localization

Python: 3.12.10, NumPy 2.1.3, SciPy 1.15.1. Diagnostic-only pyFFTW 0.15.1
bundles FFTW 3.3.5 on this machine. The direct DLL probe uses Octave's FFTW
3.3.10 build (its full version string and binary SHA-256 are recorded).
All Python FFTW comparisons use estimate planning and one thread. This is
a small controlled comparison, not a planner-performance benchmark.

Each of the 90 outputs represents one of five shapes, three source images,
two frequency operations and three rescaling options.

| Intervention | Exact outputs / 90 | Largest output difference |
| --- | --- | --- |
| Existing NumPy implementation | 51 | 255 |
| pyFFTW, ordinary C orientation | 51 | 255 |
| pyFFTW, transposed orientation, complex or real FFT | 83 | 255 |
| Octave FFTW DLL, transposed real FFT | 83 | 255 |
| Inject Octave phase/magnitude; retain Python downstream operations | 88 | 255 |
| Inject Octave phase/magnitude; Python frequency operations; Octave inverse and rescale | 90 | 0 |

The transposed pyFFTW residuals comprise five specMatch image/option outputs
in the 5x7 set (maximum 12 levels), plus two finite images in the 5x8 sfMatch
option-1 set affected by NaN rescaling. The DLL residual is similarly localized,
with maximum 13 levels in the 5x7 specMatch set. The remaining source phase
differences are still at tiny magnitudes; matching the DLL does not eliminate
them. The current experiment does not identify the exact remaining plan,
alignment or arithmetic difference.

Octave cart2pol uses `sqrt(real^2 + imag^2)` while the Python implementation
uses `hypot`. Changing only that arithmetic form in the diagnostic process
does not change the exact-output count or resolve any of these failures.
The normalized source arrays (`double/255`) agree exactly.

Stage replay captures inverse inputs from the existing Python functions and
passes them through Octave's standard inverse transform and public rescale
function. No SHINE algorithm source is reproduced by the harness. For identical
inverse inputs, the maximum finite real reconstruction difference is
5.551115123125783e-16. Replacing just the inverse/scaling on the native NumPy
path leaves 51/90 exact outputs: it does not repair the wrong promoted phases.
The same-data scaling discrepancy occurs only in 5x8 sfMatch option 1 in this
corpus. Supplying the observed reference decomposition and Octave's inverse
and scaling yields all 90 exact outputs, providing evidence against a large
mode-specific error in the Python frequency operations on these inputs.

The independent NaN probe uses an all-NaN 2x2 array plus `[[0,10],[20,30]]`.
Octave option 1 returns the finite image `[[0,85],[170,255]]`; Python returns
zeros. Both return all zeros for option 2. No sanitization was introduced.

## Diagnostic records and reproduction

All new output is under `reference/diagnostics/fft/`; the original fixture
directory is immutable in this arc. File hashes are saved in the backend report.

- `octave_environment.json`: platform, planner, threads, wisdom hashes/content
  indicators, reference commit, generation date and restoration result.
- `default/`, `estimate_1/`, `measure_1/`: 15 MAT files containing actual
  transforms, cart2pol results, final outputs and within-run repeats.
- `failing_cases.csv`: 54 compact rows covering all three source images for
  every one of the 18 failing test configurations, including images whose
  output changes only through set-wide rescaling. It includes magnitude
  minima/maxima, exact-zero counts, threshold counts, FFT/phase errors and
  final output errors.
- `backend_diagnostics.json`: per-backend/per-fixture/per-source detail,
  including retained radial-bin energies and target/source ratios. Radial
  diagnostics group exported spectra using the existing Python grid and
  column-major summation order; they are not captured private Octave locals.
- `output_comparisons.csv`: every backend/fixture/operation/option/source output
  comparison. Join on fixture and source to the detailed source summaries.
- `python_stage_inputs.mat`, `octave_stage_replay.mat`, `stage_summary.json`,
  `stage_output_comparisons.csv`: causal stage replays and the NaN probe.

From the project root, with existing development dependencies installed:

```powershell
python -m pip install --target reference/.cache/python-fftw --no-deps --only-binary=:all: -r reference/requirements-fft.txt
```

Run in Octave (using the pinned snapshot's absolute toolbox path):

```octave
addpath('reference/octave');
probe_fft_stability(toolbox, fullfile(pwd,'tests/reference/fixtures'), ...
  fullfile(pwd,'reference/diagnostics/fft'));
```

Then run `python -m reference.compare_fft_backends`, followed in Octave by
`replay_fft_stages(toolbox, fullfile(pwd,'reference/diagnostics/fft'))`, then
`python -m reference.summarize_fft_diagnostics`. The optional direct DLL
comparison runs only when the documented Windows Octave installation exists.
Use a fresh destination/copy to preserve old measure-run evidence when repeating
the Octave probe. No pyFFTW dependency is added to the package runtime or normal
test dependencies. The DLL remains outside the repository.

## Decision and remaining limits

The hypotheses are not mutually exclusive: FFT evaluation differences explain
most observed failures, and the reference's use of unresolved phase and
near-zero energy makes such small differences consequential. A genuine Python
nonfinite-rescaling discrepancy is also confirmed. A universal stable
zero-component behavior, full Octave numerical parity, and MATLAB parity remain
unestablished. The current kernel and all 18 failing tests are preserved.

Recommended next bounded step: address the separately proven rescale discrepancy
with focused reference regression coverage, then decide whether further matching
of Octave's FFT execution is worth pursuing for the remaining degenerate 5x7
case. No special zero policy should be inferred from this diagnostic evidence.

Verification: the unchanged full test suite still reports **97 passed, 18
failed**; all original 58 tests pass. Kernel files, original fixtures, existing
tests, package dependencies and tolerance values are unchanged from checkpoint
`806689fc7290a15187eae41e6a5a3fc3c0c216d5`. No xfails, skips, remote, publication,
or MATLAB validation claim were introduced.

Primary implementation/API references used to design the probes:
[Octave FFTW control](https://octave.sourceforge.io/octave/function/fftw.html),
[Octave 11.1.0 FFTW integration](https://docs.octave.org/doxygen/11/dd/d16/oct-fftw_8cc_source.html),
[pyFFTW NumPy interface](https://pyfftw.readthedocs.io/en/latest/source/pyfftw/interfaces/numpy_fft.html).
All numerical conclusions above come from the saved local experiments.
