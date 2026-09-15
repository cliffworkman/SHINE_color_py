"""Stage-separated HSV comparison; old references and measurements stay frozen."""
import argparse
import hashlib
import json
import platform
from pathlib import Path
import numpy as np
import scipy
from scipy.io import loadmat, savemat
from shine_color import color
from shine_color.numeric import to_uint8

ROOT=Path(__file__).resolve().parents[1]
DEST=ROOT/'tests/reference/fixtures/hsv_adapter'
GROUPS=('forward','boundaries','captured','inverse')


def difference(a,b):
    d=np.abs(a.astype(float)-b.astype(float))
    return dict(max_abs=float(d.max()),per_channel=d.reshape(-1,3).max(axis=0).tolist(),unequal=int(np.count_nonzero(d)))


def prepare():
    # Diagnostic-only dependency: preserve the displaced implementation's inputs.
    from skimage.color import rgb2hsv
    import skimage
    values={}
    for name in GROUPS[:-1]:
        f=loadmat(DEST/(name+'.mat'))
        hsv=rgb2hsv(f['rgb']); hsv[:,2]=f['hsv'][:,2]
        values[name]=hsv
    savemat(DEST/'cross_inputs.mat',values,do_compression=True)
    (DEST/'cross_environment.json').write_text(json.dumps(dict(skimage=skimage.__version__,numpy=np.__version__),indent=2)+'\n',newline='\n')


def measure():
    from skimage.color import rgb2hsv,hsv2rgb
    cross=loadmat(DEST/'cross_reference.mat'); inputs=loadmat(DEST/'cross_inputs.mat')
    groups={}
    for name in GROUPS:
        f=loadmat(DEST/(name+'.mat')); checks={}
        for label,inverse in [('skimage',hsv2rgb),('adapter',color.hsv_to_rgb)]:
            a=inverse(f['hsv'])
            checks[label+'_same_reference_hsv_native']=difference(a,f['native'])
            checks[label+'_same_reference_hsv_terminal']=difference(to_uint8(a*255),f['terminal'])
            if 'rgb' in f:
                forward=(rgb2hsv if label=='skimage' else color.rgb_to_hsv)(f['rgb'])
                hs=forward.copy(); hs[:,2]=f['hsv'][:,2]
                checks[label+'_forward_hs']=difference(hs,f['hsv'])
                if name=='forward':
                    checks[label+'_forward']=difference(forward,f['hsv'])
                    checks[label+'_working_v_unequal']=int(np.count_nonzero(to_uint8(forward[:,2]*255)!=f['working_v'].ravel()))
                a=inverse(hs)
                checks[label+'_end_to_end_native']=difference(a,f['native'])
                checks[label+'_end_to_end_terminal']=difference(to_uint8(a*255),f['terminal'])
        if name!='inverse':
            native=cross[name]; old=hsv2rgb(inputs[name])
            checks['skimage_hs_octave_inverse_vs_reference_native']=difference(native,f['native'])
            checks['skimage_hs_octave_inverse_vs_reference_terminal']=difference(to_uint8(native*255),f['terminal'])
            checks['same_skimage_hs_two_inverses_native']=difference(old,native)
            checks['same_skimage_hs_two_inverses_terminal']=difference(to_uint8(old*255),to_uint8(native*255))
        groups[name]=dict(count=len(f['hsv']),checks=checks)
    gate3={}; count=0
    for name in ('palette','structured','gray_ramp','dark','random','boundaries'):
        f=loadmat(ROOT/'tests/reference/fixtures/color_adapter'/(name+'.mat'))
        hsv=color.rgb_to_hsv(f['rgb']); count+=hsv[...,2].size
        checks=dict(forward=difference(hsv,f['hsv']),working_v_unequal=int(np.count_nonzero(color.v_to_working(hsv[...,2])!=f['v_work'])))
        for variant in ('native','work','processed'):
            key='hsv' if variant=='native' else 'hsv_'+variant
            out='hsv_roundtrip' if variant=='native' else key+'_rgb'
            terminal='hsv_roundtrip_u8' if variant=='native' else key+'_u8'
            for label,source in [('isolated',f[key]),('end_to_end',hsv.copy())]:
                if label=='end_to_end': source[...,2]=f[key][...,2]
                actual=color.hsv_to_rgb(source)
                checks[label+'_'+variant+'_native']=difference(actual,f[out])
                checks[label+'_'+variant+'_terminal']=difference(to_uint8(actual*255),f[terminal])
        gate3[name]=checks
    report=dict(environment=dict(python=platform.python_version(),numpy=np.__version__,scipy=scipy.__version__,platform=platform.platform()),
        groups=groups,gate3_count=count,gate3=gate3,
        fixture_sha256={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in DEST.glob('*.mat')})
    (DEST/'measurements.json').write_text(json.dumps(report,indent=2)+'\n',newline='\n')
    for name,g in groups.items():
        print(name,g['count'],{k:v for k,v in g['checks'].items() if 'terminal' in k or k.endswith('_forward')})
    print('Gate3',count,'max',max(c['forward']['max_abs'] for c in gate3.values()))


if __name__=='__main__':
    parser=argparse.ArgumentParser(); parser.add_argument('--prepare',action='store_true')
    prepare() if parser.parse_args().prepare else measure()
