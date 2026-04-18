import pytest
from unittest.mock import patch, MagicMock
from ai1_gen.latex.miktex_render import render_latex_to_rgba
from pathlib import Path

@pytest.mark.fast
@patch("subprocess.run")
@patch("fitz.open")
def test_render_latex_logic_without_miktex(mock_fitz, mock_subrun):
    def side_effect(*args, **kwargs):
        # Koddaki temp klasörünün içinde 'eq.pdf' dosyasını fiziksel olarak oluştur
        cwd = kwargs.get('cwd')
        if cwd:
            Path(cwd, "eq.pdf").write_bytes(b"%PDF-1.4 mock")
        return MagicMock(returncode=0)
    
    mock_subrun.side_effect = side_effect
    
    mock_doc = mock_fitz.return_value
    mock_page = mock_doc.load_page.return_value
    mock_page.get_pixmap.return_value = MagicMock(
        width=100,
        height=50,
        samples=bytes([0, 0, 0, 255]) * (100 * 50)
    )


    from PIL import Image
    res = render_latex_to_rgba("E=mc^2")
    assert isinstance(res, Image.Image)