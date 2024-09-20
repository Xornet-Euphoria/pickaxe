from pickle import _Unpickler
from pickletools import code2op, OpcodeInfo # type: ignore
from typing import Any, Iterable, Callable, Self
import io, pickle, struct
from .pickle_opcode import change_stack, change_memo

# todo
"""
- protocol for typing
- breakpoint
- abstraction of stack operations (push or pop)
- abstraction of events
- custom formatter for pre and post hook functions
"""


class CustomUnpickler(_Unpickler):
    UnpicklerMethod = Callable[[Self], None]

    def __init__(self, file, *, fix_imports: bool = True, encoding: str = "ASCII", errors: str = "strict", buffers: Iterable[Any] | None = None, custom_dispatch_table={}) -> None:
        if isinstance(file, bytes) or isinstance(file, bytearray):
            file = io.BytesIO(file)

        # typing
        self.dispatch: dict[int, Callable[[Self], None]]
        self.stack: list[Any]
        self.memo: dict[int, Any]

        # todo: make them private
        self._file = file
        self.current_frame_idx = 0  # used for calculation of the index

        self.read_buf: bytes | None = None
        self._memo_ctx: tuple[int, Any] | None = None

        self.original_dispatch = {opcode: original_f for opcode, original_f in _Unpickler.dispatch.items()}

        self.create_custom_dispatch_table(defined_table=custom_dispatch_table)

        super().__init__(file, fix_imports=fix_imports, encoding=encoding, errors=errors, buffers=buffers)

    
    setattr_target = {"read", "readinto", "readline"}
    def __setattr__(self, name: str, value: Any) -> None:
        if name in self.setattr_target:
            _name = f"_{name}"
            return super().__setattr__(_name, value)
        return super().__setattr__(name, value)
    

    def set_hook(self, key: int, func: UnpicklerMethod) -> None:
        self.dispatch[key] = func
    

    def create_custom_dispatch_table(self, *, defined_table: dict[int, UnpicklerMethod]={}, pre_hook=None, post_hook=None):
        for opcode in _Unpickler.dispatch:
            # get overwridden method
            original_method = self.original_dispatch[opcode]
            method_name = original_method.__name__
            current_method = getattr(self.__class__, method_name)

            if opcode not in defined_table:
                internal_func = current_method
            else:
                internal_func = defined_table[opcode]

            if pre_hook is None:
                pre_hook = self.default_pre_hook

            if post_hook is None:
                post_hook = self.default_post_hook

            hook_func = self.create_hook(opcode, internal_func, pre_hook, post_hook)

            self.set_hook(opcode, hook_func)

    
    def create_hook(self, key: int, internal_func, pre_hook, post_hook):
        def hook(self: Self):
            op = code2op[chr(key)]
            dump_stack = change_stack(op)
            dump_memo = change_memo(op)

            pre_hook(op, dump_stack=dump_stack)
            internal_func(self)
            post_hook(op, dump_stack=dump_stack)

        return hook


    def default_pre_hook(self, op: OpcodeInfo, *,
                         dump_stack=False):
        unframer = self._unframer # type: ignore
        current_frame = unframer.current_frame
        in_frame = current_frame is not None

        ip = self.current_frame_idx + current_frame.tell() if in_frame else self._file.tell()
        ip -= 1  # subtract size of opcode

        print(f"[{ip}]: {op.name}")
        if dump_stack:
            print(f"  - [STACK (before)]: {self.stack}")


    def default_post_hook(self, op: OpcodeInfo, *,
                          dump_stack=False):
        if dump_stack:
            print(f"  - [STACK (after)]: {self.stack}")

        if self._memo_ctx is not None:
            print(f"  - [NEW MEMO ({self._memo_ctx[0]})]: {self._memo_ctx[1]}")
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
    

    def load_frame(self):
        # calculate the start position of a frame
        self.current_frame_idx = self._file.tell() + 8
        super().load_frame() # type: ignore
        assert self.read_buf is not None
        frame_size, = struct.unpack("<Q", self.read_buf)
        print(f"  - frame size: {frame_size}")


    def load_memoize(self):
        new_idx = len(self.memo)
        new_obj = self.stack[-1]

        self._memo_ctx = (new_idx, new_obj)
        super().load_memoize() # type: ignore


    # maybe useless
    def flush_read_buf(self):
        self.read_buf = None
