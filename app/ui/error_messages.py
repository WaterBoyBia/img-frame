from __future__ import annotations


def message_for_error(code: str, detail: str = "") -> str:
    detail = detail or ""
    messages = {
        "unsupported_format": (
            f"无法打开“{detail}”。请使用 JPEG/JPG、PNG 或受支持的 RAW 格式。"
        ),
        "image_load_failed": f"图片读取失败：{detail}。请确认文件未损坏且具有读取权限。",
        "raw_decode_failed": f"RAW 图片解码失败：{detail}。请确认文件完整，或改用 JPEG/PNG。",
        "invalid_metadata": f"拍摄参数格式不正确：{detail}。请检查手动填写的数值。",
        "output_not_writable": (
            f"输出目录不可写：{detail}。请选择其他输出目录，并确认目录具有写入权限。"
        ),
        "export_failed": f"导出 PNG 失败：{detail}。请检查输出目录和磁盘空间。",
        "font_unavailable": "找不到微软雅黑字体，无法绘制参数文字。",
        "memory_error": "图片尺寸过大，内存不足。请先缩小图片或处理较小的文件。",
        "no_session": "尚未打开图片，请先选择一张图片。",
    }
    return messages.get(code, "处理失败，请检查文件和输出目录。")
