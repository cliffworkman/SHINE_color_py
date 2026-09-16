# Figure 2 reproduction: baseline mismatch, stopped

This is **not a successful Figure 2 reproduction**. The original working-V
statistics fail the requested two-decimal baseline gate. Per that gate,
post-normalization execution and interpretation are deferred. No settings,
algorithms, JPEGs, tolerances or targets were changed to force a match.

## Publication and inspected evidence

Dal Ben, R. (2023). *SHINE_color: Controlling low-level properties of colorful
images*. MethodsX, 11, 102377. [DOI](https://doi.org/10.1016/j.mex.2023.102377).
The [published article](https://pmc.ncbi.nlm.nih.gov/articles/PMC10522894/)
identifies Figure 2 as HSV histogram matching and attributes the photos to Pexels.
The paper's article license is not assumed to settle standalone sample-photo rights.

The supplied reference contains a draft/preprint rather than the final
publisher PDF: `../SHINE_color_fork/paper/dalben_shine_color_preprint_v3.pdf`.
Page 3 and the separate `../SHINE_color_fork/paper/fig2.png` were visually
inspected. Both contain the values supplied in the task, including cat 2's
SD of 127.26. The online publisher-figure view was not accessible through the
web tool, so no unverified assertion about a corrected final figure is made.

Inspected artifact SHA-256:

- Preprint PDF: `a68f5026df6750264707794bc47cf5141ad34bfb34a34962d3fa3b3bf36cb0f1`
- Reference `fig2.png`: `8d924c95652c7baca9429060810422f29bf8e11ada1f543baade2f058b73a01e`

## Exact sources and frozen settings

Local source directory: sibling `SHINE_color_fork/toolbox/SHINE_color_INPUT/samples/`.
No image was extracted or cropped from a figure. The original JPEGs match
their first recorded reference commit `74884eb7fe0b4a2f5dc09ee155e78ac576871526`,
the pinned repaired snapshot `870e058fe8bf1e4090baf2401ff0e127d1c0237a`, and
the earlier file-workflow smoke hashes.

During the audit, an untracked local `paper/` directory appeared. Its PDF and
Figure 2 PNG match the reference paper assets, but its JPEGs are only 350 x
348, 350 x 346 and 350 x 350. Their origin was requested from the user; they
were not substituted for the exact upstream sample inputs. A read-only check
also failed to reproduce all printed baseline targets: their means/sample SDs
round to 172.48/44.73, 80.76/68.15 and 127.28/76.79. The folder is ignored and
unchanged. This additional version does not resolve the baseline gate.

| Source | Exact JPEG SHA-256 |
| --- | --- |
| cat1.jpg | `aa350a25a0fedbe875aab0cd69e5bf925e3d4c9a5da2a1769ce34c17e63eae9a` |
| cat2.jpg | `68fc8a17422f4b1d0ed3491f21e46e262261e4abdabfa459487765cd19e5dc87` |
| cat3.jpg | `66fdaa81b735b6a9261bdce7314698ad912068048fa115c03a636d0257d5bdeb` |

Each is 1200 x 1200, RGB, orientation 1, no ICC profile. The validated image
I/O layer decodes stored JPEG codes; no resizing, cropping, upscaling, gamma
or ICC transformation is applied. The current HSV adapter extracts uint8
working V. For these sources it exactly equals the maximum of decoded R/G/B.
Statistics use the pixel mean and sample SD (`N-1` denominator).

Requested subsequent normalization settings are frozen as HSV, mode 2,
iterations 1, rescale option 1, one three-cat group. Rescale is ignored by
mode 2. Histogram tie assignment would be unseeded; no tie randomization or
normalization has run in this reproduction arc.

## Original statistics

Calculated with Python 3.12.10, NumPy 2.1.3, Pillow 10.4.0; scientific code
at `0862b5f4635a3500afd823343b016189d0dd127e` was unchanged.

| Source | Python mean | Python sample SD | Rounded M / SD | Figure M / SD | Matches M / SD |
| --- | ---: | ---: | --- | --- | --- |
| cat1.jpg | 172.47983958333333 | 44.729233010564286 | 172.48 / 44.73 | 172.47 / 44.72 | No / No |
| cat2.jpg | 80.34050555555555 | 68.07128018711924 | 80.34 / 68.07 | 80.34 / 127.26 | Yes / No |
| cat3.jpg | 127.26124166666666 | 76.76305834707568 | 127.26 / 76.76 | 127.26 / 76.76 | Yes / Yes |

Changing sample SD to population SD does not fix these rounded discrepancies.
Cat 1's printed values are consistent with truncating these particular
measurements rather than rounding, but there is no evidence that this was the
publication's reporting convention. That possibility is not adopted as fact.

For any values between 0 and 255, sample variance is at most
`N/(N-1) * mean * (255-mean)`. At cat 2's mean this bounds sample SD by
118.457764; allowing the printed mean's two-decimal rounding interval still
cannot admit 127.26. Thus its printed mean/SD pair is internally inconsistent
under the specified representation/statistics. An annotation error is strongly
indicated, but no corrected historical value is asserted. The repeated number
127.26 also appears as cat 3's mean; copying it is a possibility, not a proven cause.

## Independent Octave baseline investigation

The new external `reference/octave/probe_figure2_baseline.m` calls the
unmodified pinned toolbox's `lum2scale` with Octave `rgb2hsv`, `imhist`,
`mean2` and `std2`. It performs no histogram matching. GNU Octave 11.1.0 /
image 2.18.2 was used; the expected `rescale.m` shadow warning was recorded.

When each runtime decodes the **same JPEG bytes**, the decoded RGB arrays
differ in 1,263,181, 544,174 and 414,219 scalar values for cats 1, 2 and 3.
Octave's original mean/SD pairs are:

| Source | Octave JPEG mean | Octave JPEG sample SD |
| --- | ---: | ---: |
| cat1.jpg | 172.48752777777779 | 44.72812504298803 |
| cat2.jpg | 80.35766111111111 | 68.10529703578258 |
| cat3.jpg | 127.26916666666666 | 76.76540498640563 |

When Octave instead receives lossless PNG copies of the **same Pillow-decoded
RGB arrays**, all three 256-bin working-V histograms agree with Python
exactly. Common-input Octave mean/sample-SD pairs are:

- 172.47983958333333 / 44.72923301053604
- 80.34050555555555 / 68.07128018712417
- 127.26124166666666 / 76.76305834710676

The remaining tiny SD differences reflect floating-point reductions. This
isolates the observed cross-runtime histogram discrepancy to JPEG decoding,
not the HSV adapter on common inputs. It does not identify the exact decoder,
preprocessing or reporting convention behind the historical published figure.
The original JPEGs and canonical reference checkout remain unchanged.

## Post-match result and supported claim

Post-match histogram identity, 126.69 / 74.77 agreement, and Octave post-match
comparison: **not evaluated**. A complete before/after reproduction PNG/PDF
was deliberately not generated after the baseline stop. No strong or partial
publication-parity claim is supported. Classification is **baseline/source
mismatch relative to the printed targets**, with evidence of an inconsistent
figure annotation and a JPEG decoding dependency; it is not diagnosed as a
Python scientific implementation failure.

The positive, narrower result is exact original working-V histogram parity
between Python and Octave on the three common decoded RGB inputs. A later
authorized histogram-only run can test post-match invariants without claiming
the historical figure's originals matched. Exact final RGB equality to one
historical stochastic realization would still not be an appropriate target.

## Artifacts, regression and reproduction

All image-bearing artifacts remain in ignored local storage:

`reference/.cache/figure2_baseline_20260916/`

- `figure2_baseline_diagnostic.png`: originals, calculated histograms and
  printed-target mismatches; clearly labels post-match as not run.
- `figure2_reproduction_metrics.json`: exact baseline statistics, hashes,
  software/settings, explicit stop state and null post results.
- `figure2_reproduction_histograms.csv`: original 256-bin counts, source
  filenames/hashes on every row, no spatial image encoding.
- `decoded_cat*.png`, `octave_baseline.mat`, `octave_log.txt`: common-input
  diagnostic material and reference evidence, all ignored.

The reusable entry is `reference.figure2_baseline.baseline(samples,
destination, octave=..., toolbox=...)`; destination must be a fresh directory
outside the source. Matplotlib is an already-installed local visualization
tool, not a new runtime/dev dependency. Ordinary tests do not import it.

The tracked numerical fixture `tests/reference/fixtures/figure2_baseline.json`
contains no spatial pixel data. Ten offline regression checks verify the
256-bin statistics, source identities against existing provenance, common-input
Octave histogram equality, explicit baseline stop, and impossibility of the
printed cat 2 SD. Existing tests and scientific algorithms were not changed.

Full regression result: **1,514 passed in 58.38 seconds**, zero failures,
skips or xfails, using `python -m pytest -q`. This includes all 1,504 earlier
tests and the ten new baseline checks. This passing result preserves the
baseline mismatch as positive diagnostic evidence; it does not assert
publication parity.

The task's success-conditioned commit is deferred because the reproduction
has not passed its baseline gate. Documentation, tooling and numerical evidence
are left reviewable in the working tree. No remote, push, tag or release was made.
