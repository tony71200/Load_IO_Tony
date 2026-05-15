import time


class Tony4896DelayTime:
    @classmethod
    def INPUT_TYPES(cls):
        return {"required": {
            "query_finish": ("BOOLEAN", {"forceInput": True, "default": False}),
            "has_index": ("BOOLEAN", {"forceInput": True, "default": False}),
            "next_index": ("INT", {"forceInput": True, "default": 0, "min": 0, "max": 999999, "step": 1}),
            "delay_seconds": ("FLOAT", {"default": 1.0, "min": 0.0, "max": 86400.0, "step": 0.1}),
        }}

    RETURN_TYPES = ("INT", "BOOLEAN")
    RETURN_NAMES = ("next_index", "continue")
    FUNCTION = "delay"
    CATEGORY = "Tony4896/IO"

    def delay(self, query_finish, has_index, next_index, delay_seconds):
        if bool(query_finish) and bool(has_index):
            time.sleep(float(delay_seconds or 0))
            return (int(next_index), True)
        return (int(next_index), False)
