# Provenance and licensing preflight

Audit date: 2026-09-16. Baseline Python commit:
`0862b5f4635a3500afd823343b016189d0dd127e`.
This is a repository-content audit, not legal advice or a license grant.
No final public-distribution license decision has been made. Do not apply MIT
or any other public license to this project by inference from its reference.

## Private repository versus public distribution

No technical blocker to a private backup/collaboration push was identified in
the audited tree and reachable history. No credential patterns or private
architectural-study assets were found. Pending public licensing is not, by
itself, treated as a blocker to a private research repository. This finding
does not confer distribution rights or approve a public release. No remote
was configured and nothing was pushed during this task.

Public release still requires decisions on upstream notices, image-derived
fixtures, third-party notices, and personal paths in historical evidence.
Reference-output agreement does not settle any of those questions.

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
unmodified snapshot. The supplied sibling checkout remains clean at
`c602d4582f51bde8bda4ed10a360734f62e538dc`; the relevant toolbox content agrees
with the pinned snapshot. Upstream authorship remains with Rodrigo Dal Ben
for SHINE_color and the credited SHINE authors for the original toolbox.

Both reference repository and toolbox `LICENSE` files declare MIT, while
files including `histMatch.m`, `match.m`, `lumMatch.m`, and `lum2scale.m` retain
educational/research-only and commercial-adaptation permission restrictions.
That coexistence is unresolved here; the repository-level file is not assumed
to override embedded notices. GNU Octave/image-package conventions are a
separate provenance consideration; they are not covered by an inferred SHINE
license. There is no license field granting public rights in `pyproject.toml`
and no Python-project LICENSE was added.

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

Tracked PNGs are generated synthetic inputs. There are **no tracked JPEGs**,
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
reproduction. Private-push readiness assumes these local materials stay ignored.

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
as proof of rights to redistribute these standalone JPEGs. Status: unresolved
public-release review item; no assets were deleted.

Although the JPEG files are not tracked, the tree already contains spatially
organized cat-derived data, **not just hashes or abstract numerical summaries**:

- `reference/backend_policy/data/cats_green_stride1_inputs.mat`: three full
  1200 x 1200 green channels.
- `reference/backend_policy/data/cats_green_stride4_inputs.mat`: three sampled
  300 x 300 green channels.
- `tests/reference/fixtures/conditioned/cats_green_stride1_outputs.mat` and
  `cats_green_stride4_outputs.mat`: corresponding transformed reference arrays.

Changing the container from JPEG to MAT does not resolve image provenance.
These four files require public-release review along with any future derived
image artifacts. They remain intact for private validation.

The new `tests/reference/fixtures/figure2_baseline.json` is transparent
nonspatial evidence: source file/pixel hashes, 256-bin intensity counts,
summary statistics, and baseline comparison results. It contains no spatial
pixel arrangement or encoded image bytes. It is independently generated
numerical evidence, not a substitute image container or a legal clearance.

## Machine-specific paths

Personal absolute paths occur in `reference/backend_policy/corpus_manifest.json`,
`tests/reference/fixtures/pipeline/octave_manifest.json`, and the captured
warning in `tests/reference/fixtures/single_pixel.json`. Additional absolute
reference-function paths occur in the `color`, `color_adapter` and `hsv_adapter`
fixture directories' `octave_manifest.json` files. Installation paths
also occur in `reference/backend_policy/README.md` and
`reference/compare_fft_backends.py`. Binary MAT string metadata is inspected
by the inventory as well. Review/redact paths before a public release using
a documented provenance-preserving procedure, including reachable history
if necessary. They do not contain credentials; this audit leaves historical
evidence untouched.

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
metadata. Re-run the audit against the intended commit/tree before any future
public release; additions since this baseline need their own inventory.

README claims remain corpus- and environment-bounded GNU Octave validation,
with MATLAB parity unestablished, documented FFT degeneracy limits and
stochastic histogram ties. Neither successful tests nor a private push means
public-release readiness. See `FIGURE2_REPRODUCTION.md` for the separate
baseline mismatch that currently prevents a strong Figure 2 reproduction claim.
