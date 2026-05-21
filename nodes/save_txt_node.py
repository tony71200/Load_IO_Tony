from pathlib import Path

from .common import ANY, _clean_filename, _safe_mkdir


def _save_txt(text: str, output_dir: str, file_name: str = "", filename_prefix: str = "ComfyUI"):
    out_dir = _safe_mkdir(output_dir or ".")
    base = _clean_filename(file_name or filename_prefix or "ComfyUI")
    if not base.lower().endswith(".txt"):
        base += ".txt"
    out_path = str(Path(out_dir) / base)
    Path(out_path).write_text(text or "", encoding="utf-8")
    return out_path


def _extract_text_from_source(value, _depth: int = 0) -> str:
    if _depth > 8 or value is None:
        return ""
    if isinstance(value, str):
        return value
    if isinstance(value, (bytes, bytearray)):
        try:
            return value.decode("utf-8", errors="ignore")
        except Exception:
            return str(value)
    if isinstance(value, (int, float, bool)):
        return str(value)

    if isinstance(value, dict):
        preferred = [
            "text", "response", "content", "output", "result", "message", "caption",
        ]
        for key in preferred:
            if key in value:
                found = _extract_text_from_source(value.get(key), _depth + 1)
                if found:
                    return found
        for _, v in value.items():
            found = _extract_text_from_source(v, _depth + 1)
            if found:
                return found
        return ""

    if isinstance(value, (list, tuple, set)):
        parts = [_extract_text_from_source(v, _depth + 1) for v in value]
        parts = [p for p in parts if p]
        return "\n".join(parts)

    for attr in ["text", "response", "content", "output", "result", "message"]:
        if hasattr(value, attr):
            found = _extract_text_from_source(getattr(value, attr), _depth + 1)
            if found:
                return found
    return str(value)


class SaveTxt:
    @classmethod
    def INPUT_TYPES(cls):
        return {"required": {
            "source": (ANY,),
            "file_name": ("STRING", {"default": "", "multiline": False}), "mode": (["Auto save", "Manual save"], {"default": "Auto save"}),
            "output_dir": ("STRING", {"default": "", "multiline": False}), "filename_prefix": ("STRING", {"default": "ComfyUI", "multiline": False}),
            "manual_save_token": ("STRING", {"default": "", "multiline": False}),
        }}

    RETURN_TYPES = ("STRING", "BOOLEAN", "STRING")
    RETURN_NAMES = ("text", "done", "saved_path")
    FUNCTION = "save"
    CATEGORY = "Tony4896/IO"
    OUTPUT_NODE = True

    def save(self, source, file_name, mode, output_dir, filename_prefix, manual_save_token):
        text = _extract_text_from_source(source)
        if (mode or "Auto save") == "Auto save":
            return (text, True, _save_txt(text, output_dir, file_name, filename_prefix))
        return (text, True, manual_save_token) if manual_save_token else (text, False, "")
