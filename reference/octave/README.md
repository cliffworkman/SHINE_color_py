# GNU Octave reference fixtures

Run from the Python project root with GNU Octave 11.1.0, image 2.18.2 and
datatypes 1.1.8 installed. The reference toolbox must be an unmodified checkout
or snapshot of merged main commit `870e058fe8bf1e4090baf2401ff0e127d1c0237a`.
The original sibling reference repository must remain untouched.

```octave
addpath('reference/octave');
export_reference_fixtures('/absolute/path/to/reference/toolbox', ...
  fullfile(pwd,'tests/reference/fixtures'), ...
  '870e058fe8bf1e4090baf2401ff0e127d1c0237a');
```

`probe_edge_cases` is also callable separately with toolbox and destination
arguments. It records expression results, warnings, errors and actual match
outputs for one source pixel and target lengths 1 and 3.

PNG files are exact synthetic uint8 inputs; MAT files preserve arrays and
cell collections. SciPy is a development dependency for reading MAT fixtures.
The scripts call public toolbox functions and standard runtime diagnostics;
they do not replace, patch or copy algorithm implementations. FFT arrays are
independent diagnostic calculations, not captured private sfMatch locals.
Radial grids/coefficients are not exposed by the reference API; final sfMatch
outputs across odd/even rectangular shapes exercise them without duplicating
the reference algorithm in fixture tooling.

The local snapshot under ignored `reference/.cache/` was downloaded from
`https://codeload.github.com/cliffworkman/SHINE_color/zip/870e058fe8bf1e4090baf2401ff0e127d1c0237a`.
No reference source is committed to this Python repository. See
`docs/VALIDATION.md` for claims, divergences and empirical tolerance policy.

After generating fixtures, run `python -m reference.measure_primitives` and
`python -m reference.diagnose_fft` from the project root. These record
observations, never increase test bounds. The current reference tests have
18 intentional, unmasked failures documenting an unresolved Gate 2 numerical
discrepancy; see the validation document before interpreting the suite.

The diagnostic arc uses `fft_environment`, `probe_fft_stability` and
`replay_fft_stages` to record FFTW state, compare controlled plans/threads and
replay captured inverse inputs. It writes under `reference/diagnostics/fft/`
and preserves the original fixtures. See `docs/FFT_DIAGNOSTICS.md` for the
ordered reproduction steps, results and scope limits.

`probe_rescale_extrema` characterizes the real NaN/Inf extrema and rescale
semantics in 12 small cases. Its new evidence and the corrected A/B/C/D replay
are kept in `reference/diagnostics/nonfinite_rescale/`, preserving the prior
FFT investigation. See `docs/NONFINITE_RESCALE.md` for reproduction and results.

`export_policy_corpus` runs the later well-conditioned backend policy study in
separate conditioning/output phases. Its compact evidence and ordered commands
are in `reference/backend_policy/README.md`; the recommendation is in
`docs/FFT_BACKEND_POLICY.md`. The original fixtures and 18 failures are retained.


After FFT policy adoption, ordinary pytest coverage uses the archived inputs
under `reference/backend_policy/data` and promoted exact Octave outputs under
`tests/reference/fixtures/conditioned`. `python -m reference.promote_policy_fixtures`
can reproduce that promotion from the study cache, verifying recorded hashes.
The 18 historical failures are now explicitly marked passing degeneracy tests;
earlier stopping-condition descriptions above are historical.

`export_color(toolbox, destination)` exports the bounded Gate 3 RGB/HSV/Lab
corpus, working-channel scales, native round-trips and processed-channel probes.
Generate inputs with `python -m reference.build_color_fixtures`, then call the
Octave function with destination `tests/reference/fixtures/color`. Run
`python -m reference.compare_color` and `python -m reference.check_color_diagnostics`.
The candidate is not adopted: see `docs/COLOR_VALIDATION.md` for the Lab
cast-boundary failure and the resulting Gate 3 stop.

The subsequent authorized adapter uses `export_lab_corpus` for expanded
reference-only boundary selection and inverse/gamut probes. See
`docs/OCTAVE_LAB_SPEC.md` for predeclared rules and
`docs/COLOR_ADAPTER_VALIDATION.md` for current adoption, measurements and
reproduction commands. The older color corpus and scikit-image Lab failure
remain historical evidence.

`export_pipeline(toolbox, destination)` exercises the repaired `processImage`
dispatcher with delegating primitive-capture wrappers, in an external color/
iteration harness. It does not exercise the SHINE_color filesystem/wizard shell.
Generate predetermined inputs with `python -m reference.pipeline.build`, export
to `tests/reference/fixtures/pipeline`, then run the measure/diagnose/report_matrix
modules in `reference.pipeline`. See `docs/PIPELINE_VALIDATION.md` for current
Gate 4 stopping failures; do not interpret this fixture export as completed
pipeline acceptance. Frozen randomized stage outputs are retained for replay.
