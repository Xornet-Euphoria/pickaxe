from dataclasses import dataclass
from pickle import _Unpickler
from pickletools import code2op, OpcodeInfo # type: ignore
from typing import Any, Iterable, Callable, Self, Literal, TypeAlias
import io, struct, sys
from .pickle_opcode import change_stack

# TODO
"""
- typing protocol
- abstraction for stack operations (push/pop)
- custom formatter helpers for pre/post hooks
- verbosity settings and long-output suppression
"""


TraceEventKind: TypeAlias = Literal["opcode", "stack_before", "stack_after", "memo", "frame", "breakpoint"]
TraceOutput: TypeAlias = Callable[[str], None] | io.TextIOBase
TraceFormatter: TypeAlias = Callable[["TraceEvent"], str | Iterable[str] | None]
TRACE_EVENT_KINDS: set[TraceEventKind] = {"opcode", "stack_before", "stack_after", "memo", "frame", "breakpoint"}


@dataclass(slots=True)
class TraceEvent:
    kind: TraceEventKind
    ip: int
    op: OpcodeInfo | None = None
    stack: list[Any] | None = None
    memo: dict[int, Any] | None = None
    memo_index: int | None = None
    memo_value: Any = None
    frame_size: int | None = None


class CustomUnpickler(_Unpickler):
    UnpicklerMethod = Callable[[Self], None]

    def __init__(
        self,
        file,
        *,
        fix_imports: bool = True,
        encoding: str = "ASCII",
        errors: str = "strict",
        buffers: Iterable[Any] | None = None,
        custom_dispatch_table: dict[int, UnpicklerMethod] | None = None,
        trace_output: TraceOutput | None = None,
        trace_ops: Iterable[str] | None = None,
        trace_events: Iterable[TraceEventKind] | None = None,
        trace_formatter: TraceFormatter | None = None,
    ) -> None:
        if isinstance(file, bytes) or isinstance(file, bytearray):
            file = io.BytesIO(file)

        if custom_dispatch_table is None:
            custom_dispatch_table = {}

        # Keep dispatch instance-local while preserving useful type hints.
        self.dispatch = {opcode: original_f for opcode, original_f in _Unpickler.dispatch.items()}
        self.stack: list[Any]
        self.memo: dict[int, Any]

        # TODO: make these private.
        self._file = file
        self.current_frame_idx = 0  # Used to calculate the absolute opcode index.
        self._breakpoint_table = {}
        self._ip = 0
        self._current_op: OpcodeInfo | None = None

        self.read_buf: bytes = b""
        self._memo_ctx: tuple[int, Any] | None = None
        self._trace_formatter = trace_formatter or self.format_trace_event

        self.original_dispatch = self.dispatch.copy()
        self.set_trace_output(trace_output)
        self.set_trace_filter(ops=trace_ops, events=trace_events)

        self.create_custom_dispatch_table(defined_table=custom_dispatch_table)

        super().__init__(file, fix_imports=fix_imports, encoding=encoding, errors=errors, buffers=buffers)


    @property
    def breakpoints(self) -> dict[int, Callable[[Self], None]]:
        return self._breakpoint_table
    

    @property
    def ip(self) -> int:
        return self._ip

    
    setattr_target = {"read", "readinto", "readline"}
    def __setattr__(self, name: str, value: Any) -> None:
        if name in self.setattr_target:
            _name = f"_{name}"
            return super().__setattr__(_name, value)
        return super().__setattr__(name, value)
    

    def set_hook(self, key: int, func: UnpicklerMethod) -> None:
        self.dispatch[key] = func


    def set_trace_output(self, output: TraceOutput | None) -> None:
        self._trace_output = sys.stdout if output is None else output


    def set_trace_filter(self, *, ops: Iterable[str] | None = None, events: Iterable[TraceEventKind] | None = None) -> None:
        normalized_events = None if events is None else set(events)
        if normalized_events is not None:
            unknown_events = normalized_events - TRACE_EVENT_KINDS
            if unknown_events:
                raise ValueError(f"unknown trace event kind(s): {sorted(unknown_events)}")

        self._trace_ops = None if ops is None else {op.upper() for op in ops}
        self._trace_events = normalized_events


    def should_emit_trace_event(self, event: TraceEvent) -> bool:
        if self._trace_events is not None and event.kind not in self._trace_events:
            return False

        if self._trace_ops is not None:
            if event.op is None or event.op.name not in self._trace_ops:
                return False

        return True


    def emit_trace_event(self, event: TraceEvent) -> None:
        if not self.should_emit_trace_event(event):
            return

        lines = self._trace_formatter(event)
        if lines is None:
            return

        if isinstance(lines, str):
            lines = [lines]

        for line in lines:
            if callable(self._trace_output):
                self._trace_output(line)
            else:
                self._trace_output.write(f"{line}\n")


    def format_trace_event(self, event: TraceEvent):
        if event.kind == "opcode":
            return f"[{event.ip}]: {event.op.name}"

        if event.kind == "stack_before":
            return f"  - [STACK (before)]: {event.stack}"

        if event.kind == "stack_after":
            return f"  - [STACK (after)]: {event.stack}"

        if event.kind == "memo":
            return f"  - [MEMO ({event.memo_index})]: {event.memo_value}"

        if event.kind == "frame":
            return f"  - frame size: {event.frame_size}"

        if event.kind == "breakpoint":
            return [
                f"[BREAKPOINT] {event.ip}",
                f"  - [STACK]: {event.stack}",
                f"  - [MEMO]: {event.memo}",
            ]

        raise ValueError(f"unsupported trace event kind: {event.kind}")
    

    def create_custom_dispatch_table(self, *, defined_table: dict[int, UnpicklerMethod] | None = None):
        if defined_table is None:
            defined_table = {}

        for opcode in _Unpickler.dispatch:
            # Resolve the overridden method for this opcode.
            original_method = self.original_dispatch[opcode]
            method_name = original_method.__name__
            current_method = getattr(self.__class__, method_name)

            if opcode not in defined_table:
                internal_func = current_method
            else:
                internal_func = defined_table[opcode]

            hook_func = self.create_hook(opcode, internal_func)

            self.set_hook(opcode, hook_func)

    
    def create_hook(self, key: int, internal_func):
        def hook(self: Self):
            op = code2op[chr(key)]
            dump_stack = change_stack(op)

            unframer = self._unframer # type: ignore
            current_frame = unframer.current_frame
            in_frame = current_frame is not None

            ip = self.current_frame_idx + current_frame.tell() if in_frame else self._file.tell()
            ip -= 1  # Subtract the size of the opcode itself.

            self._ip = ip
            self._current_op = op

            if self._ip in self._breakpoint_table:
                self._breakpoint_table[self.ip](self)

            self.pre_hook(op, dump_stack=dump_stack)
            internal_func(self)
            self.post_hook(op, dump_stack=dump_stack)

        return hook


    # Override this to customize the pre-hook.
    def pre_hook(self, op: OpcodeInfo, *,
                         dump_stack=False):
        self.emit_trace_event(TraceEvent(kind="opcode", ip=self._ip, op=op))
        if dump_stack:
            self.emit_trace_event(TraceEvent(kind="stack_before", ip=self._ip, op=op, stack=list(self.stack)))

    # Override this to customize the post-hook.
    def post_hook(self, op: OpcodeInfo, *,
                          dump_stack=False):
        if dump_stack:
            self.emit_trace_event(TraceEvent(kind="stack_after", ip=self._ip, op=op, stack=list(self.stack)))

        if self._memo_ctx is not None:
            self.emit_trace_event(
                TraceEvent(
                    kind="memo",
                    ip=self._ip,
                    op=op,
                    memo_index=self._memo_ctx[0],
                    memo_value=self._memo_ctx[1],
                )
            )
            self._memo_ctx = None


    def read(self, n: int) -> bytes:
        data = self._read(n) # type: ignore
        self.read_buf = data

        return data
    

    def readinto(self, buf) -> bytes:
        data = self._readinto(buf) # type: ignore
        self.read_buf = data

        return data
    

    def readline(self) -> bytes:
        data = self._readline() # type: ignore
        self.read_buf = data

        return data
    

    def set_breakpoint(self, idx: int, f=None) -> None:
        if f is None:
            f = CustomUnpickler.default_breakpoint_hook
        
        self._breakpoint_table[idx] = f


    # Override this to customize breakpoint handling.
    def breakpoint_hook(self):
        self.emit_trace_event(
            TraceEvent(
                kind="breakpoint",
                ip=self._ip,
                op=self._current_op,
                stack=list(self.stack),
                memo=dict(self.memo),
            )
        )


    @staticmethod
    def default_breakpoint_hook(_self):
        _self.breakpoint_hook()


    def load_frame(self):
        # Calculate the start position of the current frame.
        self.current_frame_idx = self._file.tell() + 8
        super().load_frame() # type: ignore
        frame_size, = struct.unpack("<Q", self.read_buf)
        self.emit_trace_event(
            TraceEvent(
                kind="frame",
                ip=self._ip,
                op=self._current_op,
                frame_size=frame_size,
            )
        )


    def load_memoize(self):
        new_idx = len(self.memo)
        new_obj = self.stack[-1]

        self._memo_ctx = (new_idx, new_obj)
        super().load_memoize() # type: ignore


    # May be unnecessary, but useful while debugging.
    def flush_read_buf(self):
        self.read_buf = b""
