# Color validation: adopted adapter and historical candidate comparison

The subsequent authorized Lab compatibility adapter resolves the working-L
discrepancy below. Current results and adoption are documented in
[COLOR_ADAPTER_VALIDATION.md](COLOR_ADAPTER_VALIDATION.md), with the prior
[behavioral specification](OCTAVE_LAB_SPEC.md). HSV uses scikit-image 0.25.2;
Lab uses the project-owned NumPy adapter. The text below preserves the
original 527c63c diagnostic checkpoint and its stopping decision; it is
historical evidence, not current gate status.

## Historical Gate 3 stop before library adoption

Gate 2 closed with 205 passing tests at
`ecebf4de2a3808e62bc5567f6ca800303a31ceb0` (Adopt NumPy FFT policy and close
Octave kernel validation). Gate 3 then proceeded as authorized. The candidate
scikit-image 0.25.2 changes one SHINE uint8 L working value relative to Octave.
**Gate 3 is not complete. No color library is adopted, no color.py exists, and
no pipeline or Gate 4 implementation has begun.** This is the requested stop
condition for a conversion discrepancy that survives working-channel casting.
No tolerance is widened and no custom converter is introduced.

## Corpus and provenance

There are 383 pixels in three exact uint8 RGB fixtures: an 8x8 palette, a 7x9
structured image, and a 1x256 complete gray ramp. The palette includes black,
white, gray levels, RGB/CMY, near-black/white, low/high saturation, arbitrary
mixed and unequal-channel colors. The structured image uses three distinct
modular linear patterns. Values/formulas and generator version/hash are in
`tests/reference/fixtures/color/inputs.json`; exact arrays are in `inputs.mat`.
Selection preceded comparison. No failing color was removed.

The external harness `reference/octave/export_color.m` calls Octave rgb2hsv,
hsv2rgb, rgb2lab and lab2rgb, and the reference toolbox's scale2lum. It exports
native HSV/Lab (all channels), V/L uint8 working values, inverse working scales,
native and quantized round-trips, and a processed-channel probe which raises
working V/L to at least 128 while retaining H/S or a*/b*. That probe exercises
out-of-gamut Lab reconstruction without implementing a pipeline.

Reference: GNU Octave 11.1.0, image 2.18.2, Windows x86-64, toolbox commit
`870e058fe8bf1e4090baf2401ff0e127d1c0237a`. Octave provenance, actual conversion
source paths and generator hash are in `octave_manifest.json`. The canonical
fork is unchanged. Candidate: Python 3.12.10, NumPy 2.1.3, SciPy 1.15.1,
scikit-image 0.25.2, D65/2-degree defaults. scikit-image was already installed;
no installation or dependency change was needed. It remains evaluation tooling,
outside runtime and ordinary dev extras.

## Measured differences

All statistics compare candidate values to exported Octave values; RGB floats
are in native nominal 0–1 units, HSV in native 0–1, and Lab in native units.
The JSON report includes per-channel maxima/means and difference distributions
for every fixture and aggregated comparison. Integer differences are counted
exactly; floating distribution bins are descriptive, not acceptance tolerances.

| Quantity | Maximum absolute difference | Mean absolute difference | Unequal scalar values |
| --- | ---: | ---: | ---: |
| Native HSV | 5.551115123125783e-16 | 6.926815759601036e-18 | 98/1149 |
| SHINE uint8 V | 0 | 0 | 0/383 |
| V back to native scale | 0 | 0 | 0/383 |
| HSV RGB round-trip | 6.106226635438361e-16 | 1.5293950227715453e-17 | 162/1149 |
| Native Lab | 3.6811206356901494e-05 | 4.467261272048742e-07 | 622/1149 |
| SHINE uint8 L | 1 | 0.0026109660574412533 | 1/383 |
| L back to native scale | 0.3921568627450981 | 0.0010239082578200995 | 1/383 |
| Lab RGB round-trip | 1.7459920036983085e-05 | 3.517211880238597e-07 | 1143/1149 |
| Lab RGB after working-L quantization | 0.011787403684934188 | 6.167929836088349e-05 | 1143/1149 |

Both runtimes' native HSV and Lab round-trips recover all source RGB values
exactly after the established saturating uint8 cast. HSV reconstruction after
working quantization and after the processed-V probe also agrees exactly in
uint8. Native HSV differences are roundoff-scale and do not survive these casts.
The same is not true of working-L quantization: reconstructed RGB differs in
three scalar channels, with maximum error 2 and MAE 0.0034812880765883376.
Passing a native round-trip alone therefore would have missed the blocking case.

Inverse transforms are separately compared on identical Octave native inputs.
Maximum differences are 6.106226635438361e-16 for hsv2rgb and
1.7459920038802898e-05 for lab2rgb; their uint8 RGB results agree exactly here.

## The working-L discrepancy is a formula convention, not a cast bug

Palette row 2, column 1 (zero-based) is RGB **[0, 1, 0]**:

| Stage | Octave | scikit-image |
| --- | ---: | ---: |
| L* | 0.19607885001495262 | 0.19607791741637826 |
| L* × 2.55 | 0.5000010675381291 | 0.4999986894117645 |
| SHINE uint8 L | 1 | 0 |

Both use the same forward sRGB-to-XYZ matrix and D65 white point. Octave's
xyz2lab low-light branch uses slope `(29/3)^3/116` and threshold `(6/29)^3`;
scikit-image uses rounded slope `7.787` and threshold `0.008856`. For this pixel,
the slope difference alone places L×2.55 on opposite sides of the 0.5 casting
boundary. Feeding the identical Octave scaled L into Python's established
to_uint8 gives 1, exactly as Octave does. No change to numeric.py is justified.
`reference/check_color_diagnostics.py` provides a scalar causal calculation
and positive assertions of this discrepancy; it is not a replacement converter.

The inverse implementations also differ: Octave uses a rounded explicit
XYZ-to-RGB matrix while scikit-image uses an inverse matrix; their Lab inverse
branch constants differ correspondingly. scikit-image clips RGB to [0,1],
whereas the measured Octave conversion preserves out-of-range floats. The
processed-L probe produces Octave values down to -0.011523735534754071 and up
to 1.2136692386302281. The maximum raw RGB difference of 0.21366923863022813
therefore includes a clipping convention, not just conversion error. After
terminal uint8 saturation the processed-L outputs agree exactly in this probe.
That does not erase the separate input working-L discrepancy or prove parity
for other processed Lab colors.

These conventions were inspected in the installed Octave image package's
rgb2xyz.m, xyz2lab.m, lab2xyz.m and xyz2rgb.m and the installed scikit-image
colorconv.py. The latter's source hash and scalar probe are recorded in
`diagnosis.json`. The public candidate API specifies sRGB, D65 and a 2-degree
observer by default. [scikit-image 0.25.2 color API](https://scikit-image.org/docs/0.25.x/api/skimage.color.html).

## Decision, validation claim and next step

Do not adopt scikit-image unchanged as the combined HSV/Lab color layer.
HSV is a promising candidate on this corpus, but the required Lab working
representation has a confirmed discrepancy. No OpenCV substitution, custom
converter or silent quantization adjustment was attempted. The source-level
cause is understood narrowly; an Octave-compatible color implementation still
requires reviewing the complete forward/inverse and gamut conventions and
their scope before adoption.

Supported claim: **On the recorded 383-pixel corpus, scikit-image 0.25.2 matches
Octave's SHINE uint8 V values and tested uint8 HSV reconstructions exactly.
Lab native round-trips recover source uint8 RGB, but one working L value and
its quantized reconstruction differ. The color layer is not adopted or
validated as complete.** No float acceptance tolerance has been introduced.

MATLAB numerical parity has not yet been established and remains a future
secondary validation target. Neither these color results nor the kernel
results establish MATLAB parity. No universal Octave or all-natural-image
claim is made.

The next bounded decision is whether to authorize a narrowly specified
Octave-compatible Lab adapter, or explicitly accept a changed working-L
contract. Recommend investigating the former against additional cast-boundary
and gamut probes before choosing. Gate 4 requires completed Gate 3 validation
and human review; it cannot proceed from this diagnostic checkpoint.

## Reproduction and checks

The normal kernel suite remains independent of scikit-image. To reproduce the
color diagnostics use an environment containing scikit-image 0.25.2 and the
recorded NumPy/SciPy versions, then run:

```text
python -m reference.compare_color
python -m reference.check_color_diagnostics
python -m pytest -q -p no:cacheprovider --tb=short
```

The first command records measurements without setting bounds; the second
asserts source hashes, exact HSV working behavior, round-trips, untouched
chroma in the diagnostic recombination, the Lab mismatch and its scalar cause.
These are diagnostic checks, not passing Gate 3 acceptance tests for a missing
color.py. The final standard-suite run reports **205 passed in 16.28 seconds**,
with zero failures, skips or xfails. The diagnostic assertion tool also passed.
No existing tolerances or FFT
fixtures changed in this color investigation.

To regenerate source arrays, run `python -m reference.build_color_fixtures`.
To regenerate Octave outputs, add `reference/octave` to the Octave path and call
`export_color(toolbox, destination)` with the pinned toolbox directory and
`tests/reference/fixtures/color`. Preserve prior evidence before regenerating;
MAT container hashes identify a run and can change with header timestamps.
The compact MATs and all measurements are committed; no ignored cache is
needed to rerun Python comparisons. This is a diagnostic checkpoint, not the
proposed successful Gate 3 commit "Validate color conversion against GNU Octave".
