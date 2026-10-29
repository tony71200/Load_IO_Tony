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
