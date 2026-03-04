import random
import json
from ai1_gen.layout.layout_sampler import sample_page_spec
from ai1_gen.render.page_renderer import render_page_layers

def test_full_page_generation_pipeline(mock_cfg):
    rng = random.Random(1337)
    
    # 1. Layout Sampler
    page_spec = sample_page_spec(mock_cfg, rng, 0, "test_000")
    assert page_spec.page_id == "test_000"
    
    orders = [ln.global_line_order for ln in page_spec.lines]
    assert orders == list(range(len(orders))), "Global line order bozuk!"

    # 2. Render Layers
    render_result = render_page_layers(page_spec, mock_cfg, rng)
    
    img = render_result["image_u8"]
    ann = render_result["ann"]
    
    assert img.shape[2] == 3 # RGB format kontratı
    assert render_result["mask_text_u8"].shape == img.shape[:2]
    
    # YENİ: Ground Truth alanlarının kontrolü
    assert "gt_page_text" in ann
    
    # --- KONSOL ÇIKTISI (RAM'DEKİ VERİYİ GÖRMEK İÇİN) ---
    print("\n" + "="*50)
    print(f"📄 RAM'DE ÜRETİLEN SAYFA: {ann['page_id']}")
    print(f"📏 Çözünürlük: {img.shape[1]}x{img.shape[0]} px | DPI: {ann['size']['dpi']}")
    
    
    ink_percent = (render_result['mask_text_u8'] > 0).mean() * 100
    print(f"📊 Metin Yoğunluğu (Ink Ratio): %{ink_percent:.2f}")    
    
    print("-"*50)
    print("📝 ÜRETİLEN SAYFA METNİ (gt_page_text):")
    print(ann["gt_page_text"])
    print("-"*50)
    print("🔍 ÖRNEK SATIR JSON'U (İlk Satır):")
    if ann["lines"]:
        print(json.dumps(ann["lines"][0], indent=2, ensure_ascii=False))
    print("="*50 + "\n")