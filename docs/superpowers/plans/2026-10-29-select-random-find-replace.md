# Select_Random and Find_and_Replace Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add two text nodes to the Load_IO_Tony ComfyUI pack: `Select_Random` (dynamic list of trigger words, one picked per queue) and `Find_and_Replace` (alternatives → replacement, with a `{in}` template socket).

**Architecture:** Each node is one Python file under `nodes/` registered in `tony4896_io_nodes.py`, following `nodes/json_batch_node.py`. `Find_and_Replace` is backend only. `Select_Random` accepts any `item_N` prompt input through a permissive optional-input dict (`FlexibleOptionalInputType` in `nodes/common.py`, the rgthree Power LoRA Loader approach) and gets a new frontend file `web/select_random.js` that draws the rows, the add button, the count label and keeps the `index` widget's `max` in sync so ComfyUI's own `control_after_generate: randomize` picks `0 … n-1`.

**Tech Stack:** Python 3.13 (ComfyUI venv at `D:\001_Personal_Proj\Comfy\.venv`), ComfyUI frontend 1.53.10 (classic LiteGraph canvas, ES-module extensions under `web/`), plain-script tests run with the venv Python.

**Spec:** `docs/superpowers/specs/2026-10-29-select-random-find-replace-design.md`

## Global Constraints

- Branch: `20261029_SelectRandom_FindReplace` (already created; commit there, do not push).
- Node class names registered as `"Select_Random"` and `"Find_and_Replace"`, display names identical, `CATEGORY = "Tony4896/Text"`.
- Tests are plain functions with a `__main__` runner, run as
  `D:/001_Personal_Proj/Comfy/.venv/Scripts/python.exe tests/<file>.py` from the repo root. pytest is NOT installed; do not install it.
- Importing anything from `Load_IO_Tony.nodes` triggers `Load_IO_Tony/__init__.py`, which imports torch and PIL, so tests must use the venv Python, never the system Python.
- Frontend facts (verified in the 1.53.10 bundle): a plain `{type:"custom", name, value, draw, computeSize, mouse}` widget pushed onto `node.widgets` is drawn and serialized; the API prompt includes every widget with a `name` unless `widget.options.serialize === false`; `widgets_values` includes every widget unless `widget.serialize === false`; `app.canvas.prompt(title, value, callback, event, multiline)` opens a textarea dialog when `multiline` is true; `control_after_generate: randomize` computes `floor(random * (max - min) / step2) * step2 + min`, so `max` is exclusive.
- Commit subjects in the repo style: `Add ...`, `Fix ...`, `Export ...`. End every commit message with `Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>`.
- No new dependencies, no network code, keep imports at module scope.

---

## File structure

| File | Responsibility |
| --- | --- |
| `nodes/find_replace_node.py` (create) | `_find_replace()` pure function + `FindAndReplace` node class |
| `tests/test_find_replace.py` (create) | behaviour tests for `_find_replace` and `FindAndReplace.run` |
| `nodes/common.py` (modify, append) | `FlexibleOptionalInputType` |
| `nodes/select_random_node.py` (create) | `_collect_items()` + `SelectRandom` node class |
| `tests/test_select_random.py` (create) | tests for item collection, clamping, errors, flexible dict |
| `tony4896_io_nodes.py` (modify) | import + register both nodes |
| `README.md` (modify) | one short section per node |
| `web/tony4896_io.js` (modify, one line) | `export` the existing `addTextLabel` helper |
| `web/select_random.js` (create) | Select_Random UI: rows, add button, total label, index sync, configure restore |

---

### Task 1: Find_and_Replace backend

**Files:**
- Create: `nodes/find_replace_node.py`
- Create: `tests/test_find_replace.py`
- Modify: `tony4896_io_nodes.py` (imports block lines 5-24, both mapping dicts lines 28-48)
- Modify: `README.md` (append a section)

**Interfaces:**
- Consumes: nothing from other tasks.
- Produces: `_find_replace(text: str, find: str, replace: str, replace_in: str | None = None) -> str` and class `FindAndReplace` with `run(self, text, find, replace, replace_in=None) -> tuple[str]`.

- [ ] **Step 1: Write the failing test**

Create `tests/test_find_replace.py`:

```python
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from Load_IO_Tony.nodes.find_replace_node import FindAndReplace, _find_replace  # noqa: E402


def test_template_with_replace_in():
    out = _find_replace("2men at the beach, 2male again", "2men|2male", "{in} and other guy", "Ivan_Ryo")
    assert out == "Ivan_Ryo and other guy at the beach, Ivan_Ryo and other guy again"


def test_case_insensitive_substring():
    assert _find_replace("2Men and 2MALEs", "2men|2male", "x") == "x and xs"


def test_empty_find_returns_text_unchanged():
    assert _find_replace("keep me", "", "x") == "keep me"
    assert _find_replace("keep me", " | ", "x") == "keep me"


def test_longest_alternative_wins():
    assert _find_replace("2men only here", "2men|2men only", "X") == "X here"


def test_replace_in_without_template_marker():
    assert _find_replace("a 2men", "2men", "", "Ivan_Ryo") == "a Ivan_Ryo"
    assert _find_replace("a 2men", "2men", "literal", "Ivan_Ryo") == "a literal"


def test_backslash_in_replacement_is_literal():
    assert _find_replace("a b", "b", r"c\1d") == r"a c\1d"


def test_alternatives_are_escaped():
    assert _find_replace("{char} walks (fast)", "{char}|(fast)", "Ivan_Ryo") == "Ivan_Ryo walks Ivan_Ryo"


def test_node_run():
    node = FindAndReplace()
    assert node.run("{char} walks", "{char}|{char2}", "Ivan_Ryo") == ("Ivan_Ryo walks",)
    assert node.run("2men here", "2men", "{in} and other guy", replace_in="Ivan_Ryo") == ("Ivan_Ryo and other guy here",)


def test_input_types_shape():
    types = FindAndReplace.INPUT_TYPES()
    assert list(types["required"]) == ["text", "find", "replace"]
    assert types["required"]["text"][1]["forceInput"] is True
    assert list(types["optional"]) == ["replace_in"]
    assert types["optional"]["replace_in"][1]["forceInput"] is True


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            fn()
            print("ok", name)
```

- [ ] **Step 2: Run the test to verify it fails**

Run from the repo root:

```bash
D:/001_Personal_Proj/Comfy/.venv/Scripts/python.exe tests/test_find_replace.py
```

Expected: `ModuleNotFoundError: No module named 'Load_IO_Tony.nodes.find_replace_node'`

- [ ] **Step 3: Write the implementation**

Create `nodes/find_replace_node.py`:

```python
import re


def _find_replace(text, find, replace, replace_in=None):
    if replace_in is not None:
        if not replace:
            replace = replace_in
        elif "{in}" in replace:
            replace = replace.replace("{in}", replace_in)
    alts = [a.strip() for a in str(find or "").split("|") if a.strip()]
    if not alts:
        return text
    alts.sort(key=len, reverse=True)
    pattern = re.compile("|".join(re.escape(a) for a in alts), re.IGNORECASE)
    return pattern.sub(lambda m: replace, text)


class FindAndReplace:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "text": ("STRING", {"forceInput": True}),
                "find": ("STRING", {"default": "", "multiline": False}),
                "replace": ("STRING", {"default": "", "multiline": False}),
            },
            "optional": {
                "replace_in": ("STRING", {"forceInput": True}),
            },
        }

    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("text",)
    FUNCTION = "run"
    CATEGORY = "Tony4896/Text"

    def run(self, text, find, replace, replace_in=None):
        return (_find_replace(text, find, replace, replace_in),)
```

Why `lambda m: replace`: `re.sub` with a string replacement interprets `\1` and `\g<>`; a function returns the replacement literally.

- [ ] **Step 4: Run the test to verify it passes**

```bash
D:/001_Personal_Proj/Comfy/.venv/Scripts/python.exe tests/test_find_replace.py
```

Expected: nine `ok test_...` lines, exit code 0.

- [ ] **Step 5: Register the node**

In `tony4896_io_nodes.py` add after the `SaveImageA1Metadata` import:

```python
from .nodes.find_replace_node import FindAndReplace
```

Add to `NODE_CLASS_MAPPINGS` after `"SaveImageA1Metadata": SaveImageA1Metadata,`:

```python
    "Find_and_Replace": FindAndReplace,
```

Add to `NODE_DISPLAY_NAME_MAPPINGS` after `"SaveImageA1Metadata": "Save Image A1111 Metadata",`:

```python
    "Find_and_Replace": "Find_and_Replace",
```

- [ ] **Step 6: Verify the package still imports**

```bash
D:/001_Personal_Proj/Comfy/.venv/Scripts/python.exe -c "import sys; sys.path.insert(0, 'D:/001_Personal_Proj/Comfy/ComfyUI/custom_nodes'); import Load_IO_Tony as m; print(sorted(m.NODE_CLASS_MAPPINGS))"
```

Expected: the printed list contains `'Find_and_Replace'` (a `[Tony4896_IO] Failed to register web routes` line is normal outside the server).

- [ ] **Step 7: README section**

Append to `README.md`:

```markdown
## Find_and_Replace

Replaces words in a prompt. `find` holds one or more alternatives separated by `|` (`2men|2male`), matched case-insensitively; `replace` is the replacement text. Connect a wire straight to `find` or `replace` to drive them from another node. The optional `replace_in` socket turns `replace` into a template: `{in}` is substituted with the connected value (`{in} and other guy` + `Ivan_Ryo` → `Ivan_Ryo and other guy`); an empty `replace` uses the connected value as is.
```

- [ ] **Step 8: Commit**

```bash
git add nodes/find_replace_node.py tests/test_find_replace.py tony4896_io_nodes.py README.md
git commit -m "Add Find_and_Replace node

Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>"
```

---

### Task 2: Select_Random backend

**Files:**
- Modify: `nodes/common.py` (append at end of file)
- Create: `nodes/select_random_node.py`
- Create: `tests/test_select_random.py`
- Modify: `tony4896_io_nodes.py` (imports and both mappings)
- Modify: `README.md` (append a section)

**Interfaces:**
- Consumes: nothing from other tasks.
- Produces: `FlexibleOptionalInputType(type_name: str)` in `nodes/common.py`; `_collect_items(kwargs: dict) -> list[str]` and class `SelectRandom` with `pick(self, index, **kwargs) -> tuple[str]` in `nodes/select_random_node.py`. Task 3 relies on the prompt input names `index` and `item_<n>`, and on the `index` INT options `{"default": 0, "min": 0, "max": 999999, "step": 1, "control_after_generate": True}`.

- [ ] **Step 1: Write the failing test**

Create `tests/test_select_random.py`:

```python
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from Load_IO_Tony.nodes.common import FlexibleOptionalInputType  # noqa: E402
from Load_IO_Tony.nodes.select_random_node import SelectRandom, _collect_items  # noqa: E402

ITEMS = {"item_10": "ten", "item_2": " two ", "item_1": "one"}


def test_collect_sorts_numerically_and_strips():
    assert _collect_items(ITEMS) == ["one", "two", "ten"]


def test_collect_skips_blank_and_foreign_keys():
    assert _collect_items({"item_1": "   ", "item_2": "b", "other": "x", "item_x": "y"}) == ["b"]


def test_pick_by_index():
    node = SelectRandom()
    assert node.pick(0, **ITEMS) == ("one",)
    assert node.pick(2, **ITEMS) == ("ten",)


def test_pick_clamps_index():
    node = SelectRandom()
    assert node.pick(99, **ITEMS) == ("ten",)
    assert node.pick(-5, **ITEMS) == ("one",)


def test_pick_without_items_raises():
    try:
        SelectRandom().pick(0)
    except ValueError:
        pass
    else:
        raise AssertionError("expected ValueError")


def test_flexible_optional_accepts_any_key_but_lists_none():
    opt = FlexibleOptionalInputType("STRING")
    assert "item_7" in opt
    assert opt["item_7"] == ("STRING",)
    assert list(opt) == []


def test_input_types():
    types = SelectRandom.INPUT_TYPES()
    assert types["required"]["index"][1]["control_after_generate"] is True
    assert isinstance(types["optional"], FlexibleOptionalInputType)


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            fn()
            print("ok", name)
```

- [ ] **Step 2: Run the test to verify it fails**

```bash
D:/001_Personal_Proj/Comfy/.venv/Scripts/python.exe tests/test_select_random.py
```

Expected: `ImportError: cannot import name 'FlexibleOptionalInputType' from 'Load_IO_Tony.nodes.common'`

- [ ] **Step 3: Add `FlexibleOptionalInputType` to `nodes/common.py`**

Append at the end of `nodes/common.py`:

```python


class FlexibleOptionalInputType(dict):
    # Optional-input dict that claims every key so the prompt may carry
    # item_1, item_2, ... without declaring them (rgthree Power LoRA Loader trick).
    def __init__(self, type_name):
        super().__init__()
        self.type_name = type_name

    def __getitem__(self, key):
        return (self.type_name,)

    def __contains__(self, key):
        return True
```

Why this works: `comfy_execution.graph.get_input_info` checks `input_name in valid_inputs["optional"]` and then reads `valid_inputs["optional"][input_name]`; `execution.validate_inputs` only iterates the dict's real keys (none), so undeclared `item_N` values are passed to `pick(**kwargs)` without validation errors, and `/object_info` sees no optional inputs.

- [ ] **Step 4: Write the node**

Create `nodes/select_random_node.py`:

```python
import re

from .common import FlexibleOptionalInputType

_ITEM_KEY = re.compile(r"^item_(\d+)$")


def _collect_items(kwargs):
    keyed = []
    for key, value in kwargs.items():
        m = _ITEM_KEY.match(key)
        if m and str(value).strip():
            keyed.append((int(m.group(1)), str(value).strip()))
    return [v for _, v in sorted(keyed)]


class SelectRandom:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "index": ("INT", {"default": 0, "min": 0, "max": 999999, "step": 1, "control_after_generate": True}),
            },
            "optional": FlexibleOptionalInputType("STRING"),
        }

    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("text",)
    FUNCTION = "pick"
    CATEGORY = "Tony4896/Text"

    def pick(self, index, **kwargs):
        items = _collect_items(kwargs)
        if not items:
            raise ValueError("Select_Random has no item. Click 'Add item' and type a word.")
        idx = max(0, min(int(index), len(items) - 1))
        return (items[idx],)
```

- [ ] **Step 5: Run the test to verify it passes**

```bash
D:/001_Personal_Proj/Comfy/.venv/Scripts/python.exe tests/test_select_random.py
```

Expected: seven `ok test_...` lines, exit code 0.

- [ ] **Step 6: Register the node**

In `tony4896_io_nodes.py` add after the `FindAndReplace` import:

```python
from .nodes.select_random_node import SelectRandom
```

Add to `NODE_CLASS_MAPPINGS` after `"Find_and_Replace": FindAndReplace,`:

```python
    "Select_Random": SelectRandom,
```

Add to `NODE_DISPLAY_NAME_MAPPINGS` after `"Find_and_Replace": "Find_and_Replace",`:

```python
    "Select_Random": "Select_Random",
```

Re-run the import check from Task 1 Step 6; the list must now contain both `'Find_and_Replace'` and `'Select_Random'`.

- [ ] **Step 7: README section**

Append to `README.md`:

```markdown
## Select_Random

A list of trigger words, phrases or paragraphs; each queue outputs one of them. Click `Add item` to add a row, click a row to edit it in a multiline dialog, click `×` to remove it. `Total Items` shows the count. `index` is the picked row; with `control_after_generate` on `randomize` (default) ComfyUI draws a new index in `0 … n-1` for every queue, `fixed` pins one row.
```

- [ ] **Step 8: Commit**

```bash
git add nodes/common.py nodes/select_random_node.py tests/test_select_random.py tony4896_io_nodes.py README.md
git commit -m "Add Select_Random node backend

Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>"
```

---

### Task 3: Select_Random frontend

**Files:**
- Modify: `web/tony4896_io.js` (the `function addTextLabel(` line, around line 80)
- Create: `web/select_random.js`

**Interfaces:**
- Consumes: node class name `"Select_Random"`, widget `index` (INT with `options.min/max/step2`) and its `control_after_generate` combo, both auto-created by ComfyUI from Task 2's `INPUT_TYPES`; prompt input names `item_<n>`.
- Produces: `addTextLabel(node, name, defaultText)` exported from `web/tony4896_io.js` (unchanged behaviour); widget layout `[item_N rows..., "Add item" button, "Total Items" label, index, control_after_generate]` with `widgets_values = [item values..., index, control]`.

There is no JS test harness in this repo; this task is verified in the built-in browser against the running server. New Python nodes need a server restart first (Task 4 Step 1 shows how); if Task 2 is already loaded, a browser reload is enough for JS changes because extension files are served from disk.

- [ ] **Step 1: Export `addTextLabel`**

In `web/tony4896_io.js` change

```js
function addTextLabel(node, name, defaultText = "") {
```

to

```js
export function addTextLabel(node, name, defaultText = "") {
```

- [ ] **Step 2: Create `web/select_random.js`**

```js
import { app } from "../../scripts/app.js";
import { addTextLabel } from "./tony4896_io.js";

const ROW_H = 20;
const MARGIN = 15;
const X_W = 18;

function itemWidgets(node) { return node.widgets.filter(w => w.name.startsWith("item_")); }
function findWidget(node, name) { return node.widgets.find(w => w.name === name); }

function syncItems(node) {
    const n = itemWidgets(node).length;
    findWidget(node, "Total Items").value = String(n);
    const index = findWidget(node, "index");
    // control_after_generate "randomize" draws from [min, max), so max = n gives 0..n-1.
    index.options.max = n;
    if (index.value > n) index.value = n;
    const h = node.computeSize()[1];
    if (node.size[1] < h) node.setSize([node.size[0], h]);
    node.setDirtyCanvas(true, true);
}

function addItem(node, value = "") {
    node.__tonyItemCounter = (node.__tonyItemCounter || 0) + 1;
    const row = {
        name: `item_${node.__tonyItemCounter}`, type: "custom", value, options: {},
        computeSize(width) { return [width, ROW_H]; },
        draw(ctx, node, width, y) {
            const textY = y + ROW_H * 0.7;
            ctx.save();
            ctx.fillStyle = "#222";
            ctx.strokeStyle = "#666";
            ctx.beginPath();
            ctx.roundRect(MARGIN, y, width - MARGIN * 2, ROW_H, ROW_H * 0.5);
            ctx.fill();
            ctx.stroke();
            ctx.beginPath();
            ctx.rect(MARGIN, y, width - MARGIN * 2, ROW_H);
            ctx.clip();
            ctx.fillStyle = "#999";
            ctx.textAlign = "left";
            ctx.fillText(this.name, MARGIN * 2, textY);
            ctx.textAlign = "right";
            ctx.fillText("\u2715", width - MARGIN - 7, textY);
            let text = String(this.value ?? "").replace(/\s+/g, " ");
            const maxW = width - MARGIN * 4 - ctx.measureText(this.name).width - X_W;
            if (ctx.measureText(text).width > maxW) {
                while (text.length && ctx.measureText(text + "\u2026").width > maxW) text = text.slice(0, -1);
                text += "\u2026";
            }
            ctx.fillStyle = text ? "#ddd" : "#777";
            ctx.fillText(text || "click to edit", width - MARGIN - X_W, textY);
            ctx.restore();
        },
        mouse(event, pos, node) {
            if (event.type !== "pointerup") return false;
            if (pos[0] > node.size[0] - MARGIN - X_W) {
                node.removeWidget(this);
            } else {
                app.canvas.prompt("Item", this.value, (v) => {
                    this.value = String(v ?? "");
                    node.setDirtyCanvas(true, true);
                }, event, true);
            }
            syncItems(node);
            return true;
        },
    };
    node.widgets.splice(node.widgets.indexOf(findWidget(node, "Add item")), 0, row);
    return row;
}

app.registerExtension({
    name: "Tony4896.SelectRandom",
    async beforeRegisterNodeDef(nodeType, nodeData) {
        if (nodeData.name !== "Select_Random") return;

        const onNodeCreated = nodeType.prototype.onNodeCreated;
        nodeType.prototype.onNodeCreated = function () {
            onNodeCreated?.apply(this, arguments);
            const button = this.addWidget("button", "Add item", null, () => { addItem(this); syncItems(this); });
            button.serialize = false;
            button.options.serialize = false;
            const total = addTextLabel(this, "Total Items", "0");
            total.serialize = false;
            for (const name of ["index", "control_after_generate"]) {
                const w = findWidget(this, name);
                this.widgets.splice(this.widgets.indexOf(w), 1);
                this.widgets.push(w);
            }
            syncItems(this);
        };

        // Saved workflows map widgets_values by position, so the rows must exist
        // before LiteGraph assigns values. Rows = values minus the fixed serialized widgets.
        const configure = nodeType.prototype.configure;
        nodeType.prototype.configure = function (info) {
            for (const w of itemWidgets(this)) this.removeWidget(w);
            const fixed = this.widgets.filter(w => w.serialize !== false).length;
            const n = Math.max(0, (info.widgets_values?.length ?? 0) - fixed);
            for (let i = 0; i < n; i++) addItem(this);
            configure.apply(this, arguments);
            syncItems(this);
        };
    },
});
```

Notes for the implementer:
- `addTextLabel` already sets `options.serialize = false`; `total.serialize = false` keeps it out of `widgets_values` so only rows, `index` and the control combo occupy slots.
- ComfyUI's `control_after_generate` combo is created with `options.serialize = false` but without `serialize = false`, so it does take a `widgets_values` slot; the `fixed` count in `configure` accounts for it automatically.
- `mouse` is called by the canvas on `pointerdown` and again on `pointerup` with `pos` relative to the node; acting on `pointerup` only avoids opening the dialog when the user merely starts a drag.
- `node.removeWidget(widget)` exists on LGraphNode in frontend 1.53 and also detaches any input slot bound to the widget.

- [ ] **Step 3: Load the JS in the browser and smoke-test**

Prerequisite: the server is running with Task 2's Python loaded (restart per Task 4 Step 1 if needed). Open `http://127.0.0.1:8188` in the built-in browser, reload the page (Ctrl+F5 bypasses the module cache), then in the browser JS console:

```js
const node = LiteGraph.createNode("Select_Random");
app.graph.add(node);
node.widgets.map(w => w.name)
```

Expected: `["Add item", "Total Items", "index", "control_after_generate"]` and no console error mentioning `select_random.js`.

- [ ] **Step 4: Exercise add / edit / remove**

In the console:

```js
const btn = node.widgets.find(w => w.name === "Add item");
btn.callback(); btn.callback(); btn.callback();
const rows = node.widgets.filter(w => w.name.startsWith("item_"));
rows[0].value = "tnga_brief"; rows[1].value = "lrcontour_brief"; rows[2].value = "stng_bikini";
[node.widgets.map(w => w.name), node.widgets.find(w => w.name === "Total Items").value, node.widgets.find(w => w.name === "index").options.max]
```

Expected: names `["item_1","item_2","item_3","Add item","Total Items","index","control_after_generate"]`, total `"3"`, max `3`. Then click a row on the canvas: a textarea dialog opens; type text, press OK, the pill shows it. Click `✕` on a row: it disappears and `Total Items` drops to `2`. Add it back for the next step.

- [ ] **Step 5: Verify prompt serialization and save/reload**

In the console:

```js
const p = await app.graphToPrompt();
p.output[String(node.id)].inputs
```

Expected: `{item_1: "tnga_brief", item_2: ..., item_3: ..., index: <number>}` with no `Add item`, `Total Items` or `control_after_generate` keys. Save the workflow (Ctrl+S, name `test_select_random`), reload the page, reopen it: three rows with their values, total `3`, `index` max `3`. Queue the prompt three times: the `index` value changes between runs with `randomize`; set the combo to `fixed` and the value stays.

- [ ] **Step 6: Commit**

```bash
git add web/tony4896_io.js web/select_random.js
git commit -m "Add Select_Random frontend widgets

Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>"
```

---

### Task 4: End-to-end check in ComfyUI

**Files:** none modified (a test workflow is saved through the UI into `user/default/workflows/`).

**Interfaces:**
- Consumes: both nodes from Tasks 1-3.
- Produces: a saved workflow `test_select_random_find_replace` proving the chain works.

- [ ] **Step 1: Restart the server so the new Python nodes load**

In PowerShell, stop the running ComfyUI and start it again:

```powershell
Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -match 'ComfyUI\\main\.py' } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force }
Start-Process -FilePath "D:\001_Personal_Proj\Comfy\run_gpu.bat" -WorkingDirectory "D:\001_Personal_Proj\Comfy"
```

Wait until `http://127.0.0.1:8188/object_info/Select_Random` returns JSON (the first start can take a minute), then confirm:

```bash
curl -s http://127.0.0.1:8188/object_info/Find_and_Replace | head -c 300
```

Expected: JSON containing `"Find_and_Replace"` with `"category": "Tony4896/Text"`.

- [ ] **Step 2: Build the workflow in the built-in browser**

Open `http://127.0.0.1:8188`, new blank workflow, then in the console:

```js
const g = app.graph;
const sel = LiteGraph.createNode("Select_Random"); sel.pos = [100, 100]; g.add(sel);
const add = sel.widgets.find(w => w.name === "Add item");
for (const v of ["tnga_brief", "lrcontour_brief", "stng_bikini"]) { add.callback(); sel.widgets.filter(w => w.name.startsWith("item_")).at(-1).value = v; }
const prim = LiteGraph.createNode("PrimitiveStringMultiline"); prim.pos = [100, 400]; g.add(prim);
prim.widgets[0].value = "2Men at the beach, 2male smiling";
const far = LiteGraph.createNode("Find_and_Replace"); far.pos = [500, 250]; g.add(far);
far.widgets.find(w => w.name === "find").value = "2men|2male";
far.widgets.find(w => w.name === "replace").value = "{in} and other guy";
const show = LiteGraph.createNode("Display Any (rgthree)"); show.pos = [900, 250]; g.add(show);
prim.connect(0, far, far.findInputSlot("text"));
sel.connect(0, far, far.findInputSlot("replace_in"));
far.connect(0, show, 0);
g.setDirtyCanvas(true, true);
```

If `PrimitiveStringMultiline` does not exist on this ComfyUI build, use `"PrimitiveString"` instead.

- [ ] **Step 3: Queue and check**

Click Queue three times (or `await app.queuePrompt(0, 1)` three times, waiting for each to finish). Expected: Display Any shows `<trigger> and other guy at the beach, <trigger> and other guy smiling` where `<trigger>` is one of the three items, and across the three runs `index` on Select_Random changes. Set `control_after_generate` to `fixed`, queue twice: the same trigger both times. Disconnect `replace_in` and queue: the output is `{in} and other guy at the beach, ...` (the template is literal without a socket, as specified).

- [ ] **Step 4: Save and reload**

Ctrl+S, name `test_select_random_find_replace`. Reload the page and open the workflow: the three rows, their values, `Total Items 3` and both Find_and_Replace fields are restored. Queue once more to confirm it still runs.

- [ ] **Step 5: Final test run and status**

```bash
D:/001_Personal_Proj/Comfy/.venv/Scripts/python.exe tests/test_find_replace.py
D:/001_Personal_Proj/Comfy/.venv/Scripts/python.exe tests/test_select_random.py
D:/001_Personal_Proj/Comfy/.venv/Scripts/python.exe tests/test_json_batch.py
git status --short
```

Expected: all `ok` lines, exit code 0, and a clean tree (everything committed on `20261029_SelectRandom_FindReplace`). Do not push.
