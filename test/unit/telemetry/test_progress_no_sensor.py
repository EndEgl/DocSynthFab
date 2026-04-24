import pytest

from ai1_gen.telemetry.progress import TemperatureReader, TelemetryError


def test_temperature_reader_returns_na_or_raises_cleanly_when_sensor_missing():
    reader = TemperatureReader(require=False, prefer_gpu=True, throttle_s=0.0)

    try:
        result = reader.read()
    except TelemetryError:
        pytest.fail("TemperatureReader should not hard-fail when require=False")

    assert hasattr(result, "gpu_c")
    assert hasattr(result, "cpu_c")