from pathlib import Path

from app.core.image_service import ImageService


def test_image_service_opens_existing_jpeg_and_renders_preview():
    source = Path(__file__).parents[1] / "img-test" / "DSC_0061.JPG"
    service = ImageService()

    session = service.open(source)
    preview = service.render_preview(session, (320, 240))

    assert session.source_path == source
    assert session.pixels.shape[1] > preview.shape[1]
    assert session.pixels.shape[0] > preview.shape[0]
    assert preview.shape[2] == 4


def test_image_service_export_render_keeps_full_source_dimensions():
    source = Path(__file__).parents[1] / "img-test" / "DSC_0050.JPG"
    service = ImageService()

    session = service.open(source)
    rendered = service.render_export(session)

    assert rendered.shape[1] > session.pixels.shape[1]
    assert rendered.shape[0] > session.pixels.shape[0]
