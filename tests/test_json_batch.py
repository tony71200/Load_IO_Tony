import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from Load_IO_Tony.nodes.json_batch_node import JsonBatch, _load_json_prompts  # noqa: E402

SAMPLE = {
    "app": "prompt-collector",
    "total": 45,
    "prompts": [
        {"index": 31, "text": "first prompt", "original": "x", "removed": [], "edited": False},
        {"index": 32, "text": "second prompt"},
        {"index": 33, "text": "third prompt"},
    ],
}


def _write(data, suffix=".json"):
    f = tempfile.NamedTemporaryFile("w", suffix=suffix, delete=False, encoding="utf-8")
    json.dump(data, f)
    f.close()
    return f.name


def test_reads_text_and_item_index():
    items = _load_json_prompts(_write(SAMPLE), "prompts", "text")
    assert items == [("first prompt", 31), ("second prompt", 32), ("third prompt", 33)]


def test_missing_item_index_falls_back_to_position():
    items = _load_json_prompts(_write({"prompts": [{"text": "a"}, {"text": "b"}]}), "prompts", "text")
    assert items == [("a", 0), ("b", 1)]


def test_node_outputs_and_clamping():
    path = _write(SAMPLE)
    node = JsonBatch()
    assert node.read(path, "prompts", "text", 0) == ("first prompt", 1, True, 0, 31)
    assert node.read(path, "prompts", "text", 2) == ("third prompt", 3, False, 2, 33)
    assert node.read(path, "prompts", "text", 99) == ("third prompt", 3, False, 2, 33)


def test_bad_keys_raise_clear_errors():
    path = _write(SAMPLE)
    for list_key, text_key in [("nope", "text"), ("prompts", "nope")]:
        try:
            _load_json_prompts(path, list_key, text_key)
        except KeyError as e:
            assert list_key in str(e) or text_key in str(e)
        else:
            raise AssertionError("expected KeyError")


def test_empty_list_raises():
    try:
        JsonBatch().read(_write({"prompts": []}), "prompts", "text", 0)
    except ValueError:
        pass
    else:
        raise AssertionError("expected ValueError")


def test_missing_file_raises():
    try:
        _load_json_prompts("Z:/does/not/exist.json", "prompts", "text")
    except FileNotFoundError:
        pass
    else:
        raise AssertionError("expected FileNotFoundError")


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            fn()
            print("ok", name)
