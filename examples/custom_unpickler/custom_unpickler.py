from pickaxe import CustomUnpickler


if __name__ == "__main__":
    from pickle import dumps
    import pickletools
    payload = dumps({1: 1337, "2": 3.14, "asdf": "qwer"})
    up = CustomUnpickler(payload)

    pickletools.dis(payload)

    print("=" * 0x40)

    res = up.load()
    print(res)