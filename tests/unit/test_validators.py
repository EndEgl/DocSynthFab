import numpy as np
import pytest
from ai1_gen.qc.validators import _is_binary_u8, compute_density_metrics, mixed_band_variance, validate_page

@pytest.mark.fast
def test_mask_is_binary():
    valid_mask = np.array([[0, 255], [255, 0]], dtype=np.uint8)
    invalid_mask = np.array([[0, 128], [255, 0]], dtype=np.uint8)
    
    assert _is_binary_u8(valid_mask) == True
    assert _is_binary_u8(invalid_mask) == False


@pytest.mark.fast
def test_overlap_validation(mock_cfg):
    # Overlap kontratı: < 1%
    mask_text = np.zeros((100, 100), dtype=np.uint8)
    mask_math = np.zeros((100, 100), dtype=np.uint8)
    
    # 100 piksel text, 2 piksel üst üste biniyor (%2 overlap -> Hata vermeli)
    mask_text[0:10, 0:10] = 255
    mask_math[9:11, 9:11] = 255 
    
    ann = {"meta": {"density_level": "normal"}, "size": {"dpi": 300}, "lines": []}
    
    is_valid, err_code, extras = validate_page(ann, mask_text, mask_math, mock_cfg)
    assert not is_valid
    assert err_code == "qc/overlap-too-high"


@pytest.mark.fast
def test_global_line_order_contiguous(mock_cfg):
    ann = {
        "meta": {"density_level": "normal"}, "size": {"dpi": 300},
        "lines": [
            {"global_line_order": 0},
            {"global_line_order": 2} # Atlanmış index
        ]
    }
    mask = np.zeros((10, 10), dtype=np.uint8)
    is_valid, err_code, _ = validate_page(ann, mask, mask, mock_cfg)
    assert not is_valid
    assert err_code == "qc/order-not-contiguous"


@pytest.mark.fast
def test_mixed_density_fails_on_uniform_page(mock_cfg):
    mask_text = np.zeros((1000, 1000), dtype=np.uint8)
    for i in range(8):
        mask_text[i*125 : i*125 + 10, :] = 255

    ann = {
        "meta": {"density_level": "mixed", "page_family": "report"},
        "size": {"w": 1000, "h": 1000, "dpi": 300},
        "blocks": [
            {"block_type": "title", "bbox": [10, 10, 100, 50], "block_id": 0} # Başlık eklendi
        ],
        "lines": [{"global_line_order": 0, "bbox": [10, 200, 100, 20]}] # Geçerli bbox eklendi
    }
    mask_math = np.zeros_like(mask_text)
    is_valid, err_code, _ = validate_page(ann, mask_text, mask_math, mock_cfg)
    assert not is_valid
    assert err_code == "qc/mixed-variance-too-low"



@pytest.mark.fast
def test_title_too_low_fails(mock_cfg):
    # Sayfa yüksekliği 1000 olsun. Title 300'ün altına (örneğin 500'e) inerse hata vermeli.
    ann = {
        "meta": {"density_level": "normal"},
        "size": {"w": 1000, "h": 1000, "dpi": 300},
        "blocks": [{"block_type": "title", "bbox": [0, 500, 100, 50], "block_id": 0}],
        "lines": []
    }
    mask = np.zeros((1000, 1000), dtype=np.uint8)
    is_valid, err_code, _ = validate_page(ann, mask, mask, mock_cfg)
    assert not is_valid
    assert err_code == "qc/title-too-low"

@pytest.mark.fast
def test_reading_order_backward_jump_fails(mock_cfg):
    ann = {
        "meta": {"density_level": "normal", "page_family": "report"},
        "size": {"w": 1000, "h": 1000, "dpi": 300},
        "blocks": [
            {"block_type": "title", "bbox": [10, 10, 100, 50], "block_id": 0} # Başlık eklendi
        ],
        "lines": [
            {"global_line_order": 0, "bbox": [10, 500, 100, 20]},
            {"global_line_order": 1, "bbox": [10, 100, 100, 20]}
        ]
    }
    mask = np.zeros((1000, 1000), dtype=np.uint8)
    is_valid, err_code, _ = validate_page(ann, mask, mask, mock_cfg)
    assert not is_valid
    assert err_code == "qc/reading-order-suspicious"