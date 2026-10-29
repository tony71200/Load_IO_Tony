import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from Load_IO_Tony.nodes.find_replace_node import FindAndReplace, _find_replace  # noqa: E402


def test_template_with_replace_in():
    out = _find_replace("2men at the beach, 2male again", "2men|2male", "{in} and other guy", "Ivan_Ryo")
    assert out == "Ivan_Ryo and other guy at the beach, Ivan_Ryo and other guy again"


def test_case_insensitive_substring():
    assert _find_replace("2Men and 2MALEs", "2men|2male", "x", whole_word=False) == "x and xs"


def test_whole_word_default_keeps_compound_tokens():
    f = "brief|briefs|underwear|shorts|sweatshorts"
    assert _find_replace("tnga_brief underwear", f, "X") == "tnga_brief X"
    assert _find_replace("cotton sweatshorts here", "shorts", "X") == "cotton sweatshorts here"
    assert _find_replace("briefly, boxer briefs.", f, "X") == "briefly, boxer X."


def test_whole_word_matches_symbol_alternatives():
    assert _find_replace("{char} walks", "{char}", "Ivan_Ryo") == "Ivan_Ryo walks"


def test_whole_word_off_is_substring():
    assert _find_replace("sweatshorts", "shorts", "X", whole_word=False) == "sweatX"


def test_empty_find_returns_text_unchanged():
    assert _find_replace("keep me", "", "x") == "keep me"
    assert _find_replace("keep me", " | ", "x") == "keep me"


def test_longest_alternative_wins():
    assert _find_replace("2men only here", "2men|2men only", "X") == "X here"


def test_replace_in_without_template_marker():
    assert _find_replace("a 2men", "2men", "", "Ivan_Ryo") == "a Ivan_Ryo"
    assert _find_replace("a 2men", "2men", "literal", "Ivan_Ryo") == "a literal"


def test_backslash_in_replacement_is_literal():
    assert _find_replace("a b", "b", r"c\1d") == r"a c\1d"


def test_alternatives_are_escaped():
    assert _find_replace("{char} walks (fast)", "{char}|(fast)", "Ivan_Ryo") == "Ivan_Ryo walks Ivan_Ryo"


def test_node_run():
    node = FindAndReplace()
    assert node.run("{char} walks", "{char}|{char2}", "Ivan_Ryo") == ("Ivan_Ryo walks",)
    assert node.run("2men here", "2men", "{in} and other guy", replace_in="Ivan_Ryo") == ("Ivan_Ryo and other guy here",)


def test_input_types_shape():
    types = FindAndReplace.INPUT_TYPES()
    assert list(types["required"]) == ["text", "find", "replace", "whole_word"]
    assert types["required"]["text"][1]["forceInput"] is True
    assert types["required"]["whole_word"][0] == "BOOLEAN"
    assert types["required"]["whole_word"][1]["default"] is True
    assert list(types["optional"]) == ["replace_in"]
    assert types["optional"]["replace_in"][1]["forceInput"] is True


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            fn()
            print("ok", name)
