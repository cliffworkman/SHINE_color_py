# Licensing lineage and third-party notices

## Repository and new Python work

The root [LICENSE](LICENSE) reproduces the repaired/original SHINE_color MIT
license verbatim, including **Copyright (c) 2021 Rodrigo Dal Ben**.
[The identical toolbox LICENSE](docs/UPSTREAM_TOOLBOX_LICENSE.txt) is preserved
separately. Source: SHINE_color commit
`7074df49bf42d622f2ea30c3a838629eada6b787`, root and `toolbox/` respectively.

New independently written Python code, tests, export/diagnostic harnesses and
new documentation: **Copyright (c) 2026 Cliff Workman**, distributed under the
same repository-level MIT terms. This attribution does not assign Cliff
authorship of SHINE_color or SHINE. Inherited documentation and reference
material retain their original attribution and the notices below.

The owner's public-release decision is to follow the original licensing model.
The repository-level MIT text coexists upstream with narrower embedded notices.
We preserve that inconsistency; we do not decide which notice overrides another
or assert that MIT clears every reference component or sample image. These are
historical notices, not a new combined license or a clean-room claim.

## SHINE source-file notice

The following notice is reproduced from `toolbox/histMatch.m`. The same
permission/warranty paragraph occurs in these upstream files (not bundled as
implementations in this Python repository):

`avgHist.m`, `displayInfo.m`, `getRMSE.m`, `hist2list.m`, `histMatch.m`, `imstats.m`, `lum2scale.m`, `lumCalc.m`, `lumMatch.m`, `match.m`, `processImage.m`, `readImages.m`, `rescale.m`, `scale2lum.m`, `separate.m`, `sfMatch.m`, `sfPlot.m`, `SHINE_color.m`, `specMatch.m`, `spectrumPlot.m`, `tarhist.m`, `userWizard.m`, `video2frames.m`.

```text
SHINE toolbox, May 2010
(c) Verena Willenbockel, Javid Sadr, Daniel Fiset, Greg O. Horne,
Frederic Gosselin, James W. Tanaka
------------------------------------------------------------------------
Permission to use, copy, or modify this software and its documentation
for educational and research purposes only and without fee is hereby
granted, provided that this copyright notice and the original authors'
names appear on all copies and supporting documentation. This program
shall not be used, rewritten, or adapted as the basis of a commercial
software or hardware product without first obtaining permission of the
authors. The authors make no representations about the suitability of
this software for any purpose. It is provided "as is" without express
or implied warranty.
```

The original SHINE citation is Willenbockel et al. (2010),
[doi:10.3758/BRM.42.3.671](https://doi.org/10.3758/BRM.42.3.671).
SHINE_color is Rodrigo Dal Ben (2023),
[doi:10.1016/j.mex.2023.102377](https://doi.org/10.1016/j.mex.2023.102377).
The upstream startup message also identifies “MIT License, Copyright (c) 2023
Rodrigo Dal Ben”; this differs in year from the retained 2021 LICENSE files.

## Additional upstream SSIM notices

These reference components are not copied into the Python implementation;
SSIM-optimized histogram matching is unsupported. Notices and citations remain
here to preserve the reference toolbox's attribution.

From `toolbox/ssim_index.m`:

```text
SSIM Index, Version 1.0
Copyright(c) 2003 Zhou Wang
All Rights Reserved.

The author is with Howard Hughes Medical Institute, and Laboratory
for Computational Vision at Center for Neural Science and Courant
Institute of Mathematical Sciences, New York University.

----------------------------------------------------------------------
Permission to use, copy, or modify this software and its documentation
for educational and research purposes only and without fee is hereby
granted, provided that this copyright notice and the original authors'
names appear on all copies and supporting documentation. This program
shall not be used, rewritten, or adapted as the basis of a commercial
software or hardware product without first obtaining permission of the
authors. The authors make no representations about the suitability of
this software for any purpose. It is provided "as is" without express
or implied warranty.
----------------------------------------------------------------------

This is an implementation of the algorithm for calculating the
Structural SIMilarity (SSIM) index between two images. Please refer
to the following paper:

Z. Wang, A. C. Bovik, H. R. Sheikh, and E. P. Simoncelli, "Image
quality assessment: From error visibility to structural similarity"
IEEE Transactios on Image Processing, vol. 13, no. 4, pp.600-612,
Apr. 2004.

Kindly report any suggestions or corrections to zhouwang@ieee.org
```

From `toolbox/ssim_sens.m`:

```text
Copyright(c) Alireza N. Avanaki (avanaki@yahoo.com)

Please refer to the following paper:
Avanaki, A. N. (2009). Exact global histogram specification
optimized for structural similarity. Optical Review, 16,
613-621.

This piece of code comes with absolutely no warranty.
Non-commercial use (at your own risk) is permitted.
```

## GNU Octave and Python dependencies

GNU Octave 11.1.0 and image 2.18.2 were external executable references.
Installed HSV conversion functions were inspected to record arithmetic
conventions; the Python implementation is independently written, but is not
described as clean-room. No Octave implementation or binary is bundled.
Octave/image source and their own notices remain separate from SHINE's MIT text.
See the [HSV specification](docs/OCTAVE_HSV_SPEC.md),
[Lab specification](docs/OCTAVE_LAB_SPEC.md) and
[provenance record](docs/PROVENANCE_AND_LICENSING.md).

NumPy and Pillow are separately installed runtime dependencies. SciPy and
pytest support development/reference checks; scikit-image and pyFFTW support
optional historical diagnostics. Their distributions carry their own license
and bundled-component notices. No dependency source or wheel is vendored here.
The provenance record lists measured versions and package-declared licenses.

## Reference images and fixtures

The upstream sample cats are attributed to Pexels in the original sample
readme and Figure 2 caption. Individual photographer/asset URLs and acquisition
records were not available in the inspected history. The four existing
cat-derived MAT fixtures are retained for scientific regression evidence under
the owner's explicit release decision, with that provenance gap disclosed.
They contain spatial image data; MIT is not asserted to clear their image
rights. No cat JPEGs or new sample photographs are added. The README comparison
figure contains plotted counts and statistics, with no photograph pixels.
See [the fixture inventory](docs/PROVENANCE_AND_LICENSING.md#cat-images-and-image-derived-fixtures).
