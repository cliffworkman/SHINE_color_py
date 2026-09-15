"""Reference-independent expanded inputs. Run before implementing the adapter."""
import hashlib
import json
from pathlib import Path
import numpy as np
from scipy.io import savemat

ROOT = Path(__file__).resolve().parents[1]
DEST = ROOT/'tests/reference/fixtures/color_adapter'


def build():
    DEST.mkdir(exist_ok=True)
    dark = np.indices((33,33,33)).reshape(3,-1).T.astype(np.uint8)
    random = np.random.Generator(np.random.PCG64(2026091401)).integers(0,256,(65536,3),dtype=np.uint8)
    search = np.random.Generator(np.random.PCG64(2026091402)).integers(0,256,(262144,3),dtype=np.uint8)
    grays = np.repeat(np.arange(256,dtype=np.uint8)[:,None],3,axis=1)
    search = np.concatenate([search,dark,grays])
    l,a,b = np.meshgrid([-5,0,1,8,50,100,105],[-128,-80,-1,0,1,80,128],[-128,-80,-1,0,1,80,128],indexing='ij')
    gamut_grid = np.stack([l,a,b],axis=-1).reshape(-1,3).astype(float)
    neutral_l = np.array([v+d for v in (0,8,100) for d in (-1e-9,0,1e-9)])
    neutral_lab = np.column_stack([neutral_l,np.zeros((9,2))])
    savemat(DEST/'candidates.mat',dict(dark=dark,random=random,search=search,
        gamut_grid=gamut_grid,neutral_lab=neutral_lab),do_compression=True)
    manifest = dict(generator='reference/build_lab_corpus.py',version=1,
        dark_pixels=len(dark),random_pixels=len(random),search_pixels=len(search),
        random_seed=2026091401,search_seed=2026091402,
        specification_sha256=hashlib.sha256((ROOT/'docs/OCTAVE_LAB_SPEC.md').read_bytes()).hexdigest(),
        candidates_sha256=hashlib.sha256((DEST/'candidates.mat').read_bytes()).hexdigest(),
        generator_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest())
    (DEST/'candidates.json').write_text(json.dumps(manifest,indent=2)+'\n',newline='\n')
    print(manifest)


if __name__ == '__main__':
    build()
