"""Descriptive metrics on actual SHINE working channels, never a processing path."""
import hashlib
import numpy as np
from shine_color import color, histogram, spatial_frequency
from shine_color.numeric import imhist256, sample_std, matlab_round
from reference.backend_policy.screen_conditioning import characterize


def array_hash(a):
    return hashlib.sha256(np.asarray(a).tobytes(order='C')).hexdigest()


def working_channels(rgb, colorspace):
    space=colorspace.lower()
    if space=='rgb': return dict(zip(('R','G','B'),color.split_rgb(rgb)))
    if space=='hsv': return {'V':color.split_hsv(rgb)[2]}
    if space in ('lab','cielab'): return {'L':color.split_lab(rgb)[0]}
    raise ValueError('colorspace must be RGB, HSV or CIELab')


def channel_metrics(a):
    a=np.asarray(a)
    if a.ndim!=2 or a.dtype!=np.uint8: raise ValueError('QC working channels must be 2-D uint8')
    hist=imhist256(a); p=hist[hist>0]/a.size
    return dict(mean=float(a.mean()),sample_sd=sample_std(a),histogram=hist.tolist(),
        entropy_bits=float(-np.sum(p*np.log2(p))),modal_bin_fraction=float(hist.max()/a.size),
        zero_fraction=float(hist[0]/a.size),maximum_fraction=float(hist[255]/a.size),
        working_sha256=array_hash(a))


def dispersion(records):
    means=np.array([r['mean'] for r in records]); sds=np.array([r['sample_sd'] for r in records])
    h=np.array([r['histogram'] for r in records],dtype=float)
    probabilities=h/h.sum(axis=1,keepdims=True); target=probabilities.mean(axis=0)
    return dict(mean_range=float(np.ptp(means)),sd_of_means=sample_std(means),
        sample_sd_range=float(np.ptp(sds)),sd_of_sample_sds=sample_std(sds),
        histogram_mean_total_variation=float(np.abs(probabilities-target).sum(axis=1).mean()/2))


def amplitude(a):
    return spatial_frequency._decompose(a)[1]


def radial(a):
    """Retained SUMS of amplitude, exactly the kernel's bin and cutoff conventions."""
    r=spatial_frequency._radial_bin_grid(*a.shape)
    sums=np.bincount(r.ravel(order='F'),weights=a.ravel(order='F'))
    counts=np.bincount(r.ravel()); occupied=np.flatnonzero((counts>0)&(np.arange(len(counts))<=np.floor(max(a.shape)/2)))
    return occupied,sums[occupied]


def distance(a,b):
    d=np.asarray(a)-np.asarray(b); norm=float(np.linalg.norm(b))
    return dict(rmse=float(np.sqrt(np.mean(d*d))),
        relative_l2=float(np.linalg.norm(d)/norm) if norm else (0.0 if not np.any(d) else None))


def spectral_group(images, target=None):
    """Stream FFTs to bound QC memory; target is the original stage/group mean."""
    mean=np.zeros(images[0].shape,dtype=np.float64)
    for a in images: mean+=amplitude(a)
    mean/=len(images)
    if target is None: target=mean
    bins,target_profile=radial(target)
    records=[]; dispersions=[]; radial_dispersions=[]
    for a in images:
        amp=amplitude(a); _,profile=radial(amp)
        full=distance(amp,target)
        ac=amp.copy(); ac_target=target.copy()
        ac[amp.shape[0]//2,amp.shape[1]//2]=0
        ac_target[amp.shape[0]//2,amp.shape[1]//2]=0
        r=spatial_frequency._radial_bin_grid(*amp.shape); cutoff=np.floor(max(amp.shape)/2)
        low=float(np.sum(amp[(r>0)&(r<=cutoff/2)]**2))
        high=float(np.sum(amp[(r>cutoff/2)&(r<=cutoff)]**2))
        records.append(dict(full_amplitude=full,non_dc_amplitude=distance(ac,ac_target),
            radial_amplitude=distance(profile,target_profile),retained_bins=bins.tolist(),
            radial_amplitude_sums=profile.tolist(),
            low_high_power_ratio=low/high if high else None,
            low_power_fraction=low/(low+high) if low+high else 0.0))
        dispersions.append(distance(amp,mean)['rmse'])
        radial_dispersions.append(distance(profile,radial(mean)[1])['rmse'])
    return dict(images=records,target_amplitude_sha256=array_hash(target),
        target_radial_amplitude_sums=target_profile.tolist(),retained_bins=bins.tolist(),
        mean_full_amplitude_rmse_to_group_mean=float(np.mean(dispersions)),
        mean_radial_amplitude_rmse_to_group_mean=float(np.mean(radial_dispersions))),target


def conditioning(a):
    result=characterize(amplitude(a)); result.pop('retained_bins')
    result['stage_input_sha256']=array_hash(a)
    return result


def histogram_target(images):
    requested=histogram.average_histogram(images)
    values=histogram.histogram_to_value_list(requested)
    # Predict intensity counts after the kernel's existing target-list resampling.
    # This is diagnostic only: no image is normalized through this calculation.
    indices=matlab_round(np.linspace(1.,float(len(values)),images[0].size)).astype(np.int64)-1
    expected=imhist256(values[np.clip(indices,0,len(values)-1)])
    return dict(requested_rounded_histogram=requested.tolist(),
        expected_resampled_histogram=expected.tolist(),requested_count=int(requested.sum()),
        actual_pixel_count=int(images[0].size))


def change(before,after):
    d=after.astype(float)-before.astype(float)
    return dict(changed_scalar_percent=float(np.count_nonzero(d)*100/d.size),
        rgb_mae=float(np.mean(abs(d))),rgb_rmse=float(np.sqrt(np.mean(d*d))),
        rgb_max_abs=float(np.max(abs(d))),
        final_zero_scalar_percent=float(np.count_nonzero(after==0)*100/after.size),
        final_255_scalar_percent=float(np.count_nonzero(after==255)*100/after.size))


def cast_metrics(values):
    a=np.asarray(values,dtype=float)
    return dict(elements=a.size,below_zero=int(np.count_nonzero(a<0)),
        above_255=int(np.count_nonzero(a>255)),nonfinite=int(np.count_nonzero(~np.isfinite(a))),
        outside_percent=float(np.count_nonzero((a<0)|(a>255))*100/a.size))
