# src/ai1_gen/gui.py
# Önerilen sürüm aralıkları:
# - Python>=3.10,<3.14
# - PySide6>=6.5,<7.0
# - PyYAML>=6.0,<7.0

from __future__ import annotations

import csv
import html
import io
import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml

# Dosya doğrudan çalıştırılırsa package root'u sys.path'e ekle
_THIS_FILE = Path(__file__).resolve()
_PKG_DIR = _THIS_FILE.parent              # .../ai1_gen/src/ai1_gen
_SRC_ROOT = _THIS_FILE.parents[1]         # .../ai1_gen/src
_PROJECT_ROOT = _THIS_FILE.parents[2]     # .../ai1_gen

if str(_SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(_SRC_ROOT))

_DEFAULT_CONFIG = _PROJECT_ROOT / "configs" / "default.yaml"

from PySide6.QtCore import QByteArray, QTimer, Qt
from PySide6.QtGui import QAction
from PySide6.QtSvgWidgets import QSvgWidget
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QDoubleSpinBox,
    QFileDialog,
    QFormLayout,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QScrollArea,
    QSpinBox,
    QSplitter,
    QTabWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from ai1_gen.orchestrator import RunOrchestrator, RunRequest
from ai1_gen.orchestrator.result_store import tail_text


def _safe_json_loads(text: str, fallback: Any = None) -> Any:
    try:
        return json.loads(text)
    except Exception:
        return fallback


# ---------------------------------------------------------
# Template Manager Widget
# UI-level multi-template editor.
# Backend üretime bağlanmaz.
# ---------------------------------------------------------

CSV_EXPORT_DELIMITER = ";"

TEMPLATE_REGION_TYPES = [
    "text_block",
    "field",
    "table",
    "checkbox",
    "checkbox_group",
    "signature",
    "stamp",
    "figure",
    "separator",
    "empty_box",
    "barcode_like",
    "qr_like",
    "numbered_list",
    "bullet_list",
    "paragraph",
    "math_block",
    "header",
    "footer",
]

TEMPLATE_COLUMNS = [
    "template_name",
    "page_no",
    "region_id",
    "type",
    "label",
    "x",
    "y",
    "w",
    "h",
    "content_source",
    "min_rows",
    "max_rows",
    "cols",
    "required",
    "jitter",
    "style_hint",
    "mask_role",
    "annotation_label",
]

SAMPLE_TEMPLATE_ROWS: List[Dict[str, Any]] = [
    {
        "template_name": "invoice_basic",
        "page_no": 1,
        "region_id": "title",
        "type": "header",
        "label": "document_title",
        "x": 0.05,
        "y": 0.04,
        "w": 0.45,
        "h": 0.05,
        "content_source": "doc_titles",
        "min_rows": "",
        "max_rows": "",
        "cols": "",
        "required": True,
        "jitter": 0.005,
        "style_hint": "bold_header",
        "mask_role": "text",
        "annotation_label": "title",
    },
    {
        "template_name": "invoice_basic",
        "page_no": 1,
        "region_id": "seller",
        "type": "text_block",
        "label": "seller_info",
        "x": 0.05,
        "y": 0.11,
        "w": 0.42,
        "h": 0.12,
        "content_source": "company_info",
        "min_rows": "",
        "max_rows": "",
        "cols": "",
        "required": True,
        "jitter": 0.01,
        "style_hint": "normal_block",
        "mask_role": "text",
        "annotation_label": "seller_info",
    },
    {
        "template_name": "invoice_basic",
        "page_no": 1,
        "region_id": "invoice_no",
        "type": "field",
        "label": "invoice_number",
        "x": 0.66,
        "y": 0.05,
        "w": 0.26,
        "h": 0.04,
        "content_source": "invoice_numbers",
        "min_rows": "",
        "max_rows": "",
        "cols": "",
        "required": True,
        "jitter": 0.005,
        "style_hint": "small_field",
        "mask_role": "text",
        "annotation_label": "invoice_number",
    },
    {
        "template_name": "invoice_basic",
        "page_no": 1,
        "region_id": "items",
        "type": "table",
        "label": "items_table",
        "x": 0.05,
        "y": 0.30,
        "w": 0.90,
        "h": 0.38,
        "content_source": "product_rows",
        "min_rows": 4,
        "max_rows": 12,
        "cols": 6,
        "required": True,
        "jitter": 0.01,
        "style_hint": "bordered_table",
        "mask_role": "text",
        "annotation_label": "items_table",
    },
    {
        "template_name": "invoice_basic",
        "page_no": 1,
        "region_id": "signature",
        "type": "signature",
        "label": "signature_area",
        "x": 0.62,
        "y": 0.82,
        "w": 0.28,
        "h": 0.08,
        "content_source": "signatures",
        "min_rows": "",
        "max_rows": "",
        "cols": "",
        "required": False,
        "jitter": 0.01,
        "style_hint": "signature_box",
        "mask_role": "text",
        "annotation_label": "signature",
    },
]


class TemplateManagerWidget(QWidget):
    """PySide6 multi-template CSV editor.

    Bu widget bilinçli olarak sadece UI seviyesindedir:
    - çoklu template CSV import/export yapar,
    - aktif template seçtirir,
    - region edit ettirir,
    - SVG preview gösterir,
    - generator backend'ini değiştirmez.
    """

    def __init__(self, output_root_getter: Any, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)

        self.output_root_getter = output_root_getter

        self.template_rows: List[Dict[str, Any]] = []
        self.active_template_name: Optional[str] = None
        self.selected_template_region_id: Optional[str] = None

        self._build_ui()
        self._update_template_preview()

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)

        top_row = QHBoxLayout()

        self.load_sample_btn = QPushButton("Load Sample Template")
        self.import_btn = QPushButton("Import Template CSV")
        self.export_btn = QPushButton("Export Template CSV")
        self.open_btn = QPushButton("Open Template CSV")

        self.load_sample_btn.clicked.connect(self.load_sample_template_rows)
        self.import_btn.clicked.connect(self.import_template_csv)
        self.export_btn.clicked.connect(self.export_template_csv)
        self.open_btn.clicked.connect(self.open_template_csv)

        top_row.addWidget(self.load_sample_btn)
        top_row.addWidget(self.import_btn)
        top_row.addWidget(self.export_btn)
        top_row.addWidget(self.open_btn)

        root.addLayout(top_row)

        splitter = QSplitter(Qt.Horizontal)
        root.addWidget(splitter, 1)

        left = QWidget()
        left_layout = QVBoxLayout(left)

        selector_box = QGroupBox("Template Selector")
        selector_form = QFormLayout(selector_box)

        self.template_name_combo = QComboBox()
        self.template_name_combo.currentIndexChanged.connect(self._on_template_name_changed)

        self.region_combo = QComboBox()
        self.region_combo.currentIndexChanged.connect(self._on_region_changed)

        selector_form.addRow("Active Template", self.template_name_combo)
        selector_form.addRow("Selected Region", self.region_combo)

        left_layout.addWidget(selector_box)

        editor_box = QGroupBox("Region Editor")
        editor_form = QFormLayout(editor_box)

        self.type_combo = QComboBox()
        self.type_combo.addItems(TEMPLATE_REGION_TYPES)

        self.label_edit = QLineEdit()
        self.content_source_edit = QLineEdit()

        self.x_spin = QDoubleSpinBox()
        self.y_spin = QDoubleSpinBox()
        self.w_spin = QDoubleSpinBox()
        self.h_spin = QDoubleSpinBox()

        for spin in [self.x_spin, self.y_spin, self.w_spin, self.h_spin]:
            spin.setRange(0.0, 1.0)
            spin.setSingleStep(0.01)
            spin.setDecimals(4)

        self.min_rows_spin = QSpinBox()
        self.max_rows_spin = QSpinBox()
        self.cols_spin = QSpinBox()

        for spin in [self.min_rows_spin, self.max_rows_spin, self.cols_spin]:
            spin.setRange(0, 10_000)

        self.required_check = QCheckBox("Required")

        self.jitter_spin = QDoubleSpinBox()
        self.jitter_spin.setRange(0.0, 0.20)
        self.jitter_spin.setSingleStep(0.005)
        self.jitter_spin.setDecimals(4)

        editor_form.addRow("Type", self.type_combo)
        editor_form.addRow("Label", self.label_edit)
        editor_form.addRow("Content Source", self.content_source_edit)
        editor_form.addRow("X", self.x_spin)
        editor_form.addRow("Y", self.y_spin)
        editor_form.addRow("W", self.w_spin)
        editor_form.addRow("H", self.h_spin)
        editor_form.addRow("Min Rows", self.min_rows_spin)
        editor_form.addRow("Max Rows", self.max_rows_spin)
        editor_form.addRow("Cols", self.cols_spin)
        editor_form.addRow("Required", self.required_check)
        editor_form.addRow("Jitter", self.jitter_spin)

        self.apply_btn = QPushButton("Apply Region Changes")
        self.apply_btn.clicked.connect(self.apply_editor_to_selected_region)
        editor_form.addRow(self.apply_btn)

        left_layout.addWidget(editor_box)

        self.status_label = QLabel("No template loaded.")
        self.status_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        left_layout.addWidget(self.status_label)

        left_layout.addStretch(1)

        right = QWidget()
        right_layout = QVBoxLayout(right)

        right_layout.addWidget(QLabel("Template Preview"))

        self.preview_svg = QSvgWidget()
        self.preview_svg.setMinimumSize(420, 560)
        right_layout.addWidget(self.preview_svg, 1)

        splitter.addWidget(left)
        splitter.addWidget(right)
        splitter.setSizes([430, 620])

    @staticmethod
    def _parse_bool(value: Any) -> bool:
        return str(value).strip().lower() in {"1", "true", "yes", "on", "y"}

    @staticmethod
    def _parse_float(value: Any, default: float = 0.0) -> float:
        try:
            return float(value)
        except Exception:
            return float(default)

    @staticmethod
    def _parse_int_or_blank(value: Any) -> Any:
        txt = str(value or "").strip()
        if not txt:
            return ""
        try:
            return int(float(txt))
        except Exception:
            return txt

    def _coerce_template_row(self, row: Dict[str, Any]) -> Dict[str, Any]:
        out = {col: row.get(col, "") for col in TEMPLATE_COLUMNS}

        out["template_name"] = (
            str(out.get("template_name") or "custom_template").strip()
            or "custom_template"
        )
        out["page_no"] = int(self._parse_int_or_blank(out.get("page_no") or 1) or 1)
        out["region_id"] = str(out.get("region_id") or "region").strip() or "region"

        out["type"] = str(out.get("type") or "text_block").strip() or "text_block"
        if out["type"] not in TEMPLATE_REGION_TYPES:
            out["type"] = "text_block"

        out["label"] = str(out.get("label") or out["region_id"]).strip()

        out["x"] = max(0.0, min(1.0, self._parse_float(out.get("x"), 0.05)))
        out["y"] = max(0.0, min(1.0, self._parse_float(out.get("y"), 0.05)))
        out["w"] = max(0.01, min(1.0, self._parse_float(out.get("w"), 0.30)))
        out["h"] = max(0.01, min(1.0, self._parse_float(out.get("h"), 0.08)))

        if out["x"] + out["w"] > 1.0:
            out["w"] = max(0.01, 1.0 - out["x"])

        if out["y"] + out["h"] > 1.0:
            out["h"] = max(0.01, 1.0 - out["y"])

        out["content_source"] = str(out.get("content_source") or "").strip()
        out["min_rows"] = self._parse_int_or_blank(out.get("min_rows"))
        out["max_rows"] = self._parse_int_or_blank(out.get("max_rows"))
        out["cols"] = self._parse_int_or_blank(out.get("cols"))
        out["required"] = self._parse_bool(out.get("required"))
        out["jitter"] = max(0.0, min(0.20, self._parse_float(out.get("jitter"), 0.01)))
        out["style_hint"] = str(out.get("style_hint") or "normal_block").strip()
        out["mask_role"] = str(out.get("mask_role") or "text").strip()
        out["annotation_label"] = str(out.get("annotation_label") or out["label"]).strip()

        return out

    def available_template_names(self) -> List[str]:
        return sorted(
            {
                str(row.get("template_name") or "custom_template").strip()
                or "custom_template"
                for row in self.template_rows
            }
        )

    def get_active_template_name(self) -> Optional[str]:
        names = self.available_template_names()

        if not names:
            self.active_template_name = None
            return None

        if self.active_template_name not in names:
            self.active_template_name = names[0]

        return self.active_template_name

    def active_template_rows(self) -> List[Dict[str, Any]]:
        name = self.get_active_template_name()

        if not name:
            return []

        return [
            row
            for row in self.template_rows
            if str(row.get("template_name") or "custom_template").strip() == name
        ]

    def selected_template_row(self) -> Optional[Dict[str, Any]]:
        active_rows = self.active_template_rows()
        rid = self.selected_template_region_id

        if not rid:
            rid = self.region_combo.currentData() or self.region_combo.currentText()

        for row in active_rows:
            if str(row.get("region_id")) == str(rid):
                return row

        return active_rows[0] if active_rows else None

    def refresh_template_name_combo(self) -> None:
        self.template_name_combo.blockSignals(True)
        self.template_name_combo.clear()

        names = self.available_template_names()

        for name in names:
            self.template_name_combo.addItem(name, name)

        if names:
            if self.active_template_name not in names:
                self.active_template_name = names[0]

            idx = self.template_name_combo.findData(self.active_template_name)
            if idx >= 0:
                self.template_name_combo.setCurrentIndex(idx)
        else:
            self.active_template_name = None

        self.template_name_combo.blockSignals(False)

    def refresh_region_combo(self) -> None:
        self.region_combo.blockSignals(True)
        self.region_combo.clear()

        rows = self.active_template_rows()

        for row in rows:
            rid = str(row.get("region_id", ""))
            label = (
                f"{rid} · {row.get('type', '')} · "
                f"source={row.get('content_source', '')}"
            )
            self.region_combo.addItem(label, rid)

        ids = [str(row.get("region_id", "")) for row in rows]

        if ids:
            if self.selected_template_region_id not in ids:
                self.selected_template_region_id = ids[0]

            idx = self.region_combo.findData(self.selected_template_region_id)
            if idx >= 0:
                self.region_combo.setCurrentIndex(idx)
        else:
            self.selected_template_region_id = None

        self.region_combo.blockSignals(False)

    def _on_template_name_changed(self, *_: Any) -> None:
        self.active_template_name = (
            self.template_name_combo.currentData()
            or self.template_name_combo.currentText()
            or None
        )
        self.selected_template_region_id = None

        self.refresh_region_combo()
        self.load_selected_region_to_editor()
        self._update_template_preview()

    def _on_region_changed(self, *_: Any) -> None:
        self.selected_template_region_id = (
            self.region_combo.currentData()
            or self.region_combo.currentText()
            or None
        )

        self.load_selected_region_to_editor()
        self._update_template_preview()

    def load_selected_region_to_editor(self) -> None:
        row = self.selected_template_row()

        if row is None:
            return

        idx = self.type_combo.findText(str(row.get("type", "text_block")))
        if idx >= 0:
            self.type_combo.setCurrentIndex(idx)

        self.label_edit.setText(str(row.get("label", "")))
        self.content_source_edit.setText(str(row.get("content_source", "")))

        self.x_spin.setValue(float(row.get("x", 0.0)))
        self.y_spin.setValue(float(row.get("y", 0.0)))
        self.w_spin.setValue(float(row.get("w", 0.1)))
        self.h_spin.setValue(float(row.get("h", 0.1)))

        self.min_rows_spin.setValue(int(row.get("min_rows") or 0))
        self.max_rows_spin.setValue(int(row.get("max_rows") or 0))
        self.cols_spin.setValue(int(row.get("cols") or 0))

        self.required_check.setChecked(bool(row.get("required", False)))
        self.jitter_spin.setValue(float(row.get("jitter", 0.01)))

    def apply_editor_to_selected_region(self) -> None:
        row = self.selected_template_row()

        if row is None:
            return

        row["type"] = self.type_combo.currentText() or "text_block"
        row["label"] = self.label_edit.text().strip() or str(row.get("region_id", "region"))
        row["content_source"] = self.content_source_edit.text().strip()

        x = max(0.0, min(1.0, float(self.x_spin.value())))
        y = max(0.0, min(1.0, float(self.y_spin.value())))
        w = max(0.01, min(1.0 - x, float(self.w_spin.value())))
        h = max(0.01, min(1.0 - y, float(self.h_spin.value())))

        row["x"], row["y"], row["w"], row["h"] = x, y, w, h
        row["min_rows"] = int(self.min_rows_spin.value())
        row["max_rows"] = int(self.max_rows_spin.value())
        row["cols"] = int(self.cols_spin.value())
        row["required"] = bool(self.required_check.isChecked())
        row["jitter"] = max(0.0, min(0.20, float(self.jitter_spin.value())))

        self.refresh_region_combo()
        self._update_template_preview()

    def template_output_path(self) -> Path:
        out_root = str(self.output_root_getter() or "").strip()
        base = Path(out_root) if out_root else (_PROJECT_ROOT / "out" / "desktop_gui")
        return base / "template_regions.csv"

    @staticmethod
    def _strip_excel_sep_line(text: str) -> str:
        lines = str(text or "").splitlines()

        if lines and lines[0].strip().lower().startswith("sep="):
            return "\n".join(lines[1:])

        return str(text or "")

    def _make_csv_reader(self, text: str) -> csv.DictReader:
        clean_text = self._strip_excel_sep_line(text)
        sample = clean_text[:4096]

        try:
            dialect = csv.Sniffer().sniff(sample, delimiters=";,\t")
        except Exception:
            dialect = csv.excel
            dialect.delimiter = CSV_EXPORT_DELIMITER

        return csv.DictReader(io.StringIO(clean_text), dialect=dialect)

    def load_sample_template_rows(self) -> None:
        self.template_rows = [
            self._coerce_template_row(dict(row))
            for row in SAMPLE_TEMPLATE_ROWS
        ]

        names = self.available_template_names()
        self.active_template_name = names[0] if names else None

        active_rows = self.active_template_rows()
        self.selected_template_region_id = (
            str(active_rows[0].get("region_id"))
            if active_rows
            else None
        )

        self.refresh_template_name_combo()
        self.refresh_region_combo()
        self.load_selected_region_to_editor()
        self._update_template_preview()

    def import_template_csv(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Import Template CSV",
            str(_PROJECT_ROOT),
            "CSV Files (*.csv);;All Files (*)",
        )

        if not path:
            return

        try:
            text = Path(path).read_text(encoding="utf-8-sig", errors="replace")
            reader = self._make_csv_reader(text)

            rows = [
                self._coerce_template_row(dict(row))
                for row in reader
            ]

            if not rows:
                QMessageBox.warning(self, "Template CSV", "Template CSV is empty.")
                return

            self.template_rows = rows

            names = self.available_template_names()
            self.active_template_name = names[0] if names else None

            active_rows = self.active_template_rows()
            self.selected_template_region_id = (
                str(active_rows[0].get("region_id"))
                if active_rows
                else None
            )

            self.refresh_template_name_combo()
            self.refresh_region_combo()
            self.load_selected_region_to_editor()
            self._update_template_preview()

            QMessageBox.information(
                self,
                "Template CSV loaded",
                f"Loaded {len(self.template_rows)} region(s) from:\n{path}",
            )

        except Exception as e:
            QMessageBox.critical(self, "Template CSV load failed", repr(e))

    def export_template_csv(self) -> None:
        try:
            path = self.template_output_path()
            path.parent.mkdir(parents=True, exist_ok=True)

            rows = self.template_rows if self.template_rows else [
                self._coerce_template_row(dict(row))
                for row in SAMPLE_TEMPLATE_ROWS
            ]

            with path.open("w", newline="", encoding="utf-8-sig") as f:
                f.write(f"sep={CSV_EXPORT_DELIMITER}\n")

                writer = csv.DictWriter(
                    f,
                    fieldnames=TEMPLATE_COLUMNS,
                    delimiter=CSV_EXPORT_DELIMITER,
                )
                writer.writeheader()

                for row in rows:
                    writer.writerow({col: row.get(col, "") for col in TEMPLATE_COLUMNS})

            QMessageBox.information(self, "Template CSV saved", f"Saved:\n{path}")

        except Exception as e:
            QMessageBox.critical(self, "Template CSV export failed", repr(e))

    def open_template_csv(self) -> None:
        path = self.template_output_path()

        if not path.exists():
            QMessageBox.warning(
                self,
                "Template CSV",
                "Template CSV not found. Export it first.",
            )
            return

        self._open_path(str(path))

    def _template_preview_svg(self, width: int = 390, height: int = 520) -> str:
        selected_id = self.selected_template_region_id or ""

        page_x, page_y = 22, 22
        page_w, page_h = width - 44, height - 44

        palette = {
            "table": ("#eff6ff", "#2563eb"),
            "field": ("#fef3c7", "#d97706"),
            "text_block": ("#f3f4f6", "#6b7280"),
            "paragraph": ("#f3f4f6", "#6b7280"),
            "header": ("#ecfeff", "#0891b2"),
            "footer": ("#ecfeff", "#0891b2"),
            "math_block": ("#fff7ed", "#f97316"),
            "signature": ("#fdf2f8", "#db2777"),
            "checkbox": ("#f0fdf4", "#16a34a"),
            "checkbox_group": ("#f0fdf4", "#16a34a"),
            "figure": ("#f5f3ff", "#7c3aed"),
        }

        parts = [f"""
        <svg width="{width}" height="{height}" viewBox="0 0 {width} {height}"
             xmlns="http://www.w3.org/2000/svg">
          <rect x="0" y="0" width="{width}" height="{height}" rx="22" fill="#111827"/>
          <rect x="22" y="22" width="{width-44}" height="{height-44}" rx="14"
                fill="#ffffff" stroke="#d1d5db" stroke-width="2"/>
        """]

        for row in self.active_template_rows():
            rx = page_x + float(row.get("x", 0)) * page_w
            ry = page_y + float(row.get("y", 0)) * page_h
            rw = float(row.get("w", 0.1)) * page_w
            rh = float(row.get("h", 0.1)) * page_h

            rtype = str(row.get("type", "text_block"))
            fill, stroke = palette.get(rtype, ("#f3f4f6", "#6b7280"))

            selected = str(row.get("region_id")) == str(selected_id)
            sw = 4 if selected else 2
            opacity = 0.92 if selected else 0.62
            dash = "" if rtype in {"table", "field", "header"} else ' stroke-dasharray="6 5"'

            parts.append(
                f'<rect x="{rx:.1f}" y="{ry:.1f}" width="{rw:.1f}" height="{rh:.1f}" '
                f'rx="7" fill="{fill}" stroke="{stroke}" stroke-width="{sw}" '
                f'opacity="{opacity}"{dash}/>'
            )

            label = html.escape(str(row.get("label") or row.get("region_id") or "region")[:28])
            parts.append(
                f'<text x="{rx+7:.1f}" y="{ry+18:.1f}" font-size="11" '
                f'fill="#111827">{label}</text>'
            )

            if rtype == "table":
                cols = int(row.get("cols") or 4) if str(row.get("cols") or "").strip() else 4
                rows_n = int(row.get("max_rows") or 4) if str(row.get("max_rows") or "").strip() else 4

                cols = max(2, min(cols, 8))
                rows_n = max(2, min(rows_n, 8))

                for k in range(1, cols):
                    x = rx + k * rw / cols
                    parts.append(
                        f'<line x1="{x:.1f}" y1="{ry:.1f}" x2="{x:.1f}" y2="{ry+rh:.1f}" '
                        f'stroke="{stroke}" stroke-width="1" opacity="0.45"/>'
                    )

                for k in range(1, rows_n):
                    y = ry + k * rh / rows_n
                    parts.append(
                        f'<line x1="{rx:.1f}" y1="{y:.1f}" x2="{rx+rw:.1f}" y2="{y:.1f}" '
                        f'stroke="{stroke}" stroke-width="1" opacity="0.45"/>'
                    )

        parts.append("</svg>")
        return "".join(parts)

    def _update_template_preview(self) -> None:
        svg = self._template_preview_svg()
        self.preview_svg.load(QByteArray(svg.encode("utf-8")))

        active_rows = self.active_template_rows()
        active_name = self.get_active_template_name() or "-"

        self.status_label.setText(
            f"Templates loaded: {len(self.available_template_names())} · "
            f"Active: {active_name} · "
            f"Active regions: {len(active_rows)} · "
            f"Total regions: {len(self.template_rows)}"
        )

    @staticmethod
    def _open_path(path: str) -> None:
        p = str(Path(path))

        if sys.platform.startswith("win"):
            os.startfile(p)  # type: ignore[attr-defined]
            return

        import subprocess

        if sys.platform == "darwin":
            subprocess.Popen(["open", p])
        else:
            subprocess.Popen(["xdg-open", p])


class AI1GenGUI(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("AI1 Gen | Desktop GUI")
        self.resize(1520, 960)

        self.orchestrator = RunOrchestrator()
        self.current_run_id: Optional[str] = None
        self.field_widgets: Dict[str, QWidget] = {}
        self.schema_map: Dict[str, Dict[str, Any]] = {
            f["key"]: f for f in self.orchestrator.get_schema_for_ui()
        }
        self.baseline_overrides: Dict[str, Any] = {}

        self._build_ui()
        self._build_menu()
        self._load_schema()
        self._load_baseline_and_user_config()

        self.poll_timer = QTimer(self)
        self.poll_timer.setInterval(1500)
        self.poll_timer.timeout.connect(self._poll_run)

    # ---------------------------------------------------------
    # UI
    # ---------------------------------------------------------
    def _build_ui(self) -> None:
        root = QWidget()
        self.setCentralWidget(root)

        main_layout = QVBoxLayout(root)

        splitter = QSplitter(Qt.Horizontal)
        main_layout.addWidget(splitter)

        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)

        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)

        splitter.addWidget(left_panel)
        splitter.addWidget(right_panel)
        splitter.setSizes([760, 760])

        # Left
        self.run_group = self._build_run_group()
        left_layout.addWidget(self.run_group)

        self.tabs = QTabWidget()
        left_layout.addWidget(self.tabs, 1)

        # Basic tab
        self.basic_tab = QWidget()
        self.basic_layout = QVBoxLayout(self.basic_tab)
        self.basic_layout.setAlignment(Qt.AlignTop)

        self.basic_scroll = QScrollArea()
        self.basic_scroll.setWidgetResizable(True)
        self.basic_scroll_content = QWidget()
        self.basic_scroll_content.setLayout(self.basic_layout)
        self.basic_scroll.setWidget(self.basic_scroll_content)

        # Advanced tab
        self.advanced_tab = QWidget()
        self.advanced_outer_layout = QVBoxLayout(self.advanced_tab)
        self.advanced_outer_layout.setAlignment(Qt.AlignTop)

        self.advanced_manager_group = self._build_advanced_manager_group()
        self.advanced_outer_layout.addWidget(self.advanced_manager_group)

        self.advanced_scroll = QScrollArea()
        self.advanced_scroll.setWidgetResizable(True)

        self.advanced_scroll_content = QWidget()
        self.advanced_layout = QVBoxLayout(self.advanced_scroll_content)
        self.advanced_layout.setAlignment(Qt.AlignTop)
        self.advanced_scroll.setWidget(self.advanced_scroll_content)

        self.advanced_outer_layout.addWidget(self.advanced_scroll, 1)

        self.tabs.addTab(self.basic_scroll, "Basic")
        self.tabs.addTab(self.advanced_tab, "Advanced")

        self.template_tab = TemplateManagerWidget(
            output_root_getter=lambda: self.out_root_edit.text().strip(),
            parent=self,
        )
        self.tabs.addTab(self.template_tab, "Templates")

        # Right
        self.status_group = self._build_status_group()
        self.outputs_group = self._build_outputs_group()
        self.logs_group = self._build_logs_group()

        right_layout.addWidget(self.status_group)
        right_layout.addWidget(self.outputs_group)
        right_layout.addWidget(self.logs_group, 1)

    def _build_menu(self) -> None:
        menu = self.menuBar()

        file_menu = menu.addMenu("File")

        act_open_cfg = QAction("Select Config...", self)
        act_open_cfg.triggered.connect(self._select_config)
        file_menu.addAction(act_open_cfg)

        act_open_out = QAction("Select Output Folder...", self)
        act_open_out.triggered.connect(self._select_out_root)
        file_menu.addAction(act_open_out)

        file_menu.addSeparator()

        act_reload_yaml = QAction("Reload YAML", self)
        act_reload_yaml.triggered.connect(self._reload_from_yaml_files)
        file_menu.addAction(act_reload_yaml)

        act_save_advanced = QAction("Save Advanced", self)
        act_save_advanced.triggered.connect(self._save_advanced_to_user_yaml)
        file_menu.addAction(act_save_advanced)

        act_reset_advanced = QAction("Reset Advanced", self)
        act_reset_advanced.triggered.connect(self._reset_advanced_to_baseline)
        file_menu.addAction(act_reset_advanced)

        file_menu.addSeparator()

        act_quit = QAction("Quit", self)
        act_quit.triggered.connect(self.close)
        file_menu.addAction(act_quit)

    def _build_run_group(self) -> QGroupBox:
        box = QGroupBox("Run")
        layout = QGridLayout(box)

        self.config_path_edit = QLineEdit(str(_DEFAULT_CONFIG.resolve()))
        self.out_root_edit = QLineEdit(str((_PROJECT_ROOT / "out" / "desktop_gui").resolve()))

        self.pages_spin = QSpinBox()
        self.pages_spin.setRange(0, 10_000_000)
        self.pages_spin.setValue(100)

        self.workers_spin = QSpinBox()
        self.workers_spin.setRange(0, 4096)
        self.workers_spin.setValue(4)

        self.seed_spin = QSpinBox()
        self.seed_spin.setRange(-1, 2_147_483_647)
        self.seed_spin.setValue(1337)

        self.smoke_check = QCheckBox("Smoke Test")
        self.smoke_check.setChecked(False)

        self.start_btn = QPushButton("Start Run")
        self.stop_btn = QPushButton("Stop Run")
        self.stop_btn.setEnabled(False)

        self.start_btn.clicked.connect(self._start_run)
        self.stop_btn.clicked.connect(self._stop_run)

        cfg_btn = QPushButton("Browse...")
        cfg_btn.clicked.connect(self._select_config)

        out_btn = QPushButton("Browse...")
        out_btn.clicked.connect(self._select_out_root)

        self.config_path_edit.editingFinished.connect(self._load_baseline_and_user_config)
        self.out_root_edit.editingFinished.connect(self._refresh_effective_yaml_preview)
        self.pages_spin.valueChanged.connect(lambda _: self._refresh_effective_yaml_preview())
        self.workers_spin.valueChanged.connect(lambda _: self._refresh_effective_yaml_preview())
        self.seed_spin.valueChanged.connect(lambda _: self._refresh_effective_yaml_preview())
        self.smoke_check.stateChanged.connect(lambda _: self._refresh_effective_yaml_preview())

        layout.addWidget(QLabel("Config Path"), 0, 0)
        layout.addWidget(self.config_path_edit, 0, 1)
        layout.addWidget(cfg_btn, 0, 2)

        layout.addWidget(QLabel("Output Root"), 1, 0)
        layout.addWidget(self.out_root_edit, 1, 1)
        layout.addWidget(out_btn, 1, 2)

        layout.addWidget(QLabel("Pages"), 2, 0)
        layout.addWidget(self.pages_spin, 2, 1)

        layout.addWidget(QLabel("Workers"), 3, 0)
        layout.addWidget(self.workers_spin, 3, 1)

        layout.addWidget(QLabel("Seed"), 4, 0)
        layout.addWidget(self.seed_spin, 4, 1)

        layout.addWidget(self.smoke_check, 5, 1)

        btn_row = QHBoxLayout()
        btn_row.addWidget(self.start_btn)
        btn_row.addWidget(self.stop_btn)
        layout.addLayout(btn_row, 6, 0, 1, 3)

        return box

    def _build_advanced_manager_group(self) -> QGroupBox:
        box = QGroupBox("Advanced Config Manager")
        layout = QVBoxLayout(box)

        self.user_yaml_path_label = QLabel("-")
        self.user_yaml_path_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        layout.addWidget(self.user_yaml_path_label)

        btn_row = QHBoxLayout()
        self.reload_yaml_btn = QPushButton("Reload YAML")
        self.save_advanced_btn = QPushButton("Save Advanced")
        self.reset_advanced_btn = QPushButton("Reset Advanced")

        self.reload_yaml_btn.clicked.connect(self._reload_from_yaml_files)
        self.save_advanced_btn.clicked.connect(self._save_advanced_to_user_yaml)
        self.reset_advanced_btn.clicked.connect(self._reset_advanced_to_baseline)

        btn_row.addWidget(self.reload_yaml_btn)
        btn_row.addWidget(self.save_advanced_btn)
        btn_row.addWidget(self.reset_advanced_btn)
        layout.addLayout(btn_row)

        layout.addWidget(QLabel("Raw YAML Override"))
        self.raw_yaml_override_text = QPlainTextEdit()
        self.raw_yaml_override_text.setPlaceholderText("İstersen geçici raw YAML override yazabilirsin.")
        self.raw_yaml_override_text.textChanged.connect(self._refresh_effective_yaml_preview)
        layout.addWidget(self.raw_yaml_override_text)

        layout.addWidget(QLabel("Effective YAML Preview"))
        self.effective_yaml_preview = QPlainTextEdit()
        self.effective_yaml_preview.setReadOnly(True)
        layout.addWidget(self.effective_yaml_preview)

        return box

    def _build_status_group(self) -> QGroupBox:
        box = QGroupBox("Status")
        layout = QFormLayout(box)

        self.run_id_label = QLabel("-")
        self.state_label = QLabel("idle")
        self.pid_label = QLabel("-")
        self.return_code_label = QLabel("-")
        self.out_root_label = QLabel("-")
        self.progress_label = QLabel("-")

        layout.addRow("Run ID", self.run_id_label)
        layout.addRow("State", self.state_label)
        layout.addRow("PID", self.pid_label)
        layout.addRow("Return Code", self.return_code_label)
        layout.addRow("Output Root", self.out_root_label)
        layout.addRow("Progress", self.progress_label)

        return box

    def _build_outputs_group(self) -> QGroupBox:
        box = QGroupBox("Outputs / Summary")
        layout = QVBoxLayout(box)

        self.summary_text = QTextEdit()
        self.summary_text.setReadOnly(True)
        self.summary_text.setPlaceholderText("qc_summary / run summary burada görünecek.")

        btns = QHBoxLayout()

        self.open_output_btn = QPushButton("Open Output Folder")
        self.open_qc_btn = QPushButton("Open qc_summary.json")
        self.open_runlog_btn = QPushButton("Open run.log")

        self.open_output_btn.clicked.connect(self._open_output_folder)
        self.open_qc_btn.clicked.connect(self._open_qc_summary)
        self.open_runlog_btn.clicked.connect(self._open_run_log)

        btns.addWidget(self.open_output_btn)
        btns.addWidget(self.open_qc_btn)
        btns.addWidget(self.open_runlog_btn)

        layout.addLayout(btns)
        layout.addWidget(self.summary_text)

        return box

    def _build_logs_group(self) -> QGroupBox:
        box = QGroupBox("Logs")
        layout = QVBoxLayout(box)

        log_tabs = QTabWidget()

        self.stdout_text = QPlainTextEdit()
        self.stdout_text.setReadOnly(True)

        self.stderr_text = QPlainTextEdit()
        self.stderr_text.setReadOnly(True)

        log_tabs.addTab(self.stdout_text, "stdout")
        log_tabs.addTab(self.stderr_text, "stderr")

        layout.addWidget(log_tabs)

        return box

    # ---------------------------------------------------------
    # Dynamic schema forms
    # ---------------------------------------------------------
    def _load_schema(self) -> None:
        basic_schema = self.orchestrator.get_schema_for_ui("basic")
        advanced_schema = self.orchestrator.get_schema_for_ui("advanced")

        self._populate_form_area(self.basic_layout, basic_schema)
        self._populate_form_area(self.advanced_layout, advanced_schema)

    def _populate_form_area(self, parent_layout: QVBoxLayout, schema: List[Dict[str, Any]]) -> None:
        groups: Dict[str, List[Dict[str, Any]]] = {}
        for field in schema:
            groups.setdefault(field.get("group", "Other"), []).append(field)

        for group_name, fields in groups.items():
            group_box = QGroupBox(group_name)
            form = QFormLayout(group_box)

            for field in fields:
                widget = self._make_widget_for_field(field)
                self.field_widgets[field["key"]] = widget
                label = field.get("label", field["key"])
                help_text = field.get("help_text", "")
                if help_text:
                    widget.setToolTip(help_text)
                form.addRow(label, widget)

            parent_layout.addWidget(group_box)

        parent_layout.addStretch(1)

    def _make_widget_for_field(self, field: Dict[str, Any]) -> QWidget:
        field_type = field.get("field_type", "str")
        default = field.get("default", None)
        choices = field.get("choices", []) or []

        if field_type == "bool":
            w = QCheckBox()
            w.setChecked(bool(default))
            w.stateChanged.connect(lambda _: self._refresh_effective_yaml_preview())
            return w

        if field_type == "enum":
            w = QComboBox()
            for ch in choices:
                w.addItem(str(ch), ch)
            if default is not None:
                idx = w.findText(str(default))
                if idx >= 0:
                    w.setCurrentIndex(idx)
            w.currentIndexChanged.connect(lambda _: self._refresh_effective_yaml_preview())
            return w

        if field_type == "int":
            w = QSpinBox()
            w.setRange(
                int(field.get("minimum", -2_147_483_648) if field.get("minimum") is not None else -2_147_483_648),
                int(field.get("maximum", 2_147_483_647) if field.get("maximum") is not None else 2_147_483_647),
            )
            if default is not None:
                try:
                    w.setValue(int(default))
                except Exception:
                    pass
            w.valueChanged.connect(lambda _: self._refresh_effective_yaml_preview())
            return w

        if field_type == "float":
            w = QDoubleSpinBox()
            w.setDecimals(6)
            w.setRange(
                float(field.get("minimum", -1e12) if field.get("minimum") is not None else -1e12),
                float(field.get("maximum", 1e12) if field.get("maximum") is not None else 1e12),
            )
            step = field.get("step", None)
            if step is not None:
                w.setSingleStep(float(step))
            if default is not None:
                try:
                    w.setValue(float(default))
                except Exception:
                    pass
            w.valueChanged.connect(lambda _: self._refresh_effective_yaml_preview())
            return w

        # path / str / json / color_rgb
        w = QLineEdit()
        if default is not None:
            if field_type in {"json", "color_rgb"}:
                w.setText(json.dumps(default, ensure_ascii=False))
            else:
                w.setText(str(default))
        w.editingFinished.connect(self._refresh_effective_yaml_preview)
        return w

    def _read_widget_value(self, field_key: str, widget: QWidget) -> Any:
        field = self.schema_map.get(field_key, {})
        field_type = field.get("field_type", "str")

        if isinstance(widget, QCheckBox):
            return widget.isChecked()

        if isinstance(widget, QComboBox):
            return widget.currentData() if widget.currentData() is not None else widget.currentText()

        if isinstance(widget, QSpinBox):
            return int(widget.value())

        if isinstance(widget, QDoubleSpinBox):
            return float(widget.value())

        if isinstance(widget, QLineEdit):
            txt = widget.text().strip()
            if field_type in {"json", "color_rgb"}:
                return _safe_json_loads(txt, txt)
            return txt

        return None

    def _collect_overrides(self) -> Dict[str, Any]:
        out: Dict[str, Any] = {}
        for key, widget in self.field_widgets.items():
            value = self._read_widget_value(key, widget)
            field = self.schema_map.get(key, {})
            field_type = field.get("field_type", "str")

            if field_type == "json" and value == {}:
                continue
            if field_type == "path" and str(value or "").strip() == "":
                continue
            if field_type == "str" and str(value or "").strip() == "":
                continue

            out[key] = value
        return out

    def _nested_from_flat_overrides(self, flat: Dict[str, Any]) -> Dict[str, Any]:
        out: Dict[str, Any] = {}
        for key, value in flat.items():
            cur = out
            parts = key.split(".")
            for part in parts[:-1]:
                nxt = cur.get(part)
                if not isinstance(nxt, dict):
                    nxt = {}
                    cur[part] = nxt
                cur = nxt
            cur[parts[-1]] = value
        return out

    def _lookup_nested_value(self, d: Dict[str, Any], path: str, default: Any = None) -> Any:
        cur: Any = d
        for part in path.split("."):
            if not isinstance(cur, dict) or part not in cur:
                return default
            cur = cur[part]
        return cur

    def _load_form_from_override_map(self, override_map: Dict[str, Any]) -> None:
        for key, widget in self.field_widgets.items():
            value = override_map.get(key, self.schema_map.get(key, {}).get("default"))
            field_type = self.schema_map.get(key, {}).get("field_type", "str")

            try:
                if isinstance(widget, QCheckBox):
                    widget.setChecked(bool(value))
                elif isinstance(widget, QComboBox):
                    idx = widget.findText(str(value))
                    if idx >= 0:
                        widget.setCurrentIndex(idx)
                elif isinstance(widget, QSpinBox):
                    widget.setValue(int(value if value is not None else 0))
                elif isinstance(widget, QDoubleSpinBox):
                    widget.setValue(float(value if value is not None else 0.0))
                elif isinstance(widget, QLineEdit):
                    if field_type in {"json", "color_rgb"}:
                        widget.setText(json.dumps(value if value is not None else {}, ensure_ascii=False))
                    else:
                        widget.setText("" if value is None else str(value))
            except Exception:
                pass

    # ---------------------------------------------------------
    # YAML manager
    # ---------------------------------------------------------
    def _build_current_effective_yaml(self) -> str:
        config_path = self.config_path_edit.text().strip()
        out_root = self.out_root_edit.text().strip()
        raw_yaml_text = self.raw_yaml_override_text.toPlainText()

        return self.orchestrator.build_effective_config_yaml_text(
            config_path=config_path,
            overrides=self._collect_overrides(),
            raw_yaml_override_text=raw_yaml_text,
            out_root=out_root,
            pages=int(self.pages_spin.value()),
            workers=int(self.workers_spin.value()),
            seed=int(self.seed_spin.value()),
            smoke_test=bool(self.smoke_check.isChecked()),
        )

    def _refresh_effective_yaml_preview(self) -> None:
        try:
            self.effective_yaml_preview.setPlainText(self._build_current_effective_yaml())
        except Exception as e:
            self.effective_yaml_preview.setPlainText(f"# preview error\n{e}")

    def _load_baseline_and_user_config(self) -> None:
        config_path = self.config_path_edit.text().strip()
        self.baseline_overrides = self.orchestrator.build_baseline_override_map(
            config_path,
            visibility="advanced",
        )

        merged_cfg = self.orchestrator.build_config_with_user_override(
            config_path=config_path,
            overrides=None,
            raw_yaml_override_text=None,
        )

        current_map = dict(self.baseline_overrides)
        for key in current_map.keys():
            current_map[key] = self._lookup_nested_value(
                merged_cfg,
                key,
                self.baseline_overrides.get(key),
            )

        self._load_form_from_override_map(current_map)
        self.raw_yaml_override_text.setPlainText("")
        self.user_yaml_path_label.setText(str(self.orchestrator.get_user_config_path(config_path)))
        self._refresh_effective_yaml_preview()

    def _save_advanced_to_user_yaml(self) -> None:
        try:
            config_path = self.config_path_edit.text().strip()
            nested = self._nested_from_flat_overrides(self._collect_overrides())

            raw_yaml_text = self.raw_yaml_override_text.toPlainText().strip()
            if raw_yaml_text:
                raw_dict = self.orchestrator.parse_raw_yaml_override(raw_yaml_text)
                nested = self.orchestrator.merge_raw_yaml_override(
                    nested,
                    yaml.safe_dump(raw_dict, sort_keys=False, allow_unicode=True),
                )

            saved_path = self.orchestrator.save_user_override_dict(config_path, nested)
            self.user_yaml_path_label.setText(str(saved_path))
            self._refresh_effective_yaml_preview()

            QMessageBox.information(self, "Saved", f"Saved:\n{saved_path}")
        except Exception as e:
            QMessageBox.critical(self, "Save failed", repr(e))

    def _reset_advanced_to_baseline(self) -> None:
        try:
            config_path = self.config_path_edit.text().strip()
            self.orchestrator.reset_user_override_dict(config_path)

            self.baseline_overrides = self.orchestrator.build_baseline_override_map(
                config_path,
                visibility="advanced",
            )
            self._load_form_from_override_map(self.baseline_overrides)
            self.raw_yaml_override_text.setPlainText("")
            self.user_yaml_path_label.setText(str(self.orchestrator.get_user_config_path(config_path)))
            self._refresh_effective_yaml_preview()

            QMessageBox.information(self, "Reset", "Advanced settings reset to baseline.")
        except Exception as e:
            QMessageBox.critical(self, "Reset failed", repr(e))

    def _reload_from_yaml_files(self) -> None:
        try:
            self._load_baseline_and_user_config()
            QMessageBox.information(self, "Reloaded", "Reloaded from default.yaml + default.user.yaml")
        except Exception as e:
            QMessageBox.critical(self, "Reload failed", repr(e))

    # ---------------------------------------------------------
    # File selectors
    # ---------------------------------------------------------
    def _select_config(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Select config",
            self.config_path_edit.text().strip() or ".",
            "YAML Files (*.yaml *.yml);;All Files (*)",
        )
        if path:
            self.config_path_edit.setText(path)
            self._load_baseline_and_user_config()

    def _select_out_root(self) -> None:
        path = QFileDialog.getExistingDirectory(
            self,
            "Select output folder",
            self.out_root_edit.text().strip() or ".",
        )
        if path:
            self.out_root_edit.setText(path)
            self._refresh_effective_yaml_preview()

    # ---------------------------------------------------------
    # Run actions
    # ---------------------------------------------------------
    def _start_run(self) -> None:
        try:
            req = RunRequest(
                config_path=self.config_path_edit.text().strip(),
                out_root=self.out_root_edit.text().strip(),
                pages=int(self.pages_spin.value()),
                workers=int(self.workers_spin.value()),
                seed=int(self.seed_spin.value()),
                smoke_test=bool(self.smoke_check.isChecked()),
                overrides=self._collect_overrides(),
            )

            run_id = self.orchestrator.start(req)
            self.current_run_id = run_id

            self.run_id_label.setText(run_id)
            self.state_label.setText("running")
            self.progress_label.setText("started")
            self.stdout_text.clear()
            self.stderr_text.clear()
            self.summary_text.clear()

            self.start_btn.setEnabled(False)
            self.stop_btn.setEnabled(True)

            self.poll_timer.start()

        except Exception as e:
            QMessageBox.critical(self, "Run start failed", repr(e))

    def _stop_run(self) -> None:
        if not self.current_run_id:
            return
        ok = self.orchestrator.cancel(self.current_run_id)
        if ok:
            self.state_label.setText("cancelled")
            self.stop_btn.setEnabled(False)
            self.start_btn.setEnabled(True)

    def _poll_run(self) -> None:
        if not self.current_run_id:
            return

        try:
            status = self.orchestrator.get_status(self.current_run_id)
            summary = self.orchestrator.get_summary(self.current_run_id)

            self.state_label.setText(status.state)
            self.pid_label.setText(str(status.pid) if status.pid is not None else "-")
            self.return_code_label.setText(str(status.return_code) if status.return_code is not None else "-")
            self.out_root_label.setText(status.out_root or "-")

            if status.progress is not None:
                self.progress_label.setText(status.progress.state)
            else:
                self.progress_label.setText("-")

            self.summary_text.setPlainText(json.dumps(summary.to_dict(), ensure_ascii=False, indent=2))

            if status.stdout_log:
                self.stdout_text.setPlainText(tail_text(status.stdout_log, 12000))
                self.stdout_text.verticalScrollBar().setValue(self.stdout_text.verticalScrollBar().maximum())

            if status.stderr_log:
                self.stderr_text.setPlainText(tail_text(status.stderr_log, 12000))
                self.stderr_text.verticalScrollBar().setValue(self.stderr_text.verticalScrollBar().maximum())

            if status.state in {"done", "failed", "cancelled"}:
                self.poll_timer.stop()
                self.start_btn.setEnabled(True)
                self.stop_btn.setEnabled(False)

        except Exception as e:
            self.poll_timer.stop()
            QMessageBox.warning(self, "Polling error", repr(e))

    # ---------------------------------------------------------
    # Output openers
    # ---------------------------------------------------------
    def _open_output_folder(self) -> None:
        if not self.current_run_id:
            return
        try:
            summary = self.orchestrator.get_summary(self.current_run_id)
            if summary.out_root:
                self._open_path(summary.out_root)
        except Exception as e:
            QMessageBox.warning(self, "Open output failed", repr(e))

    def _open_qc_summary(self) -> None:
        if not self.current_run_id:
            return
        try:
            summary = self.orchestrator.get_summary(self.current_run_id)
            if summary.qc_summary_path:
                self._open_path(summary.qc_summary_path)
        except Exception as e:
            QMessageBox.warning(self, "Open qc_summary failed", repr(e))

    def _open_run_log(self) -> None:
        if not self.current_run_id:
            return
        try:
            summary = self.orchestrator.get_summary(self.current_run_id)
            if summary.run_log_path:
                self._open_path(summary.run_log_path)
        except Exception as e:
            QMessageBox.warning(self, "Open run.log failed", repr(e))

    def _open_path(self, path: str) -> None:
        p = str(Path(path))
        if sys.platform.startswith("win"):
            os.startfile(p)  # type: ignore[attr-defined]
        elif sys.platform == "darwin":
            import subprocess
            subprocess.Popen(["open", p])
        else:
            import subprocess
            subprocess.Popen(["xdg-open", p])


def launch_gui() -> int:
    app = QApplication.instance()
    owns_app = app is None
    if app is None:
        app = QApplication(sys.argv)

    win = AI1GenGUI()
    win.show()

    if owns_app:
        return app.exec()
    return 0


if __name__ == "__main__":
    raise SystemExit(launch_gui())