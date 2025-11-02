from commands.cleanup_expired import _delete_in_batches


def test_delete_in_batches_counts():
    # _delete_in_batches uses chunked iterator; we can simulate by passing lists
    class DummyClient:
        def __init__(self):
            self.deleted = []

        def delete_multi(self, keys):
            self.deleted.extend(keys)

    client = DummyClient()
    keys = list(range(7))
    deleted = _delete_in_batches(client, keys, batch_size=3)
    assert deleted == 7
    assert client.deleted == keys
