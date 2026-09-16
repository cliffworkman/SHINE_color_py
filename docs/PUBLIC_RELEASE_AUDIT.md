# Public GitHub publication audit

Date: 2026-09-16. Python baseline: `cea45eb4b9f480d71fa48598bad717eb0cef7399`.
Inherited documentation baseline: repaired SHINE_color
`7074df49bf42d622f2ea30c3a838629eada6b787`.

## Scope and preservation

This checkpoint prepares the owner's authorized public source/history push to
[cliffworkman/SHINE_color_py](https://github.com/cliffworkman/SHINE_color_py).
It closes the documentation/publication work following the repaired 0.0.6 and
Python Figure 2 validation arcs. It does not change scientific code, numerical
arrays, test tolerances, test selection or the version `0.1.0.dev0`.

The complete repaired README is embedded in the Python README. A mechanical
comparison removes only the clearly delimited additive Python notes and
normalizes trailing whitespace, then requires equality with the fork README.
This preserves its description/scientific purpose, color-space explanation,
requirements, step-by-step instructions, transparency guidance, modes,
iterations, return values, original contacts/references, all 0.0.2–0.0.6 release
notes and Figure 2 validation. No substantive inherited text was removed.
Python equivalents appear beside the MATLAB-specific requirements, workflow
and return semantics. The inherited Figure 2 note is copied locally so its
relative link remains valid. The original “MethodX” spelling is retained in
the inherited citation; the top citation uses *MethodsX*.

The root MIT and toolbox MIT texts retain Rodrigo Dal Ben's copyright verbatim.
The SHINE and SSIM component notices and authors are recorded in
[THIRD_PARTY_NOTICES.md](../THIRD_PARTY_NOTICES.md), separately from Cliff
Workman's new Python/tooling contribution. The historical notice conflict is
disclosed without choosing an overriding notice. See
[provenance and licensing](PROVENANCE_AND_LICENSING.md).

The Figure 2 image is unchanged, contains histograms/statistics without photo
pixels, and has SHA-256:
`29faae1553fb3b7c5a2d7c66521123c16409b4704b702735edf0dda8f80bfaf7`.
Both the inherited and Python comparison tables retain the published values.
Common-input histogram/sorted-output parity is distinguished from stochastic
RGB tie assignment and decoder dependence. Cat2's impossible SD remains a
reported discrepancy of unknown origin, not a software golden; cat1 truncation
remains a plausible formatting explanation only.

## Public-content audit

The baseline contains 291 tracked files and 17 commits. The final tree adds
five documentation/license files. The preflight inventory inspects every
tracked file, including MAT keys/shapes and string metadata, and scans reachable
Git history for credential patterns and private/cache path names. The reviewed
tree/history contain no private architectural stimuli, private pilot outputs,
tracked `arch_study/`, installed dependencies, cache directories, temporary
outputs, JPEG photographs, credential-pattern findings or unrelated personal
files. Git author identities use the maintainer's GitHub noreply address.
The 480-image private corpus, local paper assets and reference caches stay ignored.

The existing four cat-derived MAT fixtures remain intentionally tracked for
scientific regression. They contain spatial image data and originate in the
SHINE_color samples attributed to Pexels. Missing individual asset/acquisition
records are documented in the provenance inventory; no new photo assets are
added and a software license is not presented as image-rights clearance.

Three JSON metadata files replace checkout prefixes with relative paths.
A recursive comparison confirms that only those path strings changed; hashes,
statistics, errors and arrays are preserved. Current user-home checkout paths
are removed. Generic Octave installation paths remain useful reference metadata.
Older commits retain their original checkout paths, containing the public
maintainer identity and research-tool locations. They were inspected and do
not identify private stimuli or credentials. No historical commits are rewritten.
Pattern scans are bounded evidence, not a guarantee against every possible secret.

## Validation and presentation checks

- Full regression: **1,535 passed in 44.92 seconds** using Python 3.12.10,
  NumPy 2.1.3, SciPy 1.15.1 and Pillow 10.4.0. Command:
  `python -m pytest -q -p no:cacheprovider`.
- Inherited README/content equality, license equality, unchanged figure hash,
  metadata-only fixture changes and unchanged scientific source are checked.
- Repository-relative Markdown file links, GitHub-rendered navigation anchors,
  mode table, both Figure 2 tables and image references are checked.
- External links returned HTTP 200: original/repaired/Python GitHub repositories,
  both paper DOIs (following publisher redirects), OSF, the SHINE website and
  the original PDF manual. The web-search fetcher had some endpoint errors;
  direct HTTP checks succeeded. External availability can change.
- A local wheel build checks source-checkout installation metadata and inclusion
  of README, root license and component notices. Dependencies/reference data
  are not bundled. This wheel is only an ignored packaging check, not a release.
- Git whitespace and final staged inventory checks precede the commit/push.

Detailed local inventories and rendering/build receipts are deliberately ignored
under `reference/.cache/public_release/`. The existing inventory can be rerun
by calling `reference.preflight_audit.audit(reference_toolbox, output_directory)`
from the repository root with development dependencies installed.

## Publication procedure and boundaries

The remote was checked as the intended empty public repository, with default
branch `main`. The publication uses one new documentation/license commit and
the complete existing development history, followed by `git push -u origin main`.
The final receipt must verify public visibility, default branch, equal local
and remote HEAD, rendered README/image, and history equality after fetching.
If the destination gains unexpected content before the push, stop and reconcile
with the owner; do not force-push. No tags, GitHub Release, PyPI publication,
Zenodo registration, announcement, version bump or repaired-fork remote change
is part of this task.

Future maintenance: preserve corpus/environment limits on parity claims,
record any newly established sample-asset provenance, and retain the original
component notices unless their authors clarify them. These notes do not reopen
the completed scientific validation or require an additional normalization run.
