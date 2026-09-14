# SHINE_color Python research implementation

Local behavioral reimplementation of the repaired SHINE_color toolbox.
GNU Octave is the current executable reference; exact MATLAB numerical parity
is untested and remains a future, non-blocking secondary target.

The Phase 1 numerical kernel is implemented. Octave fixtures validate scaling,
luminance and histogram invariants on the recorded corpus, but expose unresolved
Fourier degeneracies. **Gate 2 is blocked: the full suite currently has 133
passing tests and 18 failing reference comparisons.** Color conversion and
whole-image orchestration are not yet implemented.

See [validation evidence and the stopping condition](docs/VALIDATION.md) and
[fixture reproduction instructions](reference/octave/README.md).
The [bounded FFT investigation](docs/FFT_DIAGNOSTICS.md) separates backend
sensitivity from the [repaired NaN-rescaling bug](docs/NONFINITE_RESCALE.md).
NumPy remains the runtime FFT backend; pyFFTW is diagnostic tooling only.
The [backend policy study](docs/FFT_BACKEND_POLICY.md) recommends retaining
NumPy: both backends match all 162 new screened synthetic/photo outputs exactly.
That recommendation has not reclassified the existing 18 failures.

Install development dependencies with `python -m pip install -e ".[dev]"`.
Run tests with `python -m pytest -q -p no:cacheprovider`.

This repository is local research work pending a licensing/provenance decision.
No public software license or publication is claimed. Masking, optimized
histogram matching, wizard, video, GUI and upscaling are out of scope.
