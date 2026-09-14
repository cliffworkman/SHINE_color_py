# Validation policy and evidence

The repaired SHINE_color implementation on `cliffworkman/SHINE_color` main is
the behavioral source. GNU Octave is the current executable validation
reference. Exact MATLAB numerical parity has not been established; MATLAB
is a future, non-blocking secondary validation target. CIELab conversion is
one area where runtime differences may exist. Octave and MATLAB are not
assumed numerically identical.

Current environment: GNU Octave 11.1.0, image 2.18.2, datatypes 1.1.8.
The pinned merged main commit is
`870e058fe8bf1e4090baf2401ff0e127d1c0237a`.
The supplied reference checkout was clean on `repair/validated-bugfixes`
at `c602d4582f51bde8bda4ed10a360734f62e538dc`; its local main was stale.
To preserve that checkout unchanged, fixtures use an unmodified download
of the pinned GitHub main commit in ignored `reference/.cache/`.
Its toolbox content matches the clean supplied repair checkout.

Deterministic results may be compared numerically. Shapes, counts, integer
histograms and uint8 results require exact comparisons when supported by
measurements. Floating-point tolerances are derived from measured differences,
recorded with the fixtures, and reviewed before becoming test bounds.
Unexpected or structured differences require investigation, not wider bounds.

Every path containing histMatch requires invariant comparisons because
equal-intensity pixels are assigned ranks using randomized tie breaking.
No raw pixel golden tests are used for those paths. Histogram equality is
appropriate immediately after histogram matching; frequency processing after
it requires stage-specific checks, since spatial assignments affect spectra.

## Validated against GNU Octave

Gate 1 is complete. **Gate 2 is blocked; the Phase 1 kernel as a whole is not
Octave-validated. Gates 3 and 4 have not been started.**

Measurements on 2026-09-14 used Python 3.12.10, NumPy 2.1.3 and SciPy 1.15.1
(the exact Python version is also in `primitive_differences.json`).
Five heterogeneous, three-image sets cover 6x8, 5x7, 5x8, 8x5 and 16x18
channels. Fixtures comprise 15 exact PNG sources, six MAT files, a manifest,
the single-pixel probe and two Python measurement/diagnosis JSON reports.
The manifest records runtime, packages, reference commit, generation date
and generating script. Measurements are reproducible with:

```text
python -m reference.measure_primitives
python -m reference.diagnose_fft
python -m pytest -q -p no:cacheprovider --tb=short
```

| Component | Observed result on the fixture corpus |
| --- | --- |
| Saturating uint8 cast, including NaN/Inf/ties | Exact |
| Rescale option 1 and option 2 | 15/15 image outputs exact for each |
| Whole-image lumMatch | 15/15 ordinary and 15/15 mixed constant-set outputs exact |
| Input/average/output histograms and expanded targets | Exact; histogram output invariants checked over five Python seeds |
| Means | Exact |
| Sample SD | Maximum absolute error 2.842170943040401e-14 |
| Histogram output SD | Maximum absolute error 1.4210854715202004e-14 in the saved measurement |
| Source and target FFT amplitudes | Maximum absolute error 2.842170943040401e-14 |
| sfMatch, rescaling 0/1/2 | 31/45 individual outputs exact; maximum error 255 |
| specMatch, rescaling 0/1/2 | 20/45 individual outputs exact; maximum error 118 |

For SD and FFT amplitude comparisons only, `atol = 128 * float64 epsilon =
2.842170943040401e-14`, `rtol = 0` is the measured maximum, expressed exactly
in binary units. No default relative tolerance is added. This is a bound for
this compact corpus and recorded environment, not a guarantee for arbitrary
image sizes or other runtime builds. All integer comparisons remain exact.
`primitive_differences.json` retains maximum, mean, 95th percentile, relative
error on nonzero reference elements, and unequal counts per comparison.
Relative errors at nearly zero FFT magnitudes are ill-conditioned.

## Blocking Gate 2 discrepancy: degenerate Fourier components

This is substantive, not an accepted divergence. The full suite reports
**97 passed, 18 failed**. All original 58 tests pass. The 18 new failures are
ordinary failing assertions, neither skipped nor xfailed, to keep the gate
visible. They cover specMatch on 5x7, 5x8, 6x8 and 8x5, and sfMatch on 5x8
and 8x5, each with rescaling 0, 1 and 2. The 16x18 set agrees exactly for
both frequency operations at all three rescaling settings.

Four small third images are additive row-plus-column patterns with exact
mathematical Fourier zeros. One other source also contains cancelling
frequencies. Octave and NumPy complex FFTs differ by at most
2.842170943040401e-14, yet the unit phase vectors differ by as much as 2.
Large phase differences occur only at reference amplitudes no larger than
7.10634347093078e-16; outside the measured FFT error floor the largest
unit-phase error is 1.9940174225283943e-14. Replacing those tiny magnitudes
with nonzero target magnitudes amplifies otherwise immaterial phase noise.
Set-wide rescaling can then propagate the discrepancy to other images.

For the third 5x8 source, the outer retained radial bin has energy exactly
zero in the Octave diagnostic spectrum and 4.1174489003860687e-16 in Python.
The reference's unguarded target/source ratio therefore has a singularity;
its sfMatch output is all zero, while Python's is not (maximum difference
255). `fft_diagnosis.json` records energies grouped using the existing Python
radial grid, additive-pattern checks and complex FFT errors. These are
diagnostics of exported spectra, not intercepted reference locals. The
zero-energy division and subsequent nonfinite reconstruction explain the
observed behavior, but no reference algorithm has been patched to force it.

Neither enlarging tolerances nor silently choosing a new phase/zero-energy
rule would establish faithful parity. No numerical algorithm was corrected:
the evidence does not establish a straightforward Phase 1 implementation
bug. A bounded next investigation should determine whether a matching FFTW
configuration reproduces Octave's zero/phase behavior, including planner and
transform-axis effects. If that is not stable, choosing a robust degeneracy
policy would require an explicit documented behavioral decision. Stop before
color conversion or pipeline implementation until this discrepancy is resolved.

HSV/CIELab comparisons, scikit-image adoption and end-to-end mode/iteration
validation have not been attempted. Scikit-image was available (0.25.2), but
has not been added as a runtime dependency. SciPy is a development/test
dependency only.

## Python-specific accepted divergences

For one source pixel and one target value, Octave 11.1.0 evaluates the colon
expression to a NaN index and `match.m` errors with invalid subscripts.
Python intentionally returns the sole target value. This well-defined behavior
is retained as an accepted divergence; no runtime behavior changed.

For one source pixel and three target values, the step is Inf, the index is
1, and both runtimes return the first target. The provisional MATLAB TODO
has been replaced by these empirical findings. `single_pixel.json` includes
captured warnings/errors and output shapes. On the separate cold probe run,
loading match.m set an `Octave:missing-semicolon` parser warning for the first
case; neither colon expression emitted a warning. This warning does not
change the observed error or result. MATLAB single-pixel behavior is untested.

## Not yet validated against MATLAB

MATLAB execution has not been used as the current Python reference. Exact
MATLAB numerical parity is unestablished. MATLAB evidence can be incorporated
later without redefining or invalidating the present Octave-validated baseline.
Development does not wait for MATLAB access.

## Scope and provenance

Local research software only, pending resolution of licensing/provenance
ambiguity. No public software license is claimed. No remote or publication.
Reference scripts call the repaired implementation without copying algorithm
source. Python work follows the mathematical/behavioral specification.
Masking, optimized histogram matching, wizard, video, GUI, upscaling, CLI,
and public release are outside this arc.
