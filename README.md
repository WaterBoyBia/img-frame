# img-frame

`img-frame` 是一个 Windows 桌面图片相框工具。程序读取照片中的相机型号、焦距、快门速度、光圈和 ISO，并在原图外侧生成可定制相框。原图区域使用完整分辨率像素参与导出，不从界面预览图生成成品。

## 当前功能

- 单张图片打开、参数识别和手动修改。
- 实时预览纯色或磨砂相框。
- 自定义相框颜色、透明度、边框厚度、字号和磨砂半径。
- 自定义输出目录，自动生成不会覆盖已有文件的文件名。
- 输出格式可选择 JPG 或 PNG，默认 JPG；PNG 保持无损并支持 8 位和 16 位图像路径。
- JPG 输出使用高质量 8 位 RGB 编码；透明区域会合成到白色背景。
- 字体统一使用微软雅黑。

## 支持格式

输入图片：

- JPEG、JPG
- PNG

当前仓库中的真实测试素材为 `img-test/DSC_0050.JPG` 和 `img-test/DSC_0061.JPG`。PNG、16 位 PNG 和 JPG 输出已有自动化契约测试。

## 默认相框

默认使用白色纯色外扩相框，布局整体居中：

1. 第一行只显示相机型号，并使用微软雅黑粗体。
2. 第二行依次显示焦距、快门速度、光圈和 ISO。
3. 只显示参数值，不显示“焦距”“快门”“ISO”等字段名称。
4. 缺失参数自动隐藏，其余内容重新居中。
5. 不显示镜头信息。

## 元数据和色彩

- ExifRead 读取常规 EXIF；可用时由 ExifTool 补齐缺失字段。
- 输出 PNG 和 JPG 均只保留 ICC 色彩配置文件。
- 输出不写入 EXIF、XMP、IPTC、GPS、厂商私有字段或自定义文本元数据。

## 输出命名

例如源文件为 `DSC_0061.JPG`：

```text
DSC_0061_framed.jpg
DSC_0061_framed_1.jpg
DSC_0061_framed_2.jpg
```

选择 PNG 时扩展名相应替换为 `.png`。程序不会覆盖原图或已经存在的导出文件。

## 开发环境

所有命令必须在 `img-frame` conda 环境中运行：

```powershell
conda activate img-frame
python -m pip install -r requirements.txt
python -m app.main
```

也可以在项目目录运行：

```powershell
.\run.ps1
```

## 测试

```powershell
conda activate img-frame
$env:QT_QPA_PLATFORM = "offscreen"
python -m pytest -q
python -m compileall app tests
```

如果系统临时目录没有写入权限，可以先将 `TEMP` 和 `TMP` 指向项目内的临时目录。

## 当前范围

首阶段只提供源码运行方式，暂不生成 PyInstaller 应用目录或 Inno Setup 安装包。安装程序将在功能和真实格式素材验证完成后单独处理。
