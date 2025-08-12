def test_imports():
    import gcd_tools
    from gcd_tools import analyze_kinds, analyze_entity_fields, cleanup_expired, config

    assert gcd_tools is not None
    assert hasattr(config, "AppConfig")