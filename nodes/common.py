import os
import re
import shutil
from pathlib import Path

import numpy as np
import torch
from PIL import Image, ImageOps

IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".bmp", ".webp", ".tif", ".tiff"}
ROOT_DIR = Path(__file__).resolve().parent.parent
TEMP_ROOT = ROOT_DIR / "_tony4896_temp"
TEMP_ROOT.mkdir(exist_ok=True)

try:
    import folder_paths
except Exception:
    folder_paths = None


class AnyType(str):
    def __ne__(self, __value):
        return False


ANY = AnyType("*")


def _decode_escape_text(value: str) -> str:
    if value is None:
        return ""
    try:
        return bytes(str(value), "utf-8").decode("unicode_escape")
    except Exception:
        return str(value)


def _safe_mkdir(path: str) -> str:
    path = os.path.abspath(os.path.expanduser(path or "."))
    os.makedirs(path, exist_ok=True)
    return path


def _clean_filename(name: str, default: str = "output") -> str:
    name = (name or "").strip() or default
    name = os.path.basename(name)
    name = re.sub(r'[<>:"/\\|?*\x00-\x1F]', "_", name).strip(" .")
    return name or default


def _safe_upload_filename(name: str, default_ext: str = "") -> str:
    name = os.path.basename(name or f"file{default_ext}")
    name = re.sub(r'[<>:"/\\|?*\x00-\x1F]', "_", name).strip(" .")
    if not name:
        name = f"file{default_ext}"
    return name


def _without_ext_and_parent(path: str) -> str:
    return Path(path).stem


def _candidate_dirs():
    dirs = [TEMP_ROOT]
    if folder_paths is not None:
        for attr in ["get_temp_directory", "get_input_directory", "get_output_directory"]:
            try:
                d = getattr(folder_paths, attr)()
                if d:
                    dirs.append(Path(d))
            except Exception:
                pass
    return dirs


def _find_by_basename(name: str):
    if not name:
        return None
    base = os.path.basename(name)
    for d in _candidate_dirs():
        if not d.exists():
            continue
        direct = d / base
        if direct.is_file():
            return str(direct)
        try:
            for p in d.rglob(base):
                if p.is_file():
                    return str(p)
        except Exception:
            pass
    return None


def _normalize_path(path: str) -> str:
    path = str(path or "").strip().strip('"')
    if not path:
        return ""
    if path.startswith("tony4896://"):
        rel = path.replace("tony4896://", "", 1).lstrip("/")
        return str((TEMP_ROOT / rel).resolve())
    p = Path(os.path.expanduser(path))
    if p.is_absolute():
        return str(p)
    found = _find_by_basename(path)
    if found:
        return found
    return str(Path(path).resolve())


def _is_safe_image_path(path: str) -> bool:
    try:
        p = Path(_normalize_path(path)).resolve()
    except Exception:
        return False
    return p.is_file() and p.suffix.lower() in IMAGE_EXTENSIONS


def _temp_size_bytes() -> int:
    total = 0
    if not TEMP_ROOT.exists():
        return 0
    for f in TEMP_ROOT.rglob("*"):
        try:
            if f.is_file():
                total += f.stat().st_size
        except Exception:
            pass
    return total


def _clear_temp_root():
    if TEMP_ROOT.exists():
        for child in TEMP_ROOT.iterdir():
            try:
                if child.is_dir():
                    shutil.rmtree(child, ignore_errors=True)
                else:
                    child.unlink(missing_ok=True)
            except Exception:
                pass
    TEMP_ROOT.mkdir(exist_ok=True)


def _list_images(folder_path: str):
    folder_path = _normalize_path(folder_path)
    folder = Path(folder_path)
    if not folder.exists() or not folder.is_dir():
        return []
    files = [str(child) for child in folder.iterdir() if child.is_file() and child.suffix.lower() in IMAGE_EXTENSIONS]
    return sorted(files, key=lambda x: os.path.basename(x).lower())


def _resolve_image_path(mode: str, image_path: str, folder_path: str, file_name: str = "", index: int = 0) -> str:
    mode = (mode or "Image").lower()
    if mode == "folder":
        images = _list_images(folder_path)
        if not images:
            raise FileNotFoundError(f"No supported images found in folder: {folder_path}")
        if file_name:
            for p in images:
                if os.path.basename(p) == file_name:
                    return p
        return images[max(0, min(int(index), len(images) - 1))]

    path = _normalize_path(image_path)
    if not path or not os.path.isfile(path):
        raise FileNotFoundError(f"Image path does not exist: {image_path}")
    if Path(path).suffix.lower() not in IMAGE_EXTENSIONS:
        raise ValueError(f"Unsupported image extension: {path}")
    return path


def _load_image_tensor(path: str):
    img = Image.open(path)
    img = ImageOps.exif_transpose(img).convert("RGB")
    width, height = img.size
    arr = np.array(img).astype(np.float32) / 255.0
    tensor = torch.from_numpy(arr)[None,]
    return tensor, width, height
