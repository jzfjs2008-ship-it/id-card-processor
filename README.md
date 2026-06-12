# 身份证照片合成助手

基于 Python + OpenCV 的桌面端身份证照片智能处理工具。自动检测、裁剪、校正身份证正反面照片并合成为一张图片，支持直接保存或 A4 排版打印。

## 功能

- **智能识别** — 自动识别人像面（人脸检测）和国徽面（红色区域密度分析），无需手动区分
- **透视校正** — 自动检测身份证四角，透视变换纠正拍摄角度
- **方向矫正** — 支持 4 个方向自动旋转摆正
- **布局选择** — 支持上下放置 / 左右放置两种合成布局
- **导出模式** — 直接输出图片，或按身份证真实尺寸（85.6mm × 54mm）居中排布在 A4 纸面，方便打印
- **文字水印** — 可自定义水印文字、透明度、字体大小、旋转角度，平铺叠加
- **拖拽导入** — 支持文件拖拽和点击浏览两种方式
- **多语言** — 中文 / English 界面切换
- **输出格式** — 支持 PNG / JPG / TIFF / BMP / WebP

## 系统要求

- Windows 7+（依赖 `windnd` 拖拽功能）
- Python 3.9+

## 安装

### 1. 克隆仓库

```bash
git clone https://github.com/jzfjs2008-ship-it/id-card-processor.git
cd id-card-processor
```

### 2. 创建虚拟环境（推荐）

```bash
python -m venv venv
# Windows
venv\Scripts\activate
# Linux/macOS
# source venv/bin/activate
```

### 3. 安装依赖

```bash
pip install -r requirements.txt
```

### 4. 运行

```bash
python main_gui.py
```

## 依赖清单

| 包 | 用途 |
|---|------|
| `opencv-python` | 图像处理、人脸检测、透视变换 |
| `Pillow` | 图片读写、水印渲染 |
| `numpy` | 数值计算 |
| `windnd` | Windows 文件拖拽支持 |

## 打包为独立 EXE

```bash
pip install pyinstaller
pyinstaller 身份证智能合成助手_v1.0.spec
```

生成的可执行文件在 `dist/` 目录下。

## 使用说明

1. 点击左侧区域（或拖入图片）加载**人像面**照片
2. 点击右侧区域（或拖入图片）加载**国徽面**照片
3. 在 **设置 → 布局** 中选择上下放置或左右放置
4. 在 **设置 → 导出模式** 中选择：
   - **直接输出图片** — 适合电脑存档
   - **A4 排版打印** — 按身份证真实尺寸居中排布在 A4 纸面
5. 可选：**设置 → 水印设置** 添加文字水印
6. 点击 **开始合成** 生成输出图片

## 项目结构

```
├── main_gui.py                       # 主界面入口
├── processor.py                      # 核心处理引擎（检测/校正/合成/水印）
├── create_test_data.py               # 测试数据生成脚本
├── haarcascade_frontalface_default.xml  # Haar Cascade 人脸检测模型
├── logo.png                          # 窗口图标
├── logo.ico                          # EXE 图标
├── requirements.txt                  # Python 依赖
└── 身份证智能合成助手_v1.0.spec       # PyInstaller 打包配置
```

## 许可

MIT License
