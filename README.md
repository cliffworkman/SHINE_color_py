# SHINE_color Python research implementation

Local behavioral reimplementation of the repaired SHINE_color toolbox.
GNU Octave is the current executable reference; exact MATLAB numerical parity
is untested and remains a future, non-blocking secondary target.

Gate 2 is complete: the Phase 1 kernel is validated against the recorded
GNU Octave corpus, with explicit backend-sensitive Fourier degeneracy tests.
NumPy/pocketfft is the Python reference FFT backend for v0.1. Both frequency
operations match 162 independently screened synthetic/photo outputs exactly.
No special zero handling is introduced; this is not universal Octave or MATLAB
parity. NumPy adapters implement the recorded Octave HSV and Lab conventions.
All 102,193 validated working L/V values and tested uint8 reconstructions agree
exactly; see [color evidence](docs/COLOR_ADAPTER_VALIDATION.md) and the later
[HSV compatibility study](docs/HSV_ADAPTER_VALIDATION.md).
Gates 3 and 4 are complete. All 480 whole-image configurations meet the
documented contract: 478 strict deterministic/captured-histogram replays and
two positive dynamic spectral-degeneracy cases with exact common-forward
replay. HSV terminal outputs are exact throughout the pipeline corpus.
The full suite has **1,412 passes, zero failures, skips or xfails**;
see [pipeline evidence](docs/PIPELINE_VALIDATION.md).

See [validation evidence](docs/VALIDATION.md), the
[adopted FFT policy](docs/FFT_BACKEND_POLICY.md), and
[fixture reproduction instructions](reference/octave/README.md).
The [FFT investigation](docs/FFT_DIAGNOSTICS.md) and
[NaN-rescaling correction](docs/NONFINITE_RESCALE.md) remain historical evidence.
pyFFTW remains optional diagnostic tooling outside runtime and normal dev extras.

Install development dependencies with `python -m pip install -e ".[dev]"`.
Run tests with `python -m pytest -q -p no:cacheprovider`.
NumPy is the only runtime dependency. The optional `reference` extra retains
scikit-image 0.25.2 solely to reproduce comparisons with the displaced converter.

This repository is local research work pending a licensing/provenance decision.
No public software license or publication is claimed. Masking, optimized
histogram matching, wizard, video, GUI and upscaling are out of scope.
