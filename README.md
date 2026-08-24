# img-frame

`img-frame` 是一个 Windows 桌面工具，用于读取照片的拍摄参数并在原图外部添加相框。相框会显示相机型号、焦距、快门速度、光圈和 ISO 等信息，原图区域保持原始像素质量。

## 首阶段范围

- 输入支持 JPEG/JPG、PNG 和常见 RAW 格式。
- 默认使用纯白色经典外扩相框，参数文字分为两行并整体水平居中：第一行显示相机型号，第二行按可用值显示焦距、快门速度、光圈和 ISO。
- 缺失的拍摄参数会隐藏，对应行或字段会重新排列，不显示空标签。
- 字体统一使用微软雅黑。
- 输出统一为 PNG。只保留源图的 ICC 色彩配置文件，不写出 EXIF、XMP、IPTC、GPS、厂商私有字段或其他文本元数据。
- 输出文件不会覆盖原图或已有成品，发生重名时会自动生成不冲突的文件名。

## 运行

所有程序和测试都使用 `img-frame` conda 环境：

```powershell
conda activate img-frame
python -m pip install -r requirements.txt
# app.main 将在后续任务中加入；当前任务只完成运行环境和测试骨架
python -m app.main
```

首阶段只提供源码运行方式，不生成 PyInstaller 应用目录或 Inno Setup 安装包。PNG、16-bit PNG 和 RAW 的真实测试素材会在补充后续素材后加入测试。

## 测试

```powershell
conda activate img-frame
python -m pytest -q
```
