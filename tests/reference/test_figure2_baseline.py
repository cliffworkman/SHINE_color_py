"""Nonspatial baseline evidence only; no cats, Octave, matplotlib or network."""
import json
from pathlib import Path
import numpy as np
import pytest
from reference.figure2_baseline import histogram_statistics, PRINTED

ROOT=Path(__file__).resolve().parents[2]
EVIDENCE=json.loads((Path(__file__).parent/'fixtures/figure2_baseline.json').read_text())


@pytest.mark.parametrize('index',range(3))
def test_original_histogram_statistics_and_provenance(index):
    row=EVIDENCE['sources'][index]
    counts=np.array(row['histogram'])
    assert counts.shape==(256,) and counts.sum()==1200*1200 and np.all(counts>=0)
    mean,sd=histogram_statistics(counts)
    assert mean==row['mean']
    assert sd==pytest.approx(row['sample_sd'],abs=1e-12,rel=0)
    assert [f'{mean:.2f}',f'{sd:.2f}']==row['rounded']
    smoke=json.loads((ROOT/'reference/file_workflow_smoke.json').read_text())
    source=smoke['manifest']['inputs'][index]
    assert row['file_sha256']==source['file_sha256']
    assert row['pixel_sha256']==source['pixel_sha256']
    assert row['printed']==list(PRINTED[index])


def test_baseline_mismatch_is_visible_not_an_xfail_or_post_claim():
    assert EVIDENCE['classification']=='baseline_mismatch_stop'
    assert [r['matches_printed'] for r in EVIDENCE['sources']]==[[False,False],[True,False],[True,True]]
    assert EVIDENCE['normalization_executed'] is False
    assert EVIDENCE['post_histograms'] is None and EVIDENCE['post_statistics'] is None


def test_reference_agrees_for_common_decoded_pixels_but_not_jpeg_decoders():
    reference=EVIDENCE['octave']
    assert reference['common_decoded_histograms']==[r['histogram'] for r in EVIDENCE['sources']]
    assert reference['common_decoded_histograms_equal']==[True]*3
    assert reference['jpeg_histograms_equal']==[False]*3
    assert all(n>0 for n in reference['source_jpeg_decoded_unequal'])


def test_cat2_published_sd_exceeds_bound_even_with_two_decimal_mean_uncertainty():
    n=1200*1200
    # E[X^2] <= 255 E[X] for 0 <= X <= 255, then sample correction.
    maximum_mean=80.345
    maximum_sd=np.sqrt(n/(n-1)*maximum_mean*(255-maximum_mean))
    assert maximum_sd<127.255


def test_statistics_from_counts_matches_explicit_sample():
    sample=np.array([0,0,10,128,255],dtype=np.uint8)
    mean,sd=histogram_statistics(np.bincount(sample,minlength=256))
    assert mean==sample.mean()
    assert sd==pytest.approx(sample.std(ddof=1),abs=1e-12,rel=0)


@pytest.mark.parametrize('counts',[np.zeros(255),np.zeros(256),-np.ones(256)])
def test_statistics_reject_invalid_counts(counts):
    with pytest.raises(ValueError): histogram_statistics(counts)
