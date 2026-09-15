"""Verify the public pipeline runs with optional scientific imports unavailable."""
import importlib.abc
import sys


class NoOptional(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if fullname.split('.')[0] in {'scipy', 'skimage'}:
            raise ImportError('Blocked optional dependency: '+fullname)


def check():
    sys.meta_path.insert(0, NoOptional())
    import numpy as np
    from shine_color.pipeline import run
    rng=np.random.default_rng(491)
    images=[rng.integers(0,256,(17,19,3),dtype=np.uint8) for _ in range(3)]
    for space in ('RGB','HSV','Lab'):
        for mode in range(1,9):
            output=run(images,space,mode,iterations=2)
            assert all(v.dtype==np.uint8 and v.shape==(17,19,3) for v in output)
    print('24 space/mode runs passed with scipy and skimage imports blocked.')


if __name__=='__main__': check()
