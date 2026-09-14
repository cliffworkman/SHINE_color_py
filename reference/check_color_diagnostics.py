"""Positive checks of Gate 3 evidence; not acceptance tests for a color layer."""
import hashlib
import inspect
import json
from pathlib import Path

import numpy as np
from skimage import color
from skimage.color import colorconv
from shine_color.numeric import to_uint8
from .compare_color import FIXTURES, records, candidate, difference


def check():
    report = json.loads((FIXTURES/'comparison.json').read_text())
    manifest = json.loads((FIXTURES/'inputs.json').read_text())
    assert hashlib.sha256((FIXTURES/'inputs.mat').read_bytes()).hexdigest() == manifest['input_sha256'] == report['inputs_sha256']
    assert hashlib.sha256((FIXTURES/'octave.mat').read_bytes()).hexdigest() == report['octave_sha256']
    all_records = records()
    assert [r['rgb'].shape[:2] for r in all_records] == [(8,8),(7,9),(1,256)]
    findings = []; clipping = []
    for group, ref in zip(manifest['names'], all_records):
        actual = candidate(ref)
        np.testing.assert_array_equal(actual['v_work'], ref['v_work'])
        np.testing.assert_array_equal(actual['v_native'], ref['v_native'])
        for space in ('hsv', 'lab'):
            np.testing.assert_array_equal(to_uint8(actual[space+'_roundtrip']*255), ref['rgb'])
            np.testing.assert_array_equal(to_uint8(ref[space+'_roundtrip']*255), ref['rgb'])
        for key in ('hsv_roundtrip', 'hsv_work_rgb', 'hsv_processed_rgb'):
            np.testing.assert_array_equal(to_uint8(actual[key]*255), to_uint8(ref[key]*255))
        for variant in ('work', 'processed'):
            np.testing.assert_array_equal(actual[f'hsv_{variant}_native'][...,:2], actual['hsv'][...,:2])
            np.testing.assert_array_equal(actual[f'lab_{variant}_native'][...,1:], actual['lab'][...,1:])
        for y, x in np.argwhere(actual['l_work'] != ref['l_work']):
            rgb = ref['rgb'][y,x]
            assert rgb.tolist() == [0,1,0]
            # Scalar causal probe only, not a replacement color converter.
            # Same Y (identical forward RGB->XYZ matrix), different low-light slope.
            luminance_y = float(color.rgb2xyz(rgb.reshape(1,1,3))[0,0,1])
            exact_slope = (29/3)**3/116
            predicted_octave = (116*(exact_slope*luminance_y+16/116)-16)*2.55
            predicted_skimage = (116*(7.787*luminance_y+16/116)-16)*2.55
            octave_scaled = float(ref['lab'][y,x,0]*2.55)
            python_scaled = float(actual['lab'][y,x,0]*2.55)
            assert predicted_octave > .5 > predicted_skimage
            assert octave_scaled > .5 > python_scaled
            assert to_uint8(octave_scaled) == ref['l_work'][y,x] == 1
            assert to_uint8(python_scaled) == actual['l_work'][y,x] == 0
            findings.append(dict(group=group, row=int(y), column=int(x), rgb=rgb.tolist(),
                octave_lab=ref['lab'][y,x].tolist(), python_lab=actual['lab'][y,x].tolist(),
                octave_scaled=octave_scaled, python_scaled=python_scaled,
                scalar_predicted_octave_scaled=predicted_octave, scalar_predicted_python_scaled=predicted_skimage,
                octave_work=int(ref['l_work'][y,x]), python_work=int(actual['l_work'][y,x]),
                octave_reconstructed_rgb_uint8=to_uint8(ref['lab_work_rgb'][y,x]*255).tolist(),
                python_reconstructed_rgb_uint8=to_uint8(actual['lab_work_rgb'][y,x]*255).tolist()))
        out = ref['lab_processed_rgb']
        clipped = np.clip(out,0,1)
        clipping.append(dict(group=group, octave_min=float(out.min()), octave_max=float(out.max()),
            octave_outside_unit_interval=int(((out<0)|(out>1)).sum()),
            python_vs_clipped_octave=difference(actual['lab_processed_rgb'],clipped),
            uint8=difference(to_uint8(actual['lab_processed_rgb']*255),to_uint8(out*255))))
    assert len(findings) == 1
    assert report['summary']['l_work']['unequal'] == 1
    assert report['summary']['l_work']['distribution'] == {'1':1}
    assert all(r['uint8']['unequal'] == 0 for r in clipping)
    result = dict(status='diagnostic assertions passed; Gate 3 adoption blocked',
        working_channel_mismatches=findings, processed_lab_clipping=clipping,
        conventions=dict(octave_lab_slope=(29/3)**3/116, skimage_lab_slope=7.787,
            octave_lab_threshold=(6/29)**3, skimage_lab_threshold=.008856,
            rgb_xyz_matrix=colorconv.xyz_from_rgb.tolist(),
            python_xyz_rgb_matrix=colorconv.rgb_from_xyz.tolist(),
            octave_xyz_rgb_matrix=[[3.240479,-1.537150,-.498535],[-.969256,1.875992,.041556],[.055648,-.204043,1.057311]],
            skimage_source_sha256=hashlib.sha256(Path(inspect.getfile(colorconv)).read_bytes()).hexdigest()),
        notes='Scalar slope probe explains the cast-boundary failure. No converter, numerical tolerance, or acceptance policy is introduced.')
    (FIXTURES/'diagnosis.json').write_text(json.dumps(result,indent=2)+'\n',newline='\n')
    print(json.dumps(result,indent=2))


if __name__ == '__main__':
    check()
