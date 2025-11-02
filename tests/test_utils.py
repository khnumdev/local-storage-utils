from commands.config import format_size, chunked


def test_format_size_bytes_and_kb():
    assert format_size(100) == "100.00 B"
    assert format_size(2048) == "2.00 KB"


def test_format_size_large():
    assert format_size(5 * 1024 * 1024) == "5.00 MB"


def test_chunked_even_and_odd():
    data = list(range(7))
    chunks = list(chunked(data, 3))
    assert chunks == [data[0:3], data[3:6], data[6:7]]
