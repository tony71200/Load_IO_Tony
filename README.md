# Tony4896_IO v4

Custom ComfyUI nodes for image/text batch IO.

## Nodes

1. **I. Load Image (Tony4896)**
   - Mode: Image / Folder
   - Browser dialog picker
   - Preview image widget
   - Outputs: image, file_name, width, height, size

2. **II. Load Image Batches (Tony4896)**
   - Folder image list
   - Current index / next index / has index
   - Manual next index and JS auto batch runner

3. **III. Load Image Text Batch (Tony4896)**
   - Folder of images + matching `<stem>.txt` prompts (`###` splits positive/negative)
   - Label shows total images and matched image/txt pairs
   - Fallback positive/negative widgets when no txt matches

4. **IV. Text Splitter Batches (Tony4896)**
   - TXT picker
   - Paragraph separator
   - Negative separator
   - Wrapped plaintext-style previews for positive and negative prompt
   - Label shows total prompt count

5. **V. Json Batch (Tony4896)**
   - JSON picker for `prompt-collector` exports: `{"prompts": [{"index": 31, "text": "..."}, ...]}`
   - `list_key` / `text_key` configurable (default `prompts` / `text`)
   - Outputs: prompt, next_index, has_index, current_index, prompt_index (the item's own `index` field)

6. **VI. Save TXT (Tony4896)**
   - Auto save / manual save
   - Output directory
   - File name / filename prefix

7. **VII. Prompt To PNG Meta / Save Image A1111 Metadata (Tony4896)**
   - Write prompt + LoRA tags into PNG metadata (A1111 / CivitAI format)

All batch nodes share the JS auto batch runner (Start/Stop Auto Batch, `auto_delay_seconds`, `auto_max_runs`).
Do not wire `next_index` back into `index`; ComfyUI graphs cannot contain cycles.

## v4 changes

- Replaced base64 image previews with `/tony4896_io/view_image` binary image streaming.
- Fixed wrong `file_name` output: now returns only the stem, e.g. `Decidueye_3Fn_Tournament_DX29`.
- Fixed refresh race that could cause `Failed to fetch` after selecting a new image.
- Added **Clear Tony Temp** button.
- Added `/tony4896_io/clear_temp` backend route.
- Text preview now wraps like a plaintext preview instead of overflowing horizontally.
- Added `IS_CHANGED` for image load nodes to improve cache invalidation when selected files change.

## Install

Copy the folder into:

```txt
ComfyUI/custom_nodes/Tony4896_IO
```

Restart ComfyUI.

## Notes

- Browser file dialogs cannot expose the original absolute local path for security reasons.
- Selected files are uploaded into this extension's temp folder:

```txt
ComfyUI/custom_nodes/Tony4896_IO/_tony4896_temp
```

- Files are not uploaded to ComfyUI's `input` folder.
- Use **Clear Tony Temp** to remove temporary uploaded files.
