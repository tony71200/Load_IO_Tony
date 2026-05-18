from pathlib import Path

from .common import _decode_escape_text, _normalize_path


def _split_text_file(txt_path: str, paragraph_sep: str, negative_sep: str):
    path = _normalize_path(txt_path)
    if not Path(path).is_file():
        raise FileNotFoundError(f"TXT file does not exist: {txt_path}")
    content = Path(path).read_text(encoding="utf-8-sig")
    psep = _decode_escape_text(paragraph_sep or "\\n\\n")
    nsep = _decode_escape_text(negative_sep or "###")
    blocks = [b.strip() for b in content.split(psep) if b.strip()]
    items = []
    for block in blocks:
        if nsep and nsep in block:
            pos, neg = block.split(nsep, 1)
            items.append((pos.strip(), neg.strip()))
        else:
            items.append((block.strip(), ""))
    return items


class TextSplitter:
    @classmethod
    def INPUT_TYPES(cls):
        return {"required": {
            "txt_path": ("STRING", {"default": "", "multiline": False}),
            "paragraph_sep": ("STRING", {"default": "\\n\\n", "multiline": False}),
            "negative_sep": ("STRING", {"default": "###", "multiline": False}),
            "index": ("INT", {"default": 0, "min": 0, "max": 999999, "step": 1}),
        }}

    RETURN_TYPES = ("STRING", "STRING", "INT", "BOOLEAN", "INT")
    RETURN_NAMES = ("positive_prompt", "negative_prompt", "next_index", "has_index", "current_index")
    FUNCTION = "split"
    CATEGORY = "Tony4896/IO"

    def split(self, txt_path, paragraph_sep, negative_sep, index):
        items = _split_text_file(txt_path, paragraph_sep, negative_sep)
        if not items:
            raise ValueError("TXT file has no valid paragraph after splitting.")
        idx = max(0, min(int(index), len(items) - 1))
        pos, neg = items[idx]
        return (pos, neg, idx + 1, (idx + 1) < len(items), idx)
