# Branch Review Q&A

## Q1: Vì sao metadata `parameters` trước đây không ổn định trong PNG cuối?
**A:** Node `PromptToPNGMeta` chỉ chèn `parameters` vào `extra_pnginfo` ở giữa graph, phụ thuộc vào node save cuối có ghi lại key này hay không. Cách tiếp cận đó không đảm bảo metadata A1111 luôn xuất hiện.

## Q2: Vấn đề lớn nhất về tương thích ComfyUI/CivitAI là gì?
**A:** Cần đồng thời giữ nguyên `prompt`/`workflow` cho ComfyUI và thêm key `parameters` cho parser A1111/CivitAI. Nếu ghi đè sai, ảnh có thể mất khả năng khôi phục workflow trong ComfyUI.

## Q3: Node mới giải quyết bằng cách nào?
**A:** Tạo node output save riêng `SaveImageA1Metadata`, tự save PNG và ghi song song `parameters`, `prompt`, cùng toàn bộ `extra_pnginfo`.

## Q4: Rủi ro logic hiện tại còn lại là gì?
**A:**
1. Hiện ưu tiên workflow 1 sampler; multi-branch phức tạp chưa tối ưu.
2. Một số node concat string không chuẩn có thể chưa resolve prompt đầy đủ.
3. Hash LoRA chỉ có khi resolve được file thực tế trong `folder_paths`.

## Q5: Kiểm tra hoạt động node cần tập trung gì?
**A:**
- Save batch ảnh có tăng counter đúng.
- PNG có đủ key `prompt`, `workflow` (nếu có), `parameters`.
- `parameters` có `Negative prompt`, `Steps`, `Sampler`, `CFG`, `Seed`, `Size`.
- LoRA tag/hash xuất hiện đúng theo tùy chọn.
