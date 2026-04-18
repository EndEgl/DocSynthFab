# tests/performance/test_benchmark.py
#
# Kapsamlı pytest-benchmark testi — ai1_gen pipeline
#
# Kurulum:
#   pip install pytest pytest-benchmark
#
# Çalıştırma (tüm benchmark'lar):
#   pytest tests/performance/test_benchmark.py -v --benchmark-sort=mean
#
# Sadece hızlı grup:
#   pytest tests/performance/test_benchmark.py -v -m "fast" --benchmark-sort=mean
#
# Sadece yavaş grup (CI'da atlanabilir):
#   pytest tests/performance/test_benchmark.py -v -m "slow" --benchmark-sort=mean
#
# JSON raporu:
#   pytest tests/performance/test_benchmark.py --benchmark-json=benchmark_results.json
#
# Histogram:
#   pytest tests/performance/test_benchmark.py --benchmark-histogram=bench_hist
#
# Sözleşme regresyon karşılaştırması (ilk çalıştırmadan sonra):
#   pytest tests/performance/test_benchmark.py --benchmark-compare
#
# Ortam:
#   PYTHONPATH=src pytest ...

from __future__ import annotations

import random
import io
from typing import Any, Dict

import numpy as np
import pytest

# ---------------------------------------------------------------------------
# Fixture: merkezi AppConfig (disk I/O yok)
# ---------------------------------------------------------------------------

@pytest.fixture(scope="session")
def bench_cfg():
    """
    Tüm benchmark oturumu boyunca tek bir AppConfig nesnesi kullanılır.
    disk I/O ve LaTeX kapalıdır; ölçümler saf CPU / RAM'i temsil eder.
    """
    from ai1_gen.config import AppConfig

    raw: Dict[str, Any] = {
        "project": {"version": "ai1-ds-v1.3.2"},
        "io": {"out_root": "/tmp/bench_out", "tmp_dir": "_tmp"},
        "run": {"pages": 100, "seed": 7, "workers": 1},
        "dist": {
            "density_dist": {
                "sparse": 0.15,
                "normal": 0.55,
                "dense": 0.20,
                "mixed": 0.10,
            },
            "scale_dist": {
                "dpi300": 0.70,
                "dpi200": 0.20,
                "lowres_capture": 0.10,
            },
            "noise_level_dist": {"clean": 0.5, "medium": 0.3, "heavy": 0.2},
        },
        "page": {"dpi_choices": [200, 300], "bg_color_rgb": [255, 255, 255]},
        "layout": {
            "targets": {
                "sparse": {"line_count_range": [5, 15],  "block_count_range": [2, 5]},
                "normal": {"line_count_range": [20, 40], "block_count_range": [6, 10]},
                "dense":  {"line_count_range": [50, 80], "block_count_range": [10, 15]},
                "mixed":  {"line_count_range": [15, 55], "block_count_range": [5, 12]},
            }
        },
        "content": {
            "has_equation_prob": 0.30,
            "has_table_prob":    0.30,
            "has_figure_prob":   0.28,
            "has_caption_prob":  0.35,
            "hard_negative_page_prob": 0.10,
        },
        "qc": {
            "mask_binary_required": True,
            "overlap_text_over_math_max_ratio": 0.01,
            "require_global_line_order_contiguous": True,
            "require_title_near_top": True,
            "require_caption_near_target": True,
            "use_page_family_rules": True,
            "soft_reading_order_check": True,
            "max_block_overlap_ratio_min_area": 0.35,
        },
        "density_thresholds": {
            "ink_ratio_text_ranges": {
                "sparse": [0.001, 0.05],
                "normal": [0.005, 0.50],
                "dense":  [0.03,  0.80],
                "mixed":  [0.005, 0.70],
            },
            "mixed": {"bands": 8, "variance_thr": 0.00001},
        },
        "augment": {
            "enable": True,
            "min_area_px": 25,
            "selection_policy": {
                "clean":  {"p_photometric": 0.4, "p_blur_noise": 0.25, "p_capture": 0.15, "p_geometry": 0.10},
                "medium": {"p_photometric": 0.5, "p_blur_noise": 0.35, "p_capture": 0.25, "p_geometry": 0.15},
                "heavy":  {"p_photometric": 0.6, "p_blur_noise": 0.50, "p_capture": 0.40, "p_geometry": 0.20},
            },
            "photometric": {"gamma": [0.75, 1.25], "brightness": [-20, 20], "contrast": [0.85, 1.20]},
            "blur_noise":  {"gaussian_kernel_choices": [3, 5, 7], "speckle": [0.02, 0.10]},
            "capture_sim": {
                "downscale_factor": [0.50, 0.85],
                "jpeg_quality_clean_medium": [40, 90],
                "jpeg_quality_heavy": [25, 70],
            },
            "geometry": {"rotation_deg": [-6.0, 6.0], "perspective_jitter_ratio": [0.0, 0.03]},
            "edge_degredation": {"prob": 0.70, "num_erasures": [2, 5], "size_ratio": [0.05, 0.15], "protect_math": True},
            "elastic_distortion": {"prob": 0.35, "alpha": [15.0, 25.0], "sigma": [6.0, 10.0]},
        },
        "render": {
            "latex": {"enable": False},           # disk I/O yok → temiz ölçüm
            "text": {
                "fonts_dir": None,                 # sistem fontuna düşer
                "scripts_dist": {
                    "latin": 0.45, "tr": 0.18, "de": 0.07,
                    "ru": 0.10, "el": 0.06, "ar": 0.09, "symbols": 0.05,
                },
            },
            "non_text": {"enable": True, "watermark_prob": 0.06},
        },
        "telemetry": {
            "mode": "multi_line",
            "temperature": {"require_temp_sensor": False, "prefer_gpu": False},
            "update_interval_s": 99.0,
        },
    }
    return AppConfig(raw)


# ---------------------------------------------------------------------------
# Yardımcı üretici fonksiyonlar
# ---------------------------------------------------------------------------

def _make_page_spec(cfg, seed: int = 42, page_id: str = "bench_000"):
    from ai1_gen.layout.layout_sampler import sample_page_spec
    rng = random.Random(seed)
    return sample_page_spec(cfg, rng, 0, page_id)


def _make_render_result(cfg, seed: int = 42):
    from ai1_gen.render.page_renderer import render_page_layers
    ps = _make_page_spec(cfg, seed)
    rng = random.Random(seed)
    return render_page_layers(ps, cfg, rng), ps


def _blank_masks(h: int = 3507, w: int = 2481):
    mt = np.zeros((h, w), dtype=np.uint8)
    mm = np.zeros((h, w), dtype=np.uint8)
    mt[500:700, 300:1800] = 255
    mm[800:900, 400:1200] = 255
    return mt, mm


# ===========================================================================
# 1. LAYOUT SAMPLER benchmarks
# ===========================================================================

@pytest.mark.fast
class TestLayoutSamplerBenchmarks:
    """
    sample_page_spec: saf Python, numpy yok — bu yüzden ns cinsinden ölçülür.
    Beklenen: < 5 ms / çağrı
    """

    def test_sample_page_spec_normal(self, benchmark, bench_cfg):
        """Normal yoğunluk, dpi300 — en sık karşılaşılan durum."""
        rng = random.Random(1)
        benchmark.extra_info["sözleşme_ms_max"] = 5.0
        benchmark.pedantic(
            _make_page_spec,
            args=(bench_cfg,),
            kwargs={"seed": 1, "page_id": "bench_000"},
            rounds=200,
            warmup_rounds=10,
        )

    def test_sample_page_spec_dense(self, benchmark, bench_cfg):
        """Dense yoğunluk — daha fazla satır / blok üretilir, biraz daha yavaş."""
        from ai1_gen.layout.layout_sampler import sample_page_spec

        raw2 = dict(bench_cfg.raw)
        raw2["dist"] = dict(bench_cfg.raw["dist"])
        raw2["dist"]["density_dist"] = {"dense": 1.0}
        from ai1_gen.config import AppConfig
        cfg2 = AppConfig(raw2)

        rng = random.Random(99)
        benchmark.pedantic(
            sample_page_spec,
            args=(cfg2, rng, 0, "bench_dense"),
            rounds=200,
            warmup_rounds=10,
        )

    def test_sample_page_spec_mixed(self, benchmark, bench_cfg):
        """Mixed yoğunluk — varyans hesabı içerir."""
        from ai1_gen.layout.layout_sampler import sample_page_spec

        raw2 = dict(bench_cfg.raw)
        raw2["dist"] = dict(bench_cfg.raw["dist"])
        raw2["dist"]["density_dist"] = {"mixed": 1.0}
        from ai1_gen.config import AppConfig
        cfg2 = AppConfig(raw2)

        rng = random.Random(55)
        benchmark.pedantic(
            sample_page_spec,
            args=(cfg2, rng, 0, "bench_mixed"),
            rounds=200,
            warmup_rounds=10,
        )

    def test_sample_100_pages_throughput(self, benchmark, bench_cfg):
        """
        100 sayfa ardışık üretimi — throughput ölçümü.
        Beklenen toplam: < 400 ms
        """
        from ai1_gen.layout.layout_sampler import sample_page_spec

        def _batch():
            rng = random.Random(777)
            return [sample_page_spec(bench_cfg, rng, i, f"p_{i:04d}") for i in range(100)]

        benchmark.pedantic(_batch, rounds=10, warmup_rounds=2)

    def test_double_col_academic_layout(self, benchmark, bench_cfg):
        """Double-column academic — en yoğun yerleşim mantığı."""
        from ai1_gen.layout.layout_sampler import sample_page_spec
        from ai1_gen.config import AppConfig

        raw2 = dict(bench_cfg.raw)
        raw2["dist"] = dict(bench_cfg.raw["dist"])
        raw2["dist"]["density_dist"] = {"dense": 1.0}
        raw2["layout"] = dict(bench_cfg.raw.get("layout", {}))
        raw2["layout"]["page_family_dist"] = {"academic": 1.0}
        raw2["layout"]["family_layout_type_dist"] = {"academic": {"double_col": 1.0}}
        cfg2 = AppConfig(raw2)

        rng = random.Random(21)
        benchmark.pedantic(
            sample_page_spec,
            args=(cfg2, rng, 0, "bench_academic"),
            rounds=200,
            warmup_rounds=10,
        )


# ===========================================================================
# 2. RENDERER benchmarks
# ===========================================================================

@pytest.mark.medium
class TestRendererBenchmarks:
    """
    render_page_layers: Pillow + numpy ağır operasyonlar.
    Beklenen: < 2 s / sayfa (LaTeX kapalı)
    """

    def test_render_single_page_dpi300(self, benchmark, bench_cfg):
        """DPI300 A4 tam sayfa render."""
        from ai1_gen.render.page_renderer import render_page_layers

        ps = _make_page_spec(bench_cfg, seed=10, page_id="r_000")
        rng = random.Random(10)

        benchmark.extra_info["sözleşme_s_max"] = 2.0
        benchmark.pedantic(
            render_page_layers,
            args=(ps, bench_cfg, rng),
            rounds=10,
            warmup_rounds=2,
        )

    def test_render_single_page_dpi200(self, benchmark, bench_cfg):
        """DPI200 A4 tam sayfa render (daha küçük canvas)."""
        from ai1_gen.render.page_renderer import render_page_layers
        from ai1_gen.layout.layout_sampler import sample_page_spec
        from ai1_gen.config import AppConfig

        raw2 = dict(bench_cfg.raw)
        raw2["dist"] = dict(bench_cfg.raw["dist"])
        raw2["dist"]["scale_dist"] = {"dpi200": 1.0}
        cfg2 = AppConfig(raw2)

        rng = random.Random(20)
        ps = sample_page_spec(cfg2, rng, 0, "r_dpi200")

        benchmark.pedantic(
            render_page_layers,
            args=(ps, cfg2, rng),
            rounds=10,
            warmup_rounds=2,
        )

    def test_render_dense_page(self, benchmark, bench_cfg):
        """Dense yoğunluklu sayfa — en fazla Pillow draw çağrısı."""
        from ai1_gen.render.page_renderer import render_page_layers
        from ai1_gen.layout.layout_sampler import sample_page_spec
        from ai1_gen.config import AppConfig

        raw2 = dict(bench_cfg.raw)
        raw2["dist"] = dict(bench_cfg.raw["dist"])
        raw2["dist"]["density_dist"] = {"dense": 1.0}
        cfg2 = AppConfig(raw2)

        rng = random.Random(30)
        ps = sample_page_spec(cfg2, rng, 0, "r_dense")

        benchmark.pedantic(
            render_page_layers,
            args=(ps, cfg2, rng),
            rounds=10,
            warmup_rounds=2,
        )

    def test_render_sparse_page(self, benchmark, bench_cfg):
        """Sparse sayfa — minimum draw çağrısı, tavan referansı."""
        from ai1_gen.render.page_renderer import render_page_layers
        from ai1_gen.layout.layout_sampler import sample_page_spec
        from ai1_gen.config import AppConfig

        raw2 = dict(bench_cfg.raw)
        raw2["dist"] = dict(bench_cfg.raw["dist"])
        raw2["dist"]["density_dist"] = {"sparse": 1.0}
        cfg2 = AppConfig(raw2)

        rng = random.Random(40)
        ps = sample_page_spec(cfg2, rng, 0, "r_sparse")

        benchmark.pedantic(
            render_page_layers,
            args=(ps, cfg2, rng),
            rounds=15,
            warmup_rounds=3,
        )

    def test_render_with_table_and_figure(self, benchmark, bench_cfg):
        """Figure + Table içeren sayfa — ek patch oluşturma maliyeti."""
        from ai1_gen.render.page_renderer import render_page_layers
        from ai1_gen.layout.layout_sampler import sample_page_spec
        from ai1_gen.config import AppConfig

        raw2 = dict(bench_cfg.raw)
        raw2["content"] = {
            "has_equation_prob": 0.0,
            "has_table_prob":    1.0,
            "has_figure_prob":   1.0,
            "has_caption_prob":  0.9,
        }
        cfg2 = AppConfig(raw2)

        rng = random.Random(50)
        ps = sample_page_spec(cfg2, rng, 0, "r_tbl_fig")

        benchmark.pedantic(
            render_page_layers,
            args=(ps, cfg2, rng),
            rounds=10,
            warmup_rounds=2,
        )

    def test_render_10_pages_throughput(self, benchmark, bench_cfg):
        """
        10 sayfa sıralı render — gerçek batch throughput tahmini.
        Beklenen: < 15 s toplam (LaTeX kapalı)
        """
        from ai1_gen.render.page_renderer import render_page_layers
        from ai1_gen.layout.layout_sampler import sample_page_spec

        def _batch():
            rng = random.Random(888)
            return [
                render_page_layers(
                    sample_page_spec(bench_cfg, rng, i, f"tp_{i:04d}"),
                    bench_cfg, rng,
                )
                for i in range(10)
            ]

        benchmark.pedantic(_batch, rounds=3, warmup_rounds=1)


# ===========================================================================
# 3. AUGMENT benchmarks
# ===========================================================================

@pytest.mark.fast
class TestAugmentBenchmarks:
    """
    apply_augment: numpy / OpenCV ağırlıklı.
    Beklenen: < 500 ms / sayfa (tüm operasyonlar açık)
    """

    @pytest.fixture(scope="class")
    def prebuilt_render(self, bench_cfg):
        """Render sonucunu bir kez üretelim; augment ölçümü temiz kalsın."""
        result, ps = _make_render_result(bench_cfg, seed=7)
        return result, ps

    def test_augment_clean_noise(self, benchmark, bench_cfg, prebuilt_render):
        """clean noise_level → düşük augment olasılıkları."""
        from ai1_gen.augment.apply_augment import apply_augment

        rr, ps = prebuilt_render
        aug_cfg = bench_cfg.augment()

        def _run():
            rng = random.Random(random.randint(0, 2**31))
            return apply_augment(
                rr["image_u8"].copy(),
                rr["mask_text_u8"].copy(),
                rr["mask_math_u8"].copy(),
                dict(rr["ann"]),
                {"noise_level": "clean", "scale_profile": "dpi300", "perspective": False},
                aug_cfg,
                rng,
            )

        benchmark.extra_info["sözleşme_ms_max"] = 500.0
        benchmark.pedantic(_run, rounds=20, warmup_rounds=3)

    def test_augment_heavy_noise(self, benchmark, bench_cfg, prebuilt_render):
        """heavy noise_level → tüm augment adımları tetiklenir."""
        from ai1_gen.augment.apply_augment import apply_augment

        rr, ps = prebuilt_render
        aug_cfg = bench_cfg.augment()

        def _run():
            rng = random.Random(random.randint(0, 2**31))
            return apply_augment(
                rr["image_u8"].copy(),
                rr["mask_text_u8"].copy(),
                rr["mask_math_u8"].copy(),
                dict(rr["ann"]),
                {"noise_level": "heavy", "scale_profile": "dpi300", "perspective": True},
                aug_cfg,
                rng,
            )

        benchmark.pedantic(_run, rounds=20, warmup_rounds=3)

    def test_augment_geometry_only(self, benchmark, bench_cfg, prebuilt_render):
        """Sadece geometrik dönüşüm — perspektif + rotasyon maliyeti."""
        from ai1_gen.augment.apply_augment import apply_augment

        rr, ps = prebuilt_render
        aug_cfg_geom = {
            "enable": True,
            "min_area_px": 25,
            "selection_policy": {"clean": {
                "p_photometric": 0.0,
                "p_blur_noise": 0.0,
                "p_capture": 0.0,
                "p_geometry": 1.0,
            }},
            "geometry": {"rotation_deg": [-6.0, 6.0], "perspective_jitter_ratio": [0.0, 0.03]},
            "edge_degredation": {"prob": 0.0},
            "elastic_distortion": {"prob": 0.0},
        }

        def _run():
            rng = random.Random(random.randint(0, 2**31))
            return apply_augment(
                rr["image_u8"].copy(),
                rr["mask_text_u8"].copy(),
                rr["mask_math_u8"].copy(),
                dict(rr["ann"]),
                {"noise_level": "clean", "scale_profile": "dpi300", "perspective": True},
                aug_cfg_geom,
                rng,
            )

        benchmark.pedantic(_run, rounds=30, warmup_rounds=5)

    def test_augment_elastic_distortion_only(self, benchmark, bench_cfg, prebuilt_render):
        """Sadece elastik deformasyon — GaussianBlur + remap maliyeti."""
        from ai1_gen.augment.apply_augment import apply_augment

        rr, ps = prebuilt_render
        aug_cfg_elastic = {
            "enable": True,
            "min_area_px": 25,
            "selection_policy": {"clean": {
                "p_photometric": 0.0,
                "p_blur_noise": 0.0,
                "p_capture": 0.0,
                "p_geometry": 0.0,
            }},
            "edge_degredation": {"prob": 0.0},
            "elastic_distortion": {"prob": 1.0, "alpha": [25.0, 25.0], "sigma": [8.0, 8.0]},
        }

        def _run():
            rng = random.Random(random.randint(0, 2**31))
            return apply_augment(
                rr["image_u8"].copy(),
                rr["mask_text_u8"].copy(),
                rr["mask_math_u8"].copy(),
                dict(rr["ann"]),
                {"noise_level": "clean", "scale_profile": "dpi300"},
                aug_cfg_elastic,
                rng,
            )

        benchmark.pedantic(_run, rounds=30, warmup_rounds=5)

    def test_augment_edge_degradation_only(self, benchmark, bench_cfg, prebuilt_render):
        """Sadece edge degradation — maskeleme + fillPoly maliyeti."""
        from ai1_gen.augment.apply_augment import apply_augment

        rr, ps = prebuilt_render
        aug_cfg_edge = {
            "enable": True,
            "min_area_px": 25,
            "selection_policy": {"clean": {
                "p_photometric": 0.0,
                "p_blur_noise": 0.0,
                "p_capture": 0.0,
                "p_geometry": 0.0,
            }},
            "edge_degredation": {
                "prob": 1.0,
                "num_erasures": [5, 5],
                "size_ratio": [0.10, 0.10],
                "protect_math": True,
            },
            "elastic_distortion": {"prob": 0.0},
        }

        def _run():
            rng = random.Random(random.randint(0, 2**31))
            return apply_augment(
                rr["image_u8"].copy(),
                rr["mask_text_u8"].copy(),
                rr["mask_math_u8"].copy(),
                dict(rr["ann"]),
                {"noise_level": "clean", "scale_profile": "dpi300"},
                aug_cfg_edge,
                rng,
            )

        benchmark.pedantic(_run, rounds=50, warmup_rounds=5)


# ===========================================================================
# 4. QC / VALIDATOR benchmarks
# ===========================================================================

@pytest.mark.fast
class TestValidatorBenchmarks:
    """
    validate_page + compute_density_metrics: numpy ağırlıklı.
    Beklenen: < 50 ms / sayfa
    """

    @pytest.fixture(scope="class")
    def qc_inputs(self, bench_cfg):
        rr, ps = _make_render_result(bench_cfg, seed=123)
        return rr["ann"], rr["mask_text_u8"], rr["mask_math_u8"]

    def test_validate_page_full(self, benchmark, bench_cfg, qc_inputs):
        """Tüm QC kuralları (mask binary, overlap, order, density, …)."""
        from ai1_gen.qc.validators import validate_page

        ann, mt, mm = qc_inputs
        benchmark.extra_info["sözleşme_ms_max"] = 50.0
        benchmark.pedantic(
            validate_page,
            args=(ann, mt, mm, bench_cfg),
            rounds=200,
            warmup_rounds=20,
        )

    def test_compute_density_metrics(self, benchmark, bench_cfg, qc_inputs):
        """compute_density_metrics: eligible area hesabı dahil."""
        from ai1_gen.qc.validators import compute_density_metrics

        ann, mt, mm = qc_inputs
        benchmark.pedantic(
            compute_density_metrics,
            args=(mt, mm, ann, bench_cfg),
            rounds=300,
            warmup_rounds=30,
        )

    def test_mixed_band_variance(self, benchmark):
        """mixed_band_variance: 8 band, 3507x2481 maske."""
        from ai1_gen.qc.validators import mixed_band_variance

        rng = np.random.default_rng(42)
        mask = (rng.random((3507, 2481)) > 0.85).astype(bool)
        eligible = np.ones_like(mask)

        benchmark.pedantic(
            mixed_band_variance,
            args=(mask,),
            kwargs={"bands": 8, "eligible": eligible},
            rounds=200,
            warmup_rounds=20,
        )

    def test_is_binary_u8_large_mask(self, benchmark):
        """_is_binary_u8: A4 dpi300 maske boyutunda."""
        from ai1_gen.qc.validators import _is_binary_u8

        mask = np.zeros((3507, 2481), dtype=np.uint8)
        mask[100:500, 100:2000] = 255

        benchmark.pedantic(
            _is_binary_u8,
            args=(mask,),
            rounds=500,
            warmup_rounds=50,
        )

    def test_validate_page_qc_fail_early_exit(self, benchmark, bench_cfg):
        """
        Erken çıkış senaryosu: overlap kuralı anında tetiklenir.
        validate_page'in dal kesmesi ne kadar hızlı?
        """
        from ai1_gen.qc.validators import validate_page

        mt = np.zeros((3507, 2481), dtype=np.uint8)
        mm = np.zeros_like(mt)
        # %50 overlap → qc/overlap-too-high anında
        mt[500:1500, 300:2000] = 255
        mm[500:1500, 300:2000] = 255  # tam üst üste

        ann = {
            "meta": {"density_level": "normal", "has_equation": False},
            "size": {"w": 2481, "h": 3507, "dpi": 300},
            "lines": [],
            "blocks": [],
        }

        benchmark.pedantic(
            validate_page,
            args=(ann, mt, mm, bench_cfg),
            rounds=500,
            warmup_rounds=50,
        )


# ===========================================================================
# 5. END-TO-END (Layout → Render → Augment → QC) benchmarks
# ===========================================================================

@pytest.mark.medium
class TestEndToEndBenchmarks:
    """
    Tek bir sayfa için tam boru hattı — en gerçekçi gecikme ölçümü.
    Beklenen: < 3 s / sayfa (LaTeX kapalı)
    """

    def _run_pipeline(self, cfg, seed: int):
        from ai1_gen.layout.layout_sampler import sample_page_spec
        from ai1_gen.render.page_renderer import render_page_layers
        from ai1_gen.augment.apply_augment import apply_augment
        from ai1_gen.qc.validators import validate_page

        rng = random.Random(seed)
        ps = sample_page_spec(cfg, rng, seed, f"e2e_{seed:06d}")
        rr = render_page_layers(ps, cfg, rng)

        aug_cfg = cfg.augment()
        ar = apply_augment(
            rr["image_u8"],
            rr["mask_text_u8"],
            rr["mask_math_u8"],
            rr["ann"],
            rr["ann"]["meta"],
            aug_cfg,
            rng,
        )

        validate_page(ar.ann_aug, ar.mask_text_aug_u8, ar.mask_math_aug_u8, cfg)
        return ar

    def test_e2e_single_page_normal(self, benchmark, bench_cfg):
        """Normal yoğunluk, tam pipeline."""
        benchmark.extra_info["sözleşme_s_max"] = 3.0
        benchmark.pedantic(
            self._run_pipeline,
            args=(bench_cfg, 42),
            rounds=5,
            warmup_rounds=1,
        )

    def test_e2e_single_page_dense_heavy(self, benchmark, bench_cfg):
        """Dense + heavy noise — en ağır senaryo."""
        from ai1_gen.config import AppConfig

        raw2 = dict(bench_cfg.raw)
        raw2["dist"] = dict(bench_cfg.raw["dist"])
        raw2["dist"]["density_dist"] = {"dense": 1.0}
        raw2["dist"]["noise_level_dist"] = {"heavy": 1.0}
        cfg2 = AppConfig(raw2)

        benchmark.pedantic(
            self._run_pipeline,
            args=(cfg2, 99),
            rounds=5,
            warmup_rounds=1,
        )

    def test_e2e_single_page_sparse_clean(self, benchmark, bench_cfg):
        """Sparse + clean — en hafif senaryo (taban hattı)."""
        from ai1_gen.config import AppConfig

        raw2 = dict(bench_cfg.raw)
        raw2["dist"] = dict(bench_cfg.raw["dist"])
        raw2["dist"]["density_dist"] = {"sparse": 1.0}
        raw2["dist"]["noise_level_dist"] = {"clean": 1.0}
        cfg2 = AppConfig(raw2)

        benchmark.pedantic(
            self._run_pipeline,
            args=(cfg2, 7),
            rounds=5,
            warmup_rounds=1,
        )


# ===========================================================================
# 6. I/O (save_png_u8 + save_json) benchmarks
# ===========================================================================

@pytest.mark.fast
class TestIOBenchmarks:
    """
    save_png_u8 / save_json: atomik yazma maliyeti.
    Beklenen: < 200 ms / PNG (A4 dpi300)
    """

    @pytest.fixture(scope="class")
    def io_inputs(self, bench_cfg, tmp_path_factory):
        rr, ps = _make_render_result(bench_cfg, seed=11)
        tmp = tmp_path_factory.mktemp("io_bench")
        return rr, tmp

    def test_save_png_image(self, benchmark, bench_cfg, io_inputs, tmp_path):
        """Tam sayfa RGB PNG atomic yazma."""
        from ai1_gen.io.exporter import save_png_u8

        rr, _ = io_inputs
        dst = tmp_path / "img.png"
        tmp_dir = tmp_path / "_tmp"
        tmp_dir.mkdir(exist_ok=True)
        img = rr["image_u8"]

        benchmark.extra_info["sözleşme_ms_max"] = 200.0
        benchmark.pedantic(
            save_png_u8,
            args=(dst, img, tmp_dir),
            rounds=10,
            warmup_rounds=2,
        )

    def test_save_png_mask(self, benchmark, bench_cfg, io_inputs, tmp_path):
        """Maske PNG atomic yazma (grayscale, daha hızlı beklenir)."""
        from ai1_gen.io.exporter import save_png_u8

        rr, _ = io_inputs
        dst = tmp_path / "mask.png"
        tmp_dir = tmp_path / "_tmp"
        tmp_dir.mkdir(exist_ok=True)
        mask = rr["mask_text_u8"]

        benchmark.pedantic(
            save_png_u8,
            args=(dst, mask, tmp_dir),
            rounds=10,
            warmup_rounds=2,
        )

    def test_save_json_annotation(self, benchmark, bench_cfg, io_inputs, tmp_path):
        """Tam annotation JSON atomic yazma."""
        from ai1_gen.io.exporter import save_json

        rr, _ = io_inputs
        dst = tmp_path / "ann.json"
        tmp_dir = tmp_path / "_tmp"
        tmp_dir.mkdir(exist_ok=True)
        ann = rr["ann"]

        benchmark.pedantic(
            save_json,
            args=(dst, ann, tmp_dir),
            rounds=50,
            warmup_rounds=5,
        )


# ===========================================================================
# 7. CONFIG LOAD benchmark
# ===========================================================================

@pytest.mark.fast
class TestConfigBenchmarks:
    """load_config: YAML ayrıştırma + AppConfig.__init__ toplam maliyeti."""

    def test_load_config_from_yaml(self, benchmark, tmp_path):
        """YAML dosyasından tam config yükleme."""
        import yaml
        from ai1_gen.config import load_config

        cfg_data = {
            "project": {"version": "ai1-ds-v1.3.2"},
            "io": {"out_root": "/tmp/x", "tmp_dir": "_tmp"},
            "run": {"pages": 1000, "seed": 42, "workers": 4},
            "dist": {
                "density_dist": {"sparse": 0.15, "normal": 0.55, "dense": 0.20, "mixed": 0.10},
                "scale_dist": {"dpi300": 0.70, "dpi200": 0.20, "lowres_capture": 0.10},
                "noise_level_dist": {"clean": 0.5, "medium": 0.3, "heavy": 0.2},
            },
            "qc": {"mask_binary_required": True},
            "augment": {"enable": True},
            "telemetry": {"temperature": {"require_temp_sensor": False}},
        }
        cfg_path = tmp_path / "bench_cfg.yaml"
        cfg_path.write_text(yaml.dump(cfg_data), encoding="utf-8")

        benchmark.pedantic(
            load_config,
            args=(cfg_path,),
            rounds=500,
            warmup_rounds=50,
        )


# ===========================================================================
# 8. LATEX EXPRESSION GENERATOR benchmark (disk I/O YOK)
# ===========================================================================

@pytest.mark.fast
class TestLatexExprBenchmarks:
    """
    sample_latex_expr: saf Python rastgele ifade üretimi.
    render_latex_to_rgba burada çalıştırılmaz (pdflatex gerektirir).
    """

    @pytest.mark.parametrize("level", ["clean", "medium", "heavy"])
    def test_sample_latex_expr(self, benchmark, level):
        from ai1_gen.latex.miktex_render import sample_latex_expr

        rng = random.Random(42)
        benchmark.pedantic(
            sample_latex_expr,
            args=(rng,),
            kwargs={"level": level},
            rounds=2000,
            warmup_rounds=100,
        )

    def test_sample_latex_expr_batch_1000(self, benchmark):
        """1000 ifade ardışık üretimi — throughput."""
        from ai1_gen.latex.miktex_render import sample_latex_expr

        def _batch():
            rng = random.Random(99)
            return [sample_latex_expr(rng, level="medium") for _ in range(1000)]

        benchmark.pedantic(_batch, rounds=10, warmup_rounds=2)


# ===========================================================================
# 9. MEMORY / ALLOCATION profil markerları (isteğe bağlı)
# ===========================================================================

@pytest.mark.slow
class TestMemoryAllocationBenchmarks:
    """
    Bu testler çalışması uzun sürer; CI'da --ignore veya -m "not slow" ile atlanabilir.
    """

    def test_render_50_pages_memory_stable(self, bench_cfg):
        """
        50 sayfa ardışık render sırasında bellek büyümesi kontrol edilir.
        pytest-benchmark ile değil; doğrudan tracemalloc ile ölçülür.
        """
        import tracemalloc
        from ai1_gen.layout.layout_sampler import sample_page_spec
        from ai1_gen.render.page_renderer import render_page_layers

        tracemalloc.start()
        snap1 = tracemalloc.take_snapshot()

        rng = random.Random(1)
        for i in range(50):
            ps = sample_page_spec(bench_cfg, rng, i, f"mem_{i:04d}")
            rr = render_page_layers(ps, bench_cfg, rng)
            del rr

        snap2 = tracemalloc.take_snapshot()
        tracemalloc.stop()

        stats = snap2.compare_to(snap1, "lineno")
        total_diff_mb = sum(s.size_diff for s in stats) / 1024 / 1024

        # Sızdırılan bellek 100 MB'ı geçmemeli (50 sayfa için makul)
        assert total_diff_mb < 100.0, (
            f"Bellek sızıntısı şüphesi: {total_diff_mb:.1f} MB artış (50 sayfa sonunda)"
        )

    def test_augment_100_pages_no_leak(self, bench_cfg):
        """
        100 augment ardışık çağrısında bellek artışı sınırı.
        """
        import tracemalloc
        from ai1_gen.augment.apply_augment import apply_augment

        rr, _ = _make_render_result(bench_cfg, seed=5)
        aug_cfg = bench_cfg.augment()

        tracemalloc.start()
        snap1 = tracemalloc.take_snapshot()

        for i in range(100):
            rng = random.Random(i)
            ar = apply_augment(
                rr["image_u8"].copy(),
                rr["mask_text_u8"].copy(),
                rr["mask_math_u8"].copy(),
                dict(rr["ann"]),
                {"noise_level": "heavy", "scale_profile": "dpi300", "perspective": True},
                aug_cfg,
                rng,
            )
            del ar

        snap2 = tracemalloc.take_snapshot()
        tracemalloc.stop()

        stats = snap2.compare_to(snap1, "lineno")
        total_diff_mb = sum(s.size_diff for s in stats) / 1024 / 1024

        assert total_diff_mb < 50.0, (
            f"Augment bellek sızıntısı: {total_diff_mb:.1f} MB (100 çağrı sonunda)"
        )