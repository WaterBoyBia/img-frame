# img-frame 首阶段实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:subagent-driven-development` (recommended) or `superpowers:executing-plans` to implement this plan task-by-task. Each step uses checkbox syntax for tracking. Git 提交步骤按项目约束省略，由用户手动执行。

**Goal:** 在 `img-frame` conda 环境中实现一个可运行的 Windows PySide6 单图相框工具，读取现有 JPG 的拍摄参数，实时预览经典外扩白色相框，并导出只保留 ICC 的无损 PNG。

**Architecture:** 使用 PySide6 负责方案 A 主窗口和异步交互；使用 Pillow + NumPy 双路径保存源像素、位深和 ICC；使用 ExifRead 读取常用参数，使用可选 ExifTool 客户端补充厂商字段。预览从缩放副本渲染，导出始终从完整分辨率源像素渲染，纯图像核心与 UI 解耦。

**Tech Stack:** Python 3.12、PySide6、Pillow、NumPy、ExifRead、rawpy/LibRaw、pytest、pytest-qt；首阶段不执行 PyInstaller 和 Inno Setup。

---

## 执行顺序说明

章节已按编号和依赖关系排列；实现时严格按以下顺序推进：

```text
1 → 2 → 3 → 4 → 5 → 6 → 7 → 8 → 9 → 10 → 11 → 12 →
13 → 14 → 15 → 16 → 17 → 18 → 19 → 20
```

其中任务 1-7 建立数据和格式基础，任务 8-12 实现纯图像核心，任务 13-14 实现会话与导出编排，任务 15-17 实现 UI，任务 18-20 完成集成验证和文档。每个任务内的步骤必须按编号执行，只有前一步测试通过后才进入下一步。

## 任务 1：建立项目骨架和测试入口

**Files:**
- Create: `requirements.txt`
- Create: `app/__init__.py`
- Create: `app/core/__init__.py`
- Create: `app/models/__init__.py`
- Create: `app/ui/__init__.py`
- Create: `app/core/errors.py`
- Create: `tests/__init__.py`
- Create: `tests/conftest.py`
- Create: `tests/test_smoke.py`
- Create: `README.md`

- [ ] **步骤 1：写依赖和最小导入测试**

`requirements.txt` 写入：

```text
PySide6>=6.7,<7
Pillow>=10.4,<12
numpy>=2.0,<3
ExifRead>=3.0,<4
rawpy>=0.24,<1
pytest>=8.0,<9
pytest-qt>=4.4,<5
```

`tests/test_smoke.py` 写入：

```python
def test_runtime_dependencies_import():
    import numpy
    import PIL
    import PySide6

    assert numpy.__version__
    assert PIL.__version__
    assert PySide6.__version__
```

- [ ] **步骤 2：在指定 conda 环境安装依赖并运行失败前置检查**

运行：

```powershell
conda run -n img-frame python -m pip install -r requirements.txt
conda run -n img-frame python -m pytest tests/test_smoke.py -q
```

预期：安装成功，测试输出 `1 passed`。

- [ ] **步骤 3：建立测试夹具和应用包初始化**

`tests/conftest.py` 写入：

```python
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
TEST_IMAGE_DIR = PROJECT_ROOT / "img-test"
JPEG_IMAGE_PATH = TEST_IMAGE_DIR / "DSC_0061.JPG"
SECOND_JPEG_IMAGE_PATH = TEST_IMAGE_DIR / "DSC_0050.JPG"
```

各 `__init__.py` 保持空文件，确保 `app` 和 `tests` 可以被稳定导入。

`app/core/errors.py` 定义跨层使用的异常：

```python
class ImgFrameError(Exception):
    code = "unknown"


class ImageLoadError(ImgFrameError):
    code = "image_load_failed"


class RawDecodeError(ImgFrameError):
    code = "raw_decode_failed"


class ExportError(ImgFrameError):
    code = "export_failed"
```

异常实例保留 `detail` 字段，UI 层只根据 `code` 和 `detail` 生成中文提示。

- [ ] **步骤 4：补充中文运行说明**

`README.md` 至少说明：

```text
conda activate img-frame
python -m app.main
```

同时注明首阶段只在 conda 环境运行，不生成安装包；真实 PNG、16-bit PNG 和 RAW 测试素材将在后续补充。

- [ ] **步骤 5：验证骨架**

运行：

```powershell
conda run -n img-frame python -m pytest -q
```

预期：`1 passed`。

## 任务 2：定义图像会话和参数模型

**Files:**
- Create: `app/models/metadata.py`
- Create: `app/models/frame_config.py`
- Create: `app/models/image_session.py`
- Create: `tests/test_models.py`

- [ ] **步骤 1：写模型失败测试**

`tests/test_models.py` 写入：

```python
from app.models.frame_config import FrameConfig
from app.models.metadata import MetadataValues


def test_metadata_defaults_are_empty():
    values = MetadataValues()

    assert values.camera_model is None
    assert values.focal_length_mm is None
    assert values.shutter_speed is None
    assert values.aperture is None
    assert values.iso is None


def test_frame_config_defaults_match_approved_design():
    config = FrameConfig()

    assert config.material == "solid"
    assert config.color == (255, 255, 255, 255)
    assert config.opacity == 1.0
    assert config.border_ratio == 0.05
    assert config.font_ratio == 0.024


def test_frame_config_rejects_invalid_ranges():
    try:
        FrameConfig(opacity=1.5)
    except ValueError:
        pass
    else:
        raise AssertionError("opacity outside [0, 1] must fail")
```

- [ ] **步骤 2：实现参数模型**

`app/models/metadata.py` 使用 dataclass：

```python
from dataclasses import dataclass


@dataclass
class MetadataValues:
    camera_model: str | None = None
    focal_length_mm: float | None = None
    shutter_speed: str | None = None
    aperture: str | None = None
    iso: int | None = None
```

`app/models/frame_config.py` 定义：

```python
from dataclasses import dataclass


@dataclass
class FrameConfig:
    material: str = "solid"
    color: tuple[int, int, int, int] = (255, 255, 255, 255)
    opacity: float = 1.0
    border_ratio: float = 0.05
    font_ratio: float = 0.024
    blur_ratio: float = 0.03

    def __post_init__(self) -> None:
        if self.material not in {"solid", "frosted"}:
            raise ValueError("unsupported frame material")
        if not 0.0 <= self.opacity <= 1.0:
            raise ValueError("opacity must be between 0 and 1")
        if not 0.0 < self.border_ratio <= 0.2:
            raise ValueError("border_ratio must be in (0, 0.2]")
        if not 0.0 < self.font_ratio <= 0.1:
            raise ValueError("font_ratio must be in (0, 0.1]")
        if not 0.0 < self.blur_ratio <= 0.2:
            raise ValueError("blur_ratio must be in (0, 0.2]")
```

`app/models/image_session.py` 使用 dataclass 定义源图会话：

```python
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from app.models.frame_config import FrameConfig
from app.models.metadata import MetadataValues


@dataclass
class ImageSession:
    source_path: Path
    pixels: np.ndarray
    icc_profile: bytes | None
    bit_depth: int
    metadata: MetadataValues
    edited_metadata: MetadataValues
    frame_config: FrameConfig
    orientation_applied: bool
```

- [ ] **步骤 3：实现模型并运行测试**

运行：

```powershell
conda run -n img-frame python -m pytest tests/test_models.py -q
```

预期：`3 passed`。

## 任务 3：实现显示值格式化和缺失字段处理

**Files:**
- Create: `app/core/metadata_format.py`
- Create: `tests/test_metadata_format.py`

- [ ] **步骤 1：写格式化失败测试**

`tests/test_metadata_format.py` 写入：

```python
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
```

- [ ] **步骤 2：实现格式化函数**

`app/core/metadata_format.py` 定义：

```python
from app.models.metadata import MetadataValues


def format_display_lines(values: MetadataValues) -> list[str]:
    first_line = (values.camera_model or "").strip()
    second_values = [
        _format_focal_length(values.focal_length_mm),
        values.shutter_speed or "",
        values.aperture or "",
        _format_iso(values.iso),
    ]
    second_line = "    ".join(value for value in second_values if value)
    return [line for line in (first_line, second_line) if line]
```

焦距使用整数时显示 `50mm`，小数保留必要精度；ISO 转为十进制字符串；不在此函数中加入字段名称。

- [ ] **步骤 3：运行格式化测试**

```powershell
conda run -n img-frame python -m pytest tests/test_metadata_format.py -q
```

预期：`3 passed`。

## 任务 4：实现 EXIF 读取和字段标准化

**Files:**
- Create: `app/core/metadata_reader.py`
- Create: `tests/test_metadata_reader.py`

- [ ] **步骤 1：写 JPG 元数据读取测试**

`tests/test_metadata_reader.py` 写入：

```python
from pathlib import Path

from app.core.metadata_reader import MetadataReader


def test_reads_metadata_from_existing_jpeg():
    path = Path(__file__).parents[1] / "img-test" / "DSC_0061.JPG"

    values = MetadataReader().read(path)

    assert values.camera_model or values.focal_length_mm or values.iso


def test_missing_fields_return_none(tmp_path):
    from PIL import Image

    path = tmp_path / "without-exif.jpg"
    Image.new("RGB", (8, 8), "white").save(path)

    values = MetadataReader().read(path)

    assert values.camera_model is None
    assert values.focal_length_mm is None
    assert values.iso is None
```

- [ ] **步骤 2：实现 EXIF 标签读取**

`MetadataReader.read(path: Path) -> MetadataValues` 使用 Pillow 打开 JPEG/PNG，再用 `ExifRead.process_file` 读取常用标签：

```python
EXIF_TAGS = {
    "camera_model": ("Image", "Model"),
    "focal_length": ("EXIF", "FocalLength"),
    "shutter_speed": ("EXIF", "ExposureTime"),
    "aperture": ("EXIF", "FNumber"),
    "iso": ("EXIF", "ISOSpeedRatings"),
}
```

实现独立的有理数转换函数：`_ratio_to_float(value)`；快门格式化为 `1/250s`，光圈格式化为 `f/2.8`，焦距格式化前保存为 `float`，ISO 转为 `int`。标签不存在、类型错误或文件无 EXIF 时返回 `None`，不抛出未处理异常。

- [ ] **步骤 3：运行元数据测试**

```powershell
conda run -n img-frame python -m pytest tests/test_metadata_reader.py -q
```

预期：`2 passed`。

## 任务 5：实现可选 ExifTool 客户端

**Files:**
- Create: `app/core/exiftool_client.py`
- Modify: `app/core/metadata_reader.py`
- Create: `tests/test_exiftool_client.py`

- [x] **步骤 1：写命令客户端测试**

`tests/test_exiftool_client.py` 使用 `unittest.mock.patch`：

```python
from unittest.mock import patch

import rawpy

from app.core.exiftool_client import ExifToolClient


def test_reads_json_output_from_exiftool(tmp_path):
    image_path = tmp_path / "image.jpg"
    image_path.write_bytes(b"data")
    payload = b'[{"Model":"NIKON D750","FocalLength":"50 mm"}]'

    with patch("subprocess.run") as run:
        run.return_value.returncode = 0
        run.return_value.stdout = payload
        run.return_value.stderr = b""

        result = ExifToolClient("exiftool.exe").read_json(image_path)

    assert result[0]["Model"] == "NIKON D750"
    run.assert_called_once()


def test_unavailable_exiftool_returns_none(tmp_path):
    with patch("subprocess.run", side_effect=FileNotFoundError):
        assert ExifToolClient("missing.exe").read_json(tmp_path / "x.jpg") is None
```

- [x] **步骤 2：实现安全的只读客户端**

`ExifToolClient` 使用 `subprocess.run([...], check=False, capture_output=True, timeout=10)`，禁止 shell；只实现读取，不实现输出元数据写入。解析失败、超时、找不到可执行文件时返回 `None`，并提供 `available` 属性。

- [x] **步骤 3：接入元数据读取回退**

`MetadataReader` 先调用 ExifRead；任一核心字段仍缺失时调用 ExifTool JSON 读取，并仅补齐缺失值，不覆盖 ExifRead 已得到的值。首阶段没有 `tools/exiftool.exe` 时，JPG 仍必须依靠 ExifRead 工作。

- [x] **步骤 4：运行客户端和回退测试**

```powershell
conda run -n img-frame python -m pytest tests/test_exiftool_client.py tests/test_metadata_reader.py -q
```

预期：`4 passed`。

## 任务 6：实现 JPEG/PNG 加载、方向校正、位深和 ICC 提取

**Files:**
- Create: `app/core/image_loader.py`
- Create: `tests/test_image_loader.py`

- [x] **步骤 1：写现有 JPG 加载测试**

`tests/test_image_loader.py` 写入：

```python
from pathlib import Path

import numpy as np

from app.core.image_loader import ImageLoader


def test_loads_existing_jpeg_with_expected_shape_and_bit_depth():
    path = Path(__file__).parents[1] / "img-test" / "DSC_0061.JPG"

    image = ImageLoader().load(path)

    assert image.pixels.ndim == 3
    assert image.pixels.shape[2] == 3
    assert image.pixels.dtype == np.uint8
    assert image.bit_depth == 8


def test_loads_png_without_text_metadata(tmp_path):
    from PIL import Image

    path = tmp_path / "simple.png"
    Image.new("RGBA", (10, 6), (1, 2, 3, 255)).save(path)

    image = ImageLoader().load(path)

    assert image.pixels.shape == (6, 10, 4)
    assert image.bit_depth == 8
```

- [x] **步骤 2：实现 `LoadedImage` 和 Pillow 读取路径**

`LoadedImage` 使用 dataclass 定义：

```python
from dataclasses import dataclass
from pathlib import Path

import numpy as np


@dataclass
class LoadedImage:
    pixels: np.ndarray
    icc_profile: bytes | None
    bit_depth: int
    mode: str
    orientation_applied: bool
    source_path: Path
```

`ImageLoader.load`：

1. 用 Pillow 打开图片。
2. 读取 `image.info.get("icc_profile")`。
3. 用 `ImageOps.exif_transpose` 完成方向校正。
4. 对 JPEG 转为 RGB；对带 Alpha 的 PNG 保留 RGBA。
5. 使用 `np.asarray` 转为数组并复制，避免引用关闭后的 Pillow 缓冲区。
6. 根据 dtype 设置 8 或 16 位深。

- [x] **步骤 3：实现格式错误和资源错误**

对不存在路径、未知扩展名、Pillow `UnidentifiedImageError` 和读取权限错误抛出 `app.core.errors.ImageLoadError`，错误消息使用英文异常码，UI 层再转换为中文文案。

- [x] **步骤 4：运行加载测试**

```powershell
conda run -n img-frame python -m pytest tests/test_image_loader.py -q
```

预期：`2 passed`。

## 任务 7：建立 RAW 解码接口和无素材回退测试

**Files:**
- Create: `app/core/raw_decoder.py`
- Modify: `app/core/image_loader.py`
- Create: `tests/test_raw_decoder.py`

- [x] **步骤 1：写 RAW 解码器契约测试**

`tests/test_raw_decoder.py` 写入：

```python
from unittest.mock import patch

import numpy as np
import rawpy

from app.core.raw_decoder import RawDecoder


def test_decodes_with_camera_white_balance_without_auto_brightening(tmp_path):
    raw_path = tmp_path / "sample.nef"
    raw_path.write_bytes(b"raw")

    with patch("rawpy.imread") as imread:
        raw = imread.return_value
        raw.postprocess.return_value = np.zeros((4, 6, 3), dtype=np.uint16)

        result = RawDecoder().decode(raw_path)

    raw.postprocess.assert_called_once_with(
        use_camera_wb=True,
        no_auto_bright=True,
        output_bps=16,
        output_color=rawpy.ColorSpace.sRGB,
    )
    assert result.pixels.dtype == np.uint16
```

- [x] **步骤 2：实现 RAW 解码器**

`RawDecoder.decode` 调用 `rawpy.imread(path)`，再调用 `postprocess(use_camera_wb=True, no_auto_bright=True, output_bps=16, output_color=rawpy.ColorSpace.sRGB)`，返回 RGB `uint16` 数组和 sRGB ICC。资源对象使用上下文管理或 `finally` 关闭；rawpy 异常统一包装为 `app.core.errors.RawDecodeError`。

- [x] **步骤 3：接入扩展名分派**

`ImageLoader.load` 对 `.cr2`、`.cr3`、`.nef`、`.nrw`、`.arw`、`.dng`、`.orf`、`.rw2`、`.raf`、`.pef`、`.srw` 和 `.3fr` 调用 `RawDecoder`；RAW 失败抛出 `RawDecodeError`，不回退为低质量 JPEG 预览。

- [x] **步骤 4：运行 RAW 契约测试**

```powershell
conda run -n img-frame python -m pytest tests/test_raw_decoder.py -q
```

预期：`1 passed`。真实 RAW 文件测试待后续素材补充。

## 任务 8：实现相框尺寸和文字布局计算

**Files:**
- Create: `app/core/frame_layout.py`
- Create: `tests/test_frame_layout.py`

- [x] **步骤 1：写布局失败测试**

`tests/test_frame_layout.py` 写入：

```python
from app.core.frame_layout import calculate_layout


def test_classic_layout_expands_outside_original_image():
    layout = calculate_layout((6000, 4000), ["NIKON D750", "50mm    1/250s"])

    assert layout.border_px == 200
    assert layout.image_rect == (200, 200, 6000, 4000)
    assert layout.canvas_size[0] == 6400
    assert layout.canvas_size[1] > 4400
    assert layout.text_rect[0] == 200
    assert layout.text_rect[2] == 6000


def test_empty_text_does_not_create_text_area():
    layout = calculate_layout((100, 80), [])

    assert layout.canvas_size == (108, 88)
    assert layout.text_rect is None


def test_long_text_gets_smaller_font_scale_but_stays_inside():
    layout = calculate_layout((1200, 800), ["A" * 300, "B" * 300])

    assert 0.6 <= layout.font_scale <= 1.0
    assert layout.text_rect[2] <= layout.canvas_size[0]
```

- [x] **步骤 2：实现 `FrameLayout` 数据结构和计算函数**

`FrameLayout` 包含 `canvas_size`、`image_rect`、`text_rect`、`border_px`、`font_px` 和 `font_scale`。`calculate_layout(image_size, lines, border_ratio=0.05, font_ratio=0.024)` 按短边计算边框像素：`border_px = max(1, round(min(width, height) * border_ratio))`。

经典外扩规则：左、上、右为 `border_px`；底部为 `border_px + text_area_height`；文字区至少容纳两行字体、行距和上下内边距。原图矩形的宽高必须与输入一致。

- [x] **步骤 3：实现长文本缩放约束**

使用微软雅黑字体测量文本宽度，从用户字号开始逐步缩小，最低缩放到 60%；计算结果包含统一的水平居中 x 坐标和两行 y 坐标，不进行换行。

- [x] **步骤 4：运行布局测试**

```powershell
conda run -n img-frame python -m pytest tests/test_frame_layout.py -q
```

预期：`3 passed`。

## 任务 9：实现 8-bit 纯色相框渲染

**Files:**
- Create: `app/core/frame_renderer.py`
- Create: `tests/test_frame_renderer.py`

- [x] **步骤 1：写 8-bit 渲染失败测试**

`tests/test_frame_renderer.py` 写入：

```python
import numpy as np

from app.core.frame_renderer import FrameRenderer
from app.core.frame_layout import calculate_layout
from app.models.frame_config import FrameConfig


def test_solid_renderer_copies_original_pixels_to_image_rect():
    source = np.zeros((4, 6, 3), dtype=np.uint8)
    source[:, :, 0] = 123
    lines = ["CAMERA", "50mm    100"]
    layout = calculate_layout((6, 4), lines, border_ratio=0.1)

    result = FrameRenderer().render(source, layout, FrameConfig(border_ratio=0.1), lines)

    x, y, width, height = layout.image_rect
    assert result[y:y + height, x:x + width, :3].tolist() == source.tolist()
    assert result.dtype == np.uint8


def test_white_frame_uses_alpha_from_opacity():
    source = np.zeros((4, 6, 3), dtype=np.uint8)
    layout = calculate_layout((6, 4), ["CAMERA"], border_ratio=0.1)

    result = FrameRenderer().render(
        source,
        layout,
        FrameConfig(opacity=0.5, border_ratio=0.1),
        ["CAMERA"],
    )

    assert result.shape[2] == 4
    assert tuple(result[0, 0]) == (255, 255, 255, 127)
```

- [x] **步骤 2：实现字体定位和自动文字颜色**

`FrameRenderer` 使用 `ImageFont.truetype("msyh.ttc", size)`；Windows 找不到时依次尝试 `C:/Windows/Fonts/msyh.ttc` 和 `C:/Windows/Fonts/msyh.ttf`，找不到则抛出 `FontUnavailableError`。使用 Pillow `ImageDraw.textbbox` 测量并在 `text_rect` 内居中。

根据相框底色亮度 `(0.299*r + 0.587*g + 0.114*b)` 自动选择黑色或白色文字，深色背景使用白字。

- [x] **步骤 3：实现纯色画布合成**

新建带 Alpha 的 RGBA 画布，先按 `FrameConfig.color` 和 `opacity` 填充外扩区域，再把源 RGB/RGBA 像素复制到 `image_rect`。透明度 Alpha 使用 `int(opacity * 255)`，避免四舍五入造成平台差异。文字只绘制在底部文本区；不改变 `image_rect` 中任何源像素。

- [x] **步骤 4：运行 8-bit 渲染测试**

```powershell
conda run -n img-frame python -m pytest tests/test_frame_renderer.py -q
```

预期：`2 passed`。

## 任务 10：实现 16-bit 合成路径

**Files:**
- Modify: `app/core/frame_renderer.py`
- Create: `tests/test_frame_renderer_16bit.py`

- [x] **步骤 1：写 16-bit 渲染测试**

`tests/test_frame_renderer_16bit.py` 写入：

```python
import numpy as np

from app.core.frame_layout import calculate_layout
from app.core.frame_renderer import FrameRenderer
from app.models.frame_config import FrameConfig


def test_16bit_source_keeps_dtype_and_source_values():
    source = np.zeros((4, 6, 3), dtype=np.uint16)
    source[:, :, 0] = 65535
    layout = calculate_layout((6, 4), ["CAMERA"], border_ratio=0.1)

    result = FrameRenderer().render(source, layout, FrameConfig(border_ratio=0.1), ["CAMERA"])

    assert result.dtype == np.uint16
    x, y, width, height = layout.image_rect
    assert int(result[y, x, 0]) == 65535
```

- [x] **步骤 2：实现位深归一化和反归一化**

渲染器根据 `source.dtype` 选择 8-bit 或 16-bit通道：

```python
max_value = 255 if source.dtype == np.uint8 else 65535
```

颜色和 Alpha 先以 0 到 1 的浮点值计算，再乘以 `max_value` 转回源 dtype；文字蒙版使用同样的缩放，不将 16-bit 降级为 8-bit。

- [x] **步骤 3：运行 16-bit 测试**

```powershell
conda run -n img-frame python -m pytest tests/test_frame_renderer_16bit.py -q
```

预期：`1 passed`。真实 16-bit PNG 文件测试待补充素材。

## 任务 11：实现磨砂相框

**Files:**
- Modify: `app/core/frame_renderer.py`
- Create: `tests/test_frosted_renderer.py`

- [x] **步骤 1：写磨砂行为测试**

`tests/test_frosted_renderer.py` 写入：

```python
import numpy as np

from app.core.frame_layout import calculate_layout
from app.core.frame_renderer import FrameRenderer
from app.models.frame_config import FrameConfig


def test_frosted_frame_changes_outer_pixels_but_not_original_area():
    source = np.zeros((8, 8, 3), dtype=np.uint8)
    source[:, :, 1] = 200
    layout = calculate_layout((8, 8), ["CAMERA"], border_ratio=0.2)

    result = FrameRenderer().render(
        source,
        layout,
        FrameConfig(material="frosted", border_ratio=0.2, blur_ratio=0.05),
        ["CAMERA"],
    )

    x, y, width, height = layout.image_rect
    assert np.array_equal(result[y:y + height, x:x + width, :3], source)
    assert not np.array_equal(result[0, 0, :3], source[0, 0])
```

- [x] **步骤 2：实现外扩采样、模糊和颜色叠加**

只从源图边缘生成外扩背景，使用 Pillow `ImageFilter.GaussianBlur`，模糊半径为 `round(short_edge * blur_ratio)`；按照 `FrameConfig.opacity` 叠加颜色，最后复制原图区域并绘制文字。

- [x] **步骤 3：运行磨砂测试**

```powershell
conda run -n img-frame python -m pytest tests/test_frosted_renderer.py -q
```

预期：`1 passed`。

## 任务 12：实现 PNG 导出和元数据清理

**Files:**
- Create: `app/core/image_exporter.py`
- Create: `tests/test_exporter.py`

- [x] **步骤 1：写导出失败测试**

`tests/test_exporter.py` 写入：

```python
from pathlib import Path

from PIL import ImageCms
from PIL import Image
from PIL.PngImagePlugin import PngInfo

from app.core.image_exporter import ImageExporter


def test_exports_png_with_icc_but_without_text_metadata(tmp_path):
    source = Image.new("RGB", (4, 4), "red")
    icc = ImageCms.ImageCmsProfile(ImageCms.createProfile("sRGB")).tobytes()
    destination = tmp_path / "result.png"

    ImageExporter().write(source, destination, icc_profile=icc)

    output = Image.open(destination)
    assert output.format == "PNG"
    assert output.info.get("icc_profile") == icc
    assert not any(key in output.info for key in ("exif", "xmp", "XML:com.adobe.xmp", "parameters"))
```

- [x] **步骤 2：实现最小 PNG 写出接口**

`ImageExporter.write(image, destination, icc_profile)`：

1. 确认目标后缀为 `.png`。
2. 如果输入是 Pillow Image，创建不携带原 `info` 的新 Image；如果输入是 NumPy 数组，按 dtype 创建新 Image，确保不会继承源元数据。
3. 只创建 `PngInfo` 为空的 PNG 写入参数。
4. 传入 ICC 时仅设置 `icc_profile`。
5. 不传入 `exif`、`xmp` 或文本参数。

同时提供 `ImageExporter.export(image, destination, icc_profile, config)` 作为会话层调用入口；该方法只负责接收并记录当前配置，然后调用 `write`，不把配置写入 PNG。

- [x] **步骤 3：实现临时文件和原子替换**

先在目标目录创建带随机后缀的临时 PNG；写入成功后使用 `Path.replace` 移动到已经由 `OutputNaming` 确定的唯一目标；失败时删除临时文件并重新抛出 `app.core.errors.ExportError`。

- [x] **步骤 4：运行导出测试**

```powershell
conda run -n img-frame python -m pytest tests/test_exporter.py -q
```

预期：`1 passed`。
## 任务 13：实现输出文件名和目录策略

**Files:**
- Create: `app/core/output_naming.py`
- Create: `tests/test_output_naming.py`

- [x] **步骤 1：写防覆盖命名测试**

`tests/test_output_naming.py` 写入：

```python
from app.core.output_naming import unique_output_path


def test_adds_framed_suffix_and_png_extension(tmp_path):
    source = tmp_path / "DSC_0061.JPG"

    assert unique_output_path(source, tmp_path).name == "DSC_0061_framed.png"


def test_increments_when_output_exists(tmp_path):
    source = tmp_path / "DSC_0061.JPG"
    (tmp_path / "DSC_0061_framed.png").touch()
    (tmp_path / "DSC_0061_framed_1.png").touch()

    assert unique_output_path(source, tmp_path).name == "DSC_0061_framed_2.png"
```

- [x] **步骤 2：实现确定性路径函数**

`unique_output_path(source_path, output_dir)` 使用 `Path.stem` 生成 `_framed.png`，目标已存在时从 `_framed_1.png` 开始递增；不得修改源文件后缀以外的用户文件。

- [x] **步骤 3：运行命名测试**

```powershell
conda run -n img-frame python -m pytest tests/test_output_naming.py -q
```

预期：`2 passed`。

## 任务 14：实现加载、预览、导出用例和会话控制器

**Files:**
- Create: `app/core/image_service.py`
- Create: `app/core/session_controller.py`
- Create: `tests/test_session_controller.py`

- [x] **步骤 1：写会话控制器测试**

`tests/test_session_controller.py` 使用 fake loader、fake renderer 和 fake exporter：

```python
from app.core.session_controller import SessionController
from app.models.frame_config import FrameConfig
from app.models.image_session import ImageSession
from app.models.metadata import MetadataValues
import numpy as np


def make_test_session(path):
    values = MetadataValues(camera_model="TEST")
    return ImageSession(
        source_path=path,
        pixels=np.zeros((4, 4, 3), dtype=np.uint8),
        icc_profile=None,
        bit_depth=8,
        metadata=values,
        edited_metadata=values,
        frame_config=FrameConfig(),
        orientation_applied=True,
    )


class FakeImageService:
    def open(self, path):
        return make_test_session(path)

    def render_preview(self, session, max_size):
        return session.pixels

    def render_export(self, session):
        return session.pixels


class FakeExporter:
    last_config = None

    def export(self, image, destination, icc_profile, config):
        self.last_config = config
        destination.touch()
        return destination


def make_controller_with_fakes():
    return SessionController(
        image_service=FakeImageService(),
        exporter=FakeExporter(),
    )


def test_open_image_creates_session_and_preview(tmp_path):
    controller = make_controller_with_fakes()
    source_path = tmp_path / "photo.jpg"

    session = controller.open_image(source_path)

    assert session.source_path == source_path
    assert controller.preview is not None


def test_export_uses_unique_path_and_current_frame_config(tmp_path):
    controller = make_controller_with_fakes()
    source_path = tmp_path / "photo.jpg"
    controller.open_image(source_path)
    controller.set_output_directory(tmp_path)

    output_path = controller.export()

    assert output_path.name == "photo_framed.png"
    assert controller.exporter.last_config == controller.session.frame_config
```

- [x] **步骤 2：实现 `ImageService`**

`ImageService.open(path)` 编排 `ImageLoader` 和 `MetadataReader`，返回 `ImageSession`；`render_preview(session, max_size)` 只对源像素生成缩放预览；`render_export(session)` 使用完整分辨率调用 `FrameRenderer`。

- [x] **步骤 3：实现 `SessionController`**

控制器保存当前会话、当前输出目录和预览结果，提供 `open_image`、`set_metadata`、`set_frame_config`、`set_output_directory`、`render_preview` 和 `export` 方法。导出前统一检查：存在会话、参数值合法、输出目录可写；不满足时抛出带 `code` 和 `detail` 的 `ImgFrameError`。

- [x] **步骤 4：实现 150 ms 预览合并策略接口**

控制器只提供 `schedule_preview_update()` 信号入口，实际 Qt 定时器放到 UI 层；同一段时间内多次滑块变化只触发一次 `render_preview`。

- [x] **步骤 5：运行控制器测试**

```powershell
conda run -n img-frame python -m pytest tests/test_session_controller.py -q
```

预期：`2 passed`。

## 任务 15：建立 PySide6 主窗口和空状态

**Files:**
- Create: `app/main.py`
- Create: `app/ui/main_window.py`
- Create: `tests/test_main_window.py`

- [ ] **步骤 1：写空状态 UI 测试**

`tests/test_main_window.py` 写入：

```python
def test_main_window_starts_with_disabled_export(qtbot):
    from app.ui.main_window import MainWindow

    window = MainWindow()
    qtbot.addWidget(window)
    window.show()

    assert not window.export_button.isEnabled()
    assert window.open_button.isEnabled()
```

- [ ] **步骤 2：实现主窗口骨架**

`MainWindow` 使用方案 A 的 `QHBoxLayout`：左侧快捷工具、中央 `PreviewWidget` 占满剩余空间、右侧 `SettingsPanel` 固定宽度 258 px；底部使用输出栏。所有按钮和标签使用中文，应用字体设置为 `Microsoft YaHei UI`，回退 `Microsoft YaHei`。

- [ ] **步骤 3：实现 `app/main.py` 启动入口**

```python
import sys

from PySide6.QtWidgets import QApplication

from app.ui.main_window import MainWindow


def main() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName("img-frame")
    window = MainWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **步骤 4：运行空状态 UI 测试**

```powershell
$env:QT_QPA_PLATFORM = "offscreen"
conda run -n img-frame python -m pytest tests/test_main_window.py -q
```

预期：`1 passed`。

## 任务 16：实现图片打开、参数编辑和实时预览

**Files:**
- Create: `app/ui/preview_widget.py`
- Create: `app/ui/settings_panel.py`
- Modify: `app/ui/main_window.py`
- Modify: `tests/test_main_window.py`

- [ ] **步骤 1：写打开图片和参数编辑测试**

追加到 `tests/test_main_window.py`：

```python
def test_opening_existing_jpeg_enables_export(qtbot):
    from pathlib import Path

    from app.ui.main_window import MainWindow

    window = MainWindow()
    qtbot.addWidget(window)
    window.open_path(Path(__file__).parents[1] / "img-test" / "DSC_0061.JPG")

    assert window.export_button.isEnabled()
    assert window.camera_model_edit.text()


def test_editing_camera_model_updates_controller(qtbot):
    from app.ui.main_window import MainWindow

    window = MainWindow()
    qtbot.addWidget(window)
    window.camera_model_edit.setText("TEST CAMERA")
    window.camera_model_edit.editingFinished.emit()

    assert window.controller.session.edited_metadata.camera_model == "TEST CAMERA"
```

- [ ] **步骤 2：实现 `PreviewWidget`**

使用 `QLabel` 显示预览 `QPixmap`，提供 `set_image`、`set_zoom` 和 `fit_to_window`；不要保存或导出它内部的缩放像素。

- [ ] **步骤 3：实现 `SettingsPanel`**

创建相机型号、焦距、快门、光圈和 ISO 编辑框；创建纯色/磨砂分段控件、颜色按钮、透明度/厚度/字号/模糊半径滑块；值变化发出 `metadata_changed` 或 `frame_config_changed` 信号。

- [ ] **步骤 4：实现短延迟刷新和线程任务**

主窗口使用 `QTimer(singleShot=True)`，超时时间 150 ms；图片加载和完整预览放入 `QThreadPool`/`QRunnable`，结果通过信号回主线程，旧任务结果带 session id，不能覆盖新会话。

- [ ] **步骤 5：运行 UI 测试**

```powershell
$env:QT_QPA_PLATFORM = "offscreen"
conda run -n img-frame python -m pytest tests/test_main_window.py -q
```

预期：`3 passed`。

## 任务 17：实现输出目录、导出反馈和错误映射

**Files:**
- Modify: `app/ui/main_window.py`
- Create: `app/ui/error_messages.py`
- Create: `tests/test_error_messages.py`

- [ ] **步骤 1：写错误文案测试**

`tests/test_error_messages.py` 写入：

```python
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
```

- [ ] **步骤 2：实现结构化错误到中文文案映射**

`message_for_error(code, detail)` 为 `unsupported_format`、`image_load_failed`、`raw_decode_failed`、`invalid_metadata`、`output_not_writable`、`export_failed`、`font_unavailable` 和 `memory_error` 提供固定中文模板；未知错误显示通用“处理失败，请检查文件和输出目录”。

- [ ] **步骤 3：实现输出目录选择和 QSettings**

底部目录按钮打开 `QFileDialog.getExistingDirectory`；成功选择后写入 `QSettings("img-frame", "img-frame")` 的 `output_directory`；启动时读取，若路径不存在则回退源目录。

- [ ] **步骤 4：实现导出状态和完成反馈**

导出按钮点击后禁用，显示“正在导出…”，通过后台任务调用 `SessionController.export`；成功后显示目标路径，并提供 `QDesktopServices.openUrl(QUrl.fromLocalFile(output_dir))`；失败时删除临时文件、恢复按钮并显示错误文案。

- [ ] **步骤 5：运行错误文案测试**

```powershell
conda run -n img-frame python -m pytest tests/test_error_messages.py -q
```

预期：`2 passed`。

## 任务 18：补充 JPG 集成测试和元数据清理验证

**Files:**
- Create: `tests/test_jpeg_integration.py`
- Modify: `tests/conftest.py`

- [ ] **步骤 1：写端到端 JPG 导出测试**

`tests/test_jpeg_integration.py` 写入：

```python
from pathlib import Path

import numpy as np
from PIL import Image

from app.core.image_exporter import ImageExporter
from app.core.image_loader import ImageLoader
from app.core.metadata_format import format_display_lines
from app.core.frame_layout import calculate_layout
from app.core.frame_renderer import FrameRenderer
from app.core.metadata_reader import MetadataReader
from app.models.frame_config import FrameConfig


def test_existing_jpeg_can_be_framed_without_metadata(tmp_path):
    source_path = Path(__file__).parents[1] / "img-test" / "DSC_0061.JPG"
    loaded = ImageLoader().load(source_path)
    values = MetadataReader().read(source_path)
    lines = format_display_lines(values)
    layout = calculate_layout((loaded.pixels.shape[1], loaded.pixels.shape[0]), lines)
    rendered = FrameRenderer().render(loaded.pixels, layout, FrameConfig(), lines)
    destination = tmp_path / "framed.png"

    ImageExporter().write(rendered, destination, loaded.icc_profile)

    output = Image.open(destination)
    assert output.format == "PNG"
    assert output.info.get("icc_profile") == loaded.icc_profile
    assert "exif" not in output.info
    assert output.size == layout.canvas_size
```

- [ ] **步骤 2：补充原图区域逐像素断言**

在同一测试中根据 `layout.image_rect` 截取输出 RGB/RGBA 区域，与 `loaded.pixels` 使用 `numpy.array_equal` 比较；如果 JPEG 含方向信息，比较对象必须是方向校正后的 `loaded.pixels`。

- [ ] **步骤 3：运行集成测试**

```powershell
conda run -n img-frame python -m pytest tests/test_jpeg_integration.py -q
```

预期：`1 passed`。

## 任务 19：补充运行文档和开发检查命令

**Files:**
- Modify: `README.md`
- Create: `run.ps1`

- [ ] **步骤 1：写中文 README**

README 说明以下内容：

```text
项目简介
当前支持格式
默认相框规则
元数据只读取不写出，ICC 保留
缺失参数的显示规则
输出命名规则
开发环境启动方式
首阶段暂不生成安装包
后续 PNG、16-bit PNG、RAW 测试素材说明
```

- [ ] **步骤 2：实现仅使用 conda 环境的启动脚本**

`run.ps1` 内容：

```powershell
conda run -n img-frame python -m app.main
```

脚本不调用系统 Python、不调用 PyInstaller、不调用 Inno Setup。

- [ ] **步骤 3：运行启动前静态检查**

```powershell
conda run -n img-frame python -m compileall app tests
```

预期：命令退出码为 0。

## 任务 20：执行首阶段完整验证

**Files:**
- Modify: all files created in tasks 1-19 only when verification exposes a defect

- [ ] **步骤 1：运行全部自动化测试**

```powershell
$env:QT_QPA_PLATFORM = "offscreen"
conda run -n img-frame python -m pytest -q
```

预期：所有测试通过，至少覆盖现有两张 JPG、模型、格式化、布局、8-bit/16-bit 合成契约、磨砂、导出和 UI 空状态。

- [ ] **步骤 2：启动真实桌面应用**

```powershell
conda run -n img-frame python -m app.main
```

手动确认：打开两张 `img-test` JPG，参数编辑、相框设置、实时预览、输出目录选择和导出按钮均可用。

- [ ] **步骤 3：验证输出文件**

对导出 PNG 检查：

```powershell
conda run -n img-frame python -c "from PIL import Image; import sys; im=Image.open(sys.argv[1]); print(im.format, im.size, im.mode, bool(im.info.get('icc_profile')), sorted(im.info.keys()))" <output.png>
```

预期：格式为 `PNG`；ICC 存在时为 `True`；`sorted(im.info.keys())` 不包含 `exif`、`xmp`、`XML:com.adobe.xmp` 或自定义文本键。

- [ ] **步骤 4：执行范围检查**

确认本阶段没有创建或调用：

```text
PyInstaller
D:\Inno Setup 6
installer\img-frame.iss
```

首阶段完成标准：自动化测试通过，应用在 `img-frame` 环境启动，现有 JPG 可以导出符合规则的 PNG。



