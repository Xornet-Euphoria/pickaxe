import pickle
from .pickle_opcode import name_to_op


class Crafter:
    def __init__(self, *, forbidden_bytes: list[bytes] | list[int]=[], check_stop=False) -> None:
        self.payload = b""
        self.forbidden_bytes = [b if isinstance(b, int) else b[0] for b in forbidden_bytes]
        self.check_stop = check_stop  # reserved and not implemented yet


    # self.payload += b の wrapperに過ぎないが、オーバーライドしてデバッグに使うといった用途を考えている
    def add_payload(self, b: bytes):
        for _b in b:
            if _b in self.forbidden_bytes:
                raise ValueError(f"{_b.to_bytes(1, "little")} is forbidden")
        self.payload += b


    def add_op(self, op_str: str):
        if op_str not in name_to_op:
            raise ValueError(f"{op_str} is not a pickle opcode")
        self.add_payload(name_to_op[op_str])


    # experimental
    def push(self, x):
        if isinstance(x, int):
            self.push_int(x)
        elif isinstance(x, str):
            self.push_str(x)
        else:
            raise ValueError(f"not supported type for auto push: {type(x)}")


    def push_int(self, n: int):
        if -2**31 <= n < 2**31:
            self._push_small_number(n)
            return
        
        b = pickle.encode_long(n)
        length = len(b)
        if length < 256:
            self.add_payload(pickle.LONG1)
            self._add_number1(length)
        else:
            self.add_payload(pickle.LONG4)
            self._add_number4(length)

        self.add_payload(b)


    def _push_small_number(self, n: int, check=False):
        if check and (n < -2**31 or 2**31-1 < n):
            raise ValueError("small integer only")
        
        if n < 0 or 0xffff < n:
            self.add_payload(pickle.BININT)
            self._add_number_to_bytes(n, 4, signed=True)
            return

        if n < 0x100:
            self._push_int1(n)
            return

        if n < 0x10000:
            self._push_int2(n)
            return


    def _push_int1(self, n: int):
        self.add_payload(pickle.BININT1)
        self._add_number1(n)


    def _push_int2(self, n: int):
        self.add_payload(pickle.BININT2)
        self._add_number2(n)


    def _push_int4(self, n: int):
        self.add_payload(pickle.BININT)
        self._add_number4(n)


    def push_str(self, s: str):
        data = s.encode("utf-8")
        length = len(data)

        if length < 0x100:
            self.add_payload(pickle.SHORT_BINUNICODE)
            self._add_number1(length)
            self.add_payload(data)
            return
        
        if length < 2**32:
            self.add_payload(pickle.BINUNICODE)
            self._add_number4(length)
            self.add_payload(data)
            return

        # not tested
        if length < 2**64:
            self.add_payload(pickle.BINUNICODE8)
            self.add_payload(length.to_bytes(8, "little"))
            self.add_payload(data)

        raise ValueError(f"Too long string ({length} bytes)")


    # utils about list, tuple and dict

    def tuple(self):
        self.add_payload(pickle.TUPLE)


    def to_tuple(self, cnt: int=0, use_mark: bool=False):
        if cnt in range(0, 4) and not use_mark:
            self.add_payload(pickle._tuplesize2code[cnt])  # type: ignore
        else:
            # todo: check whether MARK(@) is used in the payload
            self.tuple()


    # utils about objects that is not pickle-native (import, function and etc)

    def import_from(self, module: str, name: str, *, use_stack=True):
        if use_stack:
            self.push_str(module)
            self.push_str(name)
            self.add_payload(pickle.STACK_GLOBAL)
        else:
            # shorter than STACK_GLOBAL
            # if other optimization techniques are used (for example, memoize frequently used strings)
            # this method may not be effective
            self.add_payload(pickle.GLOBAL)
            self.add_payload(module.encode("utf-8"))
            self._add_newline()
            self.add_payload(name.encode("utf-8"))
            self._add_newline()


    def call_f(self, argc: int=0, use_mark=False):
        self.to_tuple(argc, use_mark=use_mark)
        self.reduce()


    def reduce(self):
        self.add_payload(pickle.REDUCE)


    # simple wrappers

    def stop(self):
        self.add_payload(pickle.STOP)


    def mark(self):
        self.add_payload(pickle.MARK)


    # utils about memo
    # todo: emulate memo and estimate index in memoize
    # todo: put_memo

    def memoize(self):
        self.add_payload(pickle.MEMOIZE)


    def get_memo(self, idx: int):
        if idx < 0x100:
            self.add_payload(pickle.BINGET)
            self._add_number1(idx)
            return

        # todo: pickle.LONGBINGET
        self.add_payload(pickle.GET)
        self._add_number(idx)
        self._add_newline()


    def put_memo(self, idx: int):
        if idx < 0:
            raise ValueError("index must not be negative")
        
        if idx < 0x100:
            self.add_payload(pickle.BINPUT)
            self._add_number1(idx)
            return
        
        if idx < 2**32:
            self.add_payload(pickle.LONG_BINPUT)
            self._add_number4(idx)
            return
        
        self.add_payload(pickle.PUT)
        self._add_number(idx)
        self._add_newline()


    # interfaces about payload

    def get_payload(self, check_stop=False, *, check_function=None) -> bytes:
        if check_stop:
            if self.payload[-1] != ord(pickle.STOP):
                self.stop()

        if check_function is not None and not check_function(self.payload):
            raise ValueError("Payload check is not passed")

        return self.payload


    def get_length(self, with_stop: bool=False) -> int:
        l = len(self.payload)
        return l + 1 if with_stop else l


    def loads(self, check_stop=False, *, check_function=None):
        _payload = self.get_payload(check_stop, check_function=check_function)

        res = pickle.loads(_payload)
        return res


    def clear(self):
        self.payload = b""


    # utils for internal
    def _add_newline(self):
        self.add_payload(b"\n")


    def _add_number(self, n: int):
        self.add_payload(str(n).encode())


    def _add_number1(self, n: int):
        self._add_number_to_bytes(n, 1)


    def _add_number2(self, n: int):
        self._add_number_to_bytes(n, 2)


    def _add_number4(self, n: int):
        self._add_number_to_bytes(n, 4)


    def _add_number_to_bytes(self, n: int, length: int, *, signed=False):
        self.add_payload(n.to_bytes(length, "little", signed=signed))
