"""Load a SIL shared library (bms_sil_api.h) and run it on a current/temperature profile."""

from __future__ import annotations

import ctypes
import subprocess
import sys
from pathlib import Path
from typing import Callable, Sequence

import numpy as np

API_HEADER_DIR = Path(__file__).resolve().parent / "c"


class SilModel:
    """Python handle to the user's C model built against ``bms_sil_api.h``."""

    def __init__(self, lib_path: str | Path):
        self.lib = ctypes.CDLL(str(Path(lib_path).resolve()))
        L = self.lib
        L.bms_sil_param_name.restype = ctypes.c_char_p
        L.bms_sil_output_name.restype = ctypes.c_char_p
        L.bms_sil_get_param.argtypes = [ctypes.c_char_p, ctypes.POINTER(ctypes.c_double)]
        L.bms_sil_set_param.argtypes = [ctypes.c_char_p, ctypes.c_double]
        L.bms_sil_reset.argtypes = [ctypes.c_double, ctypes.c_double]
        L.bms_sil_step.argtypes = [ctypes.c_double, ctypes.c_double, ctypes.c_double]
        L.bms_sil_get_output.argtypes = [ctypes.c_int]
        L.bms_sil_get_output.restype = ctypes.c_double
        if L.bms_sil_api_version() != 1:
            raise RuntimeError("unsupported bms_sil API version")
        self.param_names = [L.bms_sil_param_name(i).decode() for i in range(L.bms_sil_param_count())]
        self.output_names = [L.bms_sil_output_name(i).decode() for i in range(L.bms_sil_output_count())]
        self.defaults = self.get_params()

    def get_params(self) -> dict[str, float]:
        out = {}
        val = ctypes.c_double()
        for n in self.param_names:
            if self.lib.bms_sil_get_param(n.encode(), ctypes.byref(val)) == 0:
                out[n] = val.value
        return out

    def set_params(self, params: dict[str, float]) -> None:
        for n, v in params.items():
            if self.lib.bms_sil_set_param(n.encode(), float(v)) != 0:
                raise KeyError(f"unknown SIL parameter {n!r}")

    def run(self, t: Sequence[float], current: Sequence[float], temp_c: Sequence[float] | float,
            soc0: float, params: dict[str, float] | None = None) -> dict[str, np.ndarray]:
        """Run from ``soc0``. ``current[k]`` is applied over (t[k-1], t[k]]; outputs sampled at t[k]."""
        self.set_params({**self.defaults, **(params or {})})
        t = np.asarray(t, dtype=float)
        cur = np.asarray(current, dtype=float)
        temp = np.broadcast_to(np.asarray(temp_c, dtype=float), t.shape)
        L = self.lib
        L.bms_sil_reset(float(soc0), float(temp[0]))
        n_out = len(self.output_names)
        out = np.empty((len(t), n_out))
        for k in range(len(t)):
            if k > 0:
                L.bms_sil_step(float(t[k] - t[k - 1]), float(cur[k]), float(temp[k]))
            for j in range(n_out):
                out[k, j] = L.bms_sil_get_output(j)
        return {name: out[:, j] for j, name in enumerate(self.output_names)}

    def simulator(self, t, current, temp_c, soc0: float, output: str = "v") -> Callable[[dict], np.ndarray]:
        """Return ``f(params) -> output array`` for the inference engine."""
        def f(params: dict[str, float]) -> np.ndarray:
            return self.run(t, current, temp_c, soc0, params)[output]
        return f


def build_shared(sources: Sequence[str | Path], out: str | Path, include_dirs: Sequence[str | Path] = (),
                 defines: dict[str, str] | None = None, cc: str = "cc", extra: Sequence[str] = ()) -> Path:
    """Compile a SIL shared library with the system C compiler (development convenience).

    The in-house build system can be used instead; only the ABI in bms_sil_api.h matters.
    """
    out = Path(out)
    out.parent.mkdir(parents=True, exist_ok=True)
    flags = ["-O2", "-fPIC", "-shared", "-std=c99", f"-I{API_HEADER_DIR}"]
    flags += [f"-I{d}" for d in include_dirs]
    flags += [f"-D{k}={v}" for k, v in (defines or {}).items()]
    cmd = [cc, *flags, *map(str, sources), "-o", str(out), "-lm", *extra]
    if sys.platform == "win32":  # pragma: no cover
        cmd = [c for c in cmd if c != "-fPIC"]
    subprocess.run(cmd, check=True, capture_output=True, text=True)
    return out
