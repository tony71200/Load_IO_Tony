import { app } from "../../scripts/app.js";
import { api } from "../../scripts/api.js";

function apiURL(path) { return typeof api.apiURL === "function" ? api.apiURL(path) : path; }

function widget(node, name) { return node.widgets?.find(w => w.name === name); }
function getWidget(node, name, fallback = "") {
    const w = widget(node, name);
    return w ? w.value : fallback;
}
function setWidget(node, name, value, callCallback = true) {
    const w = widget(node, name);
    if (w) {
        w.value = value;
        if (callCallback) w.callback?.(value);
    }
}
function setWidgetSilent(node, name, value) { setWidget(node, name, value, false); }
async function getJSON(url) {
    let res;
    try {
        res = await api.fetchApi(url);
    } catch (e) {
        throw new Error(`Failed to fetch ${url}: ${e?.message || e}`);
    }
    const data = await res.json();
    if (!res.ok || !data.ok) throw new Error(data.error || `HTTP ${res.status}`);
    return data;
}
async function postJSON(url, body) {
    let res;
    try {
        res = await api.fetchApi(url, { method: "POST", body: JSON.stringify(body), headers: {"Content-Type": "application/json"} });
    } catch (e) {
        throw new Error(`Failed to fetch ${url}: ${e?.message || e}`);
    }
    const data = await res.json();
    if (!res.ok || !data.ok) throw new Error(data.error || `HTTP ${res.status}`);
    return data;
}
async function postForm(url, form) {
    let res;
    try {
        res = await api.fetchApi(url, { method: "POST", body: form });
    } catch (e) {
        throw new Error(`Failed to fetch ${url}: ${e?.message || e}`);
    }
    const data = await res.json();
    if (!res.ok || !data.ok) throw new Error(data.error || `HTTP ${res.status}`);
    return data;
}
async function clearTonyTemp() {
    return await postJSON("/tony4896_io/clear_temp", {});
}
function pickFiles({accept = "", multiple = false, directory = false} = {}) {
    return new Promise((resolve) => {
        const input = document.createElement("input");
        input.type = "file";
        input.accept = accept;
        input.multiple = multiple || directory;
        if (directory) input.webkitdirectory = true;
        input.style.display = "none";
        document.body.appendChild(input);
        input.onchange = () => {
            const files = Array.from(input.files || []);
            document.body.removeChild(input);
            resolve(files);
        };
        input.click();
    });
}
function addTextLabel(node, name, defaultText = "") {
    const w = node.addWidget("text", name, defaultText, () => {}, { serialize: false });
    w.disabled = true;
    return w;
}
function addPreviewWidget(node) {
    const preview = {
        name: "Preview Image", type: "custom", value: null, img: null, text: "No image",
        computeSize(width) { return [width, 230]; },
        draw(ctx, node, width, y) {
            const h = 220;
            ctx.save();
            ctx.strokeStyle = "#777";
            ctx.strokeRect(10, y + 4, width - 20, h - 8);
            ctx.fillStyle = "#aaa";
            ctx.font = "12px sans-serif";
            if (this.img && this.img.complete) {
                const maxW = width - 28, maxH = h - 28;
                const scale = Math.min(maxW / this.img.width, maxH / this.img.height);
                const dw = this.img.width * scale, dh = this.img.height * scale;
                const dx = 14 + (maxW - dw) / 2, dy = y + 14 + (maxH - dh) / 2;
                ctx.drawImage(this.img, dx, dy, dw, dh);
            } else {
                ctx.fillText(this.text || "No image", 18, y + 30);
            }
            ctx.restore();
        },
    };
    node.widgets.push(preview);
    return preview;
}
function wrapCanvasText(ctx, text, maxWidth) {
    const rawLines = String(text || "").replace(/\t/g, "    ").split("\n");
    const out = [];
    for (const raw of rawLines) {
        if (raw === "") { out.push(""); continue; }
        let line = "";
        const words = raw.split(/(\s+)/);
        for (const word of words) {
            const test = line + word;
            if (ctx.measureText(test).width <= maxWidth || line.length === 0) {
                line = test;
            } else {
                out.push(line.trimEnd());
                line = word.trimStart();
            }
        }
        if (line) out.push(line.trimEnd());
    }
    return out;
}
function addTextPreviewWidget(node, name, height = 190) {
    const preview = {
        name, type: "custom", value: "", scroll: 0,
        computeSize(width) { return [width, height]; },
        draw(ctx, node, width, y) {
            const h = height - 10;
            const x = 10, boxY = y + 4, boxW = width - 20, boxH = h - 8;
            ctx.save();
            ctx.fillStyle = "#1f1f1f";
            ctx.fillRect(x, boxY, boxW, boxH);
            ctx.strokeStyle = "#666";
            ctx.strokeRect(x, boxY, boxW, boxH);
            ctx.beginPath();
            ctx.rect(x + 6, boxY + 6, boxW - 12, boxH - 12);
            ctx.clip();
            ctx.fillStyle = "#ddd";
            ctx.font = "12px monospace";
            const maxWidth = boxW - 18;
            const lines = wrapCanvasText(ctx, this.value || "", maxWidth);
            let yy = boxY + 20;
            const lineH = 15;
            const maxLines = Math.floor((boxH - 14) / lineH);
            for (const line of lines.slice(0, maxLines)) {
                ctx.fillText(line, x + 10, yy);
                yy += lineH;
            }
            if (lines.length > maxLines) {
                ctx.fillStyle = "#aaa";
                ctx.fillText(`… ${lines.length - maxLines} more line(s)`, x + 10, boxY + boxH - 8);
            }
            ctx.restore();
        },
    };
    node.widgets.push(preview);
    return preview;
}
async function uploadOneImage() {
    const files = await pickFiles({ accept: ".png,.jpg,.jpeg,.bmp,.webp,.tif,.tiff,image/*" });
    if (!files.length) return null;
    const form = new FormData();
    form.append("file", files[0], files[0].name);
    return await postForm("/tony4896_io/upload_image", form);
}
async function uploadFolderImages() {
    const files = await pickFiles({ accept: ".png,.jpg,.jpeg,.bmp,.webp,.tif,.tiff,image/*", directory: true });
    if (!files.length) return null;
    const form = new FormData();
    for (const f of files) {
        const safeName = f.webkitRelativePath ? f.webkitRelativePath.split("/").pop() : f.name;
        form.append("files", f, safeName);
    }
    return await postForm("/tony4896_io/upload_folder", form);
}
async function uploadTxt() {
    const files = await pickFiles({ accept: ".txt,text/plain" });
    if (!files.length) return null;
    const form = new FormData();
    form.append("file", files[0], files[0].name);
    return await postForm("/tony4896_io/upload_txt", form);
}
async function refreshFolderList(node, folderPath, indexWidgetName = "selected_index") {
    const q = new URLSearchParams({ folder: folderPath });
    const data = await getJSON(`/tony4896_io/list_images?${q.toString()}`);
    if (data.files.length > 0) {
        const idx = Math.min(Number(getWidget(node, indexWidgetName, 0) || 0), data.files.length - 1);
        setWidgetSilent(node, "file_name", data.files[idx].name);
    }
    return data;
}
async function refreshImage(node, previewWidget, infoWidget = null, batch = false) {
    const mode = batch ? "Folder" : getWidget(node, "mode", "Image");
    const reqId = (node.__tonyRefreshId = (node.__tonyRefreshId || 0) + 1);
    const q = new URLSearchParams({
        mode,
        image_path: getWidget(node, "image_path", ""),
        folder_path: getWidget(node, "folder_path", ""),
        file_name: getWidget(node, "file_name", ""),
        index: batch ? getWidget(node, "index", 0) : getWidget(node, "selected_index", 0),
    });
    const data = await getJSON(`/tony4896_io/image_info?${q.toString()}`);
    if (reqId !== node.__tonyRefreshId) return;

    // Keep the UI file_name as basename.ext, while backend output returns stem only.
    setWidgetSilent(node, "file_name", data.name);
    if (!batch && mode === "Image") setWidgetSilent(node, "folder_path", data.folder);
    if (infoWidget) infoWidget.value = `${data.name} | ${data.size}`;

    previewWidget.text = data.size;
    const img = new Image();
    img.onload = () => app.canvas.setDirty(true, true);
    img.onerror = () => {
        if (reqId !== node.__tonyRefreshId) return;
        previewWidget.img = null;
        previewWidget.text = "Preview load failed";
        app.canvas.setDirty(true, true);
    };
    previewWidget.img = img;
    const viewParams = new URLSearchParams({ path: data.path, mtime: String(data.mtime || Date.now()) });
    img.src = apiURL(`/tony4896_io/view_image?${viewParams.toString()}`);
    node.setDirtyCanvas(true, true);
}
async function refreshTextSplitter(node, posPreview, negPreview, infoWidget = null) {
    const q = new URLSearchParams({
        txt_path: getWidget(node, "txt_path", ""),
        paragraph_sep: getWidget(node, "paragraph_sep", "\\n\\n"),
        negative_sep: getWidget(node, "negative_sep", "###"),
        index: getWidget(node, "index", 0),
    });
    const data = await getJSON(`/tony4896_io/text_split_info?${q.toString()}`);
    posPreview.value = data.positive || "";
    negPreview.value = data.negative || "";
    if (infoWidget) infoWidget.value = `index ${data.current_index + 1}/${data.count} | next=${data.next_index} | has=${data.has_index}`;
    node.setDirtyCanvas(true, true);
}


// -----------------------------------------------------------------------------
// Tony4896 Auto Batch Queue Controller
// -----------------------------------------------------------------------------
// ComfyUI graphs are DAGs, so we cannot wire next_index back to index.
// This controller runs outside the graph: queue current prompt -> wait until done
// -> increment the index widget -> queue again.
const TonyAutoBatch = {
    running: false,
    waitingForFinish: false,
    node: null,
    kind: "",
    runCount: 0,
    lastQueueAt: 0,
    refresh: null,
};

function sleep(ms) { return new Promise(resolve => setTimeout(resolve, ms)); }

function nodeStillExists(node) {
    return !!(node && app.graph && app.graph._nodes_by_id && app.graph._nodes_by_id[node.id]);
}

function getNumberWidget(node, name, fallback = 0) {
    const v = Number(getWidget(node, name, fallback));
    return Number.isFinite(v) ? v : fallback;
}

function setAutoStatus(node, text) {
    const w = widget(node, "Auto Batch Status");
    if (w) w.value = text;
    node?.setDirtyCanvas?.(true, true);
}

async function queuePromptCompat() {
    if (typeof app.queuePrompt === "function") {
        await app.queuePrompt(0, 1);
        return;
    }
    // Fallback for older/newer ComfyUI builds where app.queuePrompt changes.
    const graph = app.graphToPrompt ? await app.graphToPrompt() : null;
    if (graph && api.queuePrompt) {
        await api.queuePrompt(0, graph);
        return;
    }
    throw new Error("Cannot find a compatible ComfyUI queuePrompt API.");
}

async function getAutoBatchCount(node, kind) {
    if (kind === "image_batch") {
        const folderPath = getWidget(node, "folder_path", "");
        if (!folderPath) throw new Error("folder_path is empty.");
        const q = new URLSearchParams({ folder: folderPath });
        const data = await getJSON(`/tony4896_io/list_images?${q.toString()}`);
        return Number(data.count || 0);
    }
    if (kind === "text_batch") {
        const q = new URLSearchParams({
            txt_path: getWidget(node, "txt_path", ""),
            paragraph_sep: getWidget(node, "paragraph_sep", "\\n\\n"),
            negative_sep: getWidget(node, "negative_sep", "###"),
            index: getWidget(node, "index", 0),
        });
        const data = await getJSON(`/tony4896_io/text_split_info?${q.toString()}`);
        return Number(data.count || 0);
    }
    throw new Error(`Unsupported auto batch kind: ${kind}`);
}

async function refreshAutoNodePreview() {
    const node = TonyAutoBatch.node;
    if (!nodeStillExists(node)) return;
    try {
        if (typeof TonyAutoBatch.refresh === "function") {
            await TonyAutoBatch.refresh();
        }
    } catch (_) {
        // Preview refresh is helpful but should not kill the auto runner.
    }
}

async function startAutoBatch(node, kind, refreshCallback) {
    if (TonyAutoBatch.running) {
        alert("Another Tony4896 auto batch is already running. Stop it first.");
        return;
    }

    const count = await getAutoBatchCount(node, kind);
    const index = getNumberWidget(node, "index", 0);
    if (count <= 0) throw new Error("No batch item found.");
    if (index >= count) throw new Error(`Current index ${index} is outside batch count ${count}.`);

    TonyAutoBatch.running = true;
    TonyAutoBatch.waitingForFinish = true;
    TonyAutoBatch.node = node;
    TonyAutoBatch.kind = kind;
    TonyAutoBatch.runCount = 0;
    TonyAutoBatch.refresh = refreshCallback;
    TonyAutoBatch.lastQueueAt = Date.now();
    setAutoStatus(node, `Running: ${index + 1}/${count}`);
    await queuePromptCompat();
}

function stopAutoBatch(reason = "Stopped") {
    const node = TonyAutoBatch.node;
    TonyAutoBatch.running = false;
    TonyAutoBatch.waitingForFinish = false;
    TonyAutoBatch.node = null;
    TonyAutoBatch.kind = "";
    TonyAutoBatch.refresh = null;
    if (nodeStillExists(node)) setAutoStatus(node, reason);
}

async function onPromptFinishedForAutoBatch() {
    if (!TonyAutoBatch.running || !TonyAutoBatch.waitingForFinish) return;

    // Avoid reacting to noisy status/executing events fired immediately after queueing.
    if (Date.now() - TonyAutoBatch.lastQueueAt < 500) return;

    TonyAutoBatch.waitingForFinish = false;
    const node = TonyAutoBatch.node;
    if (!nodeStillExists(node)) {
        stopAutoBatch("Stopped: node removed");
        return;
    }

    try {
        TonyAutoBatch.runCount += 1;
        const count = await getAutoBatchCount(node, TonyAutoBatch.kind);
        const current = getNumberWidget(node, "index", 0);
        const next = current + 1;
        const maxRuns = getNumberWidget(node, "auto_max_runs", 0);
        const delaySeconds = Math.max(0, getNumberWidget(node, "auto_delay_seconds", 0));

        if (maxRuns > 0 && TonyAutoBatch.runCount >= maxRuns) {
            stopAutoBatch(`Done: reached max runs (${maxRuns})`);
            return;
        }
        if (next >= count) {
            stopAutoBatch(`Done: reached end (${count}/${count})`);
            return;
        }

        setWidget(node, "index", next);
        await refreshAutoNodePreview();
        setAutoStatus(node, `Waiting ${delaySeconds}s → next ${next + 1}/${count}`);
        if (delaySeconds > 0) await sleep(delaySeconds * 1000);

        if (!TonyAutoBatch.running || !nodeStillExists(node)) return;
        TonyAutoBatch.waitingForFinish = true;
        TonyAutoBatch.lastQueueAt = Date.now();
        setAutoStatus(node, `Running: ${next + 1}/${count}`);
        await queuePromptCompat();
    } catch (e) {
        stopAutoBatch(`Error: ${e.message}`);
        alert(e.message);
    }
}

// Different ComfyUI versions emit slightly different event payloads.
// We listen to both common signals and debounce through TonyAutoBatch.waitingForFinish.
api.addEventListener("executing", (event) => {
    const d = event.detail;
    if (d === null || d?.node === null) onPromptFinishedForAutoBatch();
});
api.addEventListener("status", (event) => {
    const q = event.detail?.exec_info?.queue_remaining;
    if (q === 0) onPromptFinishedForAutoBatch();
});


function addClearTempButton(node) {
    node.addWidget("button", "Clear Tony Temp", null, async () => {
        try {
            if (!confirm("Clear all files in Tony4896_IO/_tony4896_temp?")) return;
            const data = await clearTonyTemp();
            alert(`Cleared Tony temp: ${data.cleared_bytes || 0} bytes`);
        } catch (e) {
            alert(e.message);
        }
    });
}

app.registerExtension({
    name: "Tony4896.IO.v4",
    async beforeRegisterNodeDef(nodeType, nodeData, app) {
        const comfyClass = nodeData.name;
        if (comfyClass === "Tony4896LoadImage") {
            const orig = nodeType.prototype.onNodeCreated;
            nodeType.prototype.onNodeCreated = function () {
                orig?.apply(this, arguments);
                this.title = "I. Load Image (Tony4896)";
                const info = addTextLabel(this, "width x height", "");
                const preview = addPreviewWidget(this);
                this.addWidget("button", "Open", null, async () => {
                    try {
                        const mode = getWidget(this, "mode", "Image");
                        if (mode === "Folder") {
                            const data = await uploadFolderImages();
                            if (!data) return;
                            setWidgetSilent(this, "folder_path", data.folder);
                            setWidgetSilent(this, "file_name", data.files[0]);
                            setWidgetSilent(this, "selected_index", 0);
                        } else {
                            const data = await uploadOneImage();
                            if (!data) return;
                            setWidgetSilent(this, "image_path", data.path);
                            setWidgetSilent(this, "folder_path", data.folder);
                            setWidgetSilent(this, "file_name", data.name);
                        }
                        await refreshImage(this, preview, info, false);
                    } catch (e) { alert(e.message); }
                });
                addClearTempButton(this);
                for (const name of ["mode", "image_path", "folder_path", "file_name", "selected_index"]) {
                    const w = widget(this, name);
                    if (w) {
                        const old = w.callback;
                        w.callback = async (v) => {
                            old?.call(w, v);
                            try {
                                if (name === "folder_path" && v) await refreshFolderList(this, v);
                                await refreshImage(this, preview, info, false);
                            } catch (_) {}
                        };
                    }
                }
            };
        }
        if (comfyClass === "Tony4896LoadImageBatches") {
            const orig = nodeType.prototype.onNodeCreated;
            nodeType.prototype.onNodeCreated = function () {
                orig?.apply(this, arguments);
                this.title = "• Load Image Batches (Tony)";
                const info = addTextLabel(this, "width x height", "");
                const preview = addPreviewWidget(this);

                const syncBatchSelection = async (source = "") => {
                    const folder = getWidget(this, "folder_path", "");
                    if (!folder) return;
                    const data = await refreshFolderList(this, folder, "index");
                    if (!data?.files?.length) return;
                    if (source === "file_name") {
                        const currentName = String(getWidget(this, "file_name", "") || "");
                        const idx = data.files.findIndex(f => f.name === currentName);
                        if (idx >= 0) setWidgetSilent(this, "index", idx);
                    } else {
                        const idx = Math.max(0, Math.min(getNumberWidget(this, "index", 0), data.files.length - 1));
                        setWidgetSilent(this, "index", idx);
                        setWidgetSilent(this, "file_name", data.files[idx].name);
                    }
                };
                this.addWidget("button", "Open Folder", null, async () => {
                    try {
                        const data = await uploadFolderImages();
                        if (!data) return;
                        setWidgetSilent(this, "folder_path", data.folder);
                        setWidgetSilent(this, "file_name", data.files[0]);
                        setWidgetSilent(this, "index", 0);
                        info.value = `${data.count} image(s)`;
                        await refreshImage(this, preview, info, true);
                    } catch (e) { alert(e.message); }
                });
                addClearTempButton(this);
                this.addWidget("button", "Apply Next Index Manually", null, () => {
                    const current = Number(getWidget(this, "index", 0) || 0);
                    setWidget(this, "index", current + 1);
                });
                this.addWidget("number", "auto_delay_seconds", 0.0, () => {}, { min: 0, max: 86400, step: 0.1 });
                this.addWidget("number", "auto_max_runs", 0, () => {}, { min: 0, max: 999999, step: 1 });
                addTextLabel(this, "Auto Batch Status", "Idle");
                this.addWidget("button", "Start Auto Batch", null, async () => {
                    try {
                        await startAutoBatch(this, "image_batch", async () => refreshImage(this, preview, info, true));
                    } catch (e) { alert(e.message); }
                });
                this.addWidget("button", "Stop Auto Batch", null, () => stopAutoBatch("Stopped by user"));
                for (const name of ["folder_path", "file_name", "index"]) {
                    const w = widget(this, name);
                    if (w) {
                        const old = w.callback;
                        w.callback = async (v) => {
                            old?.call(w, v);
                            try {
                                if (name === "folder_path" && v) await syncBatchSelection("index");
                                if (name === "index") await syncBatchSelection("index");
                                if (name === "file_name") await syncBatchSelection("file_name");
                                await refreshImage(this, preview, info, true);
                            } catch (_) {}
                        };
                    }
                }
            };
        }
        if (comfyClass === "Tony4896TextSplitterBatches") {
            const orig = nodeType.prototype.onNodeCreated;
            nodeType.prototype.onNodeCreated = function () {
                orig?.apply(this, arguments);
                this.title = "III. Text Splitter Batches (Tony4896)";
                const info = addTextLabel(this, "Text Info", "");
                const posPreview = addTextPreviewWidget(this, "Preview Positive Prompt");
                const negPreview = addTextPreviewWidget(this, "Preview Negative Prompt");
                this.addWidget("button", "Open TXT", null, async () => {
                    try {
                        const data = await uploadTxt();
                        if (!data) return;
                        setWidgetSilent(this, "txt_path", data.path);
                        await refreshTextSplitter(this, posPreview, negPreview, info);
                    } catch (e) { alert(e.message); }
                });
                addClearTempButton(this);
                this.addWidget("button", "Apply Next Index Manually", null, () => {
                    const current = Number(getWidget(this, "index", 0) || 0);
                    setWidget(this, "index", current + 1);
                });
                this.addWidget("number", "auto_delay_seconds", 0.0, () => {}, { min: 0, max: 86400, step: 0.1 });
                this.addWidget("number", "auto_max_runs", 0, () => {}, { min: 0, max: 999999, step: 1 });
                addTextLabel(this, "Auto Batch Status", "Idle");
                this.addWidget("button", "Start Auto Batch", null, async () => {
                    try {
                        await startAutoBatch(this, "text_batch", async () => refreshTextSplitter(this, posPreview, negPreview, info));
                    } catch (e) { alert(e.message); }
                });
                this.addWidget("button", "Stop Auto Batch", null, () => stopAutoBatch("Stopped by user"));
                for (const name of ["txt_path", "paragraph_sep", "negative_sep", "index"]) {
                    const w = widget(this, name);
                    if (w) {
                        const old = w.callback;
                        w.callback = async (v) => { old?.call(w, v); try { await refreshTextSplitter(this, posPreview, negPreview, info); } catch (_) {} };
                    }
                }
            };
        }
        if (comfyClass === "Tony4896SaveTxt") {
            const orig = nodeType.prototype.onNodeCreated;
            nodeType.prototype.onNodeCreated = function () {
                orig?.apply(this, arguments);
                this.title = "IV. Save TXT (Tony4896)";
                const info = addTextLabel(this, "Character count", "0");
                const preview = addTextPreviewWidget(this, "Preview text");
                const syncPreview = () => {
                    const text = String(getWidget(this, "text", "") || "");
                    preview.value = text;
                    info.value = `${text.length} character(s)`;
                    this.setDirtyCanvas(true, true);
                };
                this.addWidget("button", "Save TXT", null, async () => {
                    try {
                        if (!confirm("Save TXT now?")) { setWidget(this, "manual_save_token", ""); return; }
                        const data = await postJSON("/tony4896_io/save_txt", {
                            text: getWidget(this, "text", ""),
                            output_dir: getWidget(this, "output_dir", ""),
                            file_name: getWidget(this, "file_name", ""),
                            filename_prefix: getWidget(this, "filename_prefix", "ComfyUI"),
                        });
                        setWidget(this, "manual_save_token", data.path);
                        alert(`Saved:\n${data.path}`);
                    } catch (e) { alert(e.message); }
                });
                for (const name of ["text", "file_name", "output_dir", "filename_prefix", "mode"]) {
                    const w = widget(this, name);
                    if (w) { const old = w.callback; w.callback = (v) => { old?.call(w, v); syncPreview(); }; }
                }
                syncPreview();
            };
        }
        if (comfyClass === "Tony4896DelayTime") {
            const orig = nodeType.prototype.onNodeCreated;
            nodeType.prototype.onNodeCreated = function () {
                orig?.apply(this, arguments);
                this.title = "V. Delay Time (Tony4896)";
                addTextLabel(this, "Note", "Do not connect this output back to an upstream index input.");
            };
        }
    },
});
