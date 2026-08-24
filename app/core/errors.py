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


class NoSessionError(ImgFrameError):
    code = "no_session"


class InvalidMetadataError(ImgFrameError):
    code = "invalid_metadata"


class OutputNotWritableError(ImgFrameError):
    code = "output_not_writable"
