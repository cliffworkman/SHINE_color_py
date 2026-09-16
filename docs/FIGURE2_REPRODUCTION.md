# Figure 2 reproduction: decoder and common-input audit

The printed Figure 2 source statistics remain a baseline mismatch and are not
treated as normative goldens. The authorized follow-up audit separates that
source discrepancy from JPEG decoding and from the histogram-matching
implementation. It does not change the canonical reference, source JPEGs,
algorithms, tolerances or decoder policy.

## Publication and inspected evidence

Dal Ben, R. (2023). *SHINE_color: Controlling low-level properties of colorful
images*. MethodsX, 11, 102377. [DOI](https://doi.org/10.1016/j.mex.2023.102377).
The [published article](https://pmc.ncbi.nlm.nih.gov/articles/PMC10522894/)
identifies Figure 2 as HSV histogram matching and attributes the photos to
Pexels. The paper's article license is not assumed to settle standalone
sample-photo rights.

The supplied reference contains a draft/preprint rather than the final
publisher PDF: `../SHINE_color_fork/paper/dalben_shine_color_preprint_v3.pdf`.
Page 3 and `../SHINE_color_fork/paper/fig2.png` were visually inspected. Both
contain the supplied values, including cat 2's SD of 127.26. The online
publisher-figure view was not used to infer a correction.

Inspected artifact SHA-256:

- Preprint PDF: `a68f5026df6750264707794bc47cf5141ad34bfb34a34962d3fa3b3bf36cb0f1`
- Reference `fig2.png`: `8d924c95652c7baca9429060810422f29bf8e11ada1f543baade2f058b73a01e`

## Exact sources and baseline

Local source directory: sibling `SHINE_color_fork/toolbox/SHINE_color_INPUT/samples/`.
No image was extracted or cropped from a figure. The original JPEGs match
their first recorded reference commit
`74884eb7fe0b4a2f5dc09ee155e78ac576871526` and the pinned repaired snapshot
`870e058fe8bf1e4090baf2401ff0e127d1c0237a`.

| Source | Exact JPEG SHA-256 |
| --- | --- |
| cat1.jpg | `aa350a25a0fedbe875aab0cd69e5bf925e3d4c9a5da2a1769ce34c17e63eae9a` |
| cat2.jpg | `68fc8a17422f4b1d0ed3491f21e46e262261e4abdabfa459487765cd19e5dc87` |
| cat3.jpg | `66fdaa81b735b6a9261bdce7314698ad912068048fa115c03a636d0257d5bdeb` |

Each is 1200 x 1200 RGB, orientation 1, with no ICC profile. The validated
I/O layer decodes stored JPEG codes without resizing, cropping, upscaling,
gamma or ICC transformation. Working V is the maximum decoded RGB channel;
statistics use the sample SD (`N-1` denominator).

| Source | Pillow mean | Pillow sample SD | Figure M / SD | Matches M / SD |
| --- | ---: | ---: | --- | --- |
| cat1.jpg | 172.47983958333333 | 44.729233010564286 | 172.47 / 44.72 | No / No |
| cat2.jpg | 80.34050555555555 | 68.07128018711924 | 80.34 / 127.26 | Yes / No |
| cat3.jpg | 127.26124166666666 | 76.76305834707568 | 127.26 / 76.76 | Yes / Yes |

Cat 2's printed SD cannot describe a sample of values in [0, 255] at the
printed mean: the maximum possible sample SD is 118.457764. The repeated
127.26 value is also cat 3's printed mean, so an annotation error is plausible,
but its cause is not asserted. The requested exploratory settings remain HSV,
mode 2, one iteration, rescale option 1 and one three-cat group; rescale is
ignored by mode 2 and histogram ties remain unseeded.

## Decoder comparison

Octave 11.1.0/image 2.18.2 and Pillow 10.4.0 decode the same JPEG bytes to
different RGB arrays. The following metrics count scalar channel values and
compare the two decoded arrays directly:

| Source | Unequal / 4,320,000 | Unequal % | Max abs diff | Mean abs diff |
| --- | ---: | ---: | ---: | ---: |
| cat1.jpg | 1,263,181 | 29.2403009% | 30 | 0.4777326 |
| cat2.jpg | 544,174 | 12.5966204% | 19 | 0.1860181 |
| cat3.jpg | 414,219 | 9.5884028% | 11 | 0.1334905 |

The corresponding Octave-JPEG working-V mean/sample-SD pairs are
172.48752777777779/44.72812504298803, 80.35766111111111/68.10529703578258
and 127.26916666666666/76.76540498640563. This establishes a material decoder
input difference, but does not identify the historical publication decoder.

## Common-input paths and post-match parity

The audit runs two independent paths through Python, Octave and the exact local
0.0.5 toolbox history:

- **Path A:** Pillow decodes each JPEG once; that exact RGB array is passed to
  both implementations as lossless data.
- **Path B:** Octave decodes each JPEG once; that exact RGB array is passed to
  both implementations as lossless data.

Both paths use HSV mode 2, one iteration, rescale 1 and one group. For every
path, Python and Octave have exact integer pre-histogram, target-histogram and
post-histogram counts and exact sorted working-V output values. The largest
Python-versus-Octave difference in floating summary statistics is below
`3.2e-11`; this is strong common-input algorithmic parity.

| Path / implementation | Post mean | Post sample SD | Printed 126.69 / 74.77 |
| --- | ---: | ---: | --- |
| A / Python, Octave, historical | 126.69377430555555 | 74.7712721076 | Yes / Yes |
| B / Python, Octave, historical | 126.70467916666666 | 74.7805227139 | No / No |

The post-label agreement is therefore decoder-dependent. The exact cat 2
baseline annotation remains unexplained, while the common-input comparison
does not support a Python histogram or pipeline implementation error. The old
and repaired toolbox routines `avgHist.m`, `hist2list.m`, `match.m`,
`histMatch.m` and `lum2scale.m` are operation-equivalent for this behavior;
the repaired confirmation verifies that empirically.

The historical plotting code provides no contrary source evidence: the earlier
`diag_plots.m` has no numeric labels, while the later `diagPlots.m` computes
indexed `mean2`/`std2` values and rounds them for display. No cat 2 correction
is inferred from that inspection.

## Repaired 0.0.6 confirmation

The existing external Octave results were rechecked against the frozen repaired
0.0.6 snapshot named `870e058fe8bf1e4090baf2401ff0e127d1c0237a`. The live
sibling checkout is clean at `c602d4582f51bde8bda4ed10a360734f62e538dc`;
its toolbox has the same normalized text tree, while the snapshot remains the
identity used by the archived reference run. No checkout or source file was
modified. The historical comparison uses local 0.0.5 history at
`330a9be6e49f59e5d68fb985744b2a50c278e8d8`.

The table uses SHA-256 prefixes for each three-image histogram or sorted-value
set. Full hashes and exact comparison booleans are in the compact fixture.
`M / SD` is listed for post rows; tiny cross-runtime reduction differences are
reported separately.

| Path / stage | historical 0.0.5 | repaired 0.0.6 | SHINE_color_py | Octave reference |
| --- | --- | --- | --- | --- |
| Path A pre | `f0bd…/67ef…/8f47…` | same | same | same |
| Path A target | `934c590c…` | same | same | same |
| Path A post | `2651…` (`M 126.693774 / SD 74.771272`) | same | same | same |
| Path B pre | `1e70…/0882…/b3cf…` | same | same | same |
| Path B target | `b5fe8aa2…` | same | same | same |
| Path B post | `ab34…` (`M 126.704679 / SD 74.780523`) | same | same (`SD 74.780523`) | same |

For both paths, 0.0.5 versus 0.0.6 is exact for pre histograms, target
histogram, post histograms and sorted post values. The repaired snapshot also
matches the archived Octave reference exactly on those contracts and matches
Python exactly on the same integer/sorted-value contracts. Means and sample SDs
agree numerically; independent reductions differ only at approximately
`2.2e-12` between the two Octave runs and `3.2e-11` between Octave and Python.
Thus the repaired 0.0.6 changes do not alter Figure 2 HSV histogram-matching
behavior.

The optional natural-JPEG 0.0.6 path was not rerun because GNU Octave is not
currently available on the active PATH. Its absence is explicit in the
confirmation record; no decoder result is inferred. The common-input result
therefore remains separate from the known Pillow/Octave JPEG-decoder effect.

The printed baseline remains `172.47 / 44.72`, `80.34 / 127.26` and
`127.26 / 76.76`, with printed post `126.69 / 74.77`. Cat 2's SD remains an
impossible/non-normative annotation. Cat 1's printed values are consistent
with truncating the calculated Pillow values (`172.479839…` and `44.729233…`),
but truncation remains only a plausible formatting explanation.

## Artifacts, regression and reproduction

The ignored audit directory is
`reference/.cache/figure2_audit_20260916/`:

- `figure2_reproduction.png`: source/decoder and pre/post histogram comparison;
- `figure2_reproduction_metrics.json`: full machine-readable audit record;
- `figure2_reproduction_histograms.csv`: compact histogram rows and hashes.

The reusable entry is `reference.figure2_audit.run(...)`. It preserves source
hashes, uses external Octave only through the checked-in export scripts, and
does not modify the canonical reference checkout. The tracked fixture
`tests/reference/fixtures/figure2_audit.json` contains hashes, histogram
counts, summary values and comparison evidence, but no spatial pixel data.

The repaired confirmation uses `reference.figure2_repaired_confirm` and the
tracked fixture `tests/reference/fixtures/figure2_repaired_confirmation.json`.
Its ignored artifact directory is
`reference/.cache/figure2_repaired_confirmation_20260916_v8/`.

The fourteen Figure 2 audit checks, ten Figure 2 baseline checks and seven
repaired-confirmation checks pass. The full regression was subsequently rerun
under the validated Python 3.12.10, NumPy 2.1.3, SciPy 1.15.1 and Pillow 10.4.0
environment: **1,535 passed**. An earlier run in a different interpreter
(NumPy 1.26.4, SciPy 1.13.1, Pillow 12.1.1) had environment-sensitive color and
degenerate-spectrum failures; that is not the pinned validation environment.
No tolerance, xfail or algorithm was changed. Image-bearing audit outputs remain
ignored. The later GitHub publication decision is documented in the
[provenance record](PROVENANCE_AND_LICENSING.md).
