from io import StringIO
from pickle import dumps

from pickaxe import CustomUnpickler


payload = dumps({1: 1337, "2": 3.14, "asdf": "qwer"})


if __name__ == "__main__":
    print("[*] frame and memo events only")
    frame_and_memo = StringIO()
    up = CustomUnpickler(
        payload,
        trace_output=frame_and_memo,
        trace_events={"frame", "memo"},
    )
    print(up.load())
    print(frame_and_memo.getvalue().rstrip())

    print("=" * 0x40)

    print("[*] STOP opcode only")
    stop_only = StringIO()
    up = CustomUnpickler(
        payload,
        trace_output=stop_only,
        trace_ops={"STOP"},
        trace_events={"opcode"},
    )
    print(up.load())
    print(stop_only.getvalue().rstrip())
