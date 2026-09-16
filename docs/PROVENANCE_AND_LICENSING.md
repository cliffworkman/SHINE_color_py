# Provenance and licensing

Audit date: 2026-09-16. Original preflight baseline Python commit:
`0862b5f4635a3500afd823343b016189d0dd127e`.
This document preserves the preflight evidence and records the subsequent
public-release decision. It does not resolve historical notice conflicts
by legal interpretation.

## Public-release decision and scientific lineage

The owner explicitly authorized public publication at
[cliffworkman/SHINE_color_py](https://github.com/cliffworkman/SHINE_color_py),
following the original SHINE_color licensing model and retaining useful
reference fixtures. This supersedes the earlier pending-publication decision;
it is not an inference from test agreement or from the root license alone.

The root [MIT license](../LICENSE), including Rodrigo Dal Ben's original
copyright, and [toolbox MIT license](UPSTREAM_TOOLBOX_LICENSE.txt) are preserved
verbatim. [Third-party notices](../THIRD_PARTY_NOTICES.md) retain the narrower
embedded SHINE/SSIM notices, authorship and citations. Newly written Python
code and tooling follow the same repository-level MIT terms, with Cliff
Workman's separate contribution credit. The historical coexistence of MIT and
more restrictive component notices remains explicit, not adjudicated here.

The lineage is original [SHINE_color](https://github.com/RodDalBen/SHINE_color)
by Rodrigo Dal Ben → repaired/maintained 0.0.6 → independent Python behavioral
reimplementation. The [SHINE_color paper](https://doi.org/10.1016/j.mex.2023.102377),
[SHINE paper](https://doi.org/10.3758/BRM.42.3.671),
[original website](http://www.mapageweb.umontreal.ca/gosselif/SHINE/) and
[OSF project](https://osf.io/auzjy/) remain research provenance. Cliff's additions
are repairs, Python implementation, batch workflows, manifests, regression
validation, the Figure 2 audit and maintenance; original authorship is unchanged.

## Implementation and reference provenance

The Python implementation is independently written from mathematical and
behavioral descriptions, the project's behavioral specifications, reference
output comparisons, and empirical GNU Octave behavior. It is not presented
as a mechanical source translation. This is also **not a clean-room claim**:
the HSV specification explicitly records inspection of installed Octave
functions. Source-informed arithmetic conventions need to remain visible
when assessing public-distribution provenance.

The behavioral reference is the repaired `cliffworkman/SHINE_color` merged
main commit `870e058fe8bf1e4090baf2401ff0e127d1c0237a`. Fixtures use its ignored,
unmodified snapshot. At the original preflight the supplied sibling checkout was clean at
`c602d4582f51bde8bda4ed10a360734f62e538dc`; the relevant toolbox content agrees
with the pinned snapshot. Upstream authorship remains with Rodrigo Dal Ben
for SHINE_color and the credited SHINE authors for the original toolbox.

Both reference repository and toolbox `LICENSE` files declare MIT, while
files including `histMatch.m`, `match.m`, `lumMatch.m`, and `lum2scale.m` retain
educational/research-only and commercial-adaptation permission restrictions.
That coexistence is unresolved here; the repository-level file is not assumed
to override embedded notices. GNU Octave/image-package conventions are a
separate provenance consideration; they are not covered by an inferred SHINE
license. The public documentation baseline is the repaired fork's complete
README at `7074df49bf42d622f2ea30c3a838629eada6b787`. It is retained in the Python
README with adjacent Python usage notes. Packaging now includes the root MIT
text and component notices; it neither bundles the reference implementation
nor changes the scientific kernel.

## Full tracked-tree inventory

The baseline contains 274 tracked files. `reference/preflight_audit.py` inventories
every path, SHA-256, size, MAT variable names/shapes, absolute-path hits,
credential-pattern hits, and exact long-line overlaps with reference MATLAB
files. The supplemental scan covers reachable Git history, including binary
blobs, for credential patterns and private/cache path names. These scans are
bounded evidence, not a guarantee against every possible secret or derivation.

| Primary category | Baseline files | Content |
| --- | ---: | --- |
| Original Python implementation | 13 | `shine_color/*.py` |
| Behavioral specifications | 2 | Octave HSV/Lab mathematical conventions |
| Tests | 16 | Synthetic and recorded-reference tests |
| Generated reference fixtures | 117 | PNG/MAT/JSON/CSV fixtures and metadata |
| Original reference/diagnostic harnesses | 48 | Python tooling and external `.m` probes |
| Diagnostic evidence | 58 | Numerical results, comparisons and manifests |
| Documentation | 13 | README and validation records |
| Project configuration | 7 | Packaging, ignore rules and remaining configuration |

No copied upstream implementation file or copied long source/comment line
was found in the scan and harness inspection. Tracked `.m` files are external
export/probe code. The four `pipeline_capture/*Match.m` files delegate to
original function handles; despite their names, they are not copies of the
upstream algorithms. Synthetic numerical calculations in the probes are
diagnostic code. The provenance assessment remains distinct from a legal
conclusion about independent implementation.

For the Figure 2 audit, the exact local 0.0.5 toolbox history at
`330a9be6e49f59e5d68fb985744b2a50c278e8d8` was compared with the repaired
reference. The operation-relevant routines `avgHist.m`, `hist2list.m`,
`match.m`, `histMatch.m` and `lum2scale.m` are byte-identical in both snapshots.
The comparison found no historical algorithm change that explains the Figure 2
label discrepancy.

Tracked PNGs are generated synthetic inputs and the photograph-free Figure 2
histogram/statistics figure. There are **no tracked JPEGs**,
architecture photos, architecture pilot outputs, installed dependencies or
machine caches. The ignored reference snapshot contains upstream source, but
it is not in the tracked tree. `arch_study/` and `reference/.cache/` remain
ignored. The reachable-history scan found no private/cache path or credential
pattern hits. No evidence was removed or rewritten during the audit.

A new untracked `paper/` directory appeared during this preflight, containing
reference paper assets and three smaller cat JPEGs. It is **not part of the
274-file baseline tree**. A narrow `/paper/` ignore rule now prevents accidental
staging while provenance is clarified. Its PDF and `fig2.png` match the sibling
reference assets; the three small JPEGs do not match the nominated upstream
sample hashes. Their files were left untouched and were not used for the
reproduction. These local materials stay ignored and are excluded from publication.

## Cat images and image-derived fixtures

The exact samples reside outside this Python repository at the relative path
`../SHINE_color_fork/toolbox/SHINE_color_INPUT/samples/cat{1,2,3}.jpg`.
All three are 1200 x 1200 RGB JPEGs. Their bytes match the pinned reference
snapshot, the earlier file-workflow hashes, and their first reference Git
version in commit `74884eb7fe0b4a2f5dc09ee155e78ac576871526`.

The historical sample readme at that commit attributes the cats to Pexels;
the Figure 2 caption also attributes them to Pexels. No individual Pexels
asset URL, photographer attribution, acquisition record, or asset-specific
redistribution evidence was identified in the inspected materials. The
paper's CC BY statement and the toolbox's software license are not treated
as proof of rights to redistribute these standalone JPEGs. Individual asset
provenance remains a future documentation task; no standalone JPEGs are added.

Although the JPEG files are not tracked, the tree already contains spatially
organized cat-derived data, **not just hashes or abstract numerical summaries**:

- `reference/backend_policy/data/cats_green_stride1_inputs.mat`: three full
  1200 x 1200 green channels.
- `reference/backend_policy/data/cats_green_stride4_inputs.mat`: three sampled
  300 x 300 green channels.
- `tests/reference/fixtures/conditioned/cats_green_stride1_outputs.mat` and
  `cats_green_stride4_outputs.mat`: corresponding transformed reference arrays.

Changing the container from JPEG to MAT does not resolve image provenance.
The owner reviewed this distinction and explicitly directed preservation of
useful existing image-derived fixtures for this public release. These four
files remain intact for regression reproducibility, with the Pexels attribution
and missing asset-level records disclosed. This release decision does not
assert that a software license grants image rights. Future derived assets need
their own provenance assessment.

The new `tests/reference/fixtures/figure2_baseline.json` is transparent
nonspatial evidence: source file/pixel hashes, 256-bin intensity counts,
summary statistics, and baseline comparison results. It contains no spatial
pixel arrangement or encoded image bytes. It is independently generated
numerical evidence, not a substitute image container or a legal clearance.

## Machine-specific paths

Personal absolute paths originally occurred in `reference/backend_policy/corpus_manifest.json`,
`tests/reference/fixtures/pipeline/octave_manifest.json`, and the captured
warning in `tests/reference/fixtures/single_pixel.json`. Additional absolute
reference-function paths occur in the `color`, `color_adapter` and `hsv_adapter`
fixture directories' `octave_manifest.json` files. Installation paths
also occur in `reference/backend_policy/README.md` and
`reference/compare_fft_backends.py`. Binary MAT string metadata is inspected
by the inventory as well. For the public tree, only the checkout prefixes in the corpus manifest,
pipeline manifest and single-pixel warning were replaced with repository-relative
paths (or a relative sibling path for the original samples), using forward
slashes. Reference commits, source hashes, fixture hashes, measurements, error
identifiers and all numerical arrays remain unchanged. Those path strings
identify source locations; they are not evidence of a fresh reference run.

The historical commits intentionally remain unchanged, as authorized. Their
original checkout paths disclose the already-public maintainer username and
research-tool checkout locations; inspection found no private study filenames,
credentials or unrelated personal files in those paths. Generic Octave
installation paths remain as reproducibility evidence in manifests and the
optional FFT diagnostic script. The public tree has no user-home checkout
paths. This is not a claim that every historical absolute path was erased.

## Dependencies: local package metadata

The production requirements remain only `numpy>=1.24` and `Pillow>=10.4`.
No dependency was added. Versions below are from the Python environment used
for this preflight, not the unrelated `pytest.exe` environment on PATH.
Use `python -m pytest` to select the tested interpreter.

| Package | Installed/tested version | Role | Local metadata license |
| --- | --- | --- | --- |
| NumPy | 2.1.3 | Production | BSD license classifier; BSD redistribution text |
| Pillow | 10.4.0 | Production | HPND |
| pytest | 8.3.4 | Development | MIT |
| SciPy | 1.15.1 | Development/reference | BSD license classifier; BSD redistribution text |
| scikit-image | 0.25.2 | Optional historical converter comparisons | BSD-3-Clause plus per-file notices |
| pyFFTW | Not installed in this interpreter | Optional diagnostic requirements pin 0.15.1 | No installed metadata available; no license guessed |
| Matplotlib | 3.10.0 | Existing local figure tool, not project requirement | Matplotlib license text; PSF classifier |

Binary wheels can bundle additional components and notices. The local audit
records the complete package-declared license text and hashes of available
dist-info license/notice files; the table is not a replacement for those
notices. Licenses of dev/reference dependencies are not automatically
project runtime licenses.

## Evidence and validation claims

The full local inventory is
`reference/.cache/provenance_preflight_20260916/tracked_tree_audit.json`.
It intentionally remains ignored because it contains historical personal-path
metadata. The public-release audit repeats this inventory against the final staged
tree and reachable history; its local detailed output is under
`reference/.cache/public_release/`. See [the release audit](PUBLIC_RELEASE_AUDIT.md)
for the shareable scope and results. Future additions need the same review.

README claims remain corpus- and environment-bounded GNU Octave validation,
with MATLAB parity unestablished, documented FFT degeneracy limits and
stochastic histogram ties. See [Figure 2 reproduction](FIGURE2_REPRODUCTION.md):
the recorded common-input audit establishes exact input/target/matched
histograms and sorted matched working-V outputs across historical 0.0.5,
repaired 0.0.6 and Python. Pillow-common post values reproduce the displayed
126.69 / 74.77. The impossible cat2 baseline SD remains a reported discrepancy,
not a software golden; its origin is unknown. The confirmation rechecked archived
Octave results rather than performing another runtime comparison.
