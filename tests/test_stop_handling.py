import pickle

import pytest

import pickaxe


@pytest.mark.parametrize(
    ("crafter_cls", "method_name", "value", "expected"),
    [
        (pickaxe.Crafter, "push_str", "a.", "a."),
        (pickaxe.Crafter, "push_bytes", b"a.", b"a."),
        (pickaxe.AsciiCrafter, "push_bytes", b"a.", b"a."),
        (pickaxe.UnicodeCrafter, "push_str", "a.", "a."),
    ],
)
def test_trailing_dot_data_is_not_treated_as_stop(crafter_cls, method_name, value, expected):
    crafter = crafter_cls()
    getattr(crafter, method_name)(value)

    assert crafter.loads() == expected


def test_get_payload_appends_stop_for_empty_payload():
    crafter = pickaxe.Crafter()

    assert crafter.get_payload(check_stop=True) == pickle.STOP


def test_empty_payload_raises_pickle_error_instead_of_index_error():
    crafter = pickaxe.Crafter()

    with pytest.raises(pickle.UnpicklingError):
        crafter.loads()


@pytest.mark.parametrize("stopper_name", ["stop", "add_op"])
def test_explicit_stop_is_not_duplicated(stopper_name):
    crafter = pickaxe.Crafter()
    crafter.push_str("a.")

    if stopper_name == "stop":
        crafter.stop()
    else:
        crafter.add_op("STOP")

    assert crafter.get_payload(check_stop=True) == crafter.payload
    assert crafter.get_length(with_stop=True) == len(crafter.payload)


def test_get_length_with_stop_adds_implicit_stop_only_once():
    crafter = pickaxe.Crafter()
    crafter.push_bool(True)

    assert crafter.get_length(with_stop=True) == len(crafter.payload) + 1
