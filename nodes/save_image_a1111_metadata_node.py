import hashlib
import json
import re
from datetime import datetime
from pathlib import Path

import numpy as np
from PIL import Image
from PIL.PngImagePlugin import PngInfo

from .text_splitter_node import _split_text_file

try:
    from comfy.cli_args import args
except Exception:  # pragma: no cover
    args = None

try:
    import folder_paths
except Exception:  # pragma: no cover - for non-ComfyUI test environments
    folder_paths = None


class PromptGraphResolverTony4896:
    def __init__(self, prompt):
        self.prompt = prompt or {}
        self.cache = {}

    def _node(self, node_id):
        return self.prompt.get(str(node_id), {})

    def _inputs(self, node_id):
        return self._node(node_id).get("inputs", {})

    def _class(self, node_id):
        return self._node(node_id).get("class_type", "")

    @staticmethod
    def _is_link(value):
        return isinstance(value, (list, tuple)) and len(value) == 2 and str(value[0]).isdigit()

    def _resolve_value(self, value):
        if isinstance(value, str):
            return value
        if self._is_link(value):
            return self.resolve_link(value)
        return ""

    def resolve_link(self, link):
        node_id, output_idx = str(link[0]), int(link[1])
        key = (node_id, output_idx)
        if key in self.cache:
            return self.cache[key]
        result = self.resolve_output(node_id, output_idx)
        self.cache[key] = result
        return result

    def resolve_output(self, node_id, output_idx):
        ctype = self._class(node_id)
        inputs = self._inputs(node_id)

        if ctype == "CLIPTextEncode":
            return self._resolve_value(inputs.get("text", ""))

        if ctype == "Text_Splitter":
            items = _split_text_file(
                inputs.get("txt_path", ""),
                inputs.get("paragraph_sep", "\\n\\n"),
                inputs.get("negative_sep", "###"),
            )
            if not items:
                return ""
            idx = max(0, min(int(inputs.get("index", 0)), len(items) - 1))
            pos, neg = items[idx]
            return pos if output_idx == 0 else (neg if output_idx == 1 else "")

        if "concat" in ctype.lower() or "string" in ctype.lower():
            sep = inputs.get("separator", inputs.get("delimiter", ""))
            if not isinstance(sep, str):
                sep = ""
            parts = []
            for name, raw in inputs.items():
                if name in {"separator", "delimiter"}:
                    continue
                if any(k in name.lower() for k in ["text", "string", "prefix", "suffix"]):
                    value = self._resolve_value(raw)
                    if value:
                        parts.append(value)
            return sep.join(parts)

        for field in ["text", "string", "value"]:
            if field in inputs:
                return self._resolve_value(inputs[field])
        return ""


class SaveImageA1Metadata:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "images": ("IMAGE",),
                "filename_prefix": ("STRING", {"default": "ZImage_%date:yyyy_MM_dd%/ZImage_%date:yyyy_MM_dd_HHmmss%_%Text_Splitter.index%_%KSampler.seed%"}),
            },
            "optional": {
                "positive_prompt_override": ("STRING", {"multiline": True, "default": ""}),
                "negative_prompt_override": ("STRING", {"multiline": True, "default": ""}),
                "extra_metadata": ("STRING", {"multiline": True, "default": ""}),
                "include_lora_hashes": ("BOOLEAN", {"default": True}),
                "debug_sidecar": ("BOOLEAN", {"default": False}),
            },
            "hidden": {
                "prompt": "PROMPT",
                "extra_pnginfo": "EXTRA_PNGINFO",
            },
        }

    RETURN_TYPES = ()
    FUNCTION = "save_images"
    CATEGORY = "Tony4896/IO"
    OUTPUT_NODE = True

    def __init__(self):
        self.output_dir = folder_paths.get_output_directory() if folder_paths else "."
        self.type = "output"
        self.prefix_append = ""
        self.compress_level = 4

    @staticmethod
    def _strip_ext(name):
        for ext in [".safetensors", ".ckpt", ".pt", ".pth"]:
            if name.lower().endswith(ext):
                return name[: -len(ext)]
        return name

    def _find_sampler(self, prompt):
        for node_id, node in (prompt or {}).items():
            if node.get("class_type") in {"KSampler", "KSamplerAdvanced"}:
                return str(node_id), node
        return None, None

    def _extract_prompts(self, prompt):
        node_id, sampler = self._find_sampler(prompt)
        if sampler is None:
            return "", ""
        resolver = PromptGraphResolverTony4896(prompt)
        inputs = sampler.get("inputs", {})
        pos = resolver.resolve_link(inputs.get("positive")) if resolver._is_link(inputs.get("positive")) else ""
        neg = resolver.resolve_link(inputs.get("negative")) if resolver._is_link(inputs.get("negative")) else ""
        return pos or "", neg or ""

    def _extract_loras(self, prompt):
        loras = []
        for node in (prompt or {}).values():
            ctype = node.get("class_type")
            inputs = node.get("inputs", {})
            if ctype == "LoraLoader":
                name = (inputs.get("lora_name") or "").strip()
                if name:
                    loras.append({"name": name, "strength": inputs.get("strength_model", 1)})
            if ctype == "Power Lora Loader (rgthree)":
                for key, val in inputs.items():
                    if key.startswith("lora_") and isinstance(val, dict) and val.get("on"):
                        name = (val.get("lora") or "").strip()
                        if name:
                            loras.append({"name": name, "strength": val.get("strength", 1)})
        return loras


    @staticmethod
    def _expand_date_tokens(text):
        if not isinstance(text, str) or "%date:" not in text:
            return text

        def repl(match):
            fmt = match.group(1)
            now = datetime.now()
            token_map = {
                "yyyy": f"{now.year:04d}",
                "MM": f"{now.month:02d}",
                "dd": f"{now.day:02d}",
                "HH": f"{now.hour:02d}",
                "mm": f"{now.minute:02d}",
                "ss": f"{now.second:02d}",
            }
            for token, value in sorted(token_map.items(), key=lambda kv: -len(kv[0])):
                fmt = fmt.replace(token, value)
            return fmt

        return re.sub(r"%date:([^%]+)%", repl, text)

    def _lora_hash(self, lora_name):
        if not folder_paths:
            return None
        try:
            path = folder_paths.get_full_path("loras", lora_name)
            if not path:
                return None
            h = hashlib.sha256()
            with open(path, "rb") as f:
                for chunk in iter(lambda: f.read(1024 * 1024), b""):
                    h.update(chunk)
            return h.hexdigest()[:12]
        except Exception:
            return None

    def save_images(self, images, filename_prefix="Tony4896/A1111", positive_prompt_override="", negative_prompt_override="", extra_metadata="", include_lora_hashes=True, debug_sidecar=False, prompt=None, extra_pnginfo=None):
        prompt = prompt or {}
        extra_pnginfo = extra_pnginfo or {}

        pos, neg = self._extract_prompts(prompt)
        if positive_prompt_override.strip():
            pos = positive_prompt_override
        if negative_prompt_override.strip():
            neg = negative_prompt_override

        sampler_id, sampler = self._find_sampler(prompt)
        sin = sampler.get("inputs", {}) if sampler else {}

        loras = self._extract_loras(prompt)
        lora_tags = [f"<lora:{self._strip_ext(x['name'])}:{x['strength']}>" for x in loras]

        parts = [pos.strip()]
        if lora_tags:
            parts.append("\n".join(lora_tags))
        parts.append("")
        parts.append(f"Negative prompt: {(neg or '').strip()}")

        h = images[0].shape[0] if len(images) > 0 else 0
        w = images[0].shape[1] if len(images) > 0 else 0
        params = [
            f"Steps: {sin.get('steps', '')}",
            f"Sampler: {sin.get('sampler_name', '')}",
            f"Schedule type: {sin.get('scheduler', '')}",
            f"CFG scale: {sin.get('cfg', '')}",
            f"Seed: {sin.get('seed', sin.get('noise_seed', ''))}",
            f"Size: {w}x{h}",
        ]
        if extra_metadata.strip():
            params.append(extra_metadata.strip())

        if include_lora_hashes and loras:
            hashes = []
            for item in loras:
                sh = self._lora_hash(item["name"])
                if sh:
                    hashes.append(f"{self._strip_ext(item['name'])}: {sh}")
            if hashes:
                params.append(f'Lora hashes: "{", ".join(hashes)}"')

        parts.append(", ".join([p for p in params if p and not p.endswith(": ")]))
        parameters_text = "\n".join(parts).strip()

        filename_prefix = self._expand_date_tokens(filename_prefix + self.prefix_append)

        if folder_paths:
            full_output_folder, filename, counter, subfolder, filename_prefix = folder_paths.get_save_image_path(
                filename_prefix, self.output_dir, images[0].shape[1], images[0].shape[0]
            )
        else:
            full_output_folder, filename, counter, subfolder = ".", "image", 1, ""
            Path(full_output_folder).mkdir(parents=True, exist_ok=True)

        results = []
        for batch_number, image in enumerate(images):
            i = 255.0 * image.cpu().numpy()
            img = Image.fromarray(np.clip(i, 0, 255).astype(np.uint8))
            metadata = None
            disable_metadata = bool(args and getattr(args, "disable_metadata", False))
            if not disable_metadata:
                metadata = PngInfo()
                metadata.add_text("parameters", parameters_text)
                if prompt is not None:
                    metadata.add_text("prompt", json.dumps(prompt))
                if extra_pnginfo is not None:
                    for key, value in extra_pnginfo.items():
                        metadata.add_text(key, json.dumps(value))

            filename_with_batch_num = filename.replace("%batch_num%", str(batch_number))
            file = f"{filename_with_batch_num}_{counter:05}_.png"
            out_path = Path(full_output_folder) / file
            img.save(out_path, pnginfo=metadata, compress_level=self.compress_level)

            if debug_sidecar:
                Path(str(out_path) + ".parameters.txt").write_text(parameters_text, encoding="utf-8")
                Path(str(out_path) + ".metadata_debug.json").write_text(
                    json.dumps({"positive_prompt": pos, "negative_prompt": neg, "sampler_node": sampler_id, "sampler_inputs": sin, "loras": loras}, ensure_ascii=False, indent=2),
                    encoding="utf-8",
                )

            results.append({"filename": file, "subfolder": subfolder, "type": self.type})
            counter += 1

        return {"ui": {"images": results}}
