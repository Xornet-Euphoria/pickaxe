from pathlib import Path
from pickle import dumps
from tempfile import gettempdir

from pickaxe import CustomUnpickler


payload = dumps({1: 1337, "2": 3.14, "asdf": "qwer"})
trace_path = Path(gettempdir()) / "pickaxe-trace.log"


if __name__ == "__main__":
    with trace_path.open("w", encoding="utf-8") as trace_file:
        up = CustomUnpickler(
            payload,
            trace_output=trace_file,
            trace_events={"frame", "memo"},
        )
        result = up.load()

    print(f"result: {result}")
    print(f"Trace written to: {trace_path}")
    print(trace_path.read_text(encoding="utf-8").rstrip())
