import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

def test_imports():
    import commands
    from commands import analyze_kinds, analyze_entity_fields, cleanup_expired, config

    assert commands is not None
    assert hasattr(config, "AppConfig")