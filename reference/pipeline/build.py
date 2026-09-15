"""Predetermined pipeline inputs; no output-based selection."""
from pathlib import Path
import hashlib
import json
import numpy as np
from scipy.ndimage import gaussian_filter
from scipy.io import savemat

ROOT=Path(__file__).resolve().parents[2]
DEST=ROOT/'tests/reference/fixtures/pipeline'


def build():
    DEST.mkdir(exist_ok=True)
    groups=[]
    for k,shape in enumerate([(17,19),(17,20),(20,17),(20,20)]):
        rng=np.random.Generator(np.random.PCG64(2026091404+k))
        y,x=np.indices(shape)
        noise=rng.integers(0,256,(*shape,3),dtype=np.uint8)
        texture=[]; pattern=[]
        for ch in range(3):
            smooth=gaussian_filter(rng.normal(size=shape),1.1)
            texture.append(np.clip(np.floor(120+38*smooth/smooth.std()+rng.normal(0,4,shape)+.5),0,255))
            z=125+51*np.sin(x*(.31+ch*.07)+y*.17)+33*np.cos(y*(.23+ch*.13)+ch)
            pattern.append(np.clip(np.floor(z+.5)+rng.integers(-5,6,shape),0,255))
        images=[noise,np.stack(texture,-1).astype(np.uint8),np.stack(pattern,-1).astype(np.uint8)]
        inputs=np.empty((1,3),dtype=object)
        for i,image in enumerate(images): inputs[0,i]=image
        name=f'rgb_{shape[0]}x{shape[1]}'
        path=DEST/(name+'_inputs.mat')
        savemat(path,dict(inputs=inputs),do_compression=True)
        groups.append(dict(name=name,shape=shape,seed=2026091404+k,input_sha256=hashlib.sha256(path.read_bytes()).hexdigest()))
    manifest=dict(groups=groups,criteria_sha256=hashlib.sha256((ROOT/'reference/pipeline/CRITERIA.md').read_bytes()).hexdigest(),generator='reference/pipeline/build.py',version=1)
    (DEST/'inputs.json').write_text(json.dumps(manifest,indent=2)+'\n',newline='\n')


if __name__=='__main__': build()
