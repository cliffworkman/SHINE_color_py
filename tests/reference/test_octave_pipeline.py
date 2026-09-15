"""Strict Gate 4 parity and positive contracts for dynamically degenerate FFTs."""
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
    known={( 'rgb_20x20','RGB',6,2,1),('rgb_20x20','CIELab',6,1,0)}
    key=tuple(record[k] for k in ('group','colorspace','mode','iterations','rescale_option'))
    if key in known:
        # Preserve the observable ordinary divergence. Then replay the actual
        # pipeline with common forward quantities only at screened stages.
        assert any(d['unequal'] for d in result['working']+result['injected_inputs'])
        result=execute(as_list(f['rgb']),r,replay_hist=True,common_forward_degenerate=True)
        assert result['forward_replays']
        assert any(s['ordinary']['unequal'] for s in result['forward_replays'])
        assert all(s['input_delta']['unequal']==s['replay']['unequal']==0 for s in result['forward_replays'])
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


@pytest.mark.octave_degenerate_spectrum
@pytest.mark.parametrize('space,it,option,index,unequal',[('RGB',2,1,3,343),('CIELab',1,0,1,1)])
def test_histogram_generated_phase_degeneracy(space,it,option,index,unequal):
    record=dict(group='rgb_20x20',colorspace=space,mode=6,iterations=it,rescale_option=option)
    _,r=case(record); stages=as_list(r['stages']); s=stages[index]
    previous=next(p for p in reversed(stages[:index]) if p['channel']==s['channel'])
    assert previous['operation']=='histMatch' and s['operation']=='specMatch'
    a=as_list(s['input']); expected=as_list(s['output'])
    assert delta(a,as_list(previous['output']))['unequal']==0
    # The ORIGINAL working inputs pass; it is this stage's input that fails.
    assert all(characterize(spatial_frequency._decompose(v)[1])['passes'] for v in r['seed'][int(s['channel'])-1,:])
    gaps=[]; regular_gaps=[]; failing=[]
    for image,amp,phase in zip(a,as_list(s['amplitudes']),as_list(s['phases'])):
        py_phase,py_amp=spatial_frequency._decompose(image)
        ref_stats=characterize(amp); py_stats=characterize(py_amp)
        failing.append(not ref_stats['passes'] and not py_stats['passes'])
        low=(amp<=ref_stats['scaled_threshold']) | (py_amp<=py_stats['scaled_threshold'])
        gap=np.abs(np.exp(1j*phase)-np.exp(1j*py_phase))
        if low.any():
            assert ref_stats['near_zero_coefficients']>0 and py_stats['near_zero_coefficients']>0
            gaps.append(float(gap[low].max()))
        assert gap[~low].max(initial=0)<1e-10
        regular_gaps.append(float(gap[~low].max(initial=0)))
    # The Lab case has a smaller, but still amplified, phase discrepancy.
    # The mechanism does not require an arbitrary phase-distance minimum.
    assert any(failing) and max(gaps)>max(regular_gaps)
    ordinary=delta(spectrum.spec_match(a,option),expected)
    assert ordinary['unequal']==unequal and ordinary['max_abs']==1
    pairs=iter(zip(as_list(s['phases']),as_list(s['amplitudes'])))
    with patch.object(spectrum,'_decompose',lambda image:next(pairs)):
        assert delta(spectrum.spec_match(a,option),expected)['unequal']==0
