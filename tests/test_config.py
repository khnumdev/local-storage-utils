import os
import tempfile
from commands.config import load_config, _as_list, AppConfig, format_size


def test_as_list_none_and_single():
    assert _as_list(None) == []
    assert _as_list("a") == ["a"]
    assert _as_list(["a", "b"]) == ["a", "b"]


def test_load_config_normalizes_namespaces(tmp_path: tempfile.TemporaryDirectory):
    cfg_file = tmp_path / "config.yaml"
    cfg_file.write_text("namespaces: ['']\nkinds: []\n")
    cfg = load_config(str(cfg_file))
    assert cfg.namespaces == []
    assert cfg.kinds == []


def test_format_size_small_and_large():
    assert format_size(512) == "512.00 B"
    assert format_size(1024) == "1.00 KB"
    assert format_size(1024 * 1024 * 5) == "5.00 MB"
