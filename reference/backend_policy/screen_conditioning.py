"""Screen only source spectra; no final output files are read."""
from pathlib import Path
import hashlib
import json
import numpy as np
from scipy.io import loadmat
from shine_color.spatial_frequency import _radial_bin_grid
from reference.measure_primitives import cells
ROOT=Path(__file__).resolve().parent
DATA=ROOT/'data'

CACHE=ROOT.parent/'.cache/backend_policy'


def characterize(amplitude):
    scale=max(1.,float(amplitude.max()))
    threshold=1e-10*scale
    r=_radial_bin_grid(*amplitude.shape)
    energy=np.bincount(r.ravel(order='F'),weights=amplitude.ravel(order='F'))
    count=np.bincount(r.ravel())
    retained=(count>0)&(np.arange(len(count))<=np.floor(max(amplitude.shape)/2))
    return dict(min_magnitude=float(amplitude.min()),max_magnitude=float(amplitude.max()),
        exact_zero=int((amplitude==0).sum()),below={str(t):int((amplitude<t).sum()) for t in [1e-15,1e-14,1e-13,1e-12]},
        scaled_threshold=threshold,min_retained_denominator=float(energy[retained].min()),
        near_zero_coefficients=int((amplitude<=threshold).sum()),
        near_zero_retained_bins=int((energy[retained]<=threshold).sum()),
        retained_bins=[dict(bin=int(i),count=int(count[i]),denominator=float(energy[i])) for i in np.flatnonzero(retained)],
        passes=bool(amplitude.min()>threshold and energy[retained].min()>threshold))


def screen():
    manifest=json.loads((ROOT/'corpus_manifest.json').read_text())
    assert hashlib.sha256((ROOT/'CRITERIA.md').read_bytes()).hexdigest()==manifest['criteria_sha256']
    records=[]
    for group in manifest['groups']:
        path=CACHE/(group['name']+'_spectra.mat')
        f=loadmat(path)
        sources=[characterize(a) for a in cells(f['amplitudes'])]
        records.append(dict(name=group['name'],kind=group['kind'],sources=sources,
            passes=all(s['passes'] for s in sources),spectra_sha256=hashlib.sha256(path.read_bytes()).hexdigest()))
    (ROOT/'conditioning.json').write_text(json.dumps(dict(criteria_sha256=manifest['criteria_sha256'],groups=records),separators=(',',':'))+'\n', newline='\n')
    print([(g['name'],g['passes'],min(s['min_magnitude'] for s in g['sources'])) for g in records])


if __name__=='__main__': screen()
