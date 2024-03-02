import pickaxe


def wrap_push_int(n: int):
    crafter = pickaxe.Crafter()
    crafter.push_int(n)
    return crafter.loads(check_stop=True)


def test_number():
    assert wrap_push_int(1) == 1
    assert wrap_push_int(0xdead) == 0xdead
    assert wrap_push_int(114514) == 114514
    assert wrap_push_int(0xdeadbeefcafebabe) == 0xdeadbeefcafebabe
    assert wrap_push_int(-1) == -1
    assert wrap_push_int(2**1024) == 2**1024
    assert wrap_push_int(2**2040) == 2**2040
