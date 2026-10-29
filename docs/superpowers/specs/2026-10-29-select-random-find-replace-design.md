# Select_Random and Find_and_Replace nodes

Date: 2026-10-29
Branch: `20261029_SelectRandom_FindReplace`
Status: approved

## Goal

Two text nodes for the Load_IO_Tony pack:

- `Select_Random`: the user types any number of trigger words, phrases or
  paragraphs; each queue picks one at random and outputs it.
- `Find_and_Replace`: replaces one or more alternatives in a prompt with a
  replacement string, which can be a template around a connected value.

Both nodes live in `Tony4896/Text`, are registered in `tony4896_io_nodes.py`
and get a short README section.

## Select_Random

### Backend (`nodes/select_random_node.py`)

```python
class SelectRandom:
    INPUT_TYPES: required {"index": ("INT", {"default": 0, "min": 0, "max": 999999,
                                             "control_after_generate": True})}
                 optional FlexibleOptionalInputType("STRING")   # accepts any item_N
    RETURN_TYPES = ("STRING",); RETURN_NAMES = ("text",)
    FUNCTION = "pick"; CATEGORY = "Tony4896/Text"
```

- `FlexibleOptionalInputType` goes in `nodes/common.py`: a `dict` whose
  `__contains__` is always true and whose `__getitem__` returns `("STRING",)`
  for unknown keys. This is the same approach rgthree's Power LoRA Loader uses
  so the prompt may carry `item_1`, `item_2`, ... without declaring them.
- `pick(self, index, **kwargs)`: collect `kwargs` keys matching `item_<n>`,
  sort by `n`, keep values whose `str(v).strip()` is non-empty.
  Empty list → `ValueError("Select_Random has no item.")`.
  `idx = max(0, min(int(index), len(items) - 1))`, return `(items[idx],)`.
- No `IS_CHANGED`: the frontend randomizes `index` before each queue, so the
  cache key already changes.

### Frontend (`web/select_random.js`, new file)

Widget order on the node, top to bottom:

1. `item_N` rows (custom canvas widgets, serialized)
2. `➕ Add item` button (`serialize = false`, `options.serialize = false`)
3. `Total Items` label drawn like the existing `addTextLabel` pill
   (`serialize = false`, `options.serialize = false`)
4. `index` number widget and its `control_after_generate` combo, both created
   by ComfyUI and moved to the end of `node.widgets`

Row widget (`type: "custom"`, `name: "item_N"`, `value: string`):

- `draw`: rounded pill like `addTextLabel`; left label `item_N`, right the
  value fitted with an ellipsis, a `×` glyph at the far right.
- `mouse(event, pos, node)`: on `pointerdown` inside the `×` box remove the
  widget; elsewhere on the row open
  `app.canvas.prompt("Item", value, cb, event, true)` (multiline dialog).
  After either action call `syncItems(node)`.
- `computeSize(width)` → `[width, 20]`.
- Default `serialize` and `options.serialize` so the value goes to both
  `widgets_values` and the API prompt as `item_N`.

Node-level behaviour:

- `addItem(node, value = "")`: `N = ++node.__tonyItemCounter`, push the row
  widget, then move it before the Add button.
- `syncItems(node)`: `n = count of item_ widgets`; `Total Items` label shows
  `n`; `index.options.max = Math.max(0, n - 1)`; clamp `index.value`;
  `node.setSize([node.size[0], node.computeSize()[1]])` when the node grew;
  `setDirtyCanvas(true, true)`.
- `onNodeCreated` wrapper (runs after ComfyUI created `index` and the control
  combo): add the button and label, move `index` and the combo to the end,
  `syncItems`.
- `configure` wrapper: before calling the original, remove existing `item_`
  rows, read `info.widgets_values`, compute
  `n = widgets_values.length - (serialized non-item widgets)`, add `n` empty
  rows, then let the original `configure` assign values by position.
  After it returns, `syncItems`.
- Row names are never renumbered after a removal; names only need to be
  unique within the node. `__tonyItemCounter` is restored on configure as the
  highest existing `N`.

Randomize semantics: ComfyUI's `control_after_generate` combo
(`fixed | increment | decrement | randomize`) already randomizes within
`[options.min, options.max]`, so keeping `options.max = n - 1` gives exactly
`0 … n-1`. `fixed` pins one item. Default is `randomize`.

## Find_and_Replace

### Backend (`nodes/find_replace_node.py`), no frontend code

```python
INPUT_TYPES: required {
    "text":    ("STRING", {"forceInput": True}),
    "find":    ("STRING", {"default": "", "multiline": False}),
    "replace": ("STRING", {"default": "", "multiline": False}),
}, optional {
    "replace_in": ("STRING", {"forceInput": True}),
}
RETURN_TYPES = ("STRING",); RETURN_NAMES = ("text",)
FUNCTION = "run"; CATEGORY = "Tony4896/Text"
```

`_find_replace(text, find, replace, replace_in=None)` (module function so the
test can import it):

1. Effective replacement:
   - `replace_in is None` → `replace` verbatim.
   - `replace_in` given and `replace` has `{in}` → `replace.replace("{in}", replace_in)`.
   - `replace_in` given and `replace` is empty → `replace_in`.
   - `replace_in` given, `replace` non-empty without `{in}` → `replace` verbatim
     (the user typed a literal; the socket is ignored).
2. Alternatives: `[a.strip() for a in find.split("|") if a.strip()]`.
   None → return `text` unchanged.
3. Pattern: alternatives sorted longest first, `re.escape`d, joined with `|`,
   compiled with `re.IGNORECASE`. `pattern.sub(lambda m: replacement, text)`
   so backslashes in the replacement are literal.

Connecting a wire straight to the `find` or `replace` widget is the normal
ComfyUI behaviour and needs no code: the connected value replaces the box.
`replace_in` exists only for the template case
(`replace = "{in} and other guy"`, `replace_in = "Ivan_Ryo"`).

## Registration and docs

- `tony4896_io_nodes.py`: import both classes, add `"Select_Random"` and
  `"Find_and_Replace"` to both mappings with identical display names.
- README: one short section per node under the existing node list.

## Tests (pytest, same import style as `tests/test_json_batch.py`)

`tests/test_select_random.py`

- picks by index, ignores empty items, sorts `item_10` after `item_2`
- clamps out-of-range index
- raises when there is no item

`tests/test_find_replace.py`

- `2men|2male` → `Ivan_Ryo and other guy` via `replace_in` template
- case-insensitive match (`2Men`)
- empty `find` returns input unchanged
- longest alternative wins (`2men|2men only`)
- backslash in replacement stays literal

## Manual verification

1. Restart ComfyUI (`D:\001_Personal_Proj\Comfy\run_gpu.bat`) so the new
   Python nodes load; a browser reload is enough for later JS changes.
2. Open `http://127.0.0.1:8188`, new workflow:
   `Select_Random` (tnga_brief, lrcontour_brief, stng_bikini) →
   `Find_and_Replace.replace_in`; a Primitive string → `text`;
   output → rgthree Display Any.
3. Queue three times: the index changes, the displayed prompt changes.
   Set `fixed`, queue twice: same item. Save, reload the page: rows, values
   and `Total Items` come back.

## Out of scope

- Per-row on/off toggles, move up/down, drag reorder.
- Multiple find/replace pairs in one node.
- A `find_in` socket.
