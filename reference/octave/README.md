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
