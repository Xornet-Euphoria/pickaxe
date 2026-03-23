import pickle
import pickletools

import pytest

import pickaxe


@pytest.mark.parametrize("crafter_cls", [pickaxe.Crafter, pickaxe.AsciiCrafter, pickaxe.UnicodeCrafter])
def test_push_str_updates_traced_stack_exactly(crafter_cls):
    crafter = crafter_cls()
    crafter.push_str("stack")

    assert crafter.stack_is_valid
    assert crafter.stack == ["stack"]


def test_to_tuple_tracks_exact_values():
    crafter = pickaxe.Crafter()
    crafter.push_int(7)
    crafter.push_str("x")

    crafter.to_tuple(2)

    assert crafter.stack_is_valid
    assert crafter.stack == [(7, "x")]


def test_add_op_tracks_setitem_on_exact_dict():
    crafter = pickaxe.Crafter()
    crafter.empty_dict()
    crafter.push_str("answer")
    crafter.push_int(42)

    crafter.add_op("SETITEM")

    assert crafter.stack_is_valid
    assert crafter.stack == [{"answer": 42}]
    assert crafter.loads() == {"answer": 42}


def test_memo_helpers_update_traced_state():
    crafter = pickaxe.Crafter()
    crafter.push_str("memo")
    crafter.memoize()
    crafter.get_memo(0)

    assert crafter.stack_is_valid
    assert crafter.memo_is_valid
    assert crafter.memo == {0: "memo"}
    assert crafter.stack == ["memo", "memo"]


def test_add_payload_invalidates_traced_state():
    crafter = pickaxe.Crafter()
    crafter.push_bool(True)

    crafter.add_payload(pickle.NEWFALSE)

    assert not crafter.stack_is_valid
    assert not crafter.memo_is_valid


def test_add_op_with_argument_invalidates_traced_state():
    crafter = pickaxe.Crafter()

    crafter.add_op("PROTO")

    assert crafter.payload == pickle.PROTO
    assert not crafter.stack_is_valid


def test_clear_resets_traced_state():
    crafter = pickaxe.Crafter()
    crafter.push_str("memo")
    crafter.memoize()
    crafter.add_payload(pickle.NEWFALSE)

    crafter.clear()

    assert crafter.payload == b""
    assert crafter.stack == []
    assert crafter.memo == {}
    assert crafter.stack_is_valid
    assert crafter.memo_is_valid


def test_import_from_without_stack_keeps_abstract_trace():
    crafter = pickaxe.Crafter()
    crafter.import_from("builtins", "id", use_stack=False)

    assert crafter.stack_is_valid
    assert len(crafter.stack) == 1
    assert isinstance(crafter.stack[-1], pickletools.StackObject)
    assert crafter.stack[-1].name == "any"


def test_unicode_stack_global_keeps_tracer_valid():
    crafter = pickaxe.UnicodeCrafter()
    crafter.import_from("os", "system")

    assert crafter.stack_is_valid
    assert len(crafter.stack) == 1
    assert isinstance(crafter.stack[-1], pickletools.StackObject)
    assert crafter.stack[-1].name == "any"
