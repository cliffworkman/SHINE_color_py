"""Generate predetermined candidates; never inspect matching outputs here."""
from pathlib import Path
import hashlib
import json
import numpy as np
from PIL import Image
from scipy.ndimage import gaussian_filter
from scipy.io import savemat

ROOT=Path(__file__).resolve().parent
DATA=ROOT/'data'


def cell(items):
    out=np.empty((1,len(items)),dtype=object)
    for k,item in enumerate(items): out[0,k]=item
    return out


def build():
    DATA.mkdir(exist_ok=True)
    manifest=dict(criteria_sha256=hashlib.sha256((ROOT/'CRITERIA.md').read_bytes()).hexdigest(),groups=[])
    shapes=[(31,31),(31,48),(48,31),(32,48),(64,64),(63,79),(128,128)]
    for index,shape in enumerate(shapes):
        rng=np.random.Generator(np.random.PCG64(20260914+index))
        y,x=np.indices(shape)
        uniform=rng.integers(0,256,shape,dtype=np.uint8)
        pattern=120+45*np.sin(x*.23+y*.09)+32*np.cos(y*.31)+18*np.sin(x*y*.011)
        pattern=np.clip(np.floor(pattern+.5)+rng.integers(-3,4,shape),0,255).astype(np.uint8)
        smooth=gaussian_filter(rng.normal(size=shape),2.3)+.4*gaussian_filter(rng.normal(size=shape),.7)
        texture=np.clip(np.floor(125+35*smooth/smooth.std()+rng.normal(0,2,shape)+.5),0,255).astype(np.uint8)
        name=f'synthetic_{shape[0]}x{shape[1]}'
        inputs=[uniform,pattern,texture]
        savemat(DATA/f'{name}_inputs.mat',dict(inputs=cell(inputs)),do_compression=True)
        for k,a in enumerate(inputs): Image.fromarray(a).save(DATA/f'{name}_{k+1}.png')
        manifest['groups'].append(dict(name=name,kind='synthetic_candidate',shape=shape,seed=20260914+index))
    source=ROOT.parents[1].parent/'SHINE_color_fork/toolbox/SHINE_color_INPUT/samples'
    provenance=[]; arrays=[]
    for name in ['cat1.jpg','cat2.jpg','cat3.jpg']:
        path=source/name
        with Image.open(path) as im:
            assert im.mode=='RGB' and im.size==(1200,1200)
            arrays.append(np.array(im)[:,:,1])
        provenance.append(dict(path=str(path.resolve()),sha256=hashlib.sha256(path.read_bytes()).hexdigest()))
    for stride in (1,4):
        name=f'cats_green_stride{stride}'
        inputs=[a[::stride,::stride].copy() for a in arrays]
        savemat(DATA/f'{name}_inputs.mat',dict(inputs=cell(inputs)),do_compression=True)
        manifest['groups'].append(dict(name=name,kind='natural_sample',shape=inputs[0].shape,
            channel='green',stride=stride,sources=provenance))
    manifest['input_sha256']={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(DATA.glob('*_inputs.mat'))}
    (ROOT/'corpus_manifest.json').write_text(json.dumps(manifest,indent=2)+'\n', newline='\n')
    print([(g['name'],g['shape']) for g in manifest['groups']])


if __name__=='__main__': build()
