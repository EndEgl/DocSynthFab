import json

from ai1_gen.io.exporter import save_json


def test_save_json_writes_file_atomically(tmp_path):
    target = tmp_path / "ann" / "sample.json"
    tmp_dir = tmp_path / "_tmp"
    tmp_dir.mkdir()

    data = {"page_id": "000001", "ok": True}
    save_json(target, data, tmp_dir)

    assert target.exists()
    loaded = json.loads(target.read_text(encoding="utf-8"))
    assert loaded == data


def test_save_json_overwrites_existing_file(tmp_path):
    target = tmp_path / "ann" / "sample.json"
    tmp_dir = tmp_path / "_tmp"
    tmp_dir.mkdir(parents=True, exist_ok=True)
    target.parent.mkdir(parents=True, exist_ok=True)

    target.write_text('{"old": true}', encoding="utf-8")
    save_json(target, {"new": True}, tmp_dir)

    assert json.loads(target.read_text(encoding="utf-8")) == {"new": True}