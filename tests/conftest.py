import pytest
from ai1_gen.config import AppConfig

@pytest.fixture
def mock_cfg():
    raw_cfg = {
        "project": {"version": "ai1-ds-v1.3.2"},
        "io": {"out_root": "D:\\ai1_dataset_v1_test", "tmp_dir": "_tmp"},
        "run": {"pages": 5, "seed": 42, "workers": 1},
        "dist": {
            "density_dist": {"sparse": 0.15, "normal": 0.55, "dense": 0.20, "mixed": 0.10},
            "scale_dist": {"dpi300": 0.70, "dpi200": 0.20, "lowres_capture": 0.10},
            "noise_level_dist": {"clean": 0.5, "medium": 0.3, "heavy": 0.2}
        },
        "page": {"dpi_choices": [200, 300], "bg_color_rgb": [255, 255, 255]},
        "layout": {
            "targets": {
                "sparse": {"line_count_range": [5, 15], "block_count_range": [2, 5]},
                "normal": {"line_count_range": [20, 40], "block_count_range": [6, 10]},
                "dense": {"line_count_range": [50, 80], "block_count_range": [10, 15]}
            }
        },
        "qc": {
            "mask_binary_required": True,
            "overlap_text_over_math_max_ratio": 0.01,
            "require_global_line_order_contiguous": True
        },
        # tests/conftest.py içinde thresholds kısmını şununla değiştir:
        "thresholds": {
            "ink_ratio_text_ranges": {
                "sparse": [0.001, 0.05],
                "normal": [0.01, 0.50],  # Üst sınırı %50 yaptık
                "dense": [0.05, 0.80]    # Üst sınırı %80 yaptık
            },
            "mixed": {"bands": 8, "variance_thr": 0.00001}
        },
        
        "augment": {
            "enable": True,
            "min_area_px": 25,
            "selection_policy": {
                "clean": {"p_photometric": 0.4, "p_blur_noise": 0.25, "p_capture": 0.15, "p_geometry": 0.10}
            },
            "photometric": {"gamma": [0.75, 1.25], "brightness": [-20, 20], "contrast": [0.85, 1.20]},
            "blur_noise": {"gaussian_kernel_choices": [3, 5, 7], "speckle": [0.02, 0.10]},
            "capture_sim": {
                "downscale_factor": [0.50, 0.85],
                "jpeg_quality_clean_medium": [40, 90],
                "jpeg_quality_heavy": [25, 70]
            },
            "geometry": {
                "rotation_deg": [-6.0, 6.0],
                "perspective_jitter_ratio": [0.0, 0.03]
            }
        },
        "render": {"latex": {"enable": False}}, 
        "telemetry": {
            "mode": "single_line",
            "temperature": {"require_temp_sensor": False, "prefer_gpu": True}, 
            "update_interval_s": 0.5
        }
    }
    return AppConfig(raw_cfg)