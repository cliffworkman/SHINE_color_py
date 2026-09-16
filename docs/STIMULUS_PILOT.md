# Architectural stimulus pilot QC

`reference/stimulus_pilot` is research-facing validation tooling around the
validated `shine_color.batch.process_files` workflow. It does not implement a
second normalization path and does not change the public numerical algorithms.

`prepare()` inventories a single explicitly supplied directory, records file
and decoded-pixel hashes, and freezes an output-independent sample manifest.
The pilot must use a common native shape because the validated batch workflow
requires equal dimensions. If a corpus is heterogeneous, the largest exact
native-dimension cohort is selected and the exclusion is recorded; no resize,
crop, or upscale is performed.

`run_pilot()` writes ignored local artifacts containing the frozen manifest,
per-image metrics, stage conditioning records, batch provenance manifests, and
a static HTML review page. Spectral conditioning is evaluated on the actual
arrays entering each `sf` or `spec` stage. Stage instrumentation delegates to
the existing primitives and restores all patched aliases when complete.

The exploratory configuration matrix is intentionally explicit in
`EXPLORATORY_CONFIGS`; it is not a recommendation for final stimulus
generation. Histogram stages retain their existing stochastic tie behavior.
Pilot grouping is one group only and never establishes the final experimental
grouping.

Actual images, normalized outputs, HTML reports, and CSV/JSON research data
belong under `reference/.cache/` or another local ignored artifact directory.
They must not be committed. Tests in `tests/test_stimulus_pilot.py` use only
tiny synthetic arrays.
