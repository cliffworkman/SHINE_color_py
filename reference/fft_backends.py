"""Diagnostic-only FFT adapters. Nothing here is imported by shine_color."""
from contextlib import contextmanager
from unittest.mock import patch
import ctypes
import os

import numpy as np

from shine_color import spatial_frequency, spectrum


class NumpyProxy:
    def __init__(self, fft):
        self.fft = fft

    def __getattr__(self, name):
        return getattr(np, name)


class FFTBackend:
    def __init__(self, name, kind='numpy', transpose=False, effort='FFTW_ESTIMATE'):
        self.name, self.kind = name, kind
        self.transpose, self.effort = transpose, effort

    def __getattr__(self, name):
        return getattr(np.fft, name)

    def fft2(self, a):
        if self.kind == 'numpy':
            return np.fft.fft2(a)
        from pyfftw.interfaces import numpy_fft
        x = np.ascontiguousarray(a.T if self.transpose else a)
        if self.kind == 'r2c':
            half = numpy_fft.rfft2(x, threads=1, planner_effort=self.effort)
            # Hermitian completion is a representation change, not zero handling.
            rows, cols = x.shape
            full = np.empty(x.shape, dtype=np.complex128)
            full[:, :half.shape[1]] = half
            rest = np.arange(half.shape[1], cols)
            full[:, rest] = np.conj(half[(-np.arange(rows)) % rows][:, cols-rest])
        else:
            full = numpy_fft.fft2(x, threads=1, planner_effort=self.effort)
        return full.T if self.transpose else full

    def ifft2(self, a):
        if self.kind == 'numpy':
            return np.fft.ifft2(a)
        from pyfftw.interfaces import numpy_fft
        x = np.ascontiguousarray(a.T if self.transpose else a)
        result = numpy_fft.ifft2(x, threads=1, planner_effort=self.effort)
        return result.T if self.transpose else result


class OctaveDLLBackend(FFTBackend):
    """Call the installed Octave FFTW binary directly, for this diagnostic only."""
    def __init__(self, path):
        super().__init__('octave_fftw_dll','r2c',True)
        self.dll_directory = os.add_dll_directory(str(path.parent))
        self.dll = ctypes.CDLL(str(path))
        self.version = ctypes.string_at(ctypes.addressof(ctypes.c_char.in_dll(self.dll,'fftw_version'))).decode()
        self.dll.fftw_plan_dft_r2c_2d.argtypes = [ctypes.c_int,ctypes.c_int,ctypes.c_void_p,ctypes.c_void_p,ctypes.c_uint]
        self.dll.fftw_plan_dft_r2c_2d.restype = ctypes.c_void_p
        self.dll.fftw_plan_dft_2d.argtypes = [ctypes.c_int,ctypes.c_int,ctypes.c_void_p,ctypes.c_void_p,ctypes.c_int,ctypes.c_uint]
        self.dll.fftw_plan_dft_2d.restype = ctypes.c_void_p
        self.dll.fftw_execute.argtypes = [ctypes.c_void_p]
        self.dll.fftw_destroy_plan.argtypes = [ctypes.c_void_p]
        self.dll.fftw_forget_wisdom()
        self.dll.fftw_init_threads()
        self.dll.fftw_plan_with_nthreads(1)

    def execute(self, plan):
        if not plan:
            raise RuntimeError('FFTW plan creation failed')
        try:
            self.dll.fftw_execute(plan)
        finally:
            self.dll.fftw_destroy_plan(plan)

    def fft2(self,a):
        x = np.array(a.T,dtype=np.float64,order='C',copy=True)
        rows,cols = x.shape
        half = np.empty((rows,cols//2+1),dtype=np.complex128)
        self.execute(self.dll.fftw_plan_dft_r2c_2d(rows,cols,x.ctypes.data,half.ctypes.data,64))
        full = np.empty(x.shape,dtype=np.complex128)
        full[:,:half.shape[1]] = half
        rest = np.arange(half.shape[1],cols)
        full[:,rest] = np.conj(half[(-np.arange(rows)) % rows][:,cols-rest])
        return full.T

    def ifft2(self,a):
        x = np.array(a.T,dtype=np.complex128,order='C',copy=True)
        result = np.empty(x.shape,dtype=np.complex128)
        self.execute(self.dll.fftw_plan_dft_2d(*x.shape,x.ctypes.data,result.ctypes.data,1,64))
        return result.T/a.size


@contextmanager
def use_backend(backend):
    proxy = NumpyProxy(backend)
    with patch.object(spatial_frequency, 'np', proxy), patch.object(spectrum, 'np', proxy):
        yield
