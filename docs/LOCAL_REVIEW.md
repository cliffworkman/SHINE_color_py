# Local stimulus review (Phase 1)

Compare a completed SHINE_color_py normalization run, inspect original/corrected
pairs, and save human judgments. The reviewer never runs normalization or resizes
the stimuli. It uses the package's existing NumPy and Pillow dependencies plus
Python's standard library; no web framework, Node installation, cloud service, or
account is needed.

## Build and open

Run these commands in the Python environment where SHINE_color_py is installed:

```powershell
python -m shine_color.review build --inputs "C:\study\originals" --outputs "C:\study\corrected" --manifest "C:\study\corrected\manifest.json" --review-dir "C:\study\review"
python -m shine_color.review serve "C:\study\review"
```

The server opens the default browser at a randomly assigned `127.0.0.1` port.
Use `--no-browser` to print the address without opening it, or `--port 8765` to
choose a port. Ctrl+C stops the server. Repeating `serve` resumes the same review.
Keep the terminal running while reviewing. This server is for one local machine;
it is not a remotely hosted multiuser service.

The review directory must be new and outside both image directory trees. Import
checks manifest file hashes, decoded pixel hashes, dimensions, group ordering,
and pair mapping. It rejects ambiguous/missing pairs and unsupported manifests.
It reads only manifest-listed images. Original and corrected files are unchanged.
Each pair must have identical decoded dimensions; different pairs can have
different dimensions in the supported native manifest.

Supported inputs:

- Schema-1 manifests from `batch.process_files` / `batch.process_directory`, modes
  1 (luminance matching) and 2 (histogram matching), in RGB, HSV, or CIELab.
- The existing `native_dimension_CIELab_luminance_batch` manifest, mode 1.

Modes 3–8 are deliberately rejected. Multiple iterations can be inspected, but
unrecorded targets for repeated stages are marked unavailable.

Python entry points:

```python
from shine_color.review import compare_batch, open_report

report = compare_batch(
    "originals", "corrected", manifest="corrected/manifest.json",
    review_dir="review",
)
report.to_csv("measurements.csv")
report.to_json("measurements-and-review.json")
# Later, without rebuilding:
report = open_report("review")
report.export("review-snapshot.zip", include_images=True)
```

## Review workflow

Side-by-side images share zoom and pan. Fit shows the full image; 1:1 uses one
image pixel per CSS pixel (the physical display scale can differ). Drag either
panel to pan; use the wheel or buttons to zoom. Arrow keys navigate outside text
fields. The overview thumbnail provides context when zoomed.

Choose **Unreviewed**, **Accept**, **Flag**, or **Reject**, with optional reviewer
name and notes. Changes save to `review.sqlite3` with UTC timestamps, revisions,
and a complete decision history. Navigation and export flush pending notes.
The page reports failed saves and blocks navigation until they are resolved.
Competing edits from another tab cause a conflict instead of silently overwriting
a decision: preserve your unsaved note, reload, then reconcile the edit.

Filter by decision and sort by filename, RGB change, channel mean/SD shift,
histogram change, or recorded gamut clipping. Rankings describe transformation
magnitude; they never automatically accept or reject an image. Dataset summaries
show per-image pre/post scatterplots, mean and SD distributions, an average
probability histogram, and the flagged/rejected list.

Review projects contain their own decoded PNG views and can be moved after
creation. These full-size views use the same stored-RGB decoder policy as the
normalizer: EXIF orientation is applied, but ICC/gamma conversion is not. An
untagged PNG view avoids having the browser interpret an original JPEG's embedded
profile differently. The viewer implies no display calibration. Only overview
thumbnails are resized. Budget disk space for both full-size image sets.

## Measurement meaning

All per-image statistics describe the original decoded image and the **saved
RGB output**, not an assumed pre-save intermediate. HSV V and CIELab L use
SHINE's quantized 0–255 working-channel conventions; L is not raw L* and these
codes are not physical luminance. RGB reports R, G, and B separately. SD is sample
SD (`ddof=1`; singleton SD is zero).

| Field | Meaning |
| --- | --- |
| `pre`, `post_saved` | Mean, sample SD, 256-bin histogram, fractions at 0 and 255 |
| `delta_mean`, `delta_sample_sd` | Saved output minus original |
| `rgb_rmse`, channel `rmse` | Aligned pixel RMSE in stored RGB / selected working channel |
| `histogram_total_variation` | Half the L1 distance between probability histograms, 0–1 |
| `target_*`, `target_provenance` | Derived expected target where recoverable; otherwise null with explanation |
| `recorded_intermediate_*` | Intermediate channel statistics explicitly present in the native manifest |
| `post_minus_recorded_*` | Saved/re-extracted statistics minus recorded intermediate statistics |
| `gamut_clip_fraction` | Recorded pre-quantization RGB out-of-gamut pixel fraction, if available |
| `working_L_clip_fraction` | Recorded native-run working-L clipping fraction, if available |

For one iteration of mode 1, targets are equal-image averages of the input channel
means and sample SDs. For one iteration of a standard mode-2 batch, the target
histogram is derived from rounded average bin counts and SHINE's target-list rank
resampling. This computation does not rerun matching or consume randomness.
Target deviations include clipping, quantization, and color reconstruction effects;
they are not evidence of an implementation error on their own.

Standard batch manifests do not record intermediate channel or gamut statistics.
Those values remain unavailable; a saved pixel at 0 or 255 is not proof of gamut
clipping. Native manifest intermediate values are labeled recorded, whereas
saved-output values are measured anew. Group statistics give every image equal
weight, even when image sizes differ. Per-image distribution plots round statistics
into unit-width bins; JSON retains the unrounded values.

## Persistence, export, and identity

The schema records stimulus ID, exact pair ID, run/manifest SHA-256, source/output
hashes, dimensions, pipeline settings, software provenance, metric version, and
metric domains. Decisions are bound to exact pairs and the project identity.
Rebuilding a changed run creates a separate project with no inherited acceptance.
Image hashes are checked when serving; altered review assets require rebuilding
from verified inputs. Source images may be offline after import.

Browser CSV/JSON exports include the latest saved decisions. CSV has one row per
stimulus and explicit channel column names. Missing values are blank; JSON uses
null. CSV string cells that could be spreadsheet formulas receive a leading
apostrophe; JSON preserves exact note text. JSON also includes decision history.
The initial `metrics.csv` in the project is a build-time snapshot; use browser or
Python export for current decisions.

```powershell
python -m shine_color.review export "C:\study\review" "C:\study\review.zip" --include-images
```

A new ZIP contains report/manifest JSON, metrics and decision CSVs, decision
history JSON, and the viewer. Omit `--include-images` for a metadata-only snapshot.
Existing ZIPs are never replaced. To view an extracted snapshot, start a local
static server (for example `python -m http.server 8765 --bind 127.0.0.1`) in its
directory and open `http://127.0.0.1:8765`. Snapshot views are read-only; opening
`index.html` directly through `file://` is not supported. Stop the static server
when finished. Exports contain filenames, provenance, and reviewer notes; include
images only when you intend to share them.

Back up a live project's entire directory with the reviewer stopped. Do not edit
one SQLite database simultaneously from different machines through a synced
folder. Portable exports are the supported way to share a review snapshot.

## Scope and lineage

This implements Phase 1 of [issue #1](https://github.com/cliffworkman/SHINE_color_py/issues/1).
Spectral diagnostics, external metadata joins, cross-run bakeoffs, and SSIM remain
backlog items. Explicit run/pair identities and metric domains allow future schema
extensions without treating absent measurements as zero. This feature does not
change normalization code, reference fixtures, tolerances, or package version.

SHINE_color: Rodrigo Dal Ben (2023), *MethodsX* 11, 102377,
https://doi.org/10.1016/j.mex.2023.102377. SHINE: Willenbockel, Sadr, Fiset, Horne,
Gosselin, and Tanaka (2010), *Behavior Research Methods* 42, 671–684,
https://doi.org/10.3758/BRM.42.3.671. Existing project licensing and component notices
continue to apply.

The review feature was motivated by Vasiliki and Cliff's architectural-stimulus
review, proposed by Cliff Workman, and elaborated with ChatGPT. Its interaction
design was informed by Cliff Workman's stimulus-upscaler reviewer. The code was
independently written for SHINE_color_py with substantial OpenAI Codex assistance
under human direction and review; no stimulus-upscaler source was copied.

## Phase 1 implementation record — 2026-10-15

Cliff Workman authorized this bounded implementation after the read-only issue
planning pass, incorporating ChatGPT's modes-1–2 scope. OpenAI Codex implemented
and tested it under that direction. No external metadata joins, spectral metrics,
or cross-run comparisons were added.

Validation on Windows / Python 3.12.10: all 1,561 tests passed (1,535 existing,
26 new). The new tests exercise all three colorspaces in modes 1 and 2, recovered
targets against the scientific API, unequal native pair dimensions, manifest
validation, recorded versus unavailable evidence, decision persistence/conflicts,
exports, asset verification, and local HTTP controls. Headless Edge checks covered
immediate note/navigation saves, reload persistence, synchronized zoom/pan and fit,
filtering, dataset plots, CSV download, lineage, and the exported read-only viewer.
A wheel build/install check confirmed that all browser assets ship in the package.
