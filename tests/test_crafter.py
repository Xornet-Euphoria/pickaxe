import pickaxe


def wrap_push_int(n: int):
    crafter = pickaxe.Crafter()
    crafter.push_int(n)
    return crafter.loads(check_stop=True)


def test_number():
    testcases = [1, 0xdead, 114514, 0xdeadbeefcafebabe, -1, 2**1024, -2**1024, 2**2040]
    for x in testcases:
        assert wrap_push_int(x) == x


def wrap_push_str(s: str):
    crafter = pickaxe.Crafter()
    crafter.push_str(s)
    return crafter.loads(check_stop=True)


def test_string():
    testcases = ["The quick brown fox jumps over the lazy dog", "a" * 0x1000]
    for s in testcases:
        assert wrap_push_str(s) == s


def wrap_push(x):
    crafter = pickaxe.Crafter()
    crafter.push(x)
    return crafter.loads(check_stop=True)


def test_auto_push():
    testcases = \
        [1, 0xdead, 114514, 0xdeadbeefcafebabe, -1, 2**1024, -2**1024, 2**2040] + \
        ["The quick brown fox jumps over the lazy dog", "a" * 0x1000]
    
    for x in testcases:
        assert wrap_push(x) == x