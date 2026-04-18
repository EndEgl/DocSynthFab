import pytest
import numpy as np
from unittest.mock import patch
from ai1_gen.cli import _make_fallback_render, _worker_generate_validate_save

@pytest.mark.fast
def test_make_fallback_render_validity(mock_cfg):
    """Fallback sayfasının veri yapısını ve içeriğini kontrol eder."""
    page_id = "FALLBACK_001"
    res = _make_fallback_render(mock_cfg, page_id=page_id, dpi=300)
    
    # Görüntü yapısı kontrolü
    assert isinstance(res["image_u8"], np.ndarray)
    assert res["image_u8"].shape == (3507, 2481, 3) # A4 300DPI kontratı
    
    # Maske kontrolü
    assert np.any(res["mask_text_u8"] > 0), "Fallback sayfasında metin maskesi boş olmamalı"
    
    # Meta veri kontrolü
    assert res["ann"]["page_id"] == page_id
    assert res["ann"]["meta"]["_fallback"] is True

@pytest.mark.fast
@patch("ai1_gen.cli.render_page_layers")
@patch("ai1_gen.cli.save_png_u8")
@patch("ai1_gen.cli.save_json")
def test_worker_catches_exception_and_uses_fallback(mock_save_json, mock_save_png, mock_render, mock_cfg, tmp_path):
    """Render sırasında hata oluşursa worker'ın fallback kullanarak hayatta kalmasını test eder."""
    
    # 1. Senaryo: Render fonksiyonu beklenmedik bir hata fırlatıyor
    mock_render.side_effect = Exception("MiKTeX crashed or Disk Full!")
    
    # Test klasör yapısı
    dirs = {
        "images": str(tmp_path / "images"),
        "masks": str(tmp_path / "masks"),
        "ann": str(tmp_path / "ann"),
        "gt": str(tmp_path / "gt"),
        "tmp": str(tmp_path / "tmp")
    }
    
    options = {"max_tries": 1, "fallback_dpi": 300}
    args = (0, "page_0", 42, "dummy_cfg.yaml", dirs, options)
    
    # Worker'ı çalıştır
    # NOT: cli içindeki load_config'i de mock'lamanız gerekebilir veya mevcut mock_cfg'yi paslamalısınız
    with patch("ai1_gen.cli.load_config", return_value=mock_cfg):
        result = _worker_generate_validate_save(args)
    
    # Sonuç Kontrolü
    assert result["ok"] is True, "Hata oluşsa bile fallback sayesinde 'ok' dönmeli"
    assert result["fallback_used"] is True
    assert "MiKTeX crashed" in result["recovered_from"][0]["exc"]