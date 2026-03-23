import io
import pickle
import pickletools

import pickaxe


TEST_OBJECT = {1: 1337, "2": 3.14, "asdf": "qwer"}
TEST_PAYLOAD = pickle.dumps(TEST_OBJECT, protocol=4)


def find_opcode_position(name: str, *, payload=TEST_PAYLOAD, occurrence=0) -> int:
    seen = 0
    for op, _arg, pos in pickletools.genops(payload):
        if op.name != name:
            continue

        if seen == occurrence:
            return pos

        seen += 1

    raise AssertionError(f"opcode {name} not found")


def test_trace_output_can_be_redirected_and_reports_core_events():
    trace = io.StringIO()
    up = pickaxe.CustomUnpickler(TEST_PAYLOAD, trace_output=trace)

    assert up.load() == TEST_OBJECT
    assert up.ip == find_opcode_position("STOP")

    output = trace.getvalue()
    assert "[0]: PROTO" in output
    assert "frame size:" in output
    assert "[STACK (before)]" in output
    assert "[STACK (after)]" in output
    assert "[NEW MEMO" in output


def test_trace_filter_can_select_specific_opcode_events():
    trace = io.StringIO()
    stop_pos = find_opcode_position("STOP")
    up = pickaxe.CustomUnpickler(
        TEST_PAYLOAD,
        trace_output=trace,
        trace_ops={"STOP"},
        trace_events={"opcode"},
    )

    assert up.load() == TEST_OBJECT
    assert trace.getvalue().splitlines() == [f"[{stop_pos}]: STOP"]


def test_trace_filter_can_select_multiple_event_types():
    trace = io.StringIO()
    up = pickaxe.CustomUnpickler(
        TEST_PAYLOAD,
        trace_output=trace,
        trace_events={"frame", "memo"},
    )

    assert up.load() == TEST_OBJECT

    lines = trace.getvalue().splitlines()
    assert len(lines) == 5
    assert lines[0].startswith("  - frame size: ")
    assert all("[NEW MEMO" in line for line in lines[1:])


def test_breakpoint_default_hook_dumps_stack_and_memo():
    trace = io.StringIO()
    breakpoint_pos = find_opcode_position("SETITEMS")
    up = pickaxe.CustomUnpickler(
        TEST_PAYLOAD,
        trace_output=trace,
        trace_events={"breakpoint"},
    )
    up.set_breakpoint(breakpoint_pos)

    assert up.load() == TEST_OBJECT

    output = trace.getvalue()
    assert f"[BREAKPOINT] {breakpoint_pos}" in output
    assert "[STACK]" in output
    assert "[MEMO]" in output
    assert "asdf" in output


def test_overridden_breakpoint_hook_is_used_when_no_callback_is_passed():
    breakpoint_pos = find_opcode_position("SETITEMS")

    class BreakpointRecorder(pickaxe.CustomUnpickler):
        def __init__(self, file):
            self.breakpoint_hits = []
            super().__init__(file, trace_output=io.StringIO(), trace_events=set())

        def breakpoint_hook(self):
            self.breakpoint_hits.append((self.ip, list(self.stack), dict(self.memo)))

    up = BreakpointRecorder(TEST_PAYLOAD)
    up.set_breakpoint(breakpoint_pos)

    assert up.load() == TEST_OBJECT
    assert len(up.breakpoint_hits) == 1
    assert up.breakpoint_hits[0][0] == breakpoint_pos
    assert up.breakpoint_hits[0][1][-1] == "qwer"
    assert up.breakpoint_hits[0][2][2] == "asdf"


def test_custom_dispatch_table_can_override_original_loader():
    seen_protocols = []

    def custom_proto_loader(self: pickaxe.CustomUnpickler):
        self.original_dispatch[pickle.PROTO[0]](self)
        seen_protocols.append(int.from_bytes(self.read_buf, "little"))

    up = pickaxe.CustomUnpickler(
        TEST_PAYLOAD,
        trace_output=io.StringIO(),
        custom_dispatch_table={pickle.PROTO[0]: custom_proto_loader},
    )

    assert up.load() == TEST_OBJECT
    assert seen_protocols == [4]


def test_trace_output_can_use_callable_writer():
    lines = []
    up = pickaxe.CustomUnpickler(
        TEST_PAYLOAD,
        trace_output=lines.append,
        trace_events={"frame"},
    )

    assert up.load() == TEST_OBJECT
    assert len(lines) == 1
    assert lines[0].startswith("  - frame size: ")
