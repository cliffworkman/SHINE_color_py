# Octave HSV arithmetic specification (frozen before adapter comparison)

Target: GNU Octave 11.1.0 core rgb2hsv/hsv2rgb, with image 2.18.2
loaded in the external harness. These conversions are core functions, not
image-package implementations. The local installed functions were inspected;
this mathematical specification is independently expressed from their behavior.
The adapter will implement these equations, not copy their source structure.
The exported corpus records source paths and hashes. No SHINE source is edited.

## Forward, supported SHINE input

Input is uint8 RGB with a final axis of length three. Normalize each component
by float64 division by 255. Output is float64 H,S,V; preserve the input shape.
Let M=max(R,G,B), m=min(R,G,B), d=M-m. Value V=M.
Equal channels (including black) give H=S=0. Otherwise S=1-(m/M),
not d/M. Max ties choose R before G before B. With that selected maximum:

* R: H=((1/6)*(G-B))/d.
* G: H=1/3+((1/6)*(B-R))/d.
* B: H=2/3+((1/6)*(R-G))/d.

Each fraction constant is a binary64 division. Subtract first, multiply by
1/6 second, divide by d third, add the sector offset last. If H<0 add 1
once; there is no general modulo in forward conversion. Max ties at yellow,
cyan and magenta obey the stated priority, even where alternate formulas
are mathematically equivalent. Gray excludes division by zero by definition.
Octave also accepts other native types; this adapter retains the existing
explicit uint8-only public forward contract, not Octave's entire type API.
SHINE working V is the unchanged saturating uint8(V*255), inverse working
scale is float64(working_V)/255.

## Inverse, native finite HSV

Octave does not compute a sector index floor(6H), a fractional sector, or
the textbook p/q/t table. Those are mathematically equivalent but have a
different floating-point evaluation order. Its actual representation is
three shifted periodic trapezoids, one per output component.

Let u_R=mod(H-2/3,1), u_G=mod(H,1), u_B=mod(H-1/3,1).
Subtract the offset before wrapping. Modulo is nonnegative for divisor 1;
local probes at -eps, -eps/2, 0, eps/2, 1-eps/2, 1, 1+eps preserve
the tiny nonzero residues. In particular H=1 wraps like H=0.

For each u in [0,1), the hue weight W is:

| Interval | W |
| --- | --- |
| 0 <= u < 1/6 | 6*u |
| 1/6 <= u < 1/2 | 1 |
| 1/2 <= u < 2/3 | 4-(6*u) |
| 2/3 <= u < 1 | 0 |

Compute base=V*(1-S) and chroma=S*V separately. Each output is
base+(chroma*W), with separate binary64 operations. This replaces the
p/q/t arithmetic, including how the maximum channel is reconstructed:
base+chroma can differ from V by roundoff. Achromatic S=0 yields V in
every channel. Endpoints use the intervals above, without perturbations.
There is no clipping of S, V, or native RGB; finite out-of-range S/V probes
are included to verify this property. Terminal quantization is external:
to_uint8(native_RGB*255), with no epsilon, tie snapping, or color exceptions.
Nonfinite HSV and arbitrary huge hues are outside the present acceptance scope.

## Predeclared reference corpus

Selection is frozen before Python comparisons. Independent RGB input includes
65,536 PCG64(2026091408) random triplets, all 256 grays, the 0..15 dark cube,
the 17-level cube {0,16,...,240,255}, and one-component +/-1 near-grays.
No input is removed because of Python behavior.

A separate 131,072-triplet PCG64(2026091409) search pool is reconstructed in
Octave with each processed uint8 V in {0,1,2,31,64,127,128,254,255}.
Retain every RGB/V pair having any scaled reconstructed component within
1e-10 (inclusive) of floor(component)+0.5. Preserve selection indices, V,
native HSV/RGB and terminal bytes. This is a reference-only selection rule;
it includes exact ties and both sides, without using existing failures.

Independent inverse probes cross H=k/6 (k=-3..9), offsets
{-1e-12,-eps,0,eps,1e-12}, S={0,1e-12,1/255,0.5,254/255,1,-0.1,1.1},
V={0,1/255,0.5,254/255,1,-0.1,1.1}, plus 8,192 uniform mixed HSV
triplets from PCG64(2026091410). Finally include each of the 458 recorded
Gate 4 scalar boundary occurrences, preserving its identity and processed V.
These are a separate regression stratum, not the independent selection pool.

Export reference results before adapter implementation. Then measure forward,
inverse on identical reference HSV, end-to-end processed V, and Octave inverse
on scikit-image H/S with identical processed V. Freeze references and retain
the old diagnostic records. No universal or MATLAB parity claim follows.
