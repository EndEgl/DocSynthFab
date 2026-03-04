# src/ai1_gen/telemetry/progress.py
# Önerilen sürüm aralıkları:
# - Python>=3.10,<3.14

from __future__ import annotations

import subprocess
import time
from dataclasses import dataclass
from typing import Optional


class TelemetryError(RuntimeError):
    pass


@dataclass
class TempReading:
    gpu_c: Optional[int]
    cpu_c: Optional[int]


class TemperatureReader:
    """
    Kontrat: tercih GPU (nvidia-smi), fallback CPU.
    Bu minimal sürüm GPU'ya odaklanır (en stabil).
    """
    def __init__(self, require: bool = True, prefer_gpu: bool = True, throttle_s: float = 1.0):
        self.require = bool(require)
        self.prefer_gpu = bool(prefer_gpu)
        self.throttle_s = float(throttle_s)
        self._last_t = 0.0
        self._last = TempReading(gpu_c=None, cpu_c=None)

    def _read_gpu(self) -> Optional[int]:
        try:
            out = subprocess.check_output(
                ["nvidia-smi", "--query-gpu=temperature.gpu", "--format=csv,noheader,nounits"],
                stderr=subprocess.DEVNULL,
                timeout=1.5,
                text=True,
            )
            s = (out.splitlines()[0] if out else "").strip()
            if not s:
                return None
            return int(s)
        except Exception:
            return None

    def read(self) -> TempReading:
        now = time.time()
        if now - self._last_t < self.throttle_s:
            return self._last

        gpu = self._read_gpu()
        cpu = None  # minimal: CPU yok (istersen WMI ekleriz)

        self._last_t = now
        self._last = TempReading(gpu_c=gpu, cpu_c=cpu)

        if self.require and (gpu is None and cpu is None):
            raise TelemetryError("telemetry/no-temp-sensor")

        return self._last


class ProgressPrinter:
    def __init__(self, *, mode: str = "single_line", ascii_only: bool = True):
        self.mode = mode
        self.ascii_only = ascii_only
        self._last_len = 0

    def _clean(self, s: str) -> str:
        if not self.ascii_only:
            return s
        return "".join(ch if ord(ch) < 128 else "?" for ch in s)

    def print_line(self, s: str) -> None:
        s = self._clean(s)
        if self.mode == "single_line":
            pad = max(0, self._last_len - len(s))
            out = "\r" + s + (" " * pad)
            print(out, end="", flush=True)
            self._last_len = len(s)
        else:
            print(s, flush=True)

    def finish(self) -> None:
        if self.mode == "single_line":
            print("", flush=True)