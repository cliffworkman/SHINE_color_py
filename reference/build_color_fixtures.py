"""Deterministic RGB conversion probes, chosen before library comparison."""
import hashlib
import json
from pathlib import Path
import numpy as np
from scipy.io import savemat

DEST = Path(__file__).resolve().parents[1]/'tests/reference/fixtures/color'


def build():
    DEST.mkdir(exist_ok=True)
    colors = [
        [0,0,0], [255,255,255], [1,1,1], [2,2,2], [10,10,10], [32,32,32], [127,127,127], [128,128,128],
        [254,254,254], [253,253,253], [255,0,0], [0,255,0], [0,0,255], [0,255,255], [255,0,255], [255,255,0],
        [1,0,0], [0,1,0], [0,0,1], [1,2,3], [3,2,1], [4,8,12], [10,11,12], [12,11,10],
        [254,255,255], [255,254,255], [255,255,254], [252,253,254], [254,253,252], [250,251,252], [128,127,129], [127,128,126],
        [64,65,66], [200,198,199], [128,0,0], [0,128,0], [0,0,128], [0,128,128], [128,0,128], [128,128,0],
        [255,1,17], [3,255,29], [11,7,255], [255,128,0], [128,255,0], [0,255,128], [0,128,255], [128,0,255],
        [255,0,128], [17,83,191], [201,33,117], [29,203,91], [52,99,147], [231,180,47], [7,119,230], [98,41,173],
        [46,139,87], [240,128,128], [123,104,238], [255,215,0], [19,27,43], [211,219,237], [102,153,204], [37,149,211],
    ]
    palette = np.array(colors, dtype=np.uint8).reshape(8,8,3)
    y,x = np.indices((7,9))
    structured = np.stack([(17*x+31*y)%256, (53*x+7*y+19)%256, (11*x+43*y+101)%256], axis=-1).astype(np.uint8)
    grays = np.repeat(np.arange(256, dtype=np.uint8)[None,:,None], 3, axis=2)
    inputs = np.empty((1,3), dtype=object)
    for k,a in enumerate((palette,structured,grays)):
        inputs[0,k] = a
    savemat(DEST/'inputs.mat', dict(inputs=inputs), do_compression=True)
    manifest = dict(names=['palette_8x8','structured_7x9','gray_ramp_1x256'],
        pixel_counts=[64,63,256], palette=colors,
        structured_formula=['(17*x+31*y)%256','(53*x+7*y+19)%256','(11*x+43*y+101)%256'],
        input_sha256=hashlib.sha256((DEST/'inputs.mat').read_bytes()).hexdigest(),
        generator='reference/build_color_fixtures.py', generator_version=1,
        generator_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest())
    (DEST/'inputs.json').write_text(json.dumps(manifest, indent=2)+'\n', newline='\n')


if __name__ == '__main__':
    build()
