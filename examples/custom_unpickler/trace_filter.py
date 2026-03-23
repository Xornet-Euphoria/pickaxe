from pickle import dumps

from pickaxe import CustomUnpickler


payload = dumps({1: 1337, "2": 3.14, "asdf": "qwer"})


if __name__ == "__main__":
    print("[*] Frame and memo events only")
    up = CustomUnpickler(
        payload,
        trace_events={"frame", "memo"},
    )
    print(f"result: {up.load()}")

    print("=" * 0x40)

    print("[*] STOP opcode only")
    up = CustomUnpickler(
        payload,
        trace_ops={"STOP"},
        trace_events={"opcode"},
    )
    print(f"result: {up.load()}")
