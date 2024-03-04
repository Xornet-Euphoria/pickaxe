import pytest
import pickaxe


def test_ascii_printable():
    crafter = pickaxe.AsciiCrafter()
    with pytest.raises(ValueError, match=r".+ is forbidden") as exc_info:
        crafter.add_payload(b"\xff")


def wrap_push_bool(b: bool):
    crafter = pickaxe.AsciiCrafter()
    crafter.push_bool(b)
    return crafter.loads()


def test_bool():
    testcases = [True, False]
    for b in testcases:
        assert wrap_push_bool(b) == b


def wrap_push_int(n: int):
    crafter = pickaxe.AsciiCrafter()
    crafter.push_int(n)
    return crafter.loads()


def test_number():
    testcases = [1, 0xdead, 114514, 0xdeadbeefcafebabe, -1, 2**1024, -2**1024, 2**2040]
    for x in testcases:
        assert wrap_push_int(x) == x


def wrap_push_str(s: str):
    crafter = pickaxe.AsciiCrafter()
    crafter.push_str(s)
    return crafter.loads()


def test_string():
    testcases = ["The quick brown fox jumps over the lazy dog", "a" * 0x1000]
    for s in testcases:
        assert wrap_push_str(s) == s