# Implementation Plan: Save Image A1111 Metadata

## 1. Final Decision

Create a new ComfyUI custom save node for `Load_IO_Tony`:

```text
Save Image A1111 Metadata
```

Python class name:

```python
SaveImageA1Metadata
```

The node will save generated images like ComfyUI `SaveImage`, but additionally writes an A1111/WebUI-style metadata string into the PNG metadata key:

```text
parameters
```

The node must preserve the original ComfyUI metadata keys:

```text
prompt
workflow
```

The node must not delete, rewrite, normalize, or replace existing `prompt` and `workflow` metadata.

---

## 2. Core Goal

The generated PNG should contain metadata compatible with both:

1. **ComfyUI**
   - Drag image back into ComfyUI.
   - Restore workflow normally through `prompt` and `workflow`.

2. **CivitAI / A1111-style parsers**
   - Read positive prompt.
   - Read negative prompt.
   - Read generation parameters.
   - Read LoRA tags.
   - Optionally read LoRA hashes.

The final PNG metadata should include:

```text
prompt
workflow
parameters
```

Where:

```text
prompt     = original ComfyUI prompt metadata
workflow   = original ComfyUI workflow metadata
parameters = new A1111-style metadata text
```

---

## 3. Important Design Rules

### 3.1 Do not modify ComfyUI metadata

The node must preserve ComfyUI metadata exactly as much as possible.

Correct behavior:

```python
metadata.add_text("parameters", parameters_text)

if prompt is not None:
    metadata.add_text("prompt", json.dumps(prompt))

if extra_pnginfo is not None:
    for key, value in extra_pnginfo.items():
        metadata.add_text(key, json.dumps(value))
```

Important:

- Do not remove `prompt`.
- Do not remove `workflow`.
- Do not rewrite `prompt`.
- Do not rewrite `workflow`.
- Add only `parameters` for A1111/CivitAI compatibility.

---

### 3.2 Do not patch or replace ComfyUI source code

The node should not modify the original ComfyUI `SaveImage` node source.

However, the final implementation should be a **custom save node**, not a metadata-only node placed before the original `SaveImage`.

Reason:

A node before ComfyUI `SaveImage` can generate metadata text, but it cannot reliably force the original `SaveImage` node to write that metadata into the final PNG unless using fragile hooks or monkey patching.

Therefore, the selected design is:

```text
VAEDecode
   ↓
Save Image A1111 Metadata
```

Not:

```text
Metadata Node
   ↓
Original ComfyUI SaveImage
```

---

## 4. Selected Architecture

```text
Text Splitter / Prompt Builder
        ↓
CLIPTextEncode

rgthree Power Lora Loader / LoraLoader
        ↓
KSampler
        ↓
VAEDecode
        ↓
Save Image A1111 Metadata
```

The save node receives:

```text
images
filename_prefix
```

and hidden ComfyUI runtime data:

```text
prompt
extra_pnginfo
```

Then it automatically extracts:

```text
positive prompt
negative prompt
steps
sampler
scheduler
cfg
seed
size
model name
vae name
clip name
enabled LoRAs
LoRA hashes
```

Finally it writes:

```text
parameters
```

into the saved PNG.

---

## 5. Assumptions for Version 1

The first implementation targets the user's current workflow style:

```text
1 main generation pipeline
1 KSampler
1 Save Image
```

This allows the node to use simpler and more reliable extraction logic.

Version 1 does not need to fully solve complex multi-branch workflows with multiple samplers, multiple VAEDecode nodes, or multiple save nodes.

---

## 6. Node Definition

### Display name

```text
Save Image A1111 Metadata
```

### Python class name

```python
SaveImageA1Metadata
```

### Suggested file name

```text
nodes/save_image_a1111_metadata_node.py
```

### Category

Use the existing project style:

```python
CATEGORY = "Tony4896/IO"
```

### Output node

```python
OUTPUT_NODE = True
```

---

## 7. Inputs

### Required inputs

```python
"required": {
    "images": ("IMAGE",),
    "filename_prefix": ("STRING", {"default": "Tony4896/A1111"}),
}
```

### Optional inputs

```python
"optional": {
    "positive_prompt_override": ("STRING", {"multiline": True, "default": ""}),
    "negative_prompt_override": ("STRING", {"multiline": True, "default": ""}),
    "extra_metadata": ("STRING", {"multiline": True, "default": ""}),
    "include_lora_hashes": ("BOOLEAN", {"default": True}),
    "debug_sidecar": ("BOOLEAN", {"default": False}),
}
```

### Hidden inputs

```python
"hidden": {
    "prompt": "PROMPT",
    "extra_pnginfo": "EXTRA_PNGINFO",
}
```

---

## 8. Output

The node behaves like a save node and returns UI image information:

```python
RETURN_TYPES = ()
FUNCTION = "save_images"
OUTPUT_NODE = True
```

Return format:

```python
return {"ui": {"images": results}}
```

---

## 9. Metadata Format

The PNG key must be:

```text
parameters
```

The value should follow A1111/WebUI-style format:

```text
{positive_prompt}
<lora:LoRA_A:0.8>
<lora:LoRA_B:0.6>

Negative prompt: {negative_prompt}
Steps: 9, Sampler: Euler, Schedule type: simple, CFG scale: 1.0, Seed: 663180022357408, Size: 832x1216, Model: z-image-turbo-fp8-e4m3fn, VAE: ae.safetensors
Lora hashes: "LoRA_A: abc123, LoRA_B: def456"
```

### Notes

- LoRA tags should be appended after the positive prompt.
- Negative prompt line should always exist.
- `Lora hashes` should only be written if `include_lora_hashes == True` and hashes are available.
- Empty fields should be skipped where appropriate.
- `Size` can be obtained from the image tensor shape if graph extraction fails.

---

## 10. LoRA Tag Format

LoRA tags should follow the common A1111 format:

```text
<lora:{lora_name_without_extension}:{strength}>
```

Example:

```text
<lora:Ivan_Ryo_ZImage_epoch_11:1>
```

### Rules

1. Remove known extensions:

```text
.safetensors
.ckpt
.pt
.pth
```

2. Trim whitespace.
3. Ignore disabled LoRAs.
4. Preserve LoRA order.
5. For ComfyUI `LoraLoader`, use `strength_model` as the main displayed strength.
6. For rgthree `Power Lora Loader`, use the model strength field.

---

## 11. Supported LoRA Nodes

Version 1 should support:

```text
rgthree Power Lora Loader
ComfyUI LoraLoader
```

---

### 11.1 rgthree Power Lora Loader

Expected input structure:

```json
"lora_1": {
  "on": true,
  "lora": "Ivan_Ryo_ZImage_epoch_11.safetensors",
  "strength": 1,
  "strengthTwo": 1
}
```

Extraction rule:

```text
if on == true:
    lora_name = lora
    strength = strength
```

Output:

```text
<lora:Ivan_Ryo_ZImage_epoch_11:1>
```

Optional hash output:

```text
Lora hashes: "Ivan_Ryo_ZImage_epoch_11: b9920359e0d0"
```

---

### 11.2 ComfyUI LoraLoader

Expected input fields:

```text
lora_name
strength_model
strength_clip
```

Extraction rule:

```text
lora_name = inputs["lora_name"]
strength = inputs["strength_model"]
```

Output:

```text
<lora:name_without_extension:strength_model>
```

`strength_clip` may be ignored in the main A1111 tag because the common A1111 LoRA syntax only uses one strength value.

---

## 12. LoRA Hash Handling

If `include_lora_hashes == True`, the node should try to resolve the LoRA file path from ComfyUI's LoRA folder:

```python
folder_paths.get_full_path("loras", lora_name)
```

Then compute SHA256:

```python
sha256 = hashlib.sha256()
with open(path, "rb") as f:
    for chunk in iter(lambda: f.read(1024 * 1024), b""):
        sha256.update(chunk)
```

For metadata output, use a short hash if preferred:

```text
first 10 or 12 hex characters
```

Example:

```text
Lora hashes: "Ivan_Ryo_ZImage_epoch_11: b9920359e0d0"
```

If the file path cannot be resolved, skip hash for that LoRA instead of failing the save.

---

## 13. Automatic Graph Extraction

The node should extract generation parameters from hidden `prompt` / `extra_pnginfo`.

### Target fields

| A1111 field | ComfyUI source |
|---|---|
| `Steps` | `KSampler.inputs.steps` |
| `Sampler` | `KSampler.inputs.sampler_name` |
| `Schedule type` | `KSampler.inputs.scheduler` |
| `CFG scale` | `KSampler.inputs.cfg` |
| `Seed` | `KSampler.inputs.seed` or `noise_seed` |
| `Size` | image tensor shape or latent/image node |
| `Model` | checkpoint / UNet loader node |
| `VAE` | VAE loader node |
| `Clip` | checkpoint/text encoder loader node |
| LoRA | rgthree Power Lora Loader / LoraLoader |

---

## 14. KSampler Extraction

Because version 1 assumes one main pipeline, extraction can initially scan for the first or most relevant sampler node.

Supported sampler class types should include at least:

```text
KSampler
KSamplerAdvanced
```

For standard `KSampler`, read:

```python
steps = inputs.get("steps")
cfg = inputs.get("cfg")
sampler_name = inputs.get("sampler_name")
scheduler = inputs.get("scheduler")
seed = inputs.get("seed")
```

For `KSamplerAdvanced`, support:

```python
noise_seed = inputs.get("noise_seed")
```

If no sampler is found, fill unknown fields with safe defaults or omit them.

---

## 15. Prompt Extraction

### Problem

`CLIPTextEncode.text` may not contain the final text directly.

It may contain a link:

```json
"text": ["18", 0]
```

This means the real text is produced by an upstream node such as:

```text
Text_Splitter
StringConcatenate
```

Therefore, the node must resolve the upstream graph.

---

### 15.1 Resolver strategy

Create a helper class:

```python
class PromptGraphResolverTony4896:
    def resolve_input(self, node_id, input_name):
        ...
```

Resolution rules:

```text
If input is a string literal:
    return input

If input is a link ["node_id", output_index]:
    find source node
    resolve source node output
```

---

### 15.2 CLIPTextEncode resolver

For:

```text
CLIPTextEncode
```

Read:

```python
inputs["text"]
```

If it is a string:

```python
return inputs["text"]
```

If it is a link:

```python
return resolve_link(inputs["text"])
```

---

### 15.3 TextSplitter resolver

The project already has a `TextSplitter` node.

Expected outputs:

```text
positive_prompt
negative_prompt
next_index
has_index
current_index
```

For this node, the resolver should reproduce the same splitting logic by reading the node inputs:

```text
txt_path
paragraph_sep
negative_sep
index
```

Then apply the same text-splitting behavior used by the node.

Important:

- Output index `0` should map to `positive_prompt`.
- Output index `1` should map to `negative_prompt`.

Pseudo-rule:

```python
if output_index == 0:
    return positive_prompt

if output_index == 1:
    return negative_prompt
```

---

### 15.4 StringConcatenate resolver

If `CLIPTextEncode.text` is connected through a string concatenation node, the resolver should recursively resolve all connected string inputs.

Generic strategy:

```python
parts = []

for each input in node.inputs:
    if input is string or link:
        value = resolve_input_value(input)
        if value:
            parts.append(value)

return separator.join(parts)
```

The implementation should support known field names such as:

```text
text
text_a
text_b
string
string_a
string_b
prefix
suffix
delimiter
separator
```

If separator/delimiter is not found, default to:

```text
""
```

or:

```text
"\n"
```

depending on the node's behavior.

---

### 15.5 Fallback behavior

If prompt extraction fails:

1. Use `positive_prompt_override` if provided.
2. Use `negative_prompt_override` if provided.
3. Otherwise fallback to empty string.
4. Do not crash the image save operation.

---

## 16. Positive / Negative Prompt Detection

Preferred extraction strategy:

1. Find `KSampler`.
2. Read `positive` and `negative` inputs.
3. Follow those links to the corresponding `CLIPTextEncode` nodes.
4. Resolve their `text` input through the graph resolver.

This is more accurate than scanning all `CLIPTextEncode` nodes blindly.

Expected graph:

```text
Positive prompt source
        ↓
CLIPTextEncode
        ↓
KSampler.positive

Negative prompt source
        ↓
CLIPTextEncode
        ↓
KSampler.negative
```

---

## 17. Model / VAE / CLIP Extraction

Version 1 should attempt simple extraction from known loader nodes.

Potential class types:

```text
CheckpointLoaderSimple
UNETLoader
VAELoader
DualCLIPLoader
TripleCLIPLoader
CLIPLoader
```

Possible fields:

```text
ckpt_name
unet_name
vae_name
clip_name
clip_name1
clip_name2
clip_name3
```

If model/vae/clip names cannot be confidently extracted, skip those fields.

Do not guess.

---

## 18. Save Behavior

The node should copy ComfyUI `SaveImage` behavior as much as possible:

- Save images to ComfyUI output directory.
- Respect `filename_prefix`.
- Support image batches.
- Return UI gallery-compatible image info.
- Use `folder_paths.get_save_image_path(...)`.
- Use PNG compression level similar to ComfyUI default behavior.

Basic save logic:

```python
full_output_folder, filename, counter, subfolder, filename_prefix = folder_paths.get_save_image_path(
    filename_prefix,
    self.output_dir,
    images[0].shape[1],
    images[0].shape[0]
)
```

For each image:

```python
i = 255. * image.cpu().numpy()
img = Image.fromarray(np.clip(i, 0, 255).astype(np.uint8))
```

Then save:

```python
img.save(path, pnginfo=metadata, compress_level=4)
```

---

## 19. Debug Sidecar Files

If `debug_sidecar == True`, optionally save beside the PNG:

```text
image_name.parameters.txt
image_name.metadata_debug.json
```

The debug JSON may include:

```json
{
  "positive_prompt": "...",
  "negative_prompt": "...",
  "steps": 9,
  "sampler": "Euler",
  "scheduler": "simple",
  "cfg": 1.0,
  "seed": 123,
  "size": "832x1216",
  "loras": [
    {
      "name": "Ivan_Ryo_ZImage_epoch_11.safetensors",
      "tag": "<lora:Ivan_Ryo_ZImage_epoch_11:1>",
      "strength": 1,
      "hash": "b9920359e0d0"
    }
  ],
  "warnings": []
}
```

This helps inspect extraction failures without breaking image generation.

---

## 20. Error Handling

The save node must never fail only because metadata extraction failed.

Correct behavior:

```text
Image saving is higher priority than metadata completeness.
```

If extraction fails:

- Save the image anyway.
- Preserve `prompt` and `workflow`.
- Write a partial `parameters` field if possible.
- Add debug warnings if `debug_sidecar == True`.

Examples:

```text
Warning: No KSampler found.
Warning: Could not resolve positive prompt from CLIPTextEncode.text.
Warning: LoRA file path not found, skipped hash.
```

---

## 21. Registration

Update the project node mapping.

Depending on current project structure, add:

```python
from .nodes.save_image_a1111_metadata_node import SaveImageA1Metadata
```

Then register:

```python
NODE_CLASS_MAPPINGS = {
    # existing nodes...
    "SaveImageA1Metadata": SaveImageA1Metadata,
}
```

Display name:

```python
NODE_DISPLAY_NAME_MAPPINGS = {
    # existing nodes...
    "SaveImageA1Metadata": "Save Image A1111 Metadata",
}
```

Do not replace existing mappings. Merge this node into the existing dictionary.

---

## 22. Test Cases

### Test 1: Basic save

Workflow:

```text
KSampler → VAEDecode → Save Image A1111 Metadata
```

Expected PNG metadata keys:

```text
prompt
workflow
parameters
```

Expected `parameters` contains:

```text
Negative prompt:
Steps:
Sampler:
CFG scale:
Seed:
Size:
```

---

### Test 2: TextSplitter direct to CLIPTextEncode

Workflow:

```text
TextSplitter.positive_prompt → CLIPTextEncode.text
TextSplitter.negative_prompt → CLIPTextEncode.text
```

Expected:

- Positive prompt resolved correctly.
- Negative prompt resolved correctly.
- `CLIPTextEncode.text` link should not appear in final `parameters`.

---

### Test 3: TextSplitter through StringConcatenate

Workflow:

```text
TextSplitter → StringConcatenate → CLIPTextEncode
```

Expected:

- Final flattened prompt is written into `parameters`.
- No node link array like `["18", 0]` appears in `parameters`.

---

### Test 4: rgthree Power Lora Loader

Workflow uses enabled LoRAs:

```json
"lora_1": {
  "on": true,
  "lora": "Ivan_Ryo_ZImage_epoch_11.safetensors",
  "strength": 1
}
```

Expected:

```text
<lora:Ivan_Ryo_ZImage_epoch_11:1>
```

If hash is enabled and file exists:

```text
Lora hashes: "Ivan_Ryo_ZImage_epoch_11: b9920359e0d0"
```

---

### Test 5: Disabled LoRA

Input:

```json
"lora_1": {
  "on": false,
  "lora": "Some_Lora.safetensors",
  "strength": 1
}
```

Expected:

- No LoRA tag written.
- No LoRA hash written.

---

### Test 6: ComfyUI LoraLoader

Input fields:

```text
lora_name = Some_Lora.safetensors
strength_model = 0.8
strength_clip = 1.0
```

Expected:

```text
<lora:Some_Lora:0.8>
```

---

### Test 7: Drag-back compatibility

Steps:

1. Generate image using new node.
2. Drag saved image back into ComfyUI.

Expected:

- Workflow loads normally.
- `prompt` and `workflow` metadata remain valid.

---

### Test 8: CivitAI upload

Steps:

1. Upload saved image to CivitAI.
2. Check parser result.

Expected CivitAI should detect:

- Positive prompt.
- Negative prompt.
- Steps.
- Sampler.
- CFG scale.
- Seed.
- Size.
- LoRA tags.
- LoRA hashes if supported by parser.

---

## 23. Implementation Checklist

### Phase 1: Save node foundation

- [ ] Create `nodes/save_image_a1111_metadata_node.py`.
- [ ] Implement `SaveImageA1Metadata`.
- [ ] Copy relevant save behavior from ComfyUI `SaveImage`.
- [ ] Add hidden `prompt` and `extra_pnginfo`.
- [ ] Save PNG with original `prompt` and `workflow`.
- [ ] Add `parameters` key.
- [ ] Register node.

---

### Phase 2: Sampler/settings extractor

- [ ] Find main `KSampler`.
- [ ] Extract `steps`.
- [ ] Extract `cfg`.
- [ ] Extract `sampler_name`.
- [ ] Extract `scheduler`.
- [ ] Extract `seed` / `noise_seed`.
- [ ] Extract image size from tensor shape.

---

### Phase 3: Prompt resolver

- [ ] Resolve positive prompt from `KSampler.positive`.
- [ ] Resolve negative prompt from `KSampler.negative`.
- [ ] Support direct `CLIPTextEncode.text`.
- [ ] Support linked `CLIPTextEncode.text`.
- [ ] Support `TextSplitter`.
- [ ] Support `StringConcatenate`.
- [ ] Add fallback override inputs.

---

### Phase 4: LoRA extractor

- [ ] Support rgthree Power Lora Loader.
- [ ] Support ComfyUI `LoraLoader`.
- [ ] Ignore disabled LoRAs.
- [ ] Strip LoRA extensions.
- [ ] Format A1111 LoRA tags.
- [ ] Resolve LoRA file path.
- [ ] Compute SHA256.
- [ ] Write `Lora hashes`.

---

### Phase 5: Debugging and tests

- [ ] Add `debug_sidecar`.
- [ ] Save `.parameters.txt` if enabled.
- [ ] Save `.metadata_debug.json` if enabled.
- [ ] Test direct TextSplitter workflow.
- [ ] Test TextSplitter + StringConcatenate workflow.
- [ ] Test rgthree Power Lora Loader.
- [ ] Test ComfyUI LoraLoader.
- [ ] Test drag-back into ComfyUI.
- [ ] Test CivitAI upload.

---

## 24. Final Recommendation

Implement:

```text
Save Image A1111 Metadata
```

with class:

```python
SaveImageA1Metadata
```

as a custom save node.

Do not attempt to use a metadata-only node before the original ComfyUI `SaveImage`.

Reason:

```text
A metadata-only node cannot reliably force the original SaveImage node to write the A1111 parameters metadata into the final PNG.
```

The selected implementation is stable, testable, and matches the current workflow assumption:

```text
one main KSampler
one main Save Image
rgthree Power Lora Loader and/or ComfyUI LoraLoader
TextSplitter/StringConcatenate feeding CLIPTextEncode
```

This design keeps ComfyUI compatibility while improving CivitAI metadata parsing.
