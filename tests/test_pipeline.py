"""Dataflow, explicit composition and API regressions for the whole-image pipeline."""
from pathlib import Path
from unittest.mock import patch
import numpy as np
import pytest
from scipy.io import loadmat
from shine_color import pipeline,color,histogram,luminance,spatial_frequency,spectrum
from shine_color.numeric import to_uint8

FIXTURES=Path(__file__).parent/'reference/fixtures/pipeline'


@pytest.fixture
def images():
    return list(loadmat(FIXTURES/'rgb_17x19_inputs.mat')['inputs'].ravel())


def manual_channel(images,mode,iterations,option,rng):
    current=images
    for _ in range(iterations):
        if mode==1: current=luminance.lum_match(current)
        if mode in (2,5,6): current=histogram.hist_match(current,rng=rng)
        if mode in (3,5,7): current=spatial_frequency.sf_match(current,option)
        if mode in (4,6,8): current=spectrum.spec_match(current,option)
        if mode in (7,8): current=histogram.hist_match(current,rng=rng)
    return current


def manual(images,space,mode,iterations,option,rng):
    parts=[list(getattr(color,'split_'+space)(im)) for im in images]
    active=(0,1,2) if space=='rgb' else ((2,) if space=='hsv' else (0,))
    for ch in active:
        result=manual_channel([p[ch] for p in parts],mode,iterations,option,rng)
        for p,a in zip(parts,result): p[ch]=a
    native=[getattr(color,'merge_'+space)(*p) for p in parts]
    return native if space=='rgb' else [to_uint8(a*255) for a in native]


@pytest.mark.parametrize('space',['rgb','hsv','lab'])
@pytest.mark.parametrize('mode',range(1,9))
@pytest.mark.parametrize('iterations',[1,2])
def test_public_matches_explicit_composition(images,space,mode,iterations,monkeypatch):
    originals=[im.copy() for im in images]
    expected=manual(images,space,mode,iterations,1,np.random.default_rng(701))
    original=histogram.hist_match
    rng=np.random.default_rng(701)
    monkeypatch.setattr(histogram,'hist_match',lambda a,rng=None: original(a,rng=controlled))
    controlled=rng
    actual=pipeline.run(images,space,mode,iterations)
    for a,b,source,original_image in zip(actual,expected,images,originals):
        assert a.dtype==np.uint8 and a.shape==source.shape
        np.testing.assert_array_equal(a,b)
        np.testing.assert_array_equal(source,original_image)


@pytest.mark.parametrize('mode',[5,6,7,8])
def test_bug_a_combined_mode_rejects_original_input_bypass(images,mode):
    source=[im[...,0] for im in images]
    expected=manual_channel(source,mode,1,1,np.random.default_rng(701))
    original=histogram.hist_match; rng=np.random.default_rng(701)
    with patch.object(histogram,'hist_match',lambda a,rng=None:original(a,rng=controlled)):
        controlled=rng
        actual=pipeline._process_channel(source,mode,1,1)
    if mode==5: broken=spatial_frequency.sf_match(source,1)
    elif mode==6: broken=spectrum.spec_match(source,1)
    else: broken=histogram.hist_match(source,rng=np.random.default_rng(701))
    assert any(not np.array_equal(a,b) for a,b in zip(expected,broken))
    for a,b in zip(actual,expected): np.testing.assert_array_equal(a,b)


@pytest.mark.parametrize('mode',[3,5,6,7,8])
def test_bug_c_iteration_chaining_differs_from_restarting(images,mode):
    source=[im[...,0] for im in images]
    rng=np.random.default_rng(911)
    first=manual_channel(source,mode,1,1,rng)
    second=manual_channel(first,mode,1,1,rng)
    actual=pipeline._process_channel(source,mode,2,1,rng=np.random.default_rng(911))
    assert any(not np.array_equal(a,b) for a,b in zip(first,second))
    for a,b in zip(actual,second): np.testing.assert_array_equal(a,b)


@pytest.mark.parametrize('space,channels',[('RGB',3),('HSV',1),('CIELab',1)])
@pytest.mark.parametrize('mode,order',[(5,['hist','sf']),(6,['hist','spec']),(7,['sf','hist']),(8,['spec','hist'])])
def test_stage_and_iteration_receivers_on_working_scale(images,space,channels,mode,order,monkeypatch):
    events=[]
    def stub(name):
        def call(a,*args,**kwargs):
            assert all(v.dtype==np.uint8 and v.ndim==2 for v in a)
            output=[np.full_like(v,len(events)+1) for v in a]
            events.append((name,a,output))
            return output
        return call
    monkeypatch.setattr(histogram,'hist_match',stub('hist'))
    monkeypatch.setattr(spatial_frequency,'sf_match',stub('sf'))
    monkeypatch.setattr(spectrum,'spec_match',stub('spec'))
    pipeline.run(images,space,mode,iterations=2)
    assert [e[0] for e in events]==order*2*channels
    # Every stage after the first consumes the exact object returned by its
    # predecessor, including across iterations; new channels are seeded once.
    for c in range(channels):
        block=events[c*4:(c+1)*4]
        for previous,current in zip(block,block[1:]): assert current[1] is previous[2]


@pytest.mark.parametrize('space',['RGB','HSV','CIELab'])
@pytest.mark.parametrize('mode',[1,2])
def test_nonspectral_modes_ignore_rescale(images,space,mode,monkeypatch):
    original=histogram.hist_match
    monkeypatch.setattr(histogram,'hist_match',lambda a,rng=None: original(a,rng=np.random.default_rng(10)))
    outputs=[pipeline.run(images,space,mode,rescale_option=option) for option in (0,1,2)]
    for output in outputs[1:]:
        for a,b in zip(outputs[0],output): np.testing.assert_array_equal(a,b)


@pytest.mark.parametrize('mode',[3,4,5,6,7,8])
@pytest.mark.parametrize('option',[0,1,2])
def test_rescale_reaches_only_spectral_primitives(images,mode,option,monkeypatch):
    calls=[]
    def spectral(a,value): calls.append(value); return [v.copy() for v in a]
    monkeypatch.setattr(spatial_frequency,'sf_match',spectral)
    monkeypatch.setattr(spectrum,'spec_match',spectral)
    monkeypatch.setattr(histogram,'hist_match',lambda a,rng=None:[v.copy() for v in a])
    pipeline.run(images,'RGB',mode,2,option)
    assert calls==[option]*6


def test_terminal_lab_cast_occurs_after_unclipped_inverse(images,monkeypatch):
    monkeypatch.setattr(pipeline,'_process_channel',lambda a,*args:a)
    native=np.broadcast_to([-0.1,0.5,1.2],images[0].shape).copy()
    monkeypatch.setattr(color,'merge_lab',lambda *a:native.copy())
    output=pipeline.run(images,'Lab',1)
    for a in output: np.testing.assert_array_equal(a,np.broadcast_to([0,128,255],a.shape))


@pytest.mark.parametrize('kwargs',[
    {'colorspace':'xyz'},{'colorspace':None},{'mode':0},{'mode':9},{'mode':1.5},{'mode':True},
    {'iterations':0},{'iterations':-1},{'iterations':1.0},{'iterations':True},
    {'rescale_option':3},{'rescale_option':-1},{'rescale_option':False}])
def test_invalid_parameters(images,kwargs):
    options=dict(colorspace='RGB',mode=1); options.update(kwargs)
    with pytest.raises(ValueError): pipeline.run(images,**options)


@pytest.mark.parametrize('kind',['empty','single','float','shape','dimensions','zero','array','string','nested'])
def test_invalid_images(images,kind):
    bad={
        'empty':[], 'single':images[:1], 'float':[images[0].astype(float),images[1]],
        'shape':[images[0][...,0],images[1][...,0]],'dimensions':[images[0],images[1][1:]],
        'zero':[np.empty((0,4,3),dtype=np.uint8)]*2,'array':np.stack(images),
        'string':'images.png','nested':[images[0].tolist(),images[1].tolist()],
    }[kind]
    with pytest.raises((ValueError,TypeError)): pipeline.run(bad,'RGB',1)
