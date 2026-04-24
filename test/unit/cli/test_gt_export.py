from ai1_gen.cli import _build_gt_export


def test_build_gt_export_keeps_line_text_and_meta(ann_minimal_dict):
    gt = _build_gt_export(ann_minimal_dict)

    assert gt["page_id"] == ann_minimal_dict["page_id"]
    assert gt["size"]["w"] == 200
    assert gt["meta"]["has_equation"] is False
    assert gt["lines"][0]["text"] == "Hello world"
    assert gt["lines"][0]["script"] == "latin"
    assert gt["page_text"] == "Hello world"


def test_build_gt_export_reconstructs_page_text_when_missing(ann_minimal_dict):
    ann_minimal_dict["gt_page_text"] = ""
    ann_minimal_dict["lines"].append(
        {
            "line_id": 1,
            "block_id": 0,
            "line_type": "text",
            "line_order_in_block": 1,
            "global_line_order": 1,
            "bbox": [10, 40, 60, 20],
            "gt_text": "Second line",
            "gt_script": "latin",
        }
    )

    gt = _build_gt_export(ann_minimal_dict)

    assert gt["page_text"] == "Hello world\nSecond line"


def test_build_gt_export_keeps_latex_field(ann_math_dict):
    gt = _build_gt_export(ann_math_dict)

    assert gt["lines"][0]["line_type"] == "math"
    assert gt["lines"][0]["latex"] == r"x^2 + y^2 = z^2"
    assert gt["meta"]["has_equation"] is True