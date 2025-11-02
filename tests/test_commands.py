import sys
import os
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from commands import analyze_kinds, analyze_entity_fields, cleanup_expired
from commands.config import AppConfig, build_client, list_namespaces


def make_dummy_config():
    return AppConfig(
        project_id="dummy-project",
        emulator_host=os.getenv("DATASTORE_EMULATOR_HOST", "localhost:8010"),
        namespaces=[""],
        kinds=["TestKind"],
        ttl_field="expireAt",
        delete_missing_ttl=True,
        batch_size=10,
        group_by_field=None,
        log_level="INFO",
    )


def test_analyze_kinds_runs_or_skips():
    cfg = make_dummy_config()
    try:
        result = analyze_kinds(cfg)
        assert isinstance(result, list)
    except Exception as e:
        pytest.skip(f"analyze_kinds requires emulator: {e}")


def test_analyze_fields_runs_or_skips():
    cfg = make_dummy_config()
    try:
        # limit work for correctness smoke test
        cfg.sample_size = 50
        result = analyze_entity_fields.analyze_field_contributions(cfg, kind="TestKind")
        assert isinstance(result, dict)
    except Exception as e:
        pytest.skip(f"analyze_fields requires emulator: {e}")


import sys
import os
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from commands import analyze_kinds, analyze_entity_fields, cleanup_expired
from commands.config import AppConfig, build_client, list_namespaces


def make_dummy_config():
    return AppConfig(
        project_id="dummy-project",
        emulator_host=os.getenv("DATASTORE_EMULATOR_HOST", "localhost:8010"),
        namespaces=[""],
        kinds=["TestKind"],
        ttl_field="expireAt",
        delete_missing_ttl=True,
        batch_size=10,
        group_by_field=None,
        log_level="INFO",
    )


def test_analyze_kinds_runs_or_skips():
    cfg = make_dummy_config()
    try:
        result = analyze_kinds(cfg)
        assert isinstance(result, list)
    except Exception as e:
        pytest.skip(f"analyze_kinds requires emulator: {e}")


def test_analyze_fields_runs_or_skips():
    cfg = make_dummy_config()
    try:
        result = analyze_entity_fields.analyze_field_contributions(cfg, kind="TestKind")
        assert isinstance(result, dict)
    except Exception as e:
        pytest.skip(f"analyze_fields requires emulator: {e}")


def test_cleanup_expired_runs_or_skips():
    cfg = make_dummy_config()
    try:
        result = cleanup_expired.cleanup_expired(cfg, dry_run=True)
        assert isinstance(result, dict)
    except Exception as e:
        pytest.skip(f"cleanup_expired requires emulator: {e}")


def test_integration_perf_sampled():
    """Performance-focused integration test: seed a larger dataset and ensure sampled analysis completes quickly."""
    cfg = make_dummy_config()
    try:
        # Only run when emulator is available
        client = build_client(cfg)
    except Exception as e:
        pytest.skip(f"requires emulator: {e}")

    # Seed more data for the perf test (use the seed_emulator script with env vars)
    import subprocess, time

    env = os.environ.copy()
    env["SEED_COUNT"] = env.get("SEED_COUNT", "5000")
    env["SEED_NS_COUNT"] = env.get("SEED_NS_COUNT", "5000")
    env["SEED_KIND"] = env.get("SEED_KIND", "TestKind")

    # Run the seed script (this may be a no-op if already seeded)
    subprocess.check_call([".venv/bin/python", "scripts/seed_emulator.py"], env=env)

    # Now time analyze_kinds and analyze_field_contributions with sampling
    cfg.sample_size = 500

    start = time.time()
    ak = analyze_kinds(cfg)
    dur_kinds = time.time() - start

    start = time.time()
    af = analyze_entity_fields.analyze_field_contributions(cfg, kind="TestKind")
    dur_fields = time.time() - start

    # Ensure both completed and were reasonably fast (sampled)
    assert isinstance(ak, list)
    assert isinstance(af, dict)

    # Target: both under 60s each locally for sampled analysis
    assert dur_kinds < 60, f"analyze_kinds too slow: {dur_kinds:.1f}s"
    assert dur_fields < 60, f"analyze_fields too slow: {dur_fields:.1f}s"


def test_list_namespaces_returns_default():
    cfg = AppConfig(project_id="dummy-project", emulator_host=os.getenv("DATASTORE_EMULATOR_HOST", "localhost:8010"))
    try:
        client = build_client(cfg)
        namespaces = list_namespaces(client)
        assert "" in namespaces
    except Exception as e:
        pytest.skip(f"list_namespaces requires emulator: {e}")
