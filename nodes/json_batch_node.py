import json
from pathlib import Path

from .common import _normalize_path


def _load_json_prompts(json_path: str, list_key: str, text_key: str):
    path = Path(_normalize_path(json_path))
    if not path.is_file():
        raise FileNotFoundError(f"JSON file does not exist: {json_path}")
    data = json.loads(path.read_text(encoding="utf-8-sig"))
    list_key = list_key or "prompts"
    text_key = text_key or "text"
    if not isinstance(data, dict) or list_key not in data:
        raise KeyError(f"JSON has no '{list_key}' key: {json_path}")
    items = []
    for pos, item in enumerate(data[list_key]):
        if not isinstance(item, dict) or text_key not in item:
            raise KeyError(f"Item {pos} in '{list_key}' has no '{text_key}' key: {json_path}")
        items.append((str(item[text_key]).strip(), int(item.get("index", pos))))
    return items


class JsonBatch:
    @classmethod
    def INPUT_TYPES(cls):
        return {"required": {
            "json_path": ("STRING", {"default": "", "multiline": False}),
            "list_key": ("STRING", {"default": "prompts", "multiline": False}),
            "text_key": ("STRING", {"default": "text", "multiline": False}),
            "index": ("INT", {"default": 0, "min": 0, "max": 999999, "step": 1}),
        }}

    RETURN_TYPES = ("STRING", "INT", "BOOLEAN", "INT", "INT")
    RETURN_NAMES = ("prompt", "next_index", "has_index", "current_index", "prompt_index")
    FUNCTION = "read"
    CATEGORY = "Tony4896/IO"

    @classmethod
    def IS_CHANGED(cls, json_path, list_key, text_key, index):
        try:
            st = Path(_normalize_path(json_path)).stat()
            return f"{json_path}:{st.st_mtime_ns}:{st.st_size}:{list_key}:{text_key}:{index}"
        except OSError:
            return float("nan")

    def read(self, json_path, list_key, text_key, index):
        items = _load_json_prompts(json_path, list_key, text_key)
        if not items:
            raise ValueError(f"JSON list '{list_key or 'prompts'}' is empty.")
        idx = max(0, min(int(index), len(items) - 1))
        text, prompt_index = items[idx]
        return (text, idx + 1, (idx + 1) < len(items), idx, prompt_index)
