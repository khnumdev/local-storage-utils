from google.cloud import datastore

client = datastore.Client(project="dummy-project")

import os
import random
import string

"""Seed the datastore emulator with deterministic-ish test data.

Environment variables:
  SEED_COUNT - number of entities to create in the default namespace (default: 1000)
  SEED_NS_COUNT - number of entities to create in 'test-ns' namespace (default: 1000)
  SEED_KIND - kind to use (default: TestKind)
"""

client = datastore.Client(project="dummy-project")

def rand_str(n=32):
	return "".join(random.choices(string.ascii_lowercase + string.digits, k=n))

SEED_COUNT = int(os.getenv("SEED_COUNT", "5000"))
SEED_NS_COUNT = int(os.getenv("SEED_NS_COUNT", "5000"))
KIND = os.getenv("SEED_KIND", "TestKind")

print(f"Seeding default namespace: {SEED_COUNT} entities (kind={KIND})")
for i in range(SEED_COUNT):
	key = client.key(KIND, f"id-{i}")
	e = datastore.Entity(key=key)
	# small-ish payload with multiple fields
	e.update({
		"foo": rand_str(64),
		"num": i,
		"tag": f"tag-{i % 10}",
	})
	client.put(e)

print(f"Seeding namespace 'test-ns': {SEED_NS_COUNT} entities (kind={KIND})")
for i in range(SEED_NS_COUNT):
	key = client.key(KIND, f"ns-id-{i}", namespace="test-ns")
	e = datastore.Entity(key=key)
	e.update({
		"foo": rand_str(64),
		"num": i,
		"tag": f"tag-{i % 10}",
	})
	client.put(e)

print("Seeded emulator with test entities in default and 'test-ns' namespaces.")
