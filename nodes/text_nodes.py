from pathlib import Path

from .common import ANY, _clean_filename, _decode_escape_text, _normalize_path, _safe_mkdir


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


def _save_txt(text: str, output_dir: str, file_name: str = "", filename_prefix: str = "ComfyUI"):
    out_dir = _safe_mkdir(output_dir or ".")
    base = _clean_filename(file_name or filename_prefix or "ComfyUI")
    if not base.lower().endswith(".txt"):
        base += ".txt"
    out_path = str(Path(out_dir) / base)
    Path(out_path).write_text(text or "", encoding="utf-8")
    return out_path


class Tony4896TextSplitterBatches:
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


class Tony4896SaveTxt:
    @classmethod
    def INPUT_TYPES(cls):
        return {"required": {
            "source": (ANY,), "text": ("STRING", {"forceInput": True, "default": "", "multiline": True}),
            "file_name": ("STRING", {"default": "", "multiline": False}), "mode": (["Auto save", "Manual save"], {"default": "Auto save"}),
            "output_dir": ("STRING", {"default": "", "multiline": False}), "filename_prefix": ("STRING", {"default": "ComfyUI", "multiline": False}),
            "manual_save_token": ("STRING", {"default": "", "multiline": False}),
        }}

    RETURN_TYPES = ("STRING", "BOOLEAN", "STRING")
    RETURN_NAMES = ("text", "done", "saved_path")
    FUNCTION = "save"
    CATEGORY = "Tony4896/IO"
    OUTPUT_NODE = True

    def save(self, source, text, file_name, mode, output_dir, filename_prefix, manual_save_token):
        text = "" if text is None else str(text)
        if (mode or "Auto save") == "Auto save":
            return (text, True, _save_txt(text, output_dir, file_name, filename_prefix))
        return (text, True, manual_save_token) if manual_save_token else (text, False, "")
