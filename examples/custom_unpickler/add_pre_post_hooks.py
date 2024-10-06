from pickletools import OpcodeInfo
from pickaxe import CustomUnpickler


# define new hook function
class MyCustomUnpickler(CustomUnpickler):
    def pre_hook(self, op: OpcodeInfo, *, dump_stack=False):        
        super().pre_hook(op, dump_stack=dump_stack)

        if dump_stack and self.stack:
            print("[+] custom pre hook: dump the element on the TOS")
            print(f"    TOS: {self.stack[-1]}")


    def post_hook(self, op: OpcodeInfo, *, dump_stack=False):
        super().post_hook(op, dump_stack=dump_stack)
    
        if dump_stack and self.stack:
            print("[+] custom post hook: dump the element on the TOS")
            print(f"    TOS: {self.stack[-1]}")


if __name__ == "__main__":
    import pickletools, pickle
    payload = pickle.dumps({1: 1337, "2": 3.14, "asdf": "qwer"})
    up = MyCustomUnpickler(payload)

    pickletools.dis(payload)

    print("=" * 0x40)

    res = up.load()
    print(res)