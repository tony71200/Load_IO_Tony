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

3. **III. Text Splitter Batches (Tony4896)**
   - TXT picker
   - Paragraph separator
   - Negative separator
   - Wrapped plaintext-style previews for positive and negative prompt

4. **IV. Save TXT (Tony4896)**
   - Auto save / manual save
   - Output directory
   - File name / filename prefix

5. **V. Delay Time (Tony4896)**
   - Utility delay node
   - Do not connect its output back to an upstream index input; ComfyUI graphs cannot contain cycles.

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
