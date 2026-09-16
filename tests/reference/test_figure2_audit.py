"""Offline regression from nonspatial counts; never reconstruct source photos."""
import copy
import hashlib
import json
from pathlib import Path

import numpy as np
import pytest
from shine_color import histogram
from shine_color.numeric import imhist256
from reference.figure2_audit import compare_records
from reference.figure2_baseline import histogram_statistics

DATA=json.loads((Path(__file__).parent/'fixtures/figure2_audit.json').read_text())


@pytest.mark.parametrize('path',['pillow','octave'])
def test_actual_histogram_kernel_against_reference_counts(path):
    evidence=DATA['paths'][path]
    reference=evidence['octave']
    # A 1-D ordered multiset exercises the histogram algorithm without saving
    # or recovering the photographs' spatial arrangement. Ties remain unseeded.
    inputs=[np.repeat(np.arange(256,dtype=np.uint8),h)[None,:] for h in reference['pre']['histograms']]
    target=histogram.average_histogram(inputs)
    np.testing.assert_array_equal(target,reference['target'])
    outputs=histogram.hist_match(inputs)
    for i,a in enumerate(outputs):
        np.testing.assert_array_equal(imhist256(a),reference['post']['histograms'][i])
        assert hashlib.sha256(np.sort(a.ravel()).tobytes()).hexdigest()==evidence['sorted_post_sha256'][i]
    assert sum(reference['target'])!=inputs[0].size  # target-list resampling matters
    assert all(sum(h)==inputs[0].size for h in reference['post']['histograms'])


@pytest.mark.parametrize('path',['pillow','octave'])
def test_archived_common_input_parity_and_old_reference(path):
    r=DATA['paths'][path]
    for ref in ('octave','historical'):
        assert r['python']['pre']['histograms']==r[ref]['pre']['histograms']
        assert r['python']['target']==r[ref]['target']
        assert r['python']['post']['histograms']==r[ref]['post']['histograms']
        assert all(h==r[ref]['post']['histograms'][0] for h in r[ref]['post']['histograms'])
    assert r['batch_histograms_equal']
    assert r['comparison']['sorted_values_equal']==[True]*3
    assert r['historical_comparison']['sorted_values_equal']==[True]*3


@pytest.mark.parametrize('path,rounded',[('pillow',['126.69','74.77']),('octave',['126.70','74.78'])])
def test_decoder_dependent_publication_labels(path,rounded):
    r=DATA['paths'][path]
    for runtime in ('python','octave','historical'):
        for h in r[runtime]['post']['histograms']:
            m,s=histogram_statistics(h)
            assert [f'{m:.2f}',f'{s:.2f}']==rounded
    assert all(r['python']['post']['published_label_agreement'])==(path=='pillow')


@pytest.mark.parametrize('index',range(3))
def test_decoder_evidence_hashes_and_counts(index):
    r=DATA['decoders'][index]
    assert r['dimensions']==[1200,1200]
    assert r['unequal_percent']==100*r['unequal_rgb_scalars']/r['total_rgb_scalars']
    assert 0<r['mean_abs_channel_difference']<1<r['max_abs_channel_difference']
    assert r['pillow_pixel_sha256']!=r['octave_pixel_sha256']
    for path,key in [('pillow','pillow_pixel_sha256'),('octave','octave_pixel_sha256')]:
        assert r[key]==DATA['paths'][path]['common_input_pixel_sha256'][index]


@pytest.mark.parametrize('stage',['pre','target','post','sorted'])
def test_comparison_rejects_one_count_or_value_error(stage):
    r=DATA['paths']['pillow']; python=copy.deepcopy(r['python']); reference=r['octave']
    sorted_values=[np.arange(3,dtype=np.uint8) for _ in range(3)]
    other=[a.copy() for a in sorted_values]
    if stage=='target': python['target'][0]+=1
    elif stage=='sorted': other[0][0]=1
    else: python[stage]['histograms'][0][0]+=1
    assert not compare_records(python,reference,sorted_values,other)['passes']


def test_published_cat2_sd_remains_impossible_and_not_explained_by_decoder():
    r=DATA['decoders'][1]
    for mean,sd in (r['pillow_working_v'],r['octave_working_v_using_same_python_hsv']):
        bound=np.sqrt(1440000/1439999*mean*(255-mean))
        assert sd<bound<127.255
    assert abs(r['pillow_working_v'][1]-r['octave_working_v_using_same_python_hsv'][1])<.04
