"""Compare the adapter to frozen expanded references; never set acceptance bounds."""
import hashlib
import importlib.metadata
import json
import platform
from pathlib import Path
import numpy as np
from scipy.io import loadmat
from skimage import color
from shine_color._lab_octave import rgb_to_lab_octave, lab_to_rgb_octave
from shine_color.numeric import to_uint8
from reference.compare_color import difference

ROOT = Path(__file__).resolve().parents[1]
DEST = ROOT/'tests/reference/fixtures/color_adapter'
GROUPS = ('palette','structured','gray_ramp','dark','random','boundaries')


def calculations(f):
    lab = rgb_to_lab_octave(f['rgb'])
    hsv = color.rgb2hsv(f['rgb'])
    actual = dict(lab=lab,hsv=hsv,l_work=to_uint8(lab[...,0]*2.55),v_work=to_uint8(hsv[...,2]*255))
    for space, native, index, scale, inverse in (
        ('lab',lab,0,2.55,lab_to_rgb_octave),('hsv',hsv,2,255,color.hsv2rgb)):
        actual[space+'_roundtrip'] = inverse(native)
        actual[space+'_roundtrip_u8'] = to_uint8(actual[space+'_roundtrip']*255)
        for variant in ('work','processed'):
            # Isolated inverse and end-to-end conversion are measured separately.
            actual[space+'_'+variant+'_inverse'] = inverse(f[space+'_'+variant])
            actual[space+'_'+variant+'_inverse_u8'] = to_uint8(actual[space+'_'+variant+'_inverse']*255)
            merged = native.copy()
            working = actual['l_work' if space=='lab' else 'v_work']
            if variant == 'processed': working = np.maximum(working,128)
            merged[...,index] = working.astype(float)/scale
            actual[space+'_'+variant] = merged
            actual[space+'_'+variant+'_rgb'] = inverse(merged)
            actual[space+'_'+variant+'_u8'] = to_uint8(actual[space+'_'+variant+'_rgb']*255)
        actual[space+'_native_inverse'] = inverse(f[space])
        actual[space+'_native_inverse_u8'] = to_uint8(actual[space+'_native_inverse']*255)
    return actual


def expected_for(f, key):
    for variant in ('native','work','processed'):
        if '_'+variant+'_inverse' in key:
            key = key.replace('_'+variant+'_inverse', '_roundtrip' if variant=='native' else '_'+variant+'_rgb')
            if key.endswith('_rgb_u8'): key=key.replace('_rgb_u8','_u8')
    return f[key]


def measure():
    groups = []; combined = {}; mismatches=[]
    for name in GROUPS:
        f=loadmat(DEST/(name+'.mat'))
        actual=calculations(f)
        checks={key:difference(value,expected_for(f,key)) for key,value in actual.items()}
        for index in np.argwhere(actual['l_work']!=f['l_work']):
            loc=tuple(index)
            mismatches.append(dict(group=name,index=index.tolist(),rgb=f['rgb'][loc].tolist(),
                octave_l=float(f['lab'][loc][0]),python_l=float(actual['lab'][loc][0]),
                octave_work=int(f['l_work'][loc]),python_work=int(actual['l_work'][loc])))
        groups.append(dict(name=name,pixels=int(f['l_work'].size),checks=checks))
        for key,value in actual.items():
            expected=expected_for(f,key)
            a=value.reshape(-1,3) if value.ndim==3 else value.ravel()
            b=expected.reshape(-1,3) if expected.ndim==3 else expected.ravel()
            combined.setdefault(key,[]).append((a,b))
        print(name,'working L unequal',checks['l_work']['unequal'],'working reconstruction',checks['lab_work_u8']['unequal'],flush=True)
    summary={}
    for key,pairs in combined.items():
        a,b=(np.concatenate([p[i] for p in pairs]) for i in (0,1))
        if a.ndim==2: a,b=a[None,...],b[None,...]
        summary[key]=difference(a,b)
    inverse=loadmat(DEST/'inverse.mat')
    a=lab_to_rgb_octave(inverse['lab']); b=inverse['rgb']
    gamut=dict(native=difference(a[None,...],b[None,...]), terminal=difference(to_uint8(a*255)[None,...],inverse['rgb_u8'][None,...]),
        reference_min=float(b.min()),reference_max=float(b.max()),python_min=float(a.min()),python_max=float(a.max()),
        below_zero=int((b<0).sum()),above_one=int((b>1).sum()),
        outside_classification_disagreements=int(((a<0)!=(b<0)).sum()+((a>1)!=(b>1)).sum()))
    report=dict(environment=dict(python=platform.python_version(),numpy=np.__version__,platform=platform.platform(),
        scikit_image=importlib.metadata.version('scikit-image'),skimage_requires_python=importlib.metadata.metadata('scikit-image')['Requires-Python']),
        fixture_sha256={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in DEST.glob('*.mat')},
        groups=groups,summary=summary,working_l_mismatches=mismatches,gamut=gamut)
    (DEST/'measurements.json').write_text(json.dumps(report,indent=2)+'\n',newline='\n')
    for key in ('lab','l_work','lab_roundtrip','lab_work_rgb','lab_work_u8','lab_processed_u8','hsv','v_work','hsv_work_u8','hsv_processed_u8'):
        print(key,summary[key],flush=True)
    print('GAMUT',gamut,flush=True)


if __name__ == '__main__':
    measure()
