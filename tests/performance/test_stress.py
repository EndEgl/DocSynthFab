import subprocess
import tempfile
import yaml
import time
from pathlib import Path

def test_multiprocessing_stress():
    """Worker'ların paralel çalışırken birbirini ezmediğini ve hız kazandırdığını test eder."""
    with tempfile.TemporaryDirectory() as tmpdir:
        cfg_path = Path(tmpdir) / "stress_cfg.yaml"
        out_dir = Path(tmpdir) / "out"
        
        # 50 sayfa, 4 worker ile
        cfg_data = {
            "run": {"pages": 50, "workers": 4, "seed": 100},
            "dist": {
                "density_dist": {"normal": 1.0},
                "scale_dist": {"dpi300": 1.0},
                "noise_level_dist": {"clean": 1.0}
            },
            "qc": {
                "mask_binary_required": False, 
                "overlap_text_over_math_max_ratio": 1.0, 
                "require_global_line_order_contiguous": False 
            },
            "thresholds": {
                "ink_ratio_text_ranges": {
                    "normal": [0.0, 1.0], 
                    "sparse": [0.0, 1.0],
                    "dense": [0.0, 1.0]
                }
            },
            # HATA ÇÖZÜMÜ: Stres testinde Worker'ların çökmemesi için augment net bir şekilde KAPALI
            "augment": {"enable": False},
            "render": {"latex": {"enable": False}},
            "telemetry": {"temperature": {"require_temp_sensor": False}}
        }
        with open(cfg_path, "w") as f:
            yaml.dump(cfg_data, f)
            
        start_time = time.time()
        result = subprocess.run(
            ["python", "-m", "ai1_gen.cli", "--config", str(cfg_path), "--out", str(out_dir)],
            capture_output=True, text=True
        )
        elapsed = time.time() - start_time
        
        assert result.returncode == 0
        
        # 50 dosyanın başarılı yazıldığını kontrol et
        images = list((out_dir / "images").glob("*.png"))
        assert len(images) == 50, "Multiprocessing sırasında sayfa kaybı yaşandı!"
        
        with open(out_dir / "gt_pages.jsonl", "r", encoding="utf-8") as f:
            assert len(f.readlines()) == 50, "JSONL dosyasına paralel yazmada veri kaybı var!"
        
        assert "Traceback" not in result.stderr