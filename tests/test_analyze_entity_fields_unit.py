from google.cloud import datastore
from commands.analyze_entity_fields import _clone_without_field, _estimate_field_contributions


def make_entity(client, id_, data: dict):
    key = client.key("TestKind", id_)
    e = datastore.Entity(key=key)
    for k, v in data.items():
        e[k] = v
    return e


def test_clone_without_field_and_estimate():
    client = datastore.Client(project="test-project")
    e1 = make_entity(client, 1, {"a": "x", "b": "y"})
    e2 = make_entity(client, 2, {"a": "longer", "b": "z"})

    cloned = _clone_without_field(e1, "a")
    assert "a" not in cloned
    assert cloned["b"] == "y"

    totals, total_size, count = _estimate_field_contributions([e1, e2], target_fields=None)
    assert count == 2
    assert total_size > 0
    # totals should contain keys for fields present
    assert "a" in totals and "b" in totals
