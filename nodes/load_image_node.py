from pathlib import Path

from .common import _load_image_tensor, _resolve_image_path, _without_ext_and_parent


class LoadImage:
    @classmethod
    def INPUT_TYPES(cls):
        return {"required": {
            "mode": (["Image", "Folder"], {"default": "Image"}),
            "image_path": ("STRING", {"default": "", "multiline": False}),
            "folder_path": ("STRING", {"default": "", "multiline": False}),
            "file_name": ("STRING", {"default": "", "multiline": False}),
            "selected_index": ("INT", {"default": 0, "min": 0, "max": 999999, "step": 1}),
        }}

    RETURN_TYPES = ("IMAGE", "STRING", "INT", "INT", "STRING")
    RETURN_NAMES = ("image", "file_name", "width", "height", "size")
    FUNCTION = "load"
    CATEGORY = "Tony4896/IO"

    @classmethod
    def IS_CHANGED(cls, mode, image_path, folder_path, file_name, selected_index):
        try:
            p = _resolve_image_path(mode, image_path, folder_path, file_name, selected_index)
            st = Path(p).stat()
            return f"{p}:{st.st_mtime_ns}:{st.st_size}"
        except Exception:
            return float("nan")

    def load(self, mode, image_path, folder_path, file_name, selected_index):
        path = _resolve_image_path(mode, image_path, folder_path, file_name, selected_index)
        tensor, w, h = _load_image_tensor(path)
        return (tensor, _without_ext_and_parent(path), w, h, f"{w} x {h}")
