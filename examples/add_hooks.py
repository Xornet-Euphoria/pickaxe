from pickaxe import CustomUnpickler


# define new hook function
# don't forget using original method
class MyCustomUnpickler(CustomUnpickler):
    def load_proto(self):
        print("trigger custom hook")
        super().load_proto()

        # get protocol number from reading bytes
        proto = int.from_bytes(self.read_buf, "little")
        print(f"  - proto: {proto}")


if __name__ == "__main__":
    import pickletools, pickle
    payload = pickle.dumps({1: 1337, "2": 3.14, "asdf": "qwer"})
    up = MyCustomUnpickler(payload)

    pickletools.dis(payload)

    print("=" * 0x40)

    res = up.load()
    print(res)