from pathlib import Path

from ai1_gen.io.exporter import ensure_dataset_dirs


def test_ensure_dataset_dirs_creates_expected_relative_tree(tmp_path):
    out_root = tmp_path / "relative_out"
    dirs = ensure_dataset_dirs(out_root)

    expected = {"root", "images", "masks", "ann", "gt", "splits", "tmp"}
    assert expected.issubset(dirs.keys())

    for key in expected:
        assert Path(dirs[key]).exists(), key
        assert Path(dirs[key]).is_dir(), key