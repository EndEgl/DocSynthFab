# src/docsynthfab/orchestrator/_param_fields_run.py
# Önerilen sürüm aralıkları:
# - Python>=3.10,<3.14

from __future__ import annotations

from typing import List

from .models import ParamField


RUN_FIELDS: List[ParamField] = [
    ParamField(
        key="run.fail_fast",
        label="Fail Fast",
        group="Run",
        field_type="bool",
        default=False,
        help_text="İlk ciddi hata oranında koşuyu durdurur.",
        visibility="advanced",
    ),
    ParamField(
        key="run.max_fail_ratio",
        label="Max Fail Ratio",
        group="Run",
        field_type="float",
        default=0.02,
        minimum=0.0,
        maximum=1.0,
        step=0.001,
        help_text="İzin verilen maksimum hata oranı.",
        visibility="advanced",
    ),
    ParamField(
        key="run.jsonl_flush_batch_size",
        label="JSONL Flush Batch Size",
        group="Run",
        field_type="int",
        default=50,
        minimum=1,
        help_text="JSONL tamponunun kaç kayıtta bir flush edileceği.",
        visibility="advanced",
    ),
    ParamField(
        key="run.max_pending_mult",
        label="Max Pending Multiplier",
        group="Run",
        field_type="float",
        default=2.0,
        minimum=1.0,
        step=0.1,
        help_text="Worker başına pending iş çarpanı.",
        visibility="advanced",
    ),
    ParamField(
        key="run.max_pending_min",
        label="Max Pending Minimum",
        group="Run",
        field_type="int",
        default=8,
        minimum=1,
        help_text="Minimum pending iş sayısı.",
        visibility="advanced",
    ),
    ParamField(
        key="run.worker.max_tries",
        label="Worker Max Tries",
        group="Run",
        field_type="int",
        default=4,
        minimum=1,
        help_text="Bir sayfa için maksimum tekrar deneme sayısı.",
        visibility="advanced",
    ),
    ParamField(
        key="run.worker.disable_augment_on_try",
        label="Disable Augment On Try",
        group="Run",
        field_type="int",
        default=2,
        minimum=1,
        help_text="Belirli denemeden sonra augment kapatılır.",
        visibility="advanced",
    ),
    ParamField(
        key="run.worker.jitter_seed_step",
        label="Jitter Seed Step",
        group="Run",
        field_type="int",
        default=10000019,
        minimum=1,
        help_text="Retry seed varyasyonu için adım değeri.",
        visibility="advanced",
    ),
    ParamField(
        key="run.worker.fallback_dpi",
        label="Fallback DPI",
        group="Run",
        field_type="int",
        default=300,
        minimum=72,
        help_text="Fallback render DPI değeri.",
        visibility="advanced",
    ),
    ParamField(
        key="run.splits.train",
        label="Train Split",
        group="Run",
        field_type="float",
        default=0.80,
        minimum=0.0,
        maximum=1.0,
        step=0.01,
        help_text="Train split oranı.",
        visibility="advanced",
    ),
    ParamField(
        key="run.splits.val",
        label="Val Split",
        group="Run",
        field_type="float",
        default=0.10,
        minimum=0.0,
        maximum=1.0,
        step=0.01,
        help_text="Validation split oranı.",
        visibility="advanced",
    ),
    ParamField(
        key="run.splits.test",
        label="Test Split",
        group="Run",
        field_type="float",
        default=0.10,
        minimum=0.0,
        maximum=1.0,
        step=0.01,
        help_text="Test split oranı.",
        visibility="advanced",
    ),
]



