from pickaxe import CustomUnpickler


# Define a custom hook.
# Do not forget to call the original method.
class MyCustomUnpickler(CustomUnpickler):
    def load_proto(self):
        print("Custom hook triggered")
        super().load_proto()

        # Read the protocol number from the most recent bytes.
        proto = int.from_bytes(self.read_buf, "little")
        print(f"  - protocol: {proto}")


if __name__ == "__main__":
    import pickletools, pickle
    payload = pickle.dumps({1: 1337, "2": 3.14, "asdf": "qwer"})
    up = MyCustomUnpickler(payload)

    pickletools.dis(payload)

    print("=" * 0x40)

    res = up.load()
    print(res)
