"""Gate 4 strict stopping assertions: no tolerance for unexplained uint8 drift."""
from functools import lru_cache
import hashlib
import json
from unittest.mock import patch
import numpy as np
import pytest
from shine_color import histogram,spatial_frequency,spectrum
from shine_color.numeric import imhist256
from reference.pipeline.measure import DEST,SPACES,as_list,load_group,execute,delta
from reference.backend_policy.screen_conditioning import characterize

MANIFEST=json.loads((DEST/'inputs.json').read_text())
RECORDS=json.loads((DEST/'measurements.json').read_text())
CASES=[pytest.param(r,id=f"{r['group']}-{r['colorspace']}-m{r['mode']}-it{r['iterations']}-r{r['rescale_option']}") for r in RECORDS['runs']]


@lru_cache(maxsize=4)
def group(name):
    for suffix in ('_inputs.mat','_reference.mat'):
        path=DEST/(name+suffix)
        assert hashlib.sha256(path.read_bytes()).hexdigest()==RECORDS['fixture_sha256'][path.name]
    return load_group(name)


def case(r):
    f=group(r['group'])
    run=next(a for a in as_list(f['runs']) if SPACES[a['colorspace']]==r['colorspace'] and
             all(a[k]==r[k] for k in ('mode','iterations','rescale_option')))
    return f,run


@pytest.mark.parametrize('record',CASES)
def test_exact_pipeline_or_captured_histogram_replay(record):
    f,r=case(record)
    result=execute(as_list(f['rgb']),r,replay_hist=r['mode'] in (2,5,6,7,8))
    # All cases remain strict ordinary tests. Recorded failures are not an
    # approved tolerance or automatic xfail. This gate must remain visibly open.
    assert all(d['unequal']==0 for d in result['injected_inputs']), result
    assert all(d['unequal']==0 for d in result['working']), result
    assert result['terminal']['unequal']==0, result['terminal']


@pytest.mark.parametrize('record',CASES)
def test_reference_stage_invariants_and_spectral_replay(record):
    _,r=case(record)
    order={1:['lumMatch'],2:['histMatch'],3:['sfMatch'],4:['specMatch'],
           5:['histMatch','sfMatch'],6:['histMatch','specMatch'],
           7:['sfMatch','histMatch'],8:['specMatch','histMatch']}[r['mode']]
    active=[1,2,3] if r['colorspace']==1 else ([3] if r['colorspace']==2 else [1])
    for channel in active:
        stages=[s for s in as_list(r['stages']) if s['channel']==channel]
        assert [s['operation'] for s in stages]==order*r['iterations']
        previous=list(r['seed'][channel-1,:])
        for index,s in enumerate(stages):
            assert s['iteration']==index//len(order)+1
            assert delta(as_list(s['input']),previous)['unequal']==0
            previous=as_list(s['output'])
        assert delta(previous,list(r['working'][channel-1,:]))['unequal']==0
    for s in as_list(r['stages']):
        a=as_list(s['input']); expected=as_list(s['output'])
        if s['operation']=='histMatch':
            np.testing.assert_array_equal(histogram.average_histogram(a),np.asarray(s['target_histogram']).ravel())
            actual=histogram.hist_match(a,rng=np.random.default_rng(391))
            for output,ref in zip(actual,expected):
                assert output.shape==ref.shape and output.dtype==ref.dtype==np.uint8
                np.testing.assert_array_equal(imhist256(output),imhist256(ref))
                # Same sorted values imply identical mean/sample SD without
                # making the random spatial assignment part of the contract.
                sa=np.sort(output.ravel()); sb=np.sort(ref.ravel())
                assert sa.mean()==sb.mean()
                assert sa.std(ddof=1)==sb.std(ddof=1)
        elif s['operation'] in ('sfMatch','specMatch'):
            module=spatial_frequency if s['operation']=='sfMatch' else spectrum
            func=module.sf_match if s['operation']=='sfMatch' else module.spec_match
            ref_pass=all(characterize(v)['passes'] for v in as_list(s['amplitudes']))
            py_pass=all(characterize(spatial_frequency._decompose(v)[1])['passes'] for v in a)
            if ref_pass and py_pass:
                assert delta(func(a,r['rescale_option']),expected)['unequal']==0
            else:
                # The approved degeneracy class remains separate. Exact forward
                # replay tests downstream behavior without changing production.
                pairs=iter(zip(as_list(s['phases']),as_list(s['amplitudes'])))
                with patch.object(module,'_decompose',lambda image:next(pairs)):
                    assert delta(func(a,r['rescale_option']),expected)['unequal']==0
