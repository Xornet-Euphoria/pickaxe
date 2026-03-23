import builtins
import pickle
import pickaxe


def test_name_to_op():
    import re
    op_strs = [op for op in dir(pickle) if re.match("^[A-Z]{1}[A-Z0-9_]*$", op) and isinstance(getattr(pickle, op), bytes) and len(getattr(pickle, op)) == 1]

    for op_str in op_strs:
        assert pickaxe.name_to_op[op_str].code.encode("latin-1") == getattr(pickle, op_str)


def test_add_op():
    crafter = pickaxe.Crafter()
    crafter.add_op("NEWTRUE")
    res = crafter.loads()
    assert res


def wrap_push_bool(b: bool):
    crafter = pickaxe.Crafter()
    crafter.push_bool(b)
    return crafter.loads()


def test_bool():
    testcases = [True, False]
    for b in testcases:
        assert wrap_push_bool(b) == b


def wrap_push_int(n: int):
    crafter = pickaxe.Crafter()
    crafter.push_int(n)
    return crafter.loads()


def test_number():
    testcases = [1, 0xdead, 114514, 0xdeadbeefcafebabe, -1, 2**1024, -2**1024, 2**2040]
    for x in testcases:
        assert wrap_push_int(x) == x


def wrap_push_str(s: str):
    crafter = pickaxe.Crafter()
    crafter.push_str(s)
    return crafter.loads()


def test_string():
    testcases = ["The quick brown fox jumps over the lazy dog", "a" * 0x1000]
    for s in testcases:
        assert wrap_push_str(s) == s


def wrap_push(x):
    crafter = pickaxe.Crafter()
    crafter.push(x)
    return crafter.loads()


def test_auto_push():
    testcases = \
        [1, 0xdead, 114514, 0xdeadbeefcafebabe, -1, 2**1024, -2**1024, 2**2040] + \
        ["The quick brown fox jumps over the lazy dog", "a" * 0x1000]
    
    for x in testcases:
        assert wrap_push(x) == x


def test_import_from():
    crafter = pickaxe.Crafter()
    crafter.import_from("builtins", "id")
    assert crafter.loads() == id


def test_push_str_uses_binunicode8_for_large_lengths(monkeypatch):
    fake_data = b"payload"

    class HugeUtf8Str(str):
        def encode(self, encoding="utf-8", errors="strict"):
            return fake_data

    real_len = builtins.len

    def fake_len(obj):
        if obj is fake_data:
            return 2**32
        return real_len(obj)

    monkeypatch.setattr(builtins, "len", fake_len)

    crafter = pickaxe.Crafter()
    crafter.push_str(HugeUtf8Str("ignored"))

    assert crafter.payload == pickle.BINUNICODE8 + (2**32).to_bytes(8, "little") + fake_data


def test_get_memo_uses_long_binget_for_large_indices():
    crafter = pickaxe.Crafter()
    crafter.get_memo(0x100)

    assert crafter.payload == pickle.LONG_BINGET + (0x100).to_bytes(4, "little")


def test_get_memo_falls_back_to_text_get_for_very_large_indices():
    crafter = pickaxe.Crafter()
    crafter.get_memo(2**32)

    assert crafter.payload == pickle.GET + b"4294967296\n"
