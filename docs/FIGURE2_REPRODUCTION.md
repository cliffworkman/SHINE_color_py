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
`histMatch.m` and `lum2scale.m` are byte-identical for this operation.

The historical plotting code provides no contrary source evidence: the earlier
`diag_plots.m` has no numeric labels, while the later `diagPlots.m` computes
indexed `mean2`/`std2` values and rounds them for display. No cat 2 correction
is inferred from that inspection.

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

The fourteen Figure 2 audit checks and the ten Figure 2 baseline checks pass in
the current interpreter. The repository's recorded full-regression result is
1,514 passed under Python 3.12.10, NumPy 2.1.3, SciPy 1.15.1 and Pillow 10.4.0.
The currently selected interpreter reports NumPy 1.26.4, SciPy 1.13.1 and
Pillow 12.1.1; its unrelated pre-existing ultra-tight color and degenerate
spectrum checks are environment-sensitive. No tolerance, xfail or algorithm
was changed for this audit. Image-bearing outputs remain ignored, and no
remote, push, tag or release was made.
