import os
import uuid
from pathlib import Path

from .nodes.common import (
    IMAGE_EXTENSIONS,
    TEMP_ROOT,
    _clear_temp_root,
    _is_safe_image_path,
    _list_images,
    _normalize_path,
    _resolve_image_path,
    _safe_upload_filename,
    _temp_size_bytes,
    _without_ext_and_parent,
)
from .nodes.load_image_node import LoadImage
from .nodes.load_image_batches_node import LoadImageBatches
from .nodes.load_imagetext_batches_node import LoadImageTextBatch
from .nodes.save_txt_node import SaveTxt, _save_txt
from .nodes.text_splitter_node import TextSplitter, _split_text_file
from .nodes.prompt_meta_node import PromptToPNGMeta
from .nodes.save_image_a1111_metadata_node import SaveImageA1Metadata

WEB_DIRECTORY = "./web"

NODE_CLASS_MAPPINGS = {
    "Load_Image": LoadImage,
    "Load_Image_Batches": LoadImageBatches,
    "Load_Image_Text_Batch": LoadImageTextBatch,
    "Text_Splitter": TextSplitter,
    "Save_Txt": SaveTxt,
    "Prompt_To_PNG_Meta": PromptToPNGMeta,
    "SaveImageA1Metadata": SaveImageA1Metadata,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "Load_Image": "Load_Image",
    "Load_Image_Batches": "Load_Image_Batches",
    "Load_Image_Text_Batch": "Load_Image_Text_Batch",
    "Text_Splitter": "Text_Splitter",
    "Save_Txt": "Save_Txt",
    "Prompt_To_PNG_Meta": "Prompt_To_PNG_Meta",
    "SaveImageA1Metadata": "Save Image A1111 Metadata",
}

try:
    from aiohttp import web
    from PIL import Image, ImageOps
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
                    while await field.read_chunk():
                        pass
                    continue
                dst = folder / name
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

    @PromptServer.instance.routes.post("/tony4896_io/upload_image_text_folder")
    async def upload_image_text_folder_endpoint(request):
        try:
            reader = await request.multipart()
            batch = uuid.uuid4().hex
            folder = TEMP_ROOT / "image_text_folders" / batch
            folder.mkdir(parents=True, exist_ok=True)
            saved_images = []
            saved_txt = []
            while True:
                field = await reader.next()
                if field is None:
                    break
                if field.name != "files":
                    continue
                name = _safe_upload_filename(field.filename or f"{uuid.uuid4().hex}")
                suffix = Path(name).suffix.lower()
                if suffix not in IMAGE_EXTENSIONS and suffix != ".txt":
                    while await field.read_chunk():
                        pass
                    continue
                dst = folder / name
                if dst.exists():
                    dst = folder / f"{dst.stem}_{uuid.uuid4().hex[:8]}{dst.suffix}"
                await _save_uploaded_file(field, dst)
                if dst.suffix.lower() == ".txt":
                    saved_txt.append(os.path.basename(dst))
                else:
                    saved_images.append(os.path.basename(dst))
            if not saved_images:
                raise ValueError("No supported image files were uploaded.")
            saved_images = sorted(saved_images, key=lambda x: x.lower())
            saved_txt = sorted(saved_txt, key=lambda x: x.lower())
            virtual_folder = f"tony4896://image_text_folders/{batch}"
            return web.json_response({
                "ok": True,
                "folder": str(folder),
                "txt_folder": str(folder),
                "virtual_folder": virtual_folder,
                "virtual_txt_folder": virtual_folder,
                "files": saved_images,
                "txt_files": saved_txt,
                "count": len(saved_images),
                "txt_count": len(saved_txt),
            })
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
        images = _list_images(request.query.get("folder", ""))
        return web.json_response({"ok": True, "files": [{"name": os.path.basename(p), "path": p} for p in images], "count": len(images)})

    @PromptServer.instance.routes.get("/tony4896_io/image_info")
    async def image_info_endpoint(request):
        try:
            path = _resolve_image_path(request.query.get("mode", "Image"), request.query.get("image_path", ""), request.query.get("folder_path", ""), request.query.get("file_name", ""), int(request.query.get("index", "0") or 0))
            img = ImageOps.exif_transpose(Image.open(path))
            w, h = img.size
            mtime = int(Path(path).stat().st_mtime_ns)
            return web.json_response({"ok": True, "path": path, "folder": str(Path(path).parent), "name": os.path.basename(path), "file_stem": _without_ext_and_parent(path), "width": w, "height": h, "size": f"{w} x {h}", "mtime": mtime, "view_url": f"/tony4896_io/view_image?path={path}&mtime={mtime}"})
        except Exception as e:
            return web.json_response({"ok": False, "error": str(e)}, status=500)

    @PromptServer.instance.routes.get("/tony4896_io/view_image")
    async def view_image_endpoint(request):
        try:
            path = _normalize_path(request.query.get("path", ""))
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
            return web.json_response({"ok": True, "path": _save_txt(data.get("text", ""), data.get("output_dir", ""), data.get("file_name", ""), data.get("filename_prefix", "ComfyUI"))})
        except Exception as e:
            return web.json_response({"ok": False, "error": str(e)}, status=500)
except Exception as e:
    print(f"[Tony4896_IO] Failed to register web routes: {e}")
