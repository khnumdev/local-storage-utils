"""Seed the datastore emulator with deterministic-ish test data.

Environment variables:
  SEED_COUNT - number of entities to create in the default namespace (default: 5000)
  SEED_NS_COUNT - number of entities to create in 'test-ns' namespace (default: 5000)
  SEED_KIND - kind to use (default: TestKind)
"""

import os
import random
import string

from google.cloud import datastore

from commands.config import chunked

client = datastore.Client(project="dummy-project")


def rand_str(n=32):
    return "".join(random.choices(string.ascii_lowercase + string.digits, k=n))


def _seed(namespace, count, kind, key_prefix, batch_size=500):
    print(f"Seeding namespace {namespace or '(default)'!r}: {count} entities (kind={kind})")
    entities = []
    for i in range(count):
        key = client.key(kind, f"{key_prefix}{i}", namespace=namespace)
        e = datastore.Entity(key=key)
        e.update({
            "foo": rand_str(64),
            "num": i,
            "tag": f"tag-{i % 10}",
        })
        entities.append(e)

    for batch in chunked(entities, batch_size):
        client.put_multi(batch)


if __name__ == "__main__":
    SEED_COUNT = int(os.getenv("SEED_COUNT", "5000"))
    SEED_NS_COUNT = int(os.getenv("SEED_NS_COUNT", "5000"))
    KIND = os.getenv("SEED_KIND", "TestKind")

    _seed(None, SEED_COUNT, KIND, "id-")
    _seed("test-ns", SEED_NS_COUNT, KIND, "ns-id-")

    print("Seeded emulator with test entities in default and 'test-ns' namespaces.")
