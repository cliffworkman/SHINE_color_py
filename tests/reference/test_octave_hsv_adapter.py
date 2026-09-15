"""Exact reference HSV arithmetic, independent boundary selection and Gate 3 replay."""
from functools import lru_cache
import hashlib
import json
from pathlib import Path
import numpy as np
import pytest
from scipy.io import loadmat
from shine_color import color
from shine_color.numeric import to_uint8

ROOT=Path(__file__).resolve().parents[2]
DEST=Path(__file__).with_name('fixtures')/'hsv_adapter'
REPORT=json.loads((DEST/'measurements.json').read_text())


@lru_cache(maxsize=8)
def fixture(name):
    path=DEST/(name+'.mat')
    assert hashlib.sha256(path.read_bytes()).hexdigest()==REPORT['fixture_sha256'][path.name]
    return loadmat(path)


@pytest.mark.parametrize('name',['forward','boundaries','captured','inverse'])
def test_native_and_terminal_inverse_exact(name):
    f=fixture(name); hsv=f['hsv'].copy()
    actual=color.hsv_to_rgb(hsv)
    assert actual.dtype==np.float64
    np.testing.assert_array_equal(actual,f['native'])
    np.testing.assert_array_equal(to_uint8(actual*255),f['terminal'])
    np.testing.assert_array_equal(hsv,f['hsv'])


@pytest.mark.parametrize('name',['forward','boundaries','captured'])
def test_forward_chroma_and_processed_value_exact(name):
    f=fixture(name); hsv=color.rgb_to_hsv(f['rgb'])
    assert hsv.dtype==np.float64
    np.testing.assert_array_equal(hsv[:,:2],f['hsv'][:,:2])
    if name=='forward':
        np.testing.assert_array_equal(hsv,f['hsv'])
        np.testing.assert_array_equal(color.v_to_working(hsv[:,2]),f['working_v'].ravel())
    hsv[:,2]=f['hsv'][:,2]
    actual=color.hsv_to_rgb(hsv)
    np.testing.assert_array_equal(actual,f['native'])
    np.testing.assert_array_equal(to_uint8(actual*255),f['terminal'])


def test_reference_only_selection_and_specification():
    manifest=json.loads((DEST/'candidates.json').read_text())
    assert hashlib.sha256((ROOT/'docs/OCTAVE_HSV_SPEC.md').read_bytes()).hexdigest()==manifest['specification_sha256']
    f=fixture('boundaries'); candidates=fixture('candidates')
    np.testing.assert_array_equal(f['rgb'],candidates['search'][f['indices'].ravel().astype(int)-1])
    np.testing.assert_array_equal(f['hsv'][:,2],f['processed'].ravel().astype(float)/255)
    offset=f['native']*255-(np.floor(f['native']*255)+.5)
    assert len(f['rgb'])==9363 and np.all(np.any(abs(offset)<=1e-10,axis=1))
    near=offset[abs(offset)<=1e-10]
    assert np.any(near<0) and np.any(near>0) and np.any(near==0)
    assert len(candidates['rgb'])==76337 and len(candidates['inverse'])==11832
    assert len(candidates['search'])==131072


def test_all_original_boundary_occurrences_are_preserved():
    f=fixture('captured'); manifest=json.loads((DEST/'candidates.json').read_text())
    records=manifest['captured_identity']
    assert len(records)==len(f['hsv'])==458
    for i,record in enumerate(records):
        np.testing.assert_array_equal(f['rgb'][i],record['original_rgb'])
        assert f['terminal'][i,record['index'][2]]==record['octave_terminal']


def test_inverse_wrap_and_no_clipping():
    f=fixture('inverse'); a=color.hsv_to_rgb(f['hsv'])
    assert np.any(a<0) and np.any(a>1)
    np.testing.assert_array_equal(color.hsv_to_rgb([[0,.5,.5]]),color.hsv_to_rgb([[1,.5,.5]]))


@pytest.mark.parametrize('name',['palette','structured','gray_ramp','dark','random','boundaries'])
def test_gate3_hsv_revalidation_exact_native_and_terminal(name):
    f=loadmat(DEST.parent/'color_adapter'/(name+'.mat'))
    hsv=color.rgb_to_hsv(f['rgb'])
    np.testing.assert_array_equal(hsv,f['hsv'])
    np.testing.assert_array_equal(color.v_to_working(hsv[...,2]),f['v_work'])
    for variant in ('native','work','processed'):
        key='hsv' if variant=='native' else 'hsv_'+variant
        rgb='hsv_roundtrip' if variant=='native' else key+'_rgb'
        terminal='hsv_roundtrip_u8' if variant=='native' else key+'_u8'
        source=hsv.copy(); source[...,2]=f[key][...,2]
        a=color.hsv_to_rgb(source)
        np.testing.assert_array_equal(a,f[rgb])
        np.testing.assert_array_equal(to_uint8(a*255),f[terminal])
