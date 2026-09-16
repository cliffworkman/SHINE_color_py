# SHINE_color Python research implementation

Independently implemented Python behavioral reimplementation of the repaired SHINE_color toolbox.
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
The Gate 4 suite has 1,412 passes; see [pipeline evidence](docs/PIPELINE_VALIDATION.md).

Gate 5A adds a Python file API for PNG/JPEG input and exact RGB PNG output.
Each ordered stimulus set is normalized as one group through the existing
pipeline, with collision protection and a JSON provenance manifest.
See [file workflow](docs/FILE_WORKFLOW.md) for examples, representation policies
and partial-failure behavior. No scientific kernel or reference fixture changed.
Gate 5A is complete: **1,499 tests pass, with zero failures, skips or xfails**.

The subsequent architectural pilot added research-only QC tooling and brought
the checkpoint to 1,504 passing tests. The final preflight records
[provenance and unresolved public licensing](docs/PROVENANCE_AND_LICENSING.md).
The [Figure 2 investigation](docs/FIGURE2_REPRODUCTION.md) records the original
statistic mismatch, separates Pillow and Octave JPEG decoding, and demonstrates
exact histogram/output parity on common inputs. A historical publication
reproduction is not claimed. The recorded pinned-environment preflight suite
passes **1,514 tests**, including ten offline baseline checks. The Figure 2 audit adds fourteen focused
checks, and the repaired 0.0.6 confirmation adds seven more; current validation
and the recorded pinned-environment full regression are documented in [the
audit record](docs/FIGURE2_REPRODUCTION.md).

## Reproducing SHINE_color's published histogram-matching example

SHINE_color_py was tested against the same three sample files used in the
original SHINE_color Figure 2 example. To separate JPEG-decoder effects from
algorithmic behavior, historical SHINE_color 0.0.5, repaired 0.0.6 and Python
were also given identical decoded RGB arrays. On common decoded input they
produce identical 256-bin input histograms, target histograms, matched
histograms and sorted matched Value-channel outputs in the recorded audit.
The 0.0.6 follow-up rechecked those archived Octave results; it did not run a
fresh Octave comparison. With Pillow-decoded inputs, matched outputs give
M = 126.69 and SD = 74.77, reproducing Figure 2's displayed post-match values.

![Figure 2 validation comparison](docs/assets/figure2_validation_comparison.png)

| Image | Figure 2 baseline | Supplied source | Post-match |
| --- | --- | --- | --- |
| cat1 | 172.47 / 44.72 | 172.48 / 44.73 | 126.69 / 74.77 |
| cat2 | 80.34 / 127.26 | 80.34 / 68.07 | 126.69 / 74.77 |
| cat3 | 127.26 / 76.76 | 127.26 / 76.76 | 126.69 / 74.77 |

Values are mean / sample SD of working HSV V on the 0–255 scale. Source values
are Pillow-decoded and rounded to two decimals; the post-match column is the
Pillow-common path. Exact common-input histogram and sorted-value
parity is the comparison contract. Figure 2's cat2 baseline reports M = 80.34,
SD = 127.26, while the supplied image reproduces the mean but not that SD.
At this mean, SD 127.26 exceeds the attainable bound of approximately 118.46
for 0–255 data. The origin of this apparent annotation/reporting discrepancy
is unknown. This SD is not used as a software golden. Cat1's calculated values
correspond to the displayed values if truncated to two decimals, a plausible
formatting explanation rather than an established reporting convention.
JPEG-decoder differences also affect decoded pixels: the Octave-common path
rounds to post M = 126.70, SD = 74.78. These display-level differences do not
change the common-input algorithmic comparison.

See the [detailed Figure 2 audit](docs/FIGURE2_REPRODUCTION.md) and
[provenance/licensing record](docs/PROVENANCE_AND_LICENSING.md).

See [validation evidence](docs/VALIDATION.md), the
[adopted FFT policy](docs/FFT_BACKEND_POLICY.md), and
[fixture reproduction instructions](reference/octave/README.md).
The [FFT investigation](docs/FFT_DIAGNOSTICS.md) and
[NaN-rescaling correction](docs/NONFINITE_RESCALE.md) remain historical evidence.
pyFFTW remains optional diagnostic tooling outside runtime and normal dev extras.

Install development dependencies with `python -m pip install -e ".[dev]"`.
Run tests with `python -m pytest -q -p no:cacheprovider`.
Runtime dependencies are NumPy and Pillow; the scientific core remains NumPy-only.
The optional `reference` extra retains
scikit-image 0.25.2 solely to reproduce comparisons with the displaced converter.

This repository is local research work pending a licensing/provenance decision.
No public software license or publication is claimed. Masking, optimized
histogram matching, wizard, video, GUI and upscaling are out of scope.
