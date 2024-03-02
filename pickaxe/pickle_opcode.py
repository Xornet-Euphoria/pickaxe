import pickletools


all_ops = pickletools.opcodes
name_to_op = {op.name: op.code.encode("latin-1") for op in all_ops}


if __name__ == "__main__":
    print(name_to_op)