class ImgFrameError(Exception):
    code = "unknown"

    def __init__(self, detail: str = "") -> None:
        self.detail = detail
        super().__init__(detail)


class ImageLoadError(ImgFrameError):
    code = "image_load_failed"


class RawDecodeError(ImgFrameError):
    code = "raw_decode_failed"


class ExportError(ImgFrameError):
    code = "export_failed"


class FontUnavailableError(ImgFrameError):
    code = "font_unavailable"
