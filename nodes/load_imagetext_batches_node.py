from pathlib import Path
from typing import Optional

from .common import _list_images, _load_image_tensor, _normalize_path


def _matching_txt_path(image_path: str, txt_folder_path: str) -> Optional[Path]:
    image = Path(image_path)
    txt_folder = Path(_normalize_path(txt_folder_path or str(image.parent)))
    if txt_folder.is_file():
        return txt_folder if txt_folder.suffix.lower() == ".txt" else None
    if not txt_folder.is_dir():
        return None

    expected = f"{image.stem}.txt"
    direct = txt_folder / expected
    if direct.is_file():
        return direct

    expected_lower = expected.lower()
    for child in txt_folder.iterdir():
        if child.is_file() and child.name.lower() == expected_lower:
            return child
    return None


def _split_prompt_content(content: str):
    if "###" in content:
        positive, negative = content.split("###", 1)
        return positive.strip(), negative.strip()
    return content.strip(), ""


class LoadImageTextBatch:
    @classmethod
    def INPUT_TYPES(cls):
        return {"required": {
            "folder_path": ("STRING", {"default": "", "multiline": False}),
            "txt_folder_path": ("STRING", {"default": "", "multiline": False}),
            "positive_prompt": ("STRING", {"default": "", "multiline": True}),
            "negative_prompt": ("STRING", {"default": "", "multiline": True}),
            "index": ("INT", {"default": 0, "min": 0, "max": 999999, "step": 1}),
        }}

    RETURN_TYPES = ("IMAGE", "STRING", "STRING", "INT")
    RETURN_NAMES = ("image", "positive", "negative", "index")
    FUNCTION = "load_batch"
    CATEGORY = "Tony4896/IO"

    @classmethod
    def IS_CHANGED(cls, folder_path, txt_folder_path, positive_prompt, negative_prompt, index):
        try:
            images = _list_images(folder_path)
            if not images:
                return float("nan")
            idx = max(0, min(int(index), len(images) - 1))
            image_path = images[idx]
            image_stat = Path(image_path).stat()
            txt_path = _matching_txt_path(image_path, txt_folder_path)
            txt_key = f"fallback:{positive_prompt}:{negative_prompt}"
            if txt_path is not None:
                txt_stat = txt_path.stat()
                txt_key = f"{txt_path}:{txt_stat.st_mtime_ns}:{txt_stat.st_size}"
            return f"{image_path}:{image_stat.st_mtime_ns}:{image_stat.st_size}:{txt_key}:{idx}"
        except Exception:
            return float("nan")

    def load_batch(self, folder_path, txt_folder_path, positive_prompt, negative_prompt, index):
        images = _list_images(folder_path)
        if not images:
            raise FileNotFoundError(f"No supported images found in folder: {folder_path}")

        idx = max(0, min(int(index), len(images) - 1))
        image_path = images[idx]
        tensor, _, _ = _load_image_tensor(image_path)

        txt_path = _matching_txt_path(image_path, txt_folder_path)
        if txt_path is not None:
            content = txt_path.read_text(encoding="utf-8-sig")
            positive, negative = _split_prompt_content(content)
        else:
            positive = positive_prompt or ""
            negative = negative_prompt or ""

        return (tensor, positive, negative, idx)
