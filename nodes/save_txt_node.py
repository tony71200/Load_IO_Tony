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


class SaveTxt:
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
