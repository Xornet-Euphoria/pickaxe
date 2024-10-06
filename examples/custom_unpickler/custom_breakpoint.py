from pickaxe import CustomUnpickler


class MyCustomUnpickler(CustomUnpickler):
    def breakpoint_hook(self):
        if self._ip == 39:
            print(f"[BREAKPOINT] check memo ({self.ip})")
            print(f"  {self.memo}")
        elif self._ip == 46:
            print(f"[BREAKPOINT] change stack ({self.ip})")
            print(f"  - before: {self.stack}")
            print("    change stack[-1] to 'HACKED'")
            self.stack[-1] = "HACKED"
        else:
            print(f"[BREAKPOINT] nope")
        # return super().breakpoint_hook()


if __name__ == "__main__":
    from pickle import dumps
    import pickletools
    payload = dumps({1: 1337, "2": 3.14, "asdf": "qwer"})
    up = MyCustomUnpickler(payload)

    pickletools.dis(payload)

    print("=" * 0x40)

    up.set_breakpoint(39)
    up.set_breakpoint(46)

    res = up.load()
    print(res)