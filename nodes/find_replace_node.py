import re


def _find_replace(text, find, replace, replace_in=None, whole_word=True):
    if replace_in is not None:
        if not replace:
            replace = replace_in
        elif "{in}" in replace:
            replace = replace.replace("{in}", replace_in)
    alts = [a.strip() for a in str(find or "").split("|") if a.strip()]
    if not alts:
        return text
    alts.sort(key=len, reverse=True)
    body = "|".join(re.escape(a) for a in alts)
    if whole_word:
        # "_" counts as a word char, so "tnga_brief" never matches "brief".
        body = rf"(?<!\w)(?:{body})(?!\w)"
    pattern = re.compile(body, re.IGNORECASE)
    return pattern.sub(lambda m: replace, text)


class FindAndReplace:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "text": ("STRING", {"forceInput": True}),
                "find": ("STRING", {"default": "", "multiline": False}),
                "replace": ("STRING", {"default": "", "multiline": False}),
                "whole_word": ("BOOLEAN", {"default": True, "tooltip": "Match whole words only (brief does not hit tnga_brief or briefly)."}),
            },
            "optional": {
                "replace_in": ("STRING", {"forceInput": True}),
            },
        }

    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("text",)
    FUNCTION = "run"
    CATEGORY = "Tony4896/Text"

    def run(self, text, find, replace, whole_word=True, replace_in=None):
        return (_find_replace(text, find, replace, replace_in, whole_word),)
