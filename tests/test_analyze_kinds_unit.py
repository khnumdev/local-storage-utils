from io import StringIO
import sys

from commands.analyze_kinds import print_summary_table


def test_print_summary_table_outputs_csv():
    rows = [
        {"namespace": "", "kind": "K1", "count": 10, "bytes": 1024, "size": "1.00 KB"},
        {"namespace": "ns1", "kind": "K2", "count": 5, "bytes": 512, "size": "512.00 B"},
    ]
    old = sys.stdout
    try:
        buf = StringIO()
        sys.stdout = buf
        print_summary_table(rows)
        out = buf.getvalue()
        assert "namespace,kind,count,size,bytes" in out
        assert ",K1,10,1.00 KB,1024" in out
        assert "ns1,K2,5,512.00 B,512" in out
    finally:
        sys.stdout = old
