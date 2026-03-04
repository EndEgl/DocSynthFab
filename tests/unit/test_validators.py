import numpy as np
from ai1_gen.qc.validators import _is_binary_u8, compute_density_metrics, mixed_band_variance, validate_page

def test_mask_is_binary():
    valid_mask = np.array([[0, 255], [255, 0]], dtype=np.uint8)
    invalid_mask = np.array([[0, 128], [255, 0]], dtype=np.uint8)
    
    assert _is_binary_u8(valid_mask) == True
    assert _is_binary_u8(invalid_mask) == False

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

def test_mixed_density_fails_on_uniform_page(mock_cfg):
    # Sayfa "mixed" (karışık) olarak işaretlenmiş ama her yerinde aynı metin yoğunluğu var
    mask_text = np.zeros((1000, 1000), dtype=np.uint8)
    # Her banda eşit miktarda (seyrek) metin koyalım
    for i in range(8):
        mask_text[i*125 : i*125 + 10, :] = 255
        
    ann = {
        "meta": {"density_level": "mixed"},
        "size": {"dpi": 300},
        "lines": [{"global_line_order": 0}]
    }
    
    # HATA ÇÖZÜMÜ: mask_math'i mask_text ile aynı yaparsak "Overlap" hatasına takılır. 
    # Bu yüzden mask_math'i boş (siyah) veriyoruz.
    mask_math = np.zeros_like(mask_text)
    
    is_valid, err_code, extras = validate_page(ann, mask_text, mask_math, mock_cfg)
    
    assert not is_valid
    assert err_code == "qc/mixed-variance-too-low"