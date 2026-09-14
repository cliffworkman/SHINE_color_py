# Predeclared corpus and conditioning criteria

Written before any final Python output comparisons for this study.

Candidate synthetic groups have shapes (31,31), (31,48), (48,31), (32,48),
(64,64), (63,79), (128,128). Each has exactly three images: PCG64 fixed-seed
uniform uint8 noise, an analytic spatial pattern with fixed-seed integer
perturbations in [-3,3], and multiscale smooth noise plus weak fine texture.
Seeds are 20260914 + group index. All candidates and any exclusions are retained;
no regeneration or replacement based on output agreement is allowed.

Conditioning is screened before running final-output comparisons. For each
source's Octave fftshift(fft2(double(image)/255)), set S=max(1,max magnitude).
Require minimum magnitude > 1e-10*S. For sfMatch also require every occupied,
retained radial bin's source-amplitude sum > 1e-10*S. Empty bins and bins beyond
the existing reference cutoff are irrelevant denominators and excluded from
this screen. Record all magnitudes below 1e-15, 1e-14, 1e-13, 1e-12 and every
occupied retained radial denominator. These are conditioning thresholds only,
not output tolerances and not modifications to any algorithm. This conservative
screen separates coefficients from FFT roundoff, but is not a universal
condition-number guarantee for subsequent quantization or rescale spans.

Natural sample choice, independent of conditioning: cat1.jpg, cat2.jpg, cat3.jpg
from the canonical reference's toolbox/SHINE_color_INPUT/samples folder. Read
only their green channels, with no color conversion. Test one group at original
1200x1200 resolution, and one derived group using [::4,::4] sampling (300x300;
no interpolation). Keep both regardless of conditioning. This is a three-photo
sample bundled with the toolbox, not certification of an experimental stimulus
set or a population-representative survey.

Compare sfMatch and specMatch, options 0/1/2, for every candidate and natural
group. Only groups passing the above independent screen are labelled
well-conditioned. Every uint8 discrepancy is reported exactly; no tolerance
is introduced. Distinguish few quantization-boundary pixels from large or
structured errors using distributions and intermediate diagnostics, without
reclassifying a non-exact result as exact.
