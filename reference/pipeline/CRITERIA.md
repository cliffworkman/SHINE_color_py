# Predeclared whole-image pipeline corpus and comparison strategy

Before Python/Octave output comparisons: four three-image RGB sets, shapes
17x19,17x20,20x17,20x20. Each uses PCG64 seed 2026091404+group index:
uniform full-range RGB noise, smooth heterogeneous texture with fine noise,
and a structured multichannel sinusoid plus integer perturbations [-5,5].
No candidate is selected, removed or regenerated because it agrees.

All 8 modes, RGB/HSV/CIELab, iterations 1/2, and spectral rescaling 0/1/2
are covered. Modes 1/2 use rescale option 1 in the reference matrix; Python
tests verify that other valid rescale options do not affect those operations.
This gives 120 configurations per group, 480 total.

Record the approved conditioning screen on every captured input to sfMatch
or specMatch: all source magnitudes and occupied retained radial sums must
exceed 1e-10*max(1,max source magnitude). Later stages/iterations are screened
as well as initial channels. Degeneracy remains explicit, never automatically
accepted by relaxing an output comparison.

The external Octave harness calls the actual repaired processImage dispatcher
and captures public primitive boundaries using delegating wrappers; iteration
and color wiring are external and follow the documented repaired semantics.
This does not exercise the reference's filesystem/wizard/diagnostic shell.
Captured stages and per-iteration state provide independent reference evidence.

Modes 1/3/4 require exact working and terminal RGB parity where supported by
measurement. Native RGB bounds are measured separately without changing prior
bounds. Histogram stages compare exact targets and output distributions;
mean/sample-SD follow those distributions, not random spatial identities.
Replay every spectral stage with identical captured inputs, including hist-first
modes 5/6. Replay full chains with recorded histogram outputs to isolate the
nonrandom operations and color reconstruction. For modes 7/8 iteration 2,
the prior random arrangement can affect the next spectrum: compare each stage
on its own captured input rather than claim independent final histograms must
agree. Python manual compositions and explicit dataflow regressions test the
independent randomized paths. Preserve all outputs and report any mismatch.
