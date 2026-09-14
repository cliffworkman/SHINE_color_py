# Reproduce the bounded backend study

Run from the repository root. This diagnostic uses the existing development
environment plus Pillow for input generation and optional pyFFTW in ignored
`reference/.cache/python-fftw`. None becomes a package runtime dependency.
Committed MAT inputs are sufficient for comparison without regenerating images.
The generator expects the three documented cats in the sibling reference
checkout. The audit additionally verifies those source files read-only.

Read [CRITERIA.md](CRITERIA.md) before comparisons. Historical evidence under
`reference/diagnostics/` and `tests/reference/fixtures/` is never overwritten.
Regenerating this study does replace its own outputs; preserve them separately
first if a new runtime/build is being investigated.

In PowerShell, with the pinned unmodified reference snapshot available:

```powershell
# Only needed to regenerate inputs; fixed seeds and fixed photo selection.
python -m reference.backend_policy.build_corpus

$policyOctave = 'C:/Program Files/GNU Octave/Octave-11.1.0/mingw64/bin/octave-cli.exe'
& $policyOctave --no-gui --quiet --eval "addpath('reference/octave'); export_policy_corpus(fullfile(pwd,'reference/.cache/SHINE_color-870e058fe8bf1e4090baf2401ff0e127d1c0237a/toolbox'),fullfile(pwd,'reference/backend_policy/data'),fullfile(pwd,'reference/.cache/backend_policy'),'conditioning');"
python -m reference.backend_policy.screen_conditioning

# Run only AFTER recording the independent screen; keep all candidates.
& $policyOctave --no-gui --quiet --eval "addpath('reference/octave'); export_policy_corpus(fullfile(pwd,'reference/.cache/SHINE_color-870e058fe8bf1e4090baf2401ff0e127d1c0237a/toolbox'),fullfile(pwd,'reference/backend_policy/data'),fullfile(pwd,'reference/.cache/backend_policy'),'outputs');"
python -m reference.backend_policy.compare
python -m reference.backend_policy.inspect_deployment
python -m reference.backend_policy.verify_study
python -m pytest -q -p no:cacheprovider --tb=no
```

The last command currently exits 1 with the same 18 ordinary reference failures
and 133 passes. That is the retained Gate 2 stopping condition, not a diagnostic
tool failure. The comparison reports every pixel difference; it does not set
new bounds. The audit checks integrity/aggregation, not an output acceptance
policy. `inspect_deployment` makes read-only PyPI requests and inventories wheel
archives in memory without installation. Large FFT intermediates remain in
ignored cache; exact source arrays and compact reports are retained in Git.

See [the recommendation](../../docs/FFT_BACKEND_POLICY.md) for evidence,
limitations, deployment sources and the proposed next step.
