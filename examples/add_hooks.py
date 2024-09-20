from pickaxe import CustomUnpickler


# define new hook function
# don't forget using original method
def load_proto(self):
    CustomUnpickler.load_proto(self)
    print(f"  - protocol: {self.proto}")


if __name__ == "__main__":
    import pickletools, pickle
    payload = pickle.dumps({1: 1337, "2": 3.14, "asdf": "qwer"})
    # set new hook functions
    up = CustomUnpickler(payload, custom_dispatch_table={pickle.PROTO[0]: load_proto})

    pickletools.dis(payload)

    print("=" * 0x40)

    res = up.load()
    print(res)