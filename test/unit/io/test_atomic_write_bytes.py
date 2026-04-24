from pathlib import Path


def test_tmp_dir_supports_nested_relative_atomic_targets(tmp_path):
    target = tmp_path / "nested" / "dir" / "file.bin"
    tmp_dir = tmp_path / "_tmp"
    tmp_dir.mkdir()

    target.parent.mkdir(parents=True, exist_ok=True)
    payload = b"abc123"

    temp_file = tmp_dir / "temp.bin"
    temp_file.write_bytes(payload)
    temp_file.replace(target)

    assert target.exists()
    assert target.read_bytes() == payload