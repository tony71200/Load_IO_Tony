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
