import os
import re
import time
import uuid
import shutil
from pathlib import Path

import numpy as np
import torch
from PIL import Image, ImageOps

WEB_DIRECTORY = "./web"

IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".bmp", ".webp", ".tif", ".tiff"}
ROOT_DIR = Path(__file__).resolve().parent
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
    """Return only the file stem.

    Previous versions returned "parent/stem" for uploaded files, which leaked the
    random temp folder id into the output file_name. The expected ComfyUI-style
    value is just the image name without extension.
    """
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
        # bounded recursive search for browser-upload temp files
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
    # Support values returned by the web uploader.
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
    if not p.is_file() or p.suffix.lower() not in IMAGE_EXTENSIONS:
        return False
    # Allow files selected through Tony temp, ComfyUI temp/input/output, or manually pasted absolute paths.
    # Manual absolute paths are needed by this node's design; extension check still prevents arbitrary file serving.
    return True


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
    files = []
    for child in folder.iterdir():
        if child.is_file() and child.suffix.lower() in IMAGE_EXTENSIONS:
            files.append(str(child))
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
        idx = max(0, min(int(index), len(images) - 1))
        return images[idx]

    path = _normalize_path(image_path)
    if not path or not os.path.isfile(path):
        raise FileNotFoundError(f"Image path does not exist: {image_path}")
    if Path(path).suffix.lower() not in IMAGE_EXTENSIONS:
        raise ValueError(f"Unsupported image extension: {path}")
    return path


def _load_image_tensor(path: str):
    img = Image.open(path)
    img = ImageOps.exif_transpose(img)
    img = img.convert("RGB")
    width, height = img.size
    arr = np.array(img).astype(np.float32) / 255.0
    tensor = torch.from_numpy(arr)[None,]
    return tensor, width, height


def _split_text_file(txt_path: str, paragraph_sep: str, negative_sep: str):
    path = _normalize_path(txt_path)
    if not os.path.isfile(path):
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
    out_path = os.path.join(out_dir, base)
    Path(out_path).write_text(text or "", encoding="utf-8")
    return out_path


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
        next_index = idx + 1
        has_index = next_index < len(items)
        return (pos, neg, next_index, has_index, idx)


class Tony4896SaveTxt:
    @classmethod
    def INPUT_TYPES(cls):
        return {"required": {
            "source": (ANY,),
            "text": ("STRING", {"forceInput": True, "default": "", "multiline": True}),
            "file_name": ("STRING", {"default": "", "multiline": False}),
            "mode": (["Auto save", "Manual save"], {"default": "Auto save"}),
            "output_dir": ("STRING", {"default": "", "multiline": False}),
            "filename_prefix": ("STRING", {"default": "ComfyUI", "multiline": False}),
            "manual_save_token": ("STRING", {"default": "", "multiline": False}),
        }}

    RETURN_TYPES = ("STRING", "BOOLEAN", "STRING")
    RETURN_NAMES = ("text", "done", "saved_path")
    FUNCTION = "save"
    CATEGORY = "Tony4896/IO"
    OUTPUT_NODE = True

    def save(self, source, text, file_name, mode, output_dir, filename_prefix, manual_save_token):
        text = "" if text is None else str(text)
        mode = mode or "Auto save"
        if mode == "Auto save":
            path = _save_txt(text, output_dir, file_name, filename_prefix)
            return (text, True, path)
        # Manual mode: clicking the frontend button writes a unique token/path into manual_save_token.
        if manual_save_token:
            return (text, True, manual_save_token)
        return (text, False, "")


class Tony4896DelayTime:
    @classmethod
    def INPUT_TYPES(cls):
        return {"required": {
            "query_finish": ("BOOLEAN", {"forceInput": True, "default": False}),
            "has_index": ("BOOLEAN", {"forceInput": True, "default": False}),
            "next_index": ("INT", {"forceInput": True, "default": 0, "min": 0, "max": 999999, "step": 1}),
            "delay_seconds": ("FLOAT", {"default": 1.0, "min": 0.0, "max": 86400.0, "step": 0.1}),
        }}

    RETURN_TYPES = ("INT", "BOOLEAN")
    RETURN_NAMES = ("next_index", "continue")
    FUNCTION = "delay"
    CATEGORY = "Tony4896/IO"

    def delay(self, query_finish, has_index, next_index, delay_seconds):
        should_continue = bool(query_finish) and bool(has_index)
        if should_continue:
            time.sleep(float(delay_seconds or 0))
            return (int(next_index), True)
        return (int(next_index), False)


NODE_CLASS_MAPPINGS = {
    "Tony4896LoadImage": Tony4896LoadImage,
    "Tony4896LoadImageBatches": Tony4896LoadImageBatches,
    "Tony4896TextSplitterBatches": Tony4896TextSplitterBatches,
    "Tony4896SaveTxt": Tony4896SaveTxt,
    "Tony4896DelayTime": Tony4896DelayTime,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "Tony4896LoadImage": "I. Load Image (Tony4896)",
    "Tony4896LoadImageBatches": "II. Load Image Batches (Tony4896)",
    "Tony4896TextSplitterBatches": "III. Text Splitter Batches (Tony4896)",
    "Tony4896SaveTxt": "IV. Save TXT (Tony4896)",
    "Tony4896DelayTime": "V. Delay Time (Tony4896)",
}


try:
    from aiohttp import web
    from server import PromptServer

    async def _save_uploaded_file(field, dst: Path):
        dst.parent.mkdir(parents=True, exist_ok=True)
        with dst.open("wb") as f:
            while True:
                chunk = await field.read_chunk()
                if not chunk:
                    break
                f.write(chunk)

    @PromptServer.instance.routes.post("/tony4896_io/upload_image")
    async def upload_image_endpoint(request):
        try:
            reader = await request.multipart()
            field = await reader.next()
            if field is None or field.name != "file":
                raise ValueError("Expected multipart field named 'file'.")
            name = _safe_upload_filename(field.filename or f"{uuid.uuid4().hex}.png")
            if Path(name).suffix.lower() not in IMAGE_EXTENSIONS:
                raise ValueError(f"Unsupported image extension: {name}")
            batch = uuid.uuid4().hex
            dst = TEMP_ROOT / "files" / batch / name
            await _save_uploaded_file(field, dst)
            return web.json_response({"ok": True, "path": str(dst), "virtual_path": f"tony4896://files/{batch}/{name}", "name": name, "folder": str(dst.parent)})
        except Exception as e:
            return web.json_response({"ok": False, "error": str(e)}, status=500)

    @PromptServer.instance.routes.post("/tony4896_io/upload_folder")
    async def upload_folder_endpoint(request):
        try:
            reader = await request.multipart()
            batch = uuid.uuid4().hex
            folder = TEMP_ROOT / "folders" / batch
            folder.mkdir(parents=True, exist_ok=True)
            saved = []
            while True:
                field = await reader.next()
                if field is None:
                    break
                if field.name != "files":
                    continue
                name = _safe_upload_filename(field.filename or f"{uuid.uuid4().hex}.png")
                if Path(name).suffix.lower() not in IMAGE_EXTENSIONS:
                    # consume but skip unsupported files
                    while await field.read_chunk():
                        pass
                    continue
                dst = folder / name
                # Avoid overwrite when duplicate basenames exist.
                if dst.exists():
                    dst = folder / f"{dst.stem}_{uuid.uuid4().hex[:8]}{dst.suffix}"
                await _save_uploaded_file(field, dst)
                saved.append(os.path.basename(dst))
            if not saved:
                raise ValueError("No supported image files were uploaded.")
            saved = sorted(saved, key=lambda x: x.lower())
            return web.json_response({"ok": True, "folder": str(folder), "virtual_folder": f"tony4896://folders/{batch}", "files": saved, "count": len(saved)})
        except Exception as e:
            return web.json_response({"ok": False, "error": str(e)}, status=500)

    @PromptServer.instance.routes.post("/tony4896_io/upload_txt")
    async def upload_txt_endpoint(request):
        try:
            reader = await request.multipart()
            field = await reader.next()
            if field is None or field.name != "file":
                raise ValueError("Expected multipart field named 'file'.")
            name = _safe_upload_filename(field.filename or f"{uuid.uuid4().hex}.txt", ".txt")
            if not name.lower().endswith(".txt"):
                raise ValueError("Only .txt files are supported.")
            batch = uuid.uuid4().hex
            dst = TEMP_ROOT / "txt" / batch / name
            await _save_uploaded_file(field, dst)
            return web.json_response({"ok": True, "path": str(dst), "virtual_path": f"tony4896://txt/{batch}/{name}", "name": name})
        except Exception as e:
            return web.json_response({"ok": False, "error": str(e)}, status=500)

    @PromptServer.instance.routes.get("/tony4896_io/list_images")
    async def list_images_endpoint(request):
        folder = request.query.get("folder", "")
        images = _list_images(folder)
        return web.json_response({"ok": True, "files": [{"name": os.path.basename(p), "path": p} for p in images], "count": len(images)})

    @PromptServer.instance.routes.get("/tony4896_io/image_info")
    async def image_info_endpoint(request):
        try:
            path = _resolve_image_path(
                request.query.get("mode", "Image"),
                request.query.get("image_path", ""),
                request.query.get("folder_path", ""),
                request.query.get("file_name", ""),
                int(request.query.get("index", "0") or 0),
            )
            img = Image.open(path)
            img = ImageOps.exif_transpose(img)
            w, h = img.size
            mtime = int(Path(path).stat().st_mtime_ns)
            view_url = f"/tony4896_io/view_image?path={path}&mtime={mtime}"
            return web.json_response({
                "ok": True,
                "path": path,
                "folder": str(Path(path).parent),
                "name": os.path.basename(path),
                "file_stem": _without_ext_and_parent(path),
                "width": w,
                "height": h,
                "size": f"{w} x {h}",
                "mtime": mtime,
                "view_url": view_url,
            })
        except Exception as e:
            return web.json_response({"ok": False, "error": str(e)}, status=500)

    @PromptServer.instance.routes.get("/tony4896_io/view_image")
    async def view_image_endpoint(request):
        try:
            path = request.query.get("path", "")
            path = _normalize_path(path)
            if not _is_safe_image_path(path):
                raise FileNotFoundError(f"Image path does not exist or is unsupported: {path}")
            return web.FileResponse(path)
        except Exception as e:
            return web.json_response({"ok": False, "error": str(e)}, status=404)

    @PromptServer.instance.routes.post("/tony4896_io/clear_temp")
    async def clear_temp_endpoint(request):
        try:
            before = _temp_size_bytes()
            _clear_temp_root()
            return web.json_response({"ok": True, "cleared_bytes": before, "temp_root": str(TEMP_ROOT)})
        except Exception as e:
            return web.json_response({"ok": False, "error": str(e)}, status=500)

    @PromptServer.instance.routes.get("/tony4896_io/text_split_info")
    async def text_split_info_endpoint(request):
        try:
            items = _split_text_file(request.query.get("txt_path", ""), request.query.get("paragraph_sep", "\\n\\n"), request.query.get("negative_sep", "###"))
            if not items:
                raise ValueError("TXT file has no valid paragraph after splitting.")
            idx = max(0, min(int(request.query.get("index", "0") or 0), len(items) - 1))
            pos, neg = items[idx]
            return web.json_response({"ok": True, "count": len(items), "current_index": idx, "next_index": idx + 1, "has_index": (idx + 1) < len(items), "positive": pos, "negative": neg})
        except Exception as e:
            return web.json_response({"ok": False, "error": str(e)}, status=500)

    @PromptServer.instance.routes.post("/tony4896_io/save_txt")
    async def save_txt_endpoint(request):
        try:
            data = await request.json()
            path = _save_txt(data.get("text", ""), data.get("output_dir", ""), data.get("file_name", ""), data.get("filename_prefix", "ComfyUI"))
            return web.json_response({"ok": True, "path": path})
        except Exception as e:
            return web.json_response({"ok": False, "error": str(e)}, status=500)

except Exception as e:
    print(f"[Tony4896_IO] Failed to register web routes: {e}")
