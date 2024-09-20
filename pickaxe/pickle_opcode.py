import pickletools
import typing


OpStr = typing.Literal['INT', 'BININT', 'BININT1', 'BININT2', 'LONG', 'LONG1', 'LONG4', 'STRING', 'BINSTRING', 'SHORT_BINSTRING', 'BINBYTES', 'SHORT_BINBYTES', 'BINBYTES8', 'BYTEARRAY8', 'NEXT_BUFFER', 'READONLY_BUFFER', 'NONE', 'NEWTRUE', 'NEWFALSE', 'UNICODE', 'SHORT_BINUNICODE', 'BINUNICODE', 'BINUNICODE8', 'FLOAT', 'BINFLOAT', 'EMPTY_LIST', 'APPEND', 'APPENDS', 'LIST', 'EMPTY_TUPLE', 'TUPLE', 'TUPLE1', 'TUPLE2', 'TUPLE3', 'EMPTY_DICT', 'DICT', 'SETITEM', 'SETITEMS', 'EMPTY_SET', 'ADDITEMS', 'FROZENSET', 'POP', 'DUP', 'MARK', 'POP_MARK', 'GET', 'BINGET', 'LONG_BINGET', 'PUT', 'BINPUT', 'LONG_BINPUT', 'MEMOIZE', 'EXT1', 'EXT2', 'EXT4', 'GLOBAL', 'STACK_GLOBAL', 'REDUCE', 'BUILD', 'INST', 'OBJ', 'NEWOBJ', 'NEWOBJ_EX', 'PROTO', 'STOP', 'FRAME', 'PERSID', 'BINPERSID']


all_ops = pickletools.opcodes
name_to_op = {op.name: op for op in all_ops}


def change_stack(op: pickletools.OpcodeInfo):
    stack_before = op.stack_before
    stack_after = op.stack_after

    return stack_before != stack_after


change_memo_ops = {
    name_to_op[op_str] for op_str in ["PUT", "BINPUT", "LONG_BINPUT", "MEMOIZE"]
}
def change_memo(op: pickletools.OpcodeInfo):
    return op in change_memo_ops


if __name__ == "__main__":
    print(name_to_op)