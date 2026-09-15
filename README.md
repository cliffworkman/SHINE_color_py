# SHINE_color Python research implementation

Local behavioral reimplementation of the repaired SHINE_color toolbox.
GNU Octave is the current executable reference; exact MATLAB numerical parity
is untested and remains a future, non-blocking secondary target.

Gate 2 is complete: the Phase 1 kernel is validated against the recorded
GNU Octave corpus, with explicit backend-sensitive Fourier degeneracy tests.
NumPy/pocketfft is the Python reference FFT backend for v0.1. Both frequency
operations match 162 independently screened synthetic/photo outputs exactly.
No special zero handling is introduced; this is not universal Octave or MATLAB
parity. The color layer uses scikit-image for HSV and a NumPy adapter matching
the recorded Octave Lab conventions. All 102,193 validated working L/V values
and tested uint8 reconstructions agree exactly; see
[color evidence](docs/COLOR_ADAPTER_VALIDATION.md). Gate 3 is complete and all
318 tests pass. Orchestration remains unimplemented and Gate 4 requires review.

See [validation evidence](docs/VALIDATION.md), the
[adopted FFT policy](docs/FFT_BACKEND_POLICY.md), and
[fixture reproduction instructions](reference/octave/README.md).
The [FFT investigation](docs/FFT_DIAGNOSTICS.md) and
[NaN-rescaling correction](docs/NONFINITE_RESCALE.md) remain historical evidence.
pyFFTW remains optional diagnostic tooling outside runtime and normal dev extras.

Install development dependencies with `python -m pip install -e ".[dev]"`.
Run tests with `python -m pytest -q -p no:cacheprovider`.

This repository is local research work pending a licensing/provenance decision.
No public software license or publication is claimed. Masking, optimized
histogram matching, wizard, video, GUI and upscaling are out of scope.
