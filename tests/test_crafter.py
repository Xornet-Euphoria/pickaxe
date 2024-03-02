import pickaxe


def wrap_push_int(n: int):
    crafter = pickaxe.Crafter()
    crafter.push_int(n)
    return crafter.loads(check_stop=True)


def test_number():
    testcases = [1, 0xdead, 114514, 0xdeadbeefcafebabe, -1, 2**1024, -2**1024, 2**2040]
    for x in testcases:
        assert wrap_push_int(x) == x
