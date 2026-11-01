import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from Load_IO_Tony.nodes.common import FlexibleOptionalInputType  # noqa: E402
from Load_IO_Tony.nodes.select_random_node import SelectRandom, _collect_items  # noqa: E402

ITEMS = {"item_10": "ten", "item_2": " two ", "item_1": "one"}


def test_collect_sorts_numerically_and_strips():
    assert _collect_items(ITEMS) == ["one", "two", "ten"]


def test_collect_skips_blank_and_foreign_keys():
    assert _collect_items({"item_1": "   ", "item_2": "b", "other": "x", "item_x": "y"}) == ["b"]


def test_pick_by_index():
    node = SelectRandom()
    assert node.pick(0, **ITEMS) == ("one",)
    assert node.pick(2, **ITEMS) == ("ten",)


def test_pick_clamps_index():
    node = SelectRandom()
    assert node.pick(99, **ITEMS) == ("ten",)
    assert node.pick(-5, **ITEMS) == ("one",)


def test_pick_without_items_raises():
    try:
        SelectRandom().pick(0)
    except ValueError:
        pass
    else:
        raise AssertionError("expected ValueError")


def test_flexible_optional_accepts_any_key_but_lists_none():
    opt = FlexibleOptionalInputType("STRING")
    assert "item_7" in opt
    assert opt["item_7"] == ("STRING",)
    assert list(opt) == []


def test_input_types():
    types = SelectRandom.INPUT_TYPES()
    assert types["required"]["index"][1]["control_after_generate"] is True
    assert isinstance(types["optional"], FlexibleOptionalInputType)


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            fn()
            print("ok", name)
