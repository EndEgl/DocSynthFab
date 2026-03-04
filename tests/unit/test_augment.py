import numpy as np
import random
from ai1_gen.augment.apply_augment import apply_augment

def test_augment_bbox_transformation_integrity():
    # 100x100 beyaz görsel, ortasında 10x10 siyah bir blok (metin varsayalım)
    img = np.full((100, 100, 3), 255, dtype=np.uint8)
    mask = np.zeros((100, 100), dtype=np.uint8)
    mask[45:55, 45:55] = 255 # Tam merkezde 10x10 alan
    
    ann = {
        "lines": [{"line_id": 0, "block_id": 0, "bbox": [45, 45, 10, 10], "global_line_order": 0}],
        "blocks": [{"block_id": 0, "bbox": [45, 45, 10, 10]}]
    }
    
    # HATA ÇÖZÜMÜ: Diğer olasılıkları 0'a çekiyoruz ki test KeyError fırlatmasın
    aug_cfg = {
        "min_area_px": 5,
        "geometry": {"rotation_deg": [90.0, 90.0], "perspective_jitter_ratio": [0, 0]},
        "selection_policy": {
            "clean": {
                "p_geometry": 1.0,
                "p_photometric": 0.0, 
                "p_blur_noise": 0.0, 
                "p_capture": 0.0
            }
        } 
    }
    meta = {"noise_level": "clean", "perspective": False}
    rng = random.Random(42)
    
    res = apply_augment(img, mask, mask, ann, meta, aug_cfg, rng)
    
    # Kontrol 1: Maske gerçekten döndü mü?
    assert np.sum(res.mask_text_aug_u8) > 0
    
    # Kontrol 2: Yeni BBox, döndürülmüş maskeyi kapsıyor mu?
    new_bbox = res.ann_aug["lines"][0]["bbox"]
    x, y, w, h = new_bbox
    crop = res.mask_text_aug_u8[y:y+h, x:x+w]
    assert np.mean(crop > 0) > 0.8, "Dönüşüm sonrası BBox metni ıskalıyor!"