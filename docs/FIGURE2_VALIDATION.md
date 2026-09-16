# Figure 2 validation

This note records the bounded comparison behind the README summary. It is a
behavioral validation of HSV mode 2, one iteration and one three-image group;
it does not alter the toolbox or treat the printed Figure 2 labels as universal
goldens.

Evidence provenance: the external GNU Octave 11.1.0 / image 2.18.2 audit
record identifies repaired snapshot `870e058fe8bf1e4090baf2401ff0e127d1c0237a`
and historical 0.0.5 commit `330a9be6e49f59e5d68fb985744b2a50c278e8d8`.
The subsequent Python confirmation commit `df0fb7d` rechecked those archived
results, including sorted-value hashes, rather than performing a fresh Octave
run. The maintained checkout at `c602d4582f51bde8bda4ed10a360734f62e538dc`
was clean and its toolbox matched the snapshot after line-ending normalization.
This documentation update uses that recorded empirical evidence; it does not
claim an additional independent runtime comparison or MATLAB validation.

The supplied sample files were identified by SHA-256:

| File | SHA-256 |
| --- | --- |
| cat1.jpg | `aa350a25a0fedbe875aab0cd69e5bf925e3d4c9a5da2a1769ce34c17e63eae9a` |
| cat2.jpg | `68fc8a17422f4b1d0ed3491f21e46e262261e4abdabfa459487765cd19e5dc87` |
| cat3.jpg | `66fdaa81b735b6a9261bdce7314698ad912068048fa115c03a636d0257d5bdeb` |

On identical decoded RGB arrays, historical 0.0.5, repaired 0.0.6 and
SHINE_color_py have identical 256-bin pre-match, target and post-match
histograms and identical sorted matched working-V values. Raw spatial output
identity is not required because tied pixels are assigned stochastically.
Means agree exactly. Independent sample-SD reductions differ by at most
approximately `2.2e-12` between recorded Octave runs and `3.2e-11` between
Octave and Python. Rescale option 1 is recorded but irrelevant for mode 2.

Pillow-common decoded input produces post mean / sample SD of 126.693774 /
74.771272, which rounds to the displayed 126.69 / 74.77. Octave-common input
produces 126.704679 / 74.780523, which rounds to 126.70 / 74.78. This separates
algorithmic parity from JPEG-decoder behavior.

The source baseline is:

| Image | Printed Figure 2 | Reproduced supplied source |
| --- | --- | --- |
| cat1 | 172.47 / 44.72 | 172.48 / 44.73 |
| cat2 | 80.34 / 127.26 | 80.34 / 68.07 |
| cat3 | 127.26 / 76.76 | 127.26 / 76.76 |

The origin of cat2's apparent annotation/reporting discrepancy is unknown. Its
printed SD is mathematically incompatible with a 0–255 variable at mean 80.34
(the upper bound is approximately 118.46),
so it is documented rather than reproduced by changing software. Cat1's
displayed values are consistent with truncating the calculated values to two
decimals, but that remains a plausible formatting explanation only.
The number 127.26 is also cat3's printed mean; this observation does not
establish how the cat2 label arose.

The committed comparison figure contains histograms and statistics only. It
contains no source photograph pixels. The companion Python repository holds the
full machine-readable audit and provenance discussion.
