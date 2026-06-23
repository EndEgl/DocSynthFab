# src/docsynthfab/orchestrator/_param_fields_content.py
# Önerilen sürüm aralıkları:
# - Python>=3.10,<3.14

from __future__ import annotations

from typing import List

from .models import ParamField


CONTENT_FIELDS: List[ParamField] = [
    ParamField(
        key="content.hard_negative_page_prob",
        label="Hard Negative Page Probability",
        group="Content",
        field_type="float",
        default=0.05,
        minimum=0.0,
        maximum=1.0,
        step=0.01,
        help_text="Hard negative sayfa olasılığı.",
        visibility="advanced",
    ),
    ParamField(
        key="content.source.words_csv",
        label="Words CSV",
        group="Content",
        field_type="path",
        default="data/content/words.csv",
        help_text="Kelime kaynağı CSV dosyası.",
        visibility="advanced",
    ),
    ParamField(
        key="content.source.sentences_csv",
        label="Sentences CSV",
        group="Content",
        field_type="path",
        default="data/content/sentences.csv",
        help_text="Cümle kaynağı CSV dosyası.",
        visibility="advanced",
    ),
    ParamField(
        key="content.source.generated_json",
        label="Generated Content JSON",
        group="Content",
        field_type="path",
        default="data/content/content_bank.json",
        help_text="Normalize edilmiş içerik JSON dosyası.",
        visibility="advanced",
    ),
    ParamField(
        key="content.source.label_registry_csv",
        label="Label Registry CSV",
        group="Content",
        field_type="path",
        default="data/content/label_registry.csv",
        help_text="Dinamik üretilen etiket registry CSV dosyası.",
        visibility="advanced",
    ),
    ParamField(
        key="content.generate_json_if_missing",
        label="Generate JSON If Missing",
        group="Content",
        field_type="bool",
        default=True,
        help_text="JSON yoksa otomatik üret.",
        visibility="advanced",
    ),
    ParamField(
        key="content.regenerate_json_on_start",
        label="Regenerate JSON On Start",
        group="Content",
        field_type="bool",
        default=False,
        help_text="Her başlangıçta JSON yeniden üret.",
        visibility="advanced",
    ),
    ParamField(
        key="content.mixed_probs",
        label="Mixed Mode Probabilities",
        group="Content",
        field_type="json",
        default={"chars": 0.10, "words": 0.45, "sentences": 0.45},
        help_text="Mixed text mode için olasılık dağılımı.",
        visibility="advanced",
    ),
    ParamField(
        key="content.chars",
        label="Chars Config",
        group="Content",
        field_type="json",
        default={},
        help_text="Karakter modu ayarları.",
        visibility="advanced",
    ),
    ParamField(
        key="content.words",
        label="Words Config",
        group="Content",
        field_type="json",
        default={},
        help_text="Kelime modu ayarları.",
        visibility="advanced",
    ),
    ParamField(
        key="content.sentences",
        label="Sentences Config",
        group="Content",
        field_type="json",
        default={},
        help_text="Cümle modu ayarları.",
        visibility="advanced",
    ),
]



