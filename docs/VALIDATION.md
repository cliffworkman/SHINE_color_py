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

Gates 1 and 2 are complete. **The Phase 1 kernel is validated against the
recorded GNU Octave corpus with documented backend-sensitive degeneracies.**
NumPy/pocketfft is the Python reference FFT backend for v0.1. This is a
corpus-bound validation claim, not universal Octave or MATLAB parity.

The approved policy adds 54 strict frequency tests (42 synthetic, 12 natural),
covering 162 outputs and verifying the unchanged `1e-10*max(1,max magnitude)`
conditioning screen before comparison. Exact source arrays and Octave outputs
are durable repository fixtures; ordinary tests require no ignored cache,
Octave executable or pyFFTW. The 18 former failures are positive marked tests
of source degeneracy, its output effect, and exact downstream processing with
Octave forward quantities. No numerical bounds were changed. No xfails/skips.

The Gate 2 full suite reports **205 passed, zero failures**. Expected invalid
multiplication in the zero-energy Octave-forward replay is asserted explicitly.
Gate 3's initial scikit-image Lab discrepancy is preserved in
[COLOR_VALIDATION.md](COLOR_VALIDATION.md). The authorized NumPy Lab adapter
subsequently resolves it: all 102,193 working-L values and all tested terminal
reconstructions agree exactly. HSV uses scikit-image 0.25.2 with exact working V
on that corpus. The 544 dedicated inverse probes preserve unclipped RGB.
See [COLOR_ADAPTER_VALIDATION.md](COLOR_ADAPTER_VALIDATION.md) for the fixed
measured native-float bounds, 113 new tests and detailed scope. color.py now
exists. **Gate 3 is complete: its 318 tests pass, with zero failures, skips or
xfails.** MATLAB parity remains unestablished.

## Gate 4 current state: implementation with open acceptance boundaries

The whole-image, non-masked pipeline now implements all eight modes and all
three color spaces with repaired combined-mode/iteration chaining. Its 116
API/dataflow tests and 480 reference stage tests pass. The 480 strict
end-to-end/captured-histogram replay cases contain 150 ordinary failures.
The complete suite reports **1,244 passed, 150 failed; no skips or xfails**.
All prior 318 tests remain green and unchanged.

The new failures are 148 HSV terminal-quantization cases and two full-chain
replay cases with histogram-generated spectral degeneracy. Working V is exact;
HSV native differences can cross terminal half-integer boundaries. Casting the
same Octave native RGB in Python yields exact terminal values. All 1,074
well-conditioned spectral replays are exact; two of six generated-degeneracy
stages differ and become exact with common Octave forward phase/magnitude.
No lower-level algorithm or tolerance was changed. **Gate 4 is incomplete.**

See [PIPELINE_VALIDATION.md](PIPELINE_VALIDATION.md) for API, the full mode/
colorspace/iteration matrix, histogram invariants, localization and review
questions. No masks, optimized histograms, file I/O, CLI, video or release work
has begun. The reference dispatcher is exercised through an external in-memory
harness, not its interactive/filesystem shell.

## Historical kernel measurements
The following original measurements and failure counts describe the historical
pre-adoption checkpoint and remain evidence, not current unexplained failures.

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
| Nonfinite rescale semantics | 12 Octave-probed cases: 24 exact output checks and 12 exact extrema checks |
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

## Historical Gate 2 discrepancy: degenerate Fourier components

Before policy adoption this substantive discrepancy blocked the gate. That suite reported
**133 passed, 18 failed**. All original 58 tests pass. The 18 FFT failures are
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
rule would establish faithful parity. The initial bounded investigation is
preserved in [FFT_DIAGNOSTICS.md](FFT_DIAGNOSTICS.md). Controlled Octave runs
did not show changed final uint8 outputs, although an intermediate measure
run showed small FFT roundoff changes. The subsequent rescale correction and
new measurements are in [NONFINITE_RESCALE.md](NONFINITE_RESCALE.md).

## Confirmed Python bug repaired

The 12-case Octave probe establishes that extrema omit NaNs but retain Inf,
return NaN for all-NaN reductions, and emit no execution warnings for the
probed cases. Python rescale now uses a local helper implementing those
reductions. Option 1 omits an all-NaN member's extrema; option 2 retains ordinary
means and propagates them. Pixels are untouched until the terminal uint8 cast.
All 36 new reference tests pass, and ordinary finite behavior stays exact.

All four combinations of Python/Octave inverse FFT and Python/Octave rescaling,
fed the same Octave forward-derived decomposition, now give 90/90 exact outputs.
This isolates the earlier two downstream mismatches to the rescaling bug.

## Backend-sensitive SHINE behavior and current backend status

The fix does not remove forward phase or radial-energy degeneracy. NumPy remains
51/90 exact outputs (maximum error 255; pixel-weighted MAE 5.773343187977335).
Matched-orientation pyFFTW improves from 83/90 to 85/90 (maximum error 12;
pixel-weighted MAE 0.06282335550628233). Its remaining five mismatches are rooted
in source 3 of the degenerate 5x7 specMatch set. NumPy's 39 mismatching outputs
are all traced to forward phase/radial-energy degeneracy, sometimes propagated
to other images by correctly implemented set-wide scaling. No unexplained
well-conditioned-input mismatch was found in this corpus.

NumPy remains the runtime backend; pyFFTW is not required or adopted. Original
fixtures, all 18 failing tests and tolerances are unchanged. The old diagnostic
records are preserved; new evidence is under
`reference/diagnostics/nonfinite_rescale/`. Backend choice and any future
zero-component policy require a separate decision. Gate 3 remains out of scope.

The subsequent [backend policy study](FFT_BACKEND_POLICY.md) independently
screens 21 synthetic arrays and three bundled photos at two resolutions.
NumPy and matched pyFFTW each match all 162 new uint8 outputs exactly. It
recommends retaining NumPy with documented degeneracy limits. This is a
recommendation awaiting policy adoption; it does not alter the gate, any test
status, or the existing bounds. New evidence lives in
`reference/backend_policy/`, separate from the earlier diagnostic history.

At that historical FFT checkpoint, HSV/CIELab comparisons had not been
attempted. Subsequent color work is documented above: scikit-image is now a
runtime dependency for HSV only, with its declared transitive dependencies
(including SciPy). The later in-memory mode/iteration investigation is recorded
in PIPELINE_VALIDATION.md; its unresolved acceptance boundaries are listed above.

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
