import pickaxe


def wrap_push_str(s: str):
    crafter = pickaxe.UnicodeCrafter()
    crafter.push_str(s)
    return crafter.loads()


def test_string():
    testcases = ["The quick brown fox jumps over the lazy dog", "a" * 0x1000]
    for s in testcases:
        assert wrap_push_str(s) == s


def test_import_from():
    crafter = pickaxe.UnicodeCrafter()
    crafter.import_from("builtins", "id")
    assert crafter.loads() == id