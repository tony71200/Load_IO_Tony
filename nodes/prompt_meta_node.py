class PromptToPNGMeta:
    """
    Place this node bettween text assembly and CLIPTextEncode
    It will pass through positive and negative prompt (not changed)
    Besides, it injects into PNG metadata following A1111 format for Civitai can read prompts and parameters from PNG files.
    """

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "positive": ("STRING", {"forceInput": True, "multiline": True}),
            },
            "optional": {
                "negative": ("STRING", {"forceInput": True, "multiline": True, "default": ""}),
                # If you want to inject the loras manually when using Power Lora Loader,
                # You can put them in here, example: "<lora:xxx:1>, <lora:yyy:0.5>"
                "lora_tags": ("STRING", {"default": "", "multiline": False}),
            },
            "hidden": {
                "extra_pnginfo": "EXTRA_PNGINFO",
            },
        }
    
    RETURN_TYPES = ("STRING", "STRING")
    RETURN_NAMES = ("positive", "negative")
    FUNCTION = "inject_metadata"
    CATEGORY = "Tony4896/IO"

    def inject(self, positive, negative = "", lora_tags="", extra_pnginfo=None):
        positive = positive or ""
        negative = negative or ""
        lora_tags = (lora_tags or "").strip()

        # Concate LoRA tags to the end of positive prompt, so that Civitai can read them and display in the UI.
        full_positive = f"{positive}, {lora_tags}" if lora_tags else positive

        if extra_pnginfo is not None:
            params = full_positive
            if negative:
                params += f"\nNegative prompt: {negative}"
            extra_pnginfo["parameters"] = params

        return (full_positive, negative)