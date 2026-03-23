import pickle
import pickletools
from typing import Any
from .pickle_opcode import name_to_op, OpStr

_STACK_ANY = name_to_op["BINGET"].stack_after[0]
_STACK_MARK = name_to_op["MARK"].stack_after[0]
_STACK_LIST = name_to_op["APPEND"].stack_after[0]
_STACK_DICT = name_to_op["EMPTY_DICT"].stack_after[0]
_STACK_TUPLE = name_to_op["TUPLE"].stack_after[0]
_STACK_SET = name_to_op["EMPTY_SET"].stack_after[0]
_STACK_FROZENSET = name_to_op["FROZENSET"].stack_after[0]


class Crafter:
    def __init__(self, *, forbidden_bytes: list[bytes] | list[int] | None=None, check_stop=False) -> None:
        if forbidden_bytes is None:
            forbidden_bytes = []

        self._payload = b""
        self._stack: list[Any] = []
        self._memo: dict[int, Any] = {}
        self._trace_state_valid = True
        self._has_explicit_stop = False
        self.forbidden_bytes = [b if isinstance(b, int) else b[0] for b in forbidden_bytes]
        self.check_stop = check_stop  # Reserved for future use.


    @property
    def payload(self) -> bytes:
        return self._payload

    @property
    def stack(self) -> list[Any]:
        return list(self._stack)

    @property
    def memo(self) -> dict[int, Any]:
        return dict(self._memo)

    @property
    def stack_is_valid(self) -> bool:
        return self._trace_state_valid

    @property
    def memo_is_valid(self) -> bool:
        return self._trace_state_valid


    # Thin wrapper around `self.payload += b`; kept overridable for debugging.
    def add_payload(self, b: bytes):
        self._append_payload(b)
        self._invalidate_trace_state()


    def _append_payload(self, b: bytes, *, explicit_stop=False):
        for _b in b:
            if _b in self.forbidden_bytes:
                raise ValueError(f"{_b.to_bytes(1, 'little')} is forbidden")
        self._payload += b
        self._has_explicit_stop = explicit_stop


    # Convenience wrapper around opcode lookup and payload emission.
    def add_op(self, op_str: OpStr):
        op = self._append_opcode(op_str)
        if op.arg is not None:
            self._invalidate_trace_state()
            return
        self._apply_opcode(op)


    def _append_opcode(self, op_str: OpStr):
        op_str = op_str.upper()  # type: ignore
        if op_str not in name_to_op:
            raise ValueError(f"{op_str} is not a pickle opcode")

        op = name_to_op[op_str]
        self._append_payload(op.code.encode("latin-1"), explicit_stop=op_str == "STOP")
        return op


    def pop(self):
        self.add_op("POP")
    

    def dup(self):
        self.add_op("DUP")


    # Experimental convenience method.
    def push(self, x):
        if isinstance(x, bool):
            self.push_bool(x)
        elif isinstance(x, int):
            self.push_int(x)
        elif isinstance(x, str):
            self.push_str(x)
        elif isinstance(x, bytes):
            self.push_bytes(x)
        else:
            raise ValueError(f"unsupported type for automatic push: {type(x)}")
        

    def push_bool(self, b: bool):
        self.add_op("NEWTRUE") if b else self.add_op("NEWFALSE")


    def push_int(self, n: int):
        if -2**31 <= n < 2**31:
            self._push_small_number(n)
            return
        
        b = pickle.encode_long(n)
        length = len(b)
        if length < 256:
            self._append_opcode("LONG1")
            self._add_number1(length)
        else:
            self._append_opcode("LONG4")
            self._add_number4(length)

        self._append_payload(b)
        self._push_stack_value(n)


    def _push_small_number(self, n: int, check=False):
        if check and (n < -2**31 or 2**31-1 < n):
            raise ValueError("this helper only supports small integers")
        
        if n < 0 or 0xffff < n:
            self._append_opcode("BININT")
            self._add_number_to_bytes(n, 4, signed=True)
            self._push_stack_value(n)
            return

        if n < 0x100:
            self._push_int1(n)
            return

        if n < 0x10000:
            self._push_int2(n)
            return


    def _push_int1(self, n: int):
        self._append_opcode("BININT1")
        self._add_number1(n)
        self._push_stack_value(n)


    def _push_int2(self, n: int):
        self._append_opcode("BININT2")
        self._add_number2(n)
        self._push_stack_value(n)


    def _push_int4(self, n: int):
        self._append_opcode("BININT")
        self._add_number4(n)
        self._push_stack_value(n)


    def push_str(self, s: str):
        data = s.encode("utf-8")
        length = len(data)

        if length < 0x100:
            self._append_opcode("SHORT_BINUNICODE")
            self._add_number1(length)
            self._append_payload(data)
            self._push_stack_value(s)
            return
        
        if length < 2**32:
            self._append_opcode("BINUNICODE")
            self._add_number4(length)
            self._append_payload(data)
            self._push_stack_value(s)
            return

        # Fallback for very large Unicode strings.
        if length < 2**64:
            self._append_opcode("BINUNICODE8")
            self._append_payload(length.to_bytes(8, "little"))
            self._append_payload(data)
            self._push_stack_value(s)
            return

        raise ValueError(f"Too long string ({length} bytes)")


    def _push_short_bytes(self, b: bytes):
        l = len(b)
        if l > 0xff:
            raise ValueError("byte length must be smaller than 0x100")

        self._append_opcode("SHORT_BINBYTES")
        self._add_number1(l)
        self._append_payload(b)
        self._push_stack_value(b)


    def push_bytes(self, b: bytes):
        l = len(b)
        if l < 0x100:
            self._push_short_bytes(b)
        else:
            self._append_opcode("BINBYTES")
            self._add_number4(l)
            self._append_payload(b)
            self._push_stack_value(b)


    # Helpers for list, tuple, and dict payloads.

    def tuple(self):
        self.add_op("TUPLE")


    def to_tuple(self, cnt: int=0, use_mark: bool=False):
        if cnt in range(0, 4) and not use_mark:
            if cnt == 0:
                self.add_op("EMPTY_TUPLE")
            elif cnt == 1:
                self.add_op("TUPLE1")
            elif cnt == 2:
                self.add_op("TUPLE2")
            else:
                self.add_op("TUPLE3")
        else:
            # TODO: verify that MARK is present in the payload when needed.
            self.tuple()


    def empty_dict(self):
        self.add_op("EMPTY_DICT")


    # Helpers for non-native pickle objects such as imports and callables.

    def import_from(self, module: str, name: str, *, use_stack=True):
        if use_stack:
            self.push_str(module)
            self.push_str(name)
            self.add_op("STACK_GLOBAL")
        else:
            # Usually shorter than STACK_GLOBAL, although other optimizations
            # such as memoizing frequently used strings can change the result.
            self._append_opcode("GLOBAL")
            self._append_payload(module.encode("utf-8"))
            self._add_newline()
            self._append_payload(name.encode("utf-8"))
            self._add_newline()
            self._push_stack_value(_STACK_ANY)


    def call_f(self, argc: int=0, use_mark=False):
        self.to_tuple(argc, use_mark=use_mark)
        self.reduce()


    def reduce(self):
        self.add_op("REDUCE")


    # Simple opcode wrappers.

    def stop(self):
        self.add_op("STOP")


    def mark(self):
        self.add_op("MARK")


    def proto(self, proto=pickle.DEFAULT_PROTOCOL):
        if proto > 0xff:
            raise ValueError("the protocol number must fit in 1 byte")
        if proto < 0:
            raise ValueError("the protocol number must not be negative")
        
        self._append_opcode("PROTO")
        self._add_number1(proto)


    # Helpers for memo-related operations.
    # TODO: emulate memo growth and estimate the next index in memoize().

    def memoize(self):
        self.add_op("MEMOIZE")


    def get_memo(self, idx: int):
        if idx < 0x100:
            self._append_opcode("BINGET")
            self._add_number1(idx)
        elif idx < 2**32:
            self._append_opcode("LONG_BINGET")
            self._add_number4(idx)
        else:
            self._append_opcode("GET")
            self._add_number(idx)
            self._add_newline()

        self._push_stack_value(self._memo.get(idx, _STACK_ANY))


    def put_memo(self, idx: int):
        if idx < 0:
            raise ValueError("index must not be negative")
        
        if idx < 0x100:
            self._append_opcode("BINPUT")
            self._add_number1(idx)
        elif idx < 2**32:
            self._append_opcode("LONG_BINPUT")
            self._add_number4(idx)
        else:
            self._append_opcode("PUT")
            self._add_number(idx)
            self._add_newline()

        if not self._trace_state_valid:
            return

        if not self._stack:
            self._invalidate_trace_state()
            return

        self._memo[idx] = self._stack[-1]


    # Payload interfaces.

    def get_payload(self, check_stop=False, *, check_function=None) -> bytes:
        ret = self._payload
        if check_stop and not self._has_explicit_stop:
            ret += pickle.STOP

        if check_function is not None and not check_function(ret):
            raise ValueError("payload check failed")

        return ret


    def get_length(self, with_stop: bool=False) -> int:
        l = len(self._payload)
        return l + 1 if with_stop and not self._has_explicit_stop else l


    # Unlike get_payload(), the default value of check_stop is True.
    def loads(self, check_stop=True, *, check_function=None):
        _payload = self.get_payload(check_stop, check_function=check_function)

        res = pickle.loads(_payload)
        return res
    

    # Experimental helper. pickle.STOP is added automatically when needed.
    def disassemble(self):
        pickletools.dis(self.get_payload(check_stop=True))


    def disasm(self):
        self.disassemble()


    def dis(self):
        self.disassemble()


    def clear(self):
        self._payload = b""
        self._stack = []
        self._memo = {}
        self._trace_state_valid = True
        self._has_explicit_stop = False


    # Internal helpers.
    def _add_newline(self):
        self._append_payload(b"\n")


    def _add_number(self, n: int):
        self._append_payload(str(n).encode())


    def _add_number1(self, n: int):
        self._add_number_to_bytes(n, 1)


    def _add_number2(self, n: int):
        self._add_number_to_bytes(n, 2)


    def _add_number4(self, n: int):
        self._add_number_to_bytes(n, 4)


    def _add_number_to_bytes(self, n: int, length: int, *, signed=False):
        self._append_payload(n.to_bytes(length, "little", signed=signed))


    def _invalidate_trace_state(self):
        self._trace_state_valid = False


    def _push_stack_value(self, value):
        if not self._trace_state_valid:
            return
        self._stack.append(value)


    def _pop_n(self, cnt: int):
        if cnt < 0:
            raise ValueError("count must not be negative")
        if cnt == 0:
            return []
        if len(self._stack) < cnt:
            raise IndexError("stack underflow")

        values = self._stack[-cnt:]
        del self._stack[-cnt:]
        return values


    def _pop_marked_items(self):
        for idx in range(len(self._stack) - 1, -1, -1):
            if self._stack[idx] == _STACK_MARK:
                items = self._stack[idx + 1:]
                del self._stack[idx:]
                return items
        raise ValueError("MARK was not found in the traced stack")


    def _pop_marked_items_with_target(self):
        items = self._pop_marked_items()
        if not self._stack:
            raise IndexError("stack underflow")
        target = self._stack.pop()
        return target, items


    def _make_abstract_value(self, symbol):
        name = getattr(symbol, "name", None)
        if name == "tuple":
            return _STACK_TUPLE
        if name == "list":
            return _STACK_LIST
        if name == "dict":
            return _STACK_DICT
        if name == "set":
            return _STACK_SET
        if name == "frozenset":
            return _STACK_FROZENSET
        if name == "mark":
            return _STACK_MARK
        if name == "any":
            return _STACK_ANY
        return symbol


    def _apply_opcode(self, op: pickletools.OpcodeInfo):
        if not self._trace_state_valid:
            return

        try:
            op_name = op.name

            if op_name == "POP":
                self._pop_n(1)
                return

            if op_name == "DUP":
                self._push_stack_value(self._stack[-1])
                return

            if op_name == "MARK":
                self._push_stack_value(_STACK_MARK)
                return

            if op_name == "NEWTRUE":
                self._push_stack_value(True)
                return

            if op_name == "NEWFALSE":
                self._push_stack_value(False)
                return

            if op_name == "NONE":
                self._push_stack_value(None)
                return

            if op_name == "EMPTY_LIST":
                self._push_stack_value([])
                return

            if op_name == "EMPTY_TUPLE":
                self._push_stack_value(())
                return

            if op_name == "EMPTY_DICT":
                self._push_stack_value({})
                return

            if op_name == "EMPTY_SET":
                self._push_stack_value(set())
                return

            if op_name == "MEMOIZE":
                if not self._stack:
                    raise IndexError("stack underflow")
                self._memo[len(self._memo)] = self._stack[-1]
                return

            if op_name == "TUPLE":
                self._push_stack_value(tuple(self._pop_marked_items()))
                return

            if op_name in {"TUPLE1", "TUPLE2", "TUPLE3"}:
                cnt = int(op_name[-1])
                self._push_stack_value(tuple(self._pop_n(cnt)))
                return

            if op_name == "POP_MARK":
                self._pop_marked_items()
                return

            if op_name == "APPEND":
                target, item = self._pop_n(2)
                if isinstance(target, list):
                    target.append(item)
                    self._push_stack_value(target)
                else:
                    self._push_stack_value(_STACK_LIST)
                return

            if op_name == "APPENDS":
                target, items = self._pop_marked_items_with_target()
                if isinstance(target, list):
                    target.extend(items)
                    self._push_stack_value(target)
                else:
                    self._push_stack_value(_STACK_LIST)
                return

            if op_name == "SETITEM":
                target, key, value = self._pop_n(3)
                if isinstance(target, dict):
                    target[key] = value
                    self._push_stack_value(target)
                else:
                    self._push_stack_value(_STACK_DICT)
                return

            if op_name == "SETITEMS":
                target, items = self._pop_marked_items_with_target()
                if len(items) % 2 != 0:
                    raise ValueError("SETITEMS requires an even number of marked items")
                if isinstance(target, dict):
                    for idx in range(0, len(items), 2):
                        target[items[idx]] = items[idx + 1]
                    self._push_stack_value(target)
                else:
                    self._push_stack_value(_STACK_DICT)
                return

            if op_name == "ADDITEMS":
                target, items = self._pop_marked_items_with_target()
                if isinstance(target, set):
                    target.update(items)
                    self._push_stack_value(target)
                else:
                    self._push_stack_value(_STACK_SET)
                return

            if op_name == "LIST":
                self._push_stack_value(list(self._pop_marked_items()))
                return

            if op_name == "DICT":
                items = self._pop_marked_items()
                if len(items) % 2 != 0:
                    raise ValueError("DICT requires an even number of marked items")
                d = {}
                for idx in range(0, len(items), 2):
                    d[items[idx]] = items[idx + 1]
                self._push_stack_value(d)
                return

            if op_name == "FROZENSET":
                self._push_stack_value(frozenset(self._pop_marked_items()))
                return

            if op_name == "STOP":
                self._pop_n(1)
                return

            if op_name == "STACK_GLOBAL":
                self._pop_n(2)
                self._push_stack_value(_STACK_ANY)
                return

            if op_name == "REDUCE":
                self._pop_n(2)
                self._push_stack_value(_STACK_ANY)
                return

            if op_name == "BUILD":
                self._pop_n(2)
                self._push_stack_value(_STACK_ANY)
                return

            if op.stack_before:
                self._pop_n(len(op.stack_before))
            for symbol in op.stack_after:
                self._push_stack_value(self._make_abstract_value(symbol))
        except (IndexError, ValueError, TypeError):
            self._invalidate_trace_state()


# Payloads built by this crafter contain only ASCII-printable characters.
class AsciiCrafter(Crafter):
    def __init__(self, *, forbidden_bytes: list[bytes] | list[int] | None = None, check_stop=False) -> None:
        if forbidden_bytes is None:
            forbidden_bytes = []

        forbidden_bytes += [b.to_bytes(1, "little") for b in range(0x80, 0x100)]  # type: ignore
        super().__init__(forbidden_bytes=forbidden_bytes, check_stop=check_stop)


    # TODO: rewrite some methods.
    def push_bool(self, b: bool):
        self._append_opcode("INT")
        self._append_payload(b"01" if b else b"00")
        self._add_newline()
        self._push_stack_value(b)


    def push_int(self, n: int):
        self._append_opcode("INT")
        self._append_payload(str(n).encode())
        self._add_newline()
        self._push_stack_value(n)


    # Not optimized.
    def push_str(self, s: str):
        self._append_opcode("STRING")
        encoded = f"'{s}'".encode()
        self._append_payload(encoded)
        self._add_newline()
        self._push_stack_value(s)


    # use_mark is ignored.
    def to_tuple(self, cnt: int = 0, use_mark: bool=True):
        self.tuple()


    # use_stack is ignored.
    def import_from(self, module: str, name: str, *, use_stack=False):
        return super().import_from(module, name, use_stack=False)


class UnicodeCrafter(Crafter):
    # Override this because pickle.SHORT_BINUNICODE is b'\x8c' and may
    # raise UnicodeDecodeError when the payload must stay UTF-8 decodable.
    def push_str(self, s: str):
        data = s.encode("utf-8")
        length = len(data)

        if length < 0x100:
            self._append_opcode("SHORT_BINSTRING")
            self._add_number1(length)
            self._append_payload(data)
            self._push_stack_value(s)
            return
        
        if length < 2**32:
            self._append_opcode("BINSTRING")
            self._add_number4(length)
            self._append_payload(data)
            self._push_stack_value(s)
            return


        # Fallback for very large strings.
        self._append_opcode("STRING")
        self._append_payload(b"'")
        self._append_payload(data)
        self._append_payload(b"'")
        self._add_newline()
        self._push_stack_value(s)


    def stack_global(self):
        # u"\c293"
        self.put_memo(0xc2)  # Does not affect the stack.
        self._append_opcode("STACK_GLOBAL")
        self._apply_opcode(name_to_op["STACK_GLOBAL"])


    def import_from(self, module: str, name: str, *, use_stack=True):
        self.push(module)
        self.push(name)
        self.stack_global()


    def get_payload(self, check_stop=False, *, check_function=None) -> bytes:
        # If the payload is not valid UTF-8, this raises UnicodeDecodeError.
        check_function = lambda x: x.decode("utf-8")
        return super().get_payload(check_stop, check_function=check_function)
