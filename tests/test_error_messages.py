from app.ui.error_messages import message_for_error


def test_maps_unsupported_format_to_actionable_chinese_message():
    message = message_for_error("unsupported_format", "photo.tiff")

    assert "photo.tiff" in message
    assert "JPEG" in message
    assert "PNG" in message
    assert "RAW" in message


def test_maps_output_permission_error_to_directory_action():
    message = message_for_error("output_not_writable", "D:/locked")

    assert "输出目录" in message
    assert "其他" in message
