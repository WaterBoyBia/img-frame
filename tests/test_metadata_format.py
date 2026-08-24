from app.core.metadata_format import format_display_lines
from app.models.metadata import MetadataValues


def test_formats_approved_two_line_layout_without_labels():
    values = MetadataValues("NIKON D750", 50.0, "1/250s", "f/2.8", 100)

    assert format_display_lines(values) == [
        "NIKON D750",
        "50mm    1/250s    f/2.8    100",
    ]


def test_hides_missing_fields_and_recenters_values():
    values = MetadataValues("NIKON D750", 50.0, None, "f/2.8", None)

    assert format_display_lines(values) == ["NIKON D750", "50mm    f/2.8"]


def test_hides_empty_lines():
    assert format_display_lines(MetadataValues()) == []
