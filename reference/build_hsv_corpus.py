"""Freeze independent HSV candidates before any adapter comparison."""
import hashlib
import json
from pathlib import Path
import numpy as np
from scipy.io import savemat
from reference.pipeline.measure import DEST as PIPE, as_list, load_group, SPACES

ROOT=Path(__file__).resolve().parents[1]
DEST=ROOT/'tests/reference/fixtures/hsv_adapter'


def build():
    DEST.mkdir(exist_ok=True)
    random=np.random.default_rng(2026091408).integers(0,256,(65536,3),dtype=np.uint8)
    gray=np.repeat(np.arange(256,dtype=np.uint8)[:,None],3,axis=1)
    dark=np.indices((16,16,16)).reshape(3,-1).T.astype(np.uint8)
    levels=np.r_[np.arange(0,256,16),255]
    grid=np.stack(np.meshgrid(levels,levels,levels,indexing='ij'),axis=-1).reshape(-1,3).astype(np.uint8)
    near=[]
    for channel in range(3):
        for step in (-1,1):
            a=gray.astype(int); a[:,channel]=np.clip(a[:,channel]+step,0,255)
            near.append(a.astype(np.uint8))
    rgb=np.concatenate([random,gray,dark,grid,*near])
    search=np.random.default_rng(2026091409).integers(0,256,(131072,3),dtype=np.uint8)
    h=(np.arange(-3,10)[:,None]/6+np.array([-1e-12,-np.finfo(float).eps,0,np.finfo(float).eps,1e-12])).ravel()
    s=[0,1e-12,1/255,.5,254/255,1,-.1,1.1]; v=[0,1/255,.5,254/255,1,-.1,1.1]
    inverse=np.stack(np.meshgrid(h,s,v,indexing='ij'),axis=-1).reshape(-1,3)
    inverse=np.concatenate([inverse,np.random.default_rng(2026091410).random((8192,3))])
    diagnosis=json.loads((PIPE/'diagnosis.json').read_text()); captured=[]; processed=[]; cache={}
    for p in diagnosis['hsv_pixels']:
        name=p['group']
        if name not in cache: cache[name]=load_group(name)
        r=next(r for r in as_list(cache[name]['runs']) if SPACES[r['colorspace']]=='HSV' and all(r[k]==p[k] for k in ('mode','iterations','rescale_option')))
        captured.append(p['original_rgb'])
        processed.append(r['working'][2,p['source']-1][tuple(p['index'][:2])])
    savemat(DEST/'candidates.mat',dict(rgb=rgb,search=search,inverse=inverse,
        processed_values=np.array([0,1,2,31,64,127,128,254,255],dtype=np.uint8),
        captured_rgb=np.array(captured,dtype=np.uint8),captured_v=np.array(processed,dtype=np.uint8)),do_compression=True)
    manifest=dict(forward_count=len(rgb),search_count=len(search),inverse_count=len(inverse),captured_count=len(captured),
        selection_threshold=1e-10,seeds=[2026091408,2026091409,2026091410],
        specification_sha256=hashlib.sha256((ROOT/'docs/OCTAVE_HSV_SPEC.md').read_bytes()).hexdigest(),
        candidates_sha256=hashlib.sha256((DEST/'candidates.mat').read_bytes()).hexdigest(),
        generator_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        prior_diagnosis_sha256=hashlib.sha256((PIPE/'diagnosis.json').read_bytes()).hexdigest(),captured_identity=diagnosis['hsv_pixels'])
    (DEST/'candidates.json').write_text(json.dumps(manifest,indent=2)+'\n',newline='\n')
    print({k:v for k,v in manifest.items() if k!='captured_identity'})


if __name__=='__main__': build()
