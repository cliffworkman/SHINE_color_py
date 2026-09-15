# Octave Lab behavioral specification (before adapter implementation)

Compatibility target: GNU Octave 11.1.0 with image 2.18.2 as invoked by repaired
SHINE_color commit 870e058fe8bf1e4090baf2401ff0e127d1c0237a. This independently
written specification describes mathematical transformations and empirically
identified conventions. It is not a source-code translation or a claim of
MATLAB compatibility. Scope: finite uint8 RGB input, float64 native Lab/RGB,
last axis of size three; HSV/RGB working wrappers are specified separately.

## Forward

Normalize each uint8 sRGB component by 255 in double precision. Linear-light
component c is u/12.92 for u <= 0.04045, otherwise ((u+0.055)/1.055)^2.4.
Multiply the linear RGB vector by this matrix (rows produce X,Y,Z):

```text
0.412453  0.357580  0.180423
0.212671  0.715160  0.072169
0.019334  0.119193  0.950227
```

Normalize XYZ componentwise by D65 [0.95047, 1, 1.08883]. There is no
chromatic adaptation to D50. Define delta=6/29, epsilon=delta^3 and
kappa=(29/3)^3/116. The Lab auxiliary function is f(t)=t^(1/3) for
t>epsilon and f(t)=kappa*t+16/116 otherwise. Breakpoint equality belongs
to the linear branch. These exact rational definitions are required;
rounded 7.787 and 0.008856 are different conventions near casting boundaries.

For f(X/Xn), f(Y/Yn), f(Z/Zn) = p,q,r, emit
[116*q-16, 500*(p-q), 200*(q-r)]. Units are native L*,a*,b* with nominal
L* in 0..100 for valid uint8 input. Preserve float64 without clipping.
SHINE working L is the existing saturating half-away-from-zero to_uint8(L*2.55).

## Inverse

For native [L,a,b], form q=(L+16)/116, p=q+a/500, r=q-b/200.
The inverse auxiliary function g(v) is v^3 if v^3>epsilon, otherwise
(v-16/116)/kappa. This definition includes negative values without clipping;
in particular a negative r is not set to zero. Multiply g(p),g(q),g(r)
by the same D65 white point to recover XYZ. Multiply by the explicitly
rounded inverse convention below, NOT a freshly inverted forward matrix:

```text
 3.240479 -1.537150 -0.498535
-0.969256  1.875992  0.041556
 0.055648 -0.204043  1.057311
```

For each resulting linear component c, emit 12.92*c if c<=0.0031308,
otherwise 1.055*c^(1/2.4)-0.055. Negative components take the linear branch.
There is no absolute-value extension and no output clipping. Out-of-gamut
RGB may be below zero or above one. Terminal RGB quantization is explicitly
to_uint8(rgb*255), separate from this native inverse.

Working reconstruction divides uint8 L by 2.55 in float64 and replaces only
L; a*/b* retain their native values exactly. The same principle applies to
HSV: V/255, H/S untouched. No epsilon adjustment or threshold snap is allowed.

## Source and verification scope

The sRGB companding and CIE piecewise transformations follow established
color mathematics; [W3C's color conversion discussion](https://www.w3.org/TR/css-color-4/#color-conversion-code)
provides an independently published description. That document's matrices,
white-point adaptation and extended-range choices do not define this adapter;
the target-specific values above come from the recorded Octave behavior.

Installed Octave rgb2xyz/xyz2lab/lab2xyz/xyz2rgb and input/output wrappers were
inspected to verify all stages, branch equalities, matrix orientation, dtype
and clipping. No library source/comments are copied into the implementation.
The original probes establish the dark [0,1,0] case and out-of-gamut inverse.
Expanded reference-only probes below must exist before coding the adapter;
their manifest records library source hashes and the specification hash.
The package need not emulate Octave's uint16, single, sparse, colormap-specific
validation or arbitrary invalid-input errors. Those are outside this contract.

## Predeclared expanded fixture rules

1. Dark cube: every R,G,B in 0..32, lexicographic order: 35,937 pixels. This
   crosses the sRGB companding and Lab low-light regions, including [0,1,0].
2. Full-range: 65,536 PCG64 seed 2026091401 uint8 RGB samples, all retained.
3. Boundary search pool: a separate 262,144 PCG64 seed 2026091402 sample,
   plus the dark cube and all 256 grays. Octave alone computes L*2.55.
   For each k=0..254, retain the closest strictly-below and strictly-above
   sample to k+0.5 within 0.001. Record any exact ties and missing sides;
   ties in sample distance use first pool order. Do not refill missing sides
   or select on Python output. Keep all selected records, including duplicates.
4. Inverse grid: Cartesian L in [-5,0,1,8,50,100,105] and a,b each in
   [-128,-80,-1,0,1,80,128], 343 probes. Include Lab values obtained by Octave
   from the original 64-color palette, with each L offset by -0.001,0,+0.001
   (192 probes), and nine neutral L values around 0 and 8 using +/-1e-9,
   plus 100 and 100+/-1e-9 (9 probes total).
5. Additional convention probes: normalized floating RGB triples immediately
   below, at and above 0.04045 (offset 1e-12), and normalized XYZ triples
   immediately around epsilon (offset 1e-12); inverse linear-RGB companding
   probes around 0.0031308 obtained as XYZ by solving the fixed inverse matrix.
   These reference stage probes document conventions, not added public APIs.

Export original and expanded native Lab/HSV, working channels, native/terminal
round-trips, working-quantized reconstructions and the existing processed
working-channel floor of 128. Preserve all reference results and all failures.
No output acceptance tolerances are defined by these fixture rules.
