"""Read-only top-level inventory and deterministic PRE-normalization sampling."""
from collections import Counter, defaultdict
from io import BytesIO
import hashlib
from pathlib import Path
import numpy as np
from PIL import Image
from shine_color import io
from .metrics import channel_metrics, spectral_group

IMAGE_SUFFIXES={'.png','.jpg','.jpeg','.tif','.tiff','.gif','.bmp','.webp'}
FEATURES=('v_mean','v_sample_sd','v_entropy_bits','v_low_power_fraction')


def inventory(directory, conditions=None):
    root=Path(directory).resolve(strict=True)
    if not root.is_dir(): raise ValueError('source must be an explicit image directory')
    rows=[]
    for path in sorted(root.iterdir(),key=lambda p:(p.name.casefold(),p.name)):
        if not path.is_file() or path.is_symlink() or path.suffix.lower() not in IMAGE_SUFFIXES: continue
        data=path.read_bytes()
        row=dict(relative_path=path.name,file_sha256=hashlib.sha256(data).hexdigest(),
            size_bytes=len(data),condition=(conditions or {}).get(path.name),valid=False,error=None)
        try:
            with Image.open(BytesIO(data)) as im:
                row.update(stored_dimensions=list(im.size),source_mode=im.mode,format=im.format,
                    frames=getattr(im,'n_frames',1),exif_orientation=im.getexif().get(274,1),
                    bit_depth=data[24] if data.startswith(b'\x89PNG\r\n\x1a\n') else getattr(im,'bits',None))
            rgb,metadata=io._read_rgb(path)
            if metadata['file_sha256']!=row['file_sha256']: raise ValueError('file changed during inventory')
            v=rgb.max(axis=2); stats=channel_metrics(v)
            # Use a bounded, deterministic thumbnail only for the pre-selection
            # descriptor. This is never passed to SHINE and never changes a
            # source or processing array.
            step=max(1, int(np.ceil(max(v.shape) / 128)))
            descriptor_v=v[::step, ::step]
            spectrum = spectral_group([descriptor_v])[0]
            row.update(valid=True,dimensions=metadata['dimensions'],pixel_sha256=metadata['pixel_sha256'],
                alpha_policy='accepted_without_alpha',v_mean=stats['mean'],v_sample_sd=stats['sample_sd'],
                v_entropy_bits=stats['entropy_bits'],v_low_power_fraction=(
                    spectrum['images'][0]['low_power_fraction']),
                below_128_pixel_review_size=min(rgb.shape[:2])<128)
        except (OSError,ValueError,TypeError) as error: row['error']=str(error)
        rows.append(row)
    duplicates={}
    for field in ('file_sha256','pixel_sha256'):
        groups=defaultdict(list)
        for r in rows:
            if r.get(field): groups[r[field]].append(r['relative_path'])
        duplicates[field]=[v for v in groups.values() if len(v)>1]
    dimensions=Counter('x'.join(map(str,r['dimensions'])) for r in rows if r['valid'])
    return dict(schema_version=1,source_directory=str(root),scope='top_level_nonrecursive',
        baseline_descriptor='uint8 HSV V = max(R,G,B); low-frequency descriptor uses a deterministic <=128-pixel thumbnail; selection only, not a processing-setting choice',
        rows=rows,summary=dict(candidate_files=len(rows),readable=sum(r['valid'] for r in rows),
        invalid=sum(not r['valid'] for r in rows),dimensions=dict(dimensions),
        incompatible_dimensions=len(dimensions)>1,duplicates=duplicates,
        below_128_pixel_review_size=[r['relative_path'] for r in rows if r.get('below_128_pixel_review_size')],
        invalid_condition_keys=sorted(set(conditions or {})-{r['relative_path'] for r in rows})))


def select_sample(rows, limit=24, per_condition=4):
    if not isinstance(limit,int) or not 2<=limit<=32: raise ValueError('pilot limit must be 2..32')
    if not isinstance(per_condition,int) or not 3<=per_condition<=5: raise ValueError('per_condition must be 3..5')
    rows=sorted([r for r in rows if r['valid']],key=lambda r:(r['relative_path'].casefold(),r['relative_path']))
    if len(rows)<2: raise ValueError('at least two supported candidates are required')
    labels=[r.get('condition') for r in rows]
    if any(labels):
        if not all(labels): raise ValueError('condition metadata is incomplete; do not infer missing labels')
        groups={label:[r for r in rows if r['condition']==label] for label in sorted(set(labels))}
        if len(groups)>limit: raise ValueError('pilot cap cannot represent all conditions; human selection required')
        quotas={label:1 for label in groups}
        while sum(quotas.values())<limit:
            changed=False
            for label,group in groups.items():
                if quotas[label]<min(per_condition,len(group)) and sum(quotas.values())<limit:
                    quotas[label]+=1; changed=True
            if not changed: break
        chosen=[]
        for label,group in groups.items():
            n=quotas[label]
            indices=[len(group)//2] if n==1 else [i*(len(group)-1)//(n-1) for i in range(n)]
            chosen.extend(group[i] for i in indices)
        rule=dict(method='condition_stratified_even_path_quantiles',limit=limit,per_condition=per_condition,quotas=quotas)
    else:
        x=np.array([[r[k] for k in FEATURES] for r in rows],dtype=float)
        if not np.all(np.isfinite(x)): raise ValueError('selection descriptors must be finite')
        span=np.ptp(x,axis=0); x=(x-x.min(axis=0))/np.where(span==0,1,span)
        indices=[0]
        while len(indices)<min(limit,len(rows)):
            nearest=np.min(np.sum((x[:,None,:]-x[indices][None,:,:])**2,axis=2),axis=1)
            nearest[indices]=-1
            indices.append(int(np.argmax(nearest)))
        chosen=[rows[i] for i in sorted(indices)]
        rule=dict(method='baseline_farthest_point',features=list(FEATURES),scaling='corpus min/max; constant features zero',
            first='first stable relative path',ties='first stable relative path',limit=limit)
    return chosen,rule
