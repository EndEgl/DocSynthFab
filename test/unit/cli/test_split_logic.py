from ai1_gen.cli import _normalized_split_ratios, _split_of


def test_normalized_split_ratios_normalizes_sum():
    run_cfg = {"splits": {"train": 8, "val": 1, "test": 1}}
    tr, va, te = _normalized_split_ratios(run_cfg)

    assert round(tr, 6) == 0.8
    assert round(va, 6) == 0.1
    assert round(te, 6) == 0.1
    assert round(tr + va + te, 6) == 1.0


def test_normalized_split_ratios_uses_defaults_when_sum_is_zero():
    run_cfg = {"splits": {"train": 0, "val": 0, "test": 0}}
    tr, va, te = _normalized_split_ratios(run_cfg)

    assert (tr, va, te) == (0.80, 0.10, 0.10)


def test_split_of_assigns_train_val_test_ranges():
    run_cfg = {"splits": {"train": 0.6, "val": 0.2, "test": 0.2}}

    assert _split_of(0, 10, run_cfg) == "train"
    assert _split_of(5, 10, run_cfg) == "train"
    assert _split_of(6, 10, run_cfg) == "val"
    assert _split_of(7, 10, run_cfg) == "val"
    assert _split_of(8, 10, run_cfg) == "test"
    assert _split_of(9, 10, run_cfg) == "test"