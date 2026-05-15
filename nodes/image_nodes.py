import os
from pathlib import Path

from .common import _list_images, _load_image_tensor, _resolve_image_path, _without_ext_and_parent


class Tony4896LoadImage:
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


class Tony4896LoadImageBatches:
    @classmethod
    def INPUT_TYPES(cls):
        return {"required": {
            "folder_path": ("STRING", {"default": "", "multiline": False}),
            "file_name": ("STRING", {"default": "", "multiline": False}),
            "index": ("INT", {"default": 0, "min": 0, "max": 999999, "step": 1}),
        }}

    RETURN_TYPES = ("IMAGE", "STRING", "INT", "INT", "INT", "BOOLEAN", "STRING")
    RETURN_NAMES = ("image", "file_name", "width", "height", "next_index", "has_index", "size")
    FUNCTION = "load_batch"
    CATEGORY = "Tony4896/IO"

    @classmethod
    def IS_CHANGED(cls, folder_path, file_name, index):
        try:
            images = _list_images(folder_path)
            if not images:
                return float("nan")
            idx = max(0, min(int(index), len(images) - 1))
            if file_name:
                for i, p in enumerate(images):
                    if os.path.basename(p) == file_name:
                        idx = i
                        break
            p = images[idx]
            st = Path(p).stat()
            return f"{p}:{st.st_mtime_ns}:{st.st_size}"
        except Exception:
            return float("nan")

    def load_batch(self, folder_path, file_name, index):
        images = _list_images(folder_path)
        if not images:
            raise FileNotFoundError(f"No supported images found in folder: {folder_path}")
        idx = max(0, min(int(index), len(images) - 1))
        if file_name:
            for i, p in enumerate(images):
                if os.path.basename(p) == file_name:
                    idx = i
                    break
        path = images[idx]
        tensor, w, h = _load_image_tensor(path)
        next_index = idx + 1
        has_index = next_index < len(images)
        return (tensor, _without_ext_and_parent(path), w, h, next_index, has_index, f"{w} x {h}")
