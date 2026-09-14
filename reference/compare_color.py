"""Measure the candidate against Octave without setting test tolerances."""
import hashlib
import json
import platform
from pathlib import Path
import numpy as np
import scipy
from scipy.io import loadmat
import skimage
from skimage import color
from shine_color.numeric import to_uint8

FIXTURES = Path(__file__).resolve().parents[1]/'tests/reference/fixtures/color'


def records():
    result = []
    for item in loadmat(FIXTURES/'octave.mat', struct_as_record=False)['records'].ravel():
        record = item[0,0]
        result.append({key: getattr(record, key) for key in record._fieldnames})
    return result


def candidate(ref):
    hsv = color.rgb2hsv(ref['rgb'])
    lab = color.rgb2lab(ref['rgb'], illuminant='D65', observer='2')
    v_work = to_uint8(hsv[...,2]*255)
    l_work = to_uint8(lab[...,0]*2.55)
    result = dict(hsv=hsv, lab=lab, v_work=v_work, l_work=l_work,
        v_native=v_work.astype(float)/255, l_native=l_work.astype(float)/2.55,
        hsv_roundtrip=color.hsv2rgb(hsv), lab_roundtrip=color.lab2rgb(lab),
        hsv_inverse_reference=color.hsv2rgb(ref['hsv']),
        lab_inverse_reference=color.lab2rgb(ref['lab']))
    for space, native, channel, scale, work in [('hsv',hsv,2,255,v_work), ('lab',lab,0,2.55,l_work)]:
        for variant, working in [('work',work), ('processed',np.maximum(work,128))]:
            merged = native.copy()
            merged[...,channel] = working.astype(float)/scale
            result[f'{space}_{variant}_native'] = merged
            result[f'{space}_{variant}_rgb'] = getattr(color, space+'2rgb')(merged)
    return result


def difference(a, b):
    assert a.shape == b.shape
    d = np.abs(a.astype(float)-b.astype(float))
    edges = [0,1e-15,1e-12,1e-9,1e-6,1e-3,1,float('inf')]
    distribution = {'exact': int((d==0).sum())}
    for low,high in zip(edges[:-1], edges[1:]):
        distribution[f'({low},{high}]'] = int(((d>low)&(d<=high)).sum())
    if a.dtype == b.dtype == np.uint8:
        vals,counts = np.unique(d[d!=0], return_counts=True)
        distribution = {str(int(v)): int(c) for v,c in zip(vals,counts)}
    return dict(max_abs=float(d.max()), mean_abs=float(d.mean()), unequal=int((d!=0).sum()),
        elements=d.size, distribution=distribution,
        per_channel=[dict(max_abs=float(d[...,k].max()),mean_abs=float(d[...,k].mean()))
                     for k in range(3)] if d.ndim==3 else None)


def run():
    manifest = json.loads((FIXTURES/'inputs.json').read_text())
    groups = []; all_pairs = {}
    for name,ref in zip(manifest['names'], records()):
        actual = candidate(ref)
        expected = {**ref, 'hsv_inverse_reference':ref['hsv_roundtrip'], 'lab_inverse_reference':ref['lab_roundtrip']}
        for space in ('hsv','lab'):
            for variant in ('roundtrip','work_rgb','processed_rgb','inverse_reference'):
                key=f'{space}_{variant}'
                actual[key+'_uint8'] = to_uint8(actual[key]*255)
                expected[key+'_uint8'] = to_uint8(expected[key]*255)
            actual[space+'_roundtrip_to_source_uint8'] = to_uint8(actual[space+'_roundtrip']*255)
            expected[space+'_roundtrip_to_source_uint8'] = ref['rgb']
        groups.append(dict(name=name, comparisons={key:difference(a,expected[key]) for key,a in actual.items()}))
        for key,a in actual.items():
            all_pairs.setdefault(key, []).append((a.reshape(-1,3) if a.ndim==3 else a.ravel(),
                                                 expected[key].reshape(-1,3) if a.ndim==3 else expected[key].ravel()))
    summary = {}
    for key,pairs in all_pairs.items():
        a,b = (np.concatenate([p[i] for p in pairs]) for i in (0,1))
        if a.ndim==2: a,b=a[None,...],b[None,...]
        summary[key] = difference(a,b)
    report = dict(environment=dict(python=platform.python_version(), numpy=np.__version__,scipy=scipy.__version__,
        skimage=skimage.__version__,platform=platform.platform()),
        inputs_sha256=hashlib.sha256((FIXTURES/'inputs.mat').read_bytes()).hexdigest(),
        octave_sha256=hashlib.sha256((FIXTURES/'octave.mat').read_bytes()).hexdigest(),
        groups=groups, summary=summary)
    (FIXTURES/'comparison.json').write_text(json.dumps(report,indent=2)+'\n',newline='\n')
    for key,s in summary.items():
        print(key,s['max_abs'],s['mean_abs'],s['unequal'],flush=True)


if __name__ == '__main__':
    run()
