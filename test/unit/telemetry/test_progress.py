from __future__ import annotations

import time

import pytest

from docsynthfab.telemetry.progress import (
    ProgressPrinter,
    TemperatureReader,
    TelemetryError,
    TempReading,
)


# ======================================================================================
# TemperatureReader
# ======================================================================================

def test_temperature_reader_returns_reading_when_sensor_missing_and_require_false(
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.setattr(TemperatureReader, "_read_gpu", lambda self: None)

    reader = TemperatureReader(require=False, prefer_gpu=True, throttle_s=0.0)

    result = reader.read()

    assert isinstance(result, TempReading)
    assert result.gpu_c is None
    assert result.cpu_c is None


def test_temperature_reader_raises_when_sensor_missing_and_require_true(
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.setattr(TemperatureReader, "_read_gpu", lambda self: None)

    reader = TemperatureReader(require=True, prefer_gpu=True, throttle_s=0.0)

    with pytest.raises(TelemetryError, match="telemetry/no-temp-sensor"):
        reader.read()


def test_temperature_reader_returns_gpu_temperature_when_available(
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.setattr(TemperatureReader, "_read_gpu", lambda self: 67)

    reader = TemperatureReader(require=True, prefer_gpu=True, throttle_s=0.0)

    result = reader.read()

    assert result.gpu_c == 67
    assert result.cpu_c is None


def test_temperature_reader_throttles_and_returns_cached_value(
    monkeypatch: pytest.MonkeyPatch,
):
    calls = {"n": 0}

    def fake_read_gpu(self):
        calls["n"] += 1
        return 50 + calls["n"]

    monkeypatch.setattr(TemperatureReader, "_read_gpu", fake_read_gpu)

    reader = TemperatureReader(require=False, prefer_gpu=True, throttle_s=999.0)

    first = reader.read()
    second = reader.read()

    assert first.gpu_c == 51
    assert second.gpu_c == 51
    assert calls["n"] == 1


def test_temperature_reader_refreshes_after_throttle_window(
    monkeypatch: pytest.MonkeyPatch,
):
    calls = {"n": 0}

    def fake_read_gpu(self):
        calls["n"] += 1
        return 60 + calls["n"]

    monkeypatch.setattr(TemperatureReader, "_read_gpu", fake_read_gpu)

    reader = TemperatureReader(require=False, prefer_gpu=True, throttle_s=0.01)

    first = reader.read()
    time.sleep(0.02)
    second = reader.read()

    assert first.gpu_c == 61
    assert second.gpu_c == 62
    assert calls["n"] == 2


# ======================================================================================
# ProgressPrinter
# ======================================================================================

def test_progress_printer_clean_replaces_non_ascii_when_ascii_only_true():
    printer = ProgressPrinter(mode="multi_line", ascii_only=True)

    cleaned = printer._clean("temp gpu=70°C ölçü")

    assert cleaned == "temp gpu=70?C ?l??"


def test_progress_printer_clean_keeps_unicode_when_ascii_only_false():
    printer = ProgressPrinter(mode="multi_line", ascii_only=False)

    text = "temp gpu=70°C ölçü"

    assert printer._clean(text) == text


def test_progress_printer_print_line_multi_line(capsys):
    printer = ProgressPrinter(mode="multi_line", ascii_only=True)

    printer.print_line("hello ölçü")

    captured = capsys.readouterr()

    assert "hello" in captured.out
    assert "?l??" in captured.out


def test_progress_printer_print_line_single_line_updates_last_len(capsys):
    printer = ProgressPrinter(mode="single_line", ascii_only=True)

    printer.print_line("progress 1")
    printer.print_line("ok")
    printer.finish()

    captured = capsys.readouterr()

    assert "\rprogress 1" in captured.out
    assert "\rok" in captured.out
    assert printer._last_len == 2


def test_progress_printer_finish_prints_newline_in_single_line_mode(capsys):
    printer = ProgressPrinter(mode="single_line", ascii_only=True)

    printer.finish()

    captured = capsys.readouterr()

    assert captured.out == "\n"


def test_progress_printer_finish_no_extra_output_in_multi_line_mode(capsys):
    printer = ProgressPrinter(mode="multi_line", ascii_only=True)

    printer.finish()

    captured = capsys.readouterr()

    assert captured.out == ""



