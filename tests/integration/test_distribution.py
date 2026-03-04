import pytest
from collections import Counter
import random
from ai1_gen.layout.layout_sampler import sample_page_spec

def test_metadata_distribution_accuracy(mock_cfg):
    """
    Sözleşme Madde 11: 1000 örneklem üzerinden dağılım doğruluğunu RAM'de ölçer.
    Hiçbir dosya SSD'ye kaydedilmez.
    """
    n_samples = 1000
    rng = random.Random(42)
    
    densities = []
    scales = []
    
    # SSD'ye yazmadan sadece meta veri üretimi (RAM'de kalır)
    for i in range(n_samples):
        page_spec = sample_page_spec(mock_cfg, rng, i, f"sim_{i:04d}")
        densities.append(page_spec.density_level)
        scales.append(page_spec.scale_profile)
        
    d_counts = Counter(densities)
    s_counts = Counter(scales)
    
    # Sözleşme hedefleri (conftest içindeki mock_cfg'den alınır)
    target_d = mock_cfg.density_dist()
    target_s = mock_cfg.scale_dist()
    
    # Tolerans: 1000 sayfa için +- 3% (0.03)
    tolerance = 0.03
    
    print(f"\n--- Dağılım Analizi (N={n_samples}) ---")
    
    for level, target_ratio in target_d.items():
        actual_ratio = d_counts[level] / n_samples
        diff = abs(actual_ratio - target_ratio)
        print(f"Density {level:7}: Hedef {target_ratio:.2%}, Gerçek {actual_ratio:.2%}")
        assert diff <= tolerance, f"Density {level} dağılımı bozulmuş! Fark: {diff:.4f}"

    for profile, target_ratio in target_s.items():
        actual_ratio = s_counts[profile] / n_samples
        diff = abs(actual_ratio - target_ratio)
        print(f"Scale {profile:10}: Hedef {target_ratio:.2%}, Gerçek {actual_ratio:.2%}")
        assert diff <= tolerance, f"Scale {profile} dağılımı bozulmuş! Fark: {diff:.4f}"