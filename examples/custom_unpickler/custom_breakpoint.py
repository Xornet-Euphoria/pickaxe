from pickaxe import CustomUnpickler


# class MyCustomUnpickler(CustomUnpickler):
#     def breakpoint_hook(self):
#         if self._ip == 39:
#             print(f"[BREAKPOINT] check memo ({self.ip})")
#             print(f"  {self.memo}")
#         elif self._ip == 46:
#             print(f"[BREAKPOINT] change stack ({self.ip})")
#             print(f"  - before: {self.stack}")
#             print("    change stack[-1] to 'HACKED'")
#             self.stack[-1] = "HACKED"
#         else:
#             print(f"[BREAKPOINT] nope")
#         # return super().breakpoint_hook()


def dump_memo(self: CustomUnpickler):
    print(f"[BREAKPOINT] check memo ({self.ip})")
    print(f"  {self.memo}")


def change_stack(self: CustomUnpickler):
    print(f"[BREAKPOINT] change stack ({self.ip})")
    print(f"  - before: {self.stack}")
    print("    change stack[-1] to 'HACKED'")
    self.stack[-1] = "HACKED"


if __name__ == "__main__":
    from pickle import dumps
    import pickletools, pprint
    payload = dumps({1: 1337, "2": 3.14, "asdf": "qwer"})
    up = CustomUnpickler(payload)

    pickletools.dis(payload)

    print("=" * 0x40)

    up.set_breakpoint(39, dump_memo)
    up.set_breakpoint(46, change_stack)
    up.set_breakpoint(47)

    pprint.pprint(up.breakpoints)

    res = up.load()
    print(res)