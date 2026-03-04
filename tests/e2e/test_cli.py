import subprocess
import tempfile
import yaml
import re
import json
from pathlib import Path

def test_cli_execution_and_telemetry_output():
    with tempfile.TemporaryDirectory() as tmpdir:
        out_dir = Path(tmpdir) / "output"
        cfg_path = Path(tmpdir) / "test_config.yaml"
        
        # Test için "gerçekçi" eşiklere sahip config (Fanus kırıldı)
        cfg_data = {
            "project": {"version": "ai1-ds-v1.3.2"},
            "io": {"out_root": str(out_dir), "tmp_dir": "_tmp"},
            "run": {"pages": 2, "seed": 42, "workers": 1},
            "dist": {
                "density_dist": {"normal": 1.0},
                "scale_dist": {"dpi300": 1.0},
                "noise_level_dist": {"clean": 1.0}
            },
            "qc": {
                "mask_binary_required": True,
                "overlap_text_over_math_max_ratio": 0.01, # Gerçekçi eşik: %1 çakışma limiti
                "require_global_line_order_contiguous": True
            },
            "thresholds": {
                "ink_ratio_text_ranges": {
                    "normal": [0.01, 0.50], # %1 ile %50 arası (sıkı ve gerçekçi)
                    "sparse": [0.001, 0.05],
                    "dense": [0.05, 0.80]
                }
            },
            "telemetry": {
                "mode": "single_line",
                "temperature": {"require_temp_sensor": False},
                "update_interval_s": 0.0
            }
        }
        
        with open(cfg_path, "w", encoding="utf-8") as f:
            yaml.dump(cfg_data, f)
            
        # CLI'ı subprocess ile çağır
        cmd = ["python", "-m", "ai1_gen.cli", "--config", str(cfg_path)]
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        assert result.returncode == 0, f"CLI Error: {result.stderr}"
        
        # Klasörler oluştu mu?
        assert (out_dir / "images").exists()
        assert (out_dir / "ann").exists()
        assert (out_dir / "gt").exists() 
        assert (out_dir / "qc_summary.json").exists()
        assert (out_dir / "run.log").exists()

        # Stdout format Regex kontrolü
        pattern = re.compile(r"\[\d{2}:\d{2}:\d{2}\] pages \d+/\d+ \(\s*\d+\.\d+%\) \| ok \d+ fail \d+ \| eta \d{2}:\d{2}:\d{2} \| temp gpu=.* cpu=.*")
        assert pattern.search(result.stdout) is not None, "CLI çıktısı sözleşme formatına uymuyor!"
        
        # --- KONSOL ÇIKTISI (GEÇİCİ DOSYAYI SİLİNMEDEN OKUMAK İÇİN) ---
        print("\n" + "="*50)
        print("🚀 CLI ÇALIŞTIRMA SONUCU (STDOUT):")
        print(result.stdout.strip())
        print("-" * 50)
        
        # --- QC KONTROLÜ VE EKRANA YAZDIRMA ---
        with open(out_dir / "qc_summary.json", "r", encoding="utf-8") as f:
            qc_data = json.load(f)
            
        print("\n🛑 QC SUMMARY:")
        print(json.dumps(qc_data, indent=2))
        
        total_processed = qc_data.get("ok", 0) + qc_data.get("fail", 0)
        assert total_processed == 2, f"Toplam 2 sayfa işlenmeliydi, ancak {total_processed} sayfa işlendi."

        # --- HATA LOGLARI ---
        failed_log = out_dir / "failed_pages.log"
        if failed_log.exists():
            print("\n❌ REDDEDİLEN SAYFALAR (failed_pages.log):")
            with open(failed_log, "r", encoding="utf-8") as f:
                print(f.read())
                
        print("\n📜 RUN.LOG İÇERİĞİ:")
        with open(out_dir / "run.log", "r", encoding="utf-8") as f:
            print(f.read())

        # --- GT_PAGES KONTROLÜ ---
        gt_jsonl = out_dir / "gt_pages.jsonl"
        print("📂 ÜRETİLEN GT_PAGES.JSONL İÇERİĞİ:")
        if gt_jsonl.exists():
            with open(gt_jsonl, "r", encoding="utf-8") as f:
                jsonl_lines = f.readlines()
                for line in jsonl_lines:
                    print(line.strip())
            # JSONL'ye sadece QC'den başarıyla geçen sayfalar yazılmalı
            assert len(jsonl_lines) == qc_data.get("ok", 0), "gt_pages.jsonl başarılı sayfa sayısıyla eşleşmiyor!"
        else:
            # Eğer dosya yoksa, 0 sayfa başarılı olmuş olmalı
            assert qc_data.get("ok", 0) == 0, "Başarılı sayfa var ama gt_pages.jsonl oluşturulmamış!"