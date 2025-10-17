from google.cloud import datastore

client = datastore.Client(project="dummy-project")

# Seed default namespace
key = client.key("TestKind", "test-id")
entity = datastore.Entity(key=key)
entity.update({"foo": "bar"})
client.put(entity)

# Seed custom namespace
key_ns = client.key("TestKind", "test-id-ns", namespace="test-ns")
entity_ns = datastore.Entity(key=key_ns)
entity_ns.update({"foo": "baz"})
client.put(entity_ns)

print("Seeded emulator with test entities in default and 'test-ns' namespaces.")
