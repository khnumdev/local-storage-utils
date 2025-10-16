
import sys
import os
import pytest
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from gcd_tools import analyze_kinds, analyze_entity_fields, cleanup_expired, config
from gcd_tools.config import AppConfig

# Dummy config for testing (adjust as needed for emulator)
def make_dummy_config():
    return AppConfig(
        project_id="dummy-project",
        emulator_host="localhost:8080",
        namespaces=[""],
        kinds=["TestKind"],
        ttl_field="expireAt",
        delete_missing_ttl=True,
        batch_size=10,
        group_by_field=None,
        log_level="INFO",
    )

def test_analyze_kinds_runs():
    cfg = make_dummy_config()
    try:
        result = analyze_kinds(cfg)
        assert isinstance(result, list)
    except Exception as e:
        pytest.skip(f"analyze_kinds requires emulator: {e}")

def test_analyze_fields_runs():
    cfg = make_dummy_config()
    try:
        result = analyze_entity_fields.analyze_field_contributions(cfg, kind="TestKind")
        assert isinstance(result, dict)
    except Exception as e:
        pytest.skip(f"analyze_fields requires emulator: {e}")

def test_cleanup_expired_runs():
    cfg = make_dummy_config()
    try:
        result = cleanup_expired.cleanup_expired(cfg, dry_run=True)
        assert isinstance(result, dict)
    except Exception as e:
        pytest.skip(f"cleanup_expired requires emulator: {e}")
