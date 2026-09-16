# Gate 5A: file-based research workflow

The file API loads a complete stimulus group, calls the validated in-memory
pipeline once, saves exact terminal RGB uint8 PNG pixels, and writes a JSON
manifest identifying the inputs, outputs, parameters and software. It does
not change any scientific algorithm. Use the **entire set to be normalized
together**: SHINE targets are computed across the group, so processing one
file at a time is not equivalent.

```python
from shine_color.batch import process_files, process_directory

result = process_files(
    ["stimuli/building_001.jpg", "stimuli/building_002.jpg", "stimuli/building_003.png"],
    "normalized",
    colorspace="HSV",
    mode=1,
    iterations=1,
    rescale_option=1,
)
print(result.output_paths)
print(result.manifest_path)  # normalized/manifest.json

# Alternatively: supported top-level files, sorted as one normalization group.
result = process_directory("stimuli", "normalized_second_set", "CIELab", 3)
```

Both functions have the same processing parameters and keyword-only
`overwrite=False`. `process_files` accepts an ordered sequence with at least
two source paths. It resolves files, preserves their sequence, loads all images,
checks dimensions after orientation, preflights every destination, and invokes
`pipeline.run(images, colorspace, mode, iterations, rescale_option)` **once**.
All oriented arrays must have the same nonempty `(height,width,3)` shape.

The returned `BatchResult` has `output_paths`, `manifest_path`, and `manifest`
(the JSON-compatible dictionary written to disk). It does not retain another
copy of every output array. Independent `shine_color.io.load_rgb(path)` and
`save_rgb(array, path, overwrite=False)` provide the same representation
contract. `save_rgb` requires an existing parent directory; batch functions
create their output directory only after successful group processing.

## Parameters and scope

Colorspace is RGB, HSV, or CIELab, case-insensitive; Lab is an alias. HSV
processes only working V, Lab only working L, and RGB processes channels
independently. Mode is required. Iterations is a positive integer and chains
the preceding output. Rescale is 0/1/2 and applies only to spectral stages.
The file layer delegates parameter validation and normalization to the core.

| Mode | Ordered operations per iteration |
| --- | --- |
| 1 | lum_match |
| 2 | hist_match |
| 3 | sf_match |
| 4 | spec_match |
| 5 | hist_match -> sf_match |
| 6 | hist_match -> spec_match |
| 7 | sf_match -> hist_match |
| 8 | spec_match -> hist_match |

## Image representation

**Pillow is the explicit image-I/O runtime dependency (`Pillow>=10.4`).**
It supplies PNG/JPEG codecs and EXIF orientation support without requiring
SciPy or scikit-image. The implementation was tested with Pillow 10.4.0,
Python 3.12.10 and NumPy 2.1.3; these are measured versions, not a claim that
every future decoder build is numerically identical. Every batch records
Pillow, libjpeg and zlib versions as well as Python/NumPy.

| Input | Policy |
| --- | --- |
| PNG / JPEG RGB | Decode to ordinary RGB uint8 |
| Grayscale / black-and-white | Expand to 8-bit if necessary, then replicate channels |
| Opaque palette PNG | Look up its 8-bit RGB palette entries |
| RGBA / LA / any transparency metadata | Reject, even if alpha is entirely opaque or the transparent index is unused |
| 16-bit PNG or other high-bit-depth data | Reject; no implicit down-conversion |
| CMYK, other color modes | Reject |
| Multiframe/APNG | Reject |
| TIFF, GIF, other formats | Unsupported |

Inputs must have `.png`, `.jpg`, or `.jpeg` extensions, case-insensitively;
the decoded format must match the extension. Unsupported explicit files or
invalid supported files raise errors. JPEG inputs have already incurred
lossy encoding: the scientific input is the decoded RGB array, whose hash is
recorded. JPEG output is not offered. Every output is a lossless RGB PNG.

Pillow can expose a 16-bit RGB PNG as decoded mode RGB with 8-bit components.
The loader therefore checks the PNG IHDR bit depth **before decoding**, in
addition to decoded-mode checks. This prevents silently collapsing scientific
16-bit data. See the tested
[Pillow 10.4.0 PNG decoder](https://github.com/python-pillow/Pillow/blob/10.4.0/src/PIL/PngImagePlugin.py).

EXIF orientation 1..8 is normalized on load, including mirrored orientations.
Processing uses the physically oriented array; shape checks follow orientation.
Invalid orientation values are rejected. Outputs are fresh RGB images without
EXIF, so an already rotated result cannot be rotated again by a stale tag.
The behavior follows [Pillow's EXIF transpose operation](https://pillow.readthedocs.io/en/stable/reference/ImageOps.html#PIL.ImageOps.exif_transpose)
and is tested independently against array transforms for all eight cases.

**No ICC or gamma color transformation is performed.** ICC/gamma metadata is
recorded as present/absent, then omitted from outputs together with EXIF, XMP
and other ancillary metadata. RGB PNG code values are preserved; grayscale
replication, palette lookup, orientation, and normal JPEG decoding are explicit
representation operations. ImageCms is never invoked. The output is untagged:
this contract concerns scientific pixel values, not identical appearance under
different color-managed viewers. Convert profile-dependent inputs explicitly
before use if the study requires a particular color space. No hidden background
color, alpha compositing, gamma application, scaling or channel reordering occurs.

## Ordering, names and existing files

`process_files` preserves the resolved input sequence. Duplicate source files,
including hard-link aliases, are rejected. Output names are `<input stem>.png`.
Stems must be unique under Unicode `casefold`, so `A.jpg` and `a.png` cannot
silently collapse into one output. Existing case-variant destination names
also produce a clear error. Inputs can never be overwritten by outputs, even
with `overwrite=True`, including existing hard-link aliases.

`process_directory` selects only regular, non-symlink files directly inside
the input directory. Ordering is `(filename.casefold(), filename)` using
Python Unicode ordering, not operating-system enumeration or natural-number
sorting. Unsupported extensions, symlinks and subdirectories are ignored.
Supported extensions containing invalid or disallowed image data cause the
whole operation to fail. The input and output directories must differ.
An output directory nested inside the input is safe because traversal is
nonrecursive. The manifest records the resulting ordered sequence explicitly.

All output PNG destinations **and manifest.json** are checked before pipeline
processing. Existing destinations fail by default. `overwrite=True` explicitly
permits replacing the named outputs and manifest, and is recorded in provenance.
Unrelated files are preserved; use the manifest's output list to identify the
current batch rather than assuming every file in the folder belongs to it.
Output symlinks and directory/file conflicts are rejected.

## Publication and failure behavior

After processing succeeds, the batch acquires an exclusive `.shine-color.lock`
directory, repeats destination checks, and stages files in a fresh directory
inside the output directory. Each PNG is reloaded and required to match the
pipeline's returned uint8 array exactly before publication. Final file hashes
are checked as outputs are published. **manifest.json is published last.**

Default publication uses atomic no-clobber hard links from staged files to
final names. This prevents a late-arriving destination from being overwritten,
including a manifest created after preflight. NTFS is tested. Filesystems that
do not support hard links fail explicitly rather than falling back to unsafe
overwriting. Explicit overwrite uses same-filesystem `os.replace`.

For overwrite, all previous destination files are backed up in staging before
any final file changes. The old manifest is removed before output replacement.
Caught publication failures roll back installed files; the old manifest is
restored only after every old output is restored. Caught staging/processing
failures leave previous outputs unchanged. New files from a failed publication
are removed; unrelated or late-arriving external files are preserved when
overwrite is disabled. Successful operations remove their staging and lock.
Cleanup retries Windows sharing/lock violations (errors 32/33) with a bounded
3.15-second total backoff. Other permission failures are not suppressed. A
real-photo rerun exposed a transient sharing violation in the Dropbox-backed
workspace after successful publication; the retry and persistent-failure
behavior now have explicit regression tests. If cleanup still fails, the call
raises and retains the lock. A fully written manifest may then exist because
only cleanup failed; verify its hashes and inspect the lock/staging files before
using or recovering that completed batch.

This is **not a power-loss-safe, directory-wide transaction**. Forced process
termination or a power failure can leave partial files and the lock/staging
directory. Readers and other tools must not use or modify a batch directory
while its lock exists. If rollback itself fails, `BatchRecoveryError` reports
the retained recovery path; the lock and backup copies remain and no old
success manifest is restored. Inspect these files and verify hashes before
manually recovering; a subsequent call will refuse the lock. There is no
automatic deletion of unknown recovery files. No guarantees are made for
noncooperating concurrent overwrite writers or storage failures that prevent
rollback. An empty newly created output directory may remain after a failure.

## Manifest schema 1 and reproducibility

Each successful batch has one UTF-8 `manifest.json` with:

* `software`: project/version, Git SHA and dirty state when available, source
  implementation digest, Python/NumPy/Pillow versions, libjpeg/zlib versions.
* `pipeline`: canonical colorspace, mode, ordered operations per iteration,
  iterations and rescale option.
* `group`: count, `provided_sequence` ordering and explicit ordered input names.
  The directory helper passes its deterministically sorted sequence here.
* `inputs`: relative filename, byte size, original format/mode, stored and
  oriented dimensions, EXIF orientation/application, ICC/gamma presence,
  original-file hash and oriented decoded-pixel hash.
* `outputs`: PNG filename, byte size, dimensions, file hash and final pixel hash.
* UTC processing timestamps, overwrite flag, I/O policies, hashing definition,
  and histogram randomness classification.

All file hashes are SHA-256 of exact file bytes. Input hashing and decoding
consume the same byte snapshot. Pixel hashes are SHA-256 of uint8 RGB bytes in
**C order `(height,width,3)`**; dimensions are recorded separately as
`[width,height]`. No absolute source paths, usernames or hostnames are needed.
The source implementation digest hashes sorted module names and source bytes;
Git commit alone does not describe uncommitted edits, so dirty state and this
digest are also recorded. Git fields are null when unavailable, as in an
installed package without its repository. Version remains **0.1.0.dev0**;
no release or Git tag was created.

Histogram tie breaking currently creates a fresh `numpy.random.default_rng()`
when no private test RNG is supplied. Modes 2/5/6/7/8 therefore record
`histogram_tie_breaking: "stochastic_unseeded"`; modes 1/3/4 record
`"not_applicable"`. There is no new public seed parameter or automatic seed.
The manifest identifies the actual generated outputs; it does not promise
bitwise rerun reproducibility for unseeded histogram modes, or across changed
JPEG decoders/FFT/runtime builds. The existing FFT degeneracy policy remains
in force at each actual spectral-stage input.

## Validation evidence

The complete suite reports **1,499 passed in 51.10 seconds**, with zero failures,
skips or xfails: 1,412 unchanged prior tests plus 87 new tests (39 I/O, 48 batch).
New temporary-directory
tests cover exact PNG round trips, supported representation policies, all eight
orientations, high-depth rejection, ignored ICC/gamma metadata, group invocation,
stable ordering, shape errors, collisions, overwrite/source protection, manifest
content/hashes, publication races, rollback and retained recovery after failed
rollback. No network access is required by the tests.

Batch-versus-direct comparisons require exact saved PNG pixels for RGB mode 1,
HSV mode 3, Lab mode 4 and combined modes 5..8 at two iterations with varied
rescale options. Histogram comparisons use scoped Python RNG control in tests
only. The scientific pipeline and all original reference fixtures are unchanged.

The non-destructive smoke test uses only the three previously nominated
`cat1.jpg`, `cat2.jpg`, `cat3.jpg` reference photographs, with original SHA-256
values checked against the existing corpus. At full 1200x1200 resolution, HSV
mode 1 runs once on all three images. All PNG reloads equal the returned arrays
exactly; input bytes remain unchanged; manifest fields and hashes verify.
Temporary image outputs are removed. The compact retained evidence is
`reference/file_workflow_smoke.json`, reproduced with
`python -m reference.check_file_workflow`. This is workflow validation, not
validation on experimental architectural stimuli.

Run `python -m pytest -q -p no:cacheprovider` for the complete suite. The final
Gate 5A result and test count are recorded in `docs/VALIDATION.md`.

Supported claim: **The Python implementation provides a validated file-based
research workflow around the previously validated in-memory SHINE_color
pipeline. PNG output preserves the pipeline's terminal RGB uint8 arrays
exactly, and each batch records parameters and file/pixel hashes sufficient
to identify the processed stimulus set and software configuration.**

MATLAB numerical parity has not been established and remains a future
non-blocking secondary validation target. Universal validation is not claimed.
Masking/background detection/templates, optimized/SSIM histogram matching,
CLI, GUI, interactive wizard, video, upscaling, public release and GitHub
publication remain excluded. Gate 5A stops here for human review. No remote,
push or publication occurred.
