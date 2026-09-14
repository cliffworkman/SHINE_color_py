# FFT backend policy study — recommendation for review

**Recommend option B: retain NumPy for v0.1.** Both Python backends produced
exact Octave uint8 results on all 126 independently screened synthetic outputs
and all 36 outputs from three bundled photographs at two resolutions. The
large NumPy disagreements remain confined to the earlier degenerate corpus
in the evidence collected so far. This small sample does not establish that
real stimuli can never have degenerate spectra.

This is a recommendation, not a new acceptance policy. Runtime dependencies,
algorithm, original fixtures, tolerances and all existing tests are unchanged.
Gate 2 remains blocked with 133 passing tests and 18 ordinary failures.
Gate 3 has not begun. No zero handling is proposed for implementation here.

## Independent conditioning and corpus

[CRITERIA.md](../reference/backend_policy/CRITERIA.md) was written before final
output comparisons. Source selection and the conditioning screen read no
matching outputs. For Octave's FFT of `double(image)/255`, define
`S = max(1, max(abs(FFT)))`. Require every magnitude and every occupied,
retained sfMatch source-amplitude bin sum to exceed `1e-10*S`. The radial
screen uses the established Python radial grid and column-major summation;
these are diagnostics of exported spectra, not captured private Octave locals.
Empty bins and bins outside SHINE's cutoff are irrelevant denominators.
This threshold classifies conditioning only; every output comparison is exact.
It does not guarantee arbitrary downstream rescale/quantization conditioning.

Seven predeclared groups contain three uint8 arrays each: fixed-seed PCG64
uniform noise, an analytic spatial pattern with integer perturbations in
[-3,3], and a multiscale noise texture with fine detail. Seeds are 20260914
through 20260920. No candidates were excluded, replaced or regenerated based
on parity. All 21 passed. Shapes cover both parities, squares and rectangles.

Three clearly identifiable toolbox samples, `cat1.jpg`, `cat2.jpg`, `cat3.jpg`,
were read from the sibling reference checkout's `SHINE_color_INPUT/samples`
directory. Their green channels were tested at native 1200x1200 and at
300x300 via `[::4,::4]` without interpolation. This uses six source arrays
from three photographs, not six independent photographs. There is no color
conversion. Source hashes and exact extracted arrays are retained; the
reference checkout and JPEGs remain unchanged. These are bundled workflow
examples, not an experimental-stimulus certification or representative survey.
Both groups were retained regardless of conditioning and passed the screen.

| Group | Minimum source magnitude | Minimum occupied retained radial denominator |
| --- | ---: | ---: |
| Synthetic 31x31 | 0.006775416 | 32.862786 |
| Synthetic 31x48 | 0.009234143 | 10.754633 |
| Synthetic 48x31 | 0.006439218 | 13.280568 |
| Synthetic 32x48 | 0.009894270 | 20.521581 |
| Synthetic 64x64 | 0.007843137 | 88.089839 |
| Synthetic 63x79 | 0.002768511 | 76.128917 |
| Synthetic 128x128 | 0.004762872 | 208.586677 |
| Cats 1200x1200 | 0.024829009 | 58727.827566 |
| Cats 300x300 | 0.018619057 | 6127.390167 |

Values are minima across each group's three sources. Every source has zero
exact-zero coefficients and zero counts below each of 1e-15, 1e-14, 1e-13,
1e-12; no coefficient or relevant radial denominator is effectively zero by
the predeclared screen. Python spectra pass it too. Full per-image values,
scales and per-bin denominators are in
[conditioning.json](../reference/backend_policy/conditioning.json) and
[results.json](../reference/backend_policy/results.json).

## Results and localization

Each source was processed with sfMatch and specMatch at all three rescaling
options, including option 2. Octave calls the public unmodified functions at
reference commit `870e058fe8bf1e4090baf2401ff0e127d1c0237a`. Each backend is
compared separately against Octave, not merely against the other Python run.

| Corpus | Backend | Exact image outputs | Max absolute error | Mean image MAE | Pixel-weighted MAE | Compared pixels |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| Screened synthetic | NumPy | 126/126 | 0 | 0 | 0 | 556,740 |
| Screened synthetic | Matched pyFFTW | 126/126 | 0 | 0 | 0 | 556,740 |
| Three photos, two sizes | NumPy | 36/36 | 0 | 0 | 0 | 27,540,000 |
| Three photos, two sizes | Matched pyFFTW | 36/36 | 0 | 0 | 0 | 27,540,000 |

The nonzero pixel-difference distribution is empty in all four comparisons.
Each operation/option is exact independently. The 324 individual image
comparisons are recorded in
[output_comparisons.csv](../reference/backend_policy/output_comparisons.csv).

The earliest numerical differences occur in the forward complex FFT. There
is **no observed substantive output divergence** on this corpus. Intermediate
comparisons were made even when final outputs agreed:

| Corpus/backend | Maximum complex FFT error | Maximum phase error, radians |
| --- | ---: | ---: |
| Synthetic / NumPy | 1.8189894e-12 | 2.0679569e-12 |
| Synthetic / pyFFTW | 2.8353322e-13 | 4.5385917e-13 |
| Photos / NumPy | 5.8207661e-11 | 5.0350835e-12 |
| Photos / pyFFTW | 1.1641532e-10 | 4.6007642e-12 |

These size-dependent absolute errors are observations, not proposed tolerance
changes. pyFFTW's forward error is not uniformly smaller. Source magnitudes,
phases and averaged target magnitudes were recorded. The comparison tool
also implements Octave-forward injection for a mismatching operation; no new
case needed that replay. Exact final uint8 agreement does not imply bitwise
identical floating-point intermediates.

The earlier history remains separate and unchanged:

| Degenerate corpus after the rescale fix | Exact outputs | Max error | Pixel-weighted MAE |
| --- | ---: | ---: | ---: |
| NumPy | 51/90 | 255 | 5.773343187977335 |
| Matched pyFFTW | 85/90 | 12 | 0.06282335550628233 |

See [NONFINITE_RESCALE.md](NONFINITE_RESCALE.md) for the classification and
90/90 exact downstream replays with Octave forward quantities, and
[FFT_DIAGNOSTICS.md](FFT_DIAGNOSTICS.md) for the original planner probes.
Controlled Octave planning changed some intermediate roundoff, but did not
change the probed final uint8 outputs; we do not claim observed Octave final
output instability. No new implementation error was exposed by this study.

## Deployment cost, checked 2026-09-14

Current pyFFTW 0.15.1 requires Python >=3.11 and supplies standard CPython
3.11–3.14 wheels for all four platforms below. The project's declared
Python >=3.10 range therefore is not fully served by that release. Version
0.15.0 has CPython 3.10 wheels on all four platforms; retaining Python 3.10
would require validating an older dependency branch or changing the Python
floor. Open-ended support for future Python versions is not guaranteed by
current wheels. [Current PyPI release](https://pypi.org/project/pyFFTW/),
[0.15.0 metadata](https://pypi.org/pypi/pyfftw/0.15.0/json).

The following are actual downloaded CPython 3.12 wheel inventories, checked
against PyPI SHA256 hashes in memory. No package or system library was
installed during this deployment inspection. MB means decimal million bytes;
expanded size excludes installation overhead and NumPy, already required.

| Platform | Current wheel target | Download / expanded MB | Bundled FFTW marker |
| --- | --- | ---: | --- |
| Windows x86-64 | win_amd64 | 2.63 / 7.31 | 3.3.5 |
| macOS Intel | macOS 13+ x86_64 | 3.32 / 9.27 | 3.3.10 |
| macOS Apple Silicon | macOS 14+ arm64 | 1.70 / 4.45 | 3.3.10 |
| Linux x86-64 | manylinux2014 / glibc 2.17+ compatible tags | 3.17 / 9.52 | 3.3.5 |

These wheels include FFTW native libraries and the Python extension; macOS
and Linux also include threading libraries. Separate FFTW installation or
compilation is unnecessary for a compatible wheel. The 0.15.0 CPython 3.10
macOS Intel wheel targets 12+, Apple Silicon 14+, and Linux glibc 2.28+.
Older operating systems, other ABIs and musl systems must not be assumed
covered. Raw filenames, binary inventories, versions and sizes are in
[deployment.json](../reference/backend_policy/deployment.json).

For unmatched configurations, source installation requires a native build
toolchain and FFTW libraries; this creates a meaningful fallback burden.
We have no empirical installation-failure rate and did not test installations
on macOS or Linux. For the mainstream wheel matrix, compilation should not
normally be required. Compared with NumPy alone, this is a modest download
but an additional binary compatibility and release-validation obligation.
[Official pyFFTW requirements and build instructions](https://github.com/pyFFTW/pyFFTW).

## Reproducibility and scientific meaning

The executed environment was Windows x86-64, Python 3.12.10, NumPy 2.1.3,
SciPy 1.15.1 and optional pyFFTW 0.15.1 with Windows FFTW binary marker 3.3.5.
The pyFFTW `fftw_version` property is empty on this installation; the binary
marker is recorded separately rather than silently substituted. Octave
11.1.0 uses FFTW 3.3.10, planner estimate, three threads. Its initial wisdom
string is nonempty but contains no plan entries. Conditioning and output
runs each record this state in their manifests.

The matched adapter uses transposed contiguous orientation, c2c transforms,
one thread, explicit FFTW_ESTIMATE and forgotten wisdom before each
backend/group. This is a diagnostic process-local adapter; nothing imports it
from the installed package. Planner effort and threads are controllable through
the documented interface. [pyFFTW NumPy interface](https://pyfftw.readthedocs.io/en/latest/source/pyfftw/interfaces/numpy_fft.html).

Using estimate and fixed threads avoids timing-based plan selection, and
pinning builds, orientation, transform kind and wisdom policy makes a nominated
environment reproducible enough to test. It does not guarantee cross-platform
or cross-version parity: the inspected wheels already bundle different FFTW
versions. FFTW itself explains why planning choices can change rounding.
[FFTW reproducibility FAQ](https://fftw.org/faq/section3.html#nondeterministic).
NumPy also needs recorded versions/platforms and repeated reference checks;
the simpler dependency set is not a universal bitwise reproducibility promise.

At well-conditioned frequencies, source phase is meaningful. Both backends
preserve the tested SHINE output behavior exactly, with tiny intermediate
differences; there is no measured scientific advantage to pyFFTW here.
At mathematical zeros, phase is undefined, and SHINE magnitude replacement
can promote incidental roundoff phase into visible finite-amplitude structure.
Near-zero radial denominators similarly amplify otherwise negligible errors.
The resulting images differ materially, but those differences do not make
one arbitrary zero-phase choice scientifically privileged.

Thus pyFFTW's demonstrated benefit in this study is primarily closer mimicry
of the nominated Octave runtime on degenerate spectra. Reproducing an existing
Octave-generated stimulus pixel for pixel could itself be a valid user goal;
85/90 parity still would not meet that goal universally. No evidence here
justifies imposing a second production backend or native dependency for that
partial benefit. Degeneracy is possible in real workflows (for example highly
regular synthetic stimuli), even though it was absent from these photographs.

## Decision and next bounded step

Choose **B, retain NumPy**, with explicitly limited validation claims and
documented backend-sensitive degeneracy. Do not adopt A solely to make most
old examples green: the remaining five pyFFTW output mismatches persist.
Do not adopt C without a concrete requirement for alternate runtime fidelity;
it would add validation and user-facing configuration without a measured
benefit on the screened corpus.

After that policy is reviewed and adopted, recommend a separate Gate 2
test-policy change: preserve all degenerate inputs and raw Octave goldens as
historical evidence, classify their cases explicitly as backend-sensitive
degeneracy diagnostics, and add strict exact reference coverage for the
independently screened corpus. Divergence tests should verify the documented
mechanism and scope, not accept arbitrary mismatches or require a particular
error count across changing FFT builds. Finite output shape/dtype and
stage-specific meaningful-frequency or radial properties are suitable
invariants; invariants involving post-clipping spectra require separate
justification. Keep exact runtime-specific reproduction checks available in
a nominated environment, but do not make incidental zero phases the universal
algorithm contract. No skip, xfail, fixture edit or test reclassification has
been made here; the existing 18 remain ordinary failures.

No epsilon denominators, canonical phase, masking, regularization or other
algorithmic repair is warranted by the present evidence. Any such behavior
change requires a separate scientific decision.

If the recommendation is adopted, use this exact validation claim:

> In the recorded Windows/Python/NumPy and GNU Octave 11.1.0 environments,
> the NumPy sf_match and spec_match implementations produce exact uint8
> outputs for rescale options 0, 1 and 2 on 21 independently screened
> synthetic arrays and green-channel arrays from three bundled photographs
> at two resolutions. Backend-sensitive divergences remain documented for
> degenerate Fourier spectra. This establishes neither universal Octave
> parity nor MATLAB, color-conversion or pipeline validation.

The next bounded step is to review/adopt the backend and failing-test policy,
then implement that classification and exact screened-corpus coverage in a
separate change, rerun Gate 2, and assess its stopping condition. Gate 3 must
remain stopped until that work is complete.

## Artifacts and checks

Added `reference/backend_policy/`: predeclared criteria, deterministic
generator, screen, comparison, deployment inspector, independent audit tool,
27 source arrays in nine MAT files, 21 synthetic PNG previews, manifests,
conditioning, per-output comparisons and deployment/audit evidence. Large
intermediate spectra and Octave output MAT files are reproducible and kept
only in ignored `reference/.cache/backend_policy/`; their run-specific hashes
bind the recorded results. MAT headers can change on regeneration, so hashes
identify this run rather than promise byte-identical containers on rerun.
Added the external `reference/octave/export_policy_corpus.m` harness and this
report; updated README, validation and harness documentation links.

Executed the generation, independent screen, both Octave phases, full backend
comparison, PyPI/wheel inspection and independent evidence audit. The audit
checks source-file hashes and channel extraction, PNG/MAT equality,
shapes/dtypes, recorded hashes, CSV/JSON agreement and independently aggregated
distributions. All 324 new output comparisons are exact. The unchanged full
suite, `python -m pytest -q -p no:cacheprovider --tb=no`, reports **133 passed,
18 failed**. The Python runtime/dependency files, existing tests, historical
diagnostics and canonical reference checkout are unchanged. Local Git only,
on `phase2/octave-reference`; commit message:
`Evaluate FFT backend policy for Octave fidelity`.
