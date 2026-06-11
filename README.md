# 身份证照片合成助手

基于 Python + OpenCV 的桌面端身份证照片智能处理工具，自动检测、裁剪、校正身份证正反面照片并合成为一张图片。

## 功能

- **智能检测** — 自动识别人像面和国徽面，无需手动区分
- **透视校正** — 自动检测身份证四角，透视变换纠正拍摄角度
- **方向矫正** — 支持 4 个方向自动旋转摆正
- **人像裁剪** — 基于 Haar Cascade 人脸检测精确定位
- **国徽识别** — 基于 HSV 红色区域密度的国徽面判定
- **布局选择** — 支持上下放置 / 左右放置两种合成布局
- **文字水印** — 可自定义水印文字、透明度、位置
- **拖拽导入** — 支持文件拖拽和点击浏览两种方式
- **多语言** — 中文 / English 界面切换
- **输出格式** — 支持 JPG / PNG 格式

## 技术栈

| 组件 | 技术 |
|------|------|
| GUI | tkinter + windnd |
| 图像处理 | OpenCV (cv2), Pillow |
| 人脸检测 | Haar Cascade (OpenCV) |
| 打包 | PyInstaller |

## 快速开始

```bash
pip install -r requirements.txt
python main_gui.py
```

### 打包 EXE

```bash
pyinstaller 身份证智能合成助手_v1.0.spec
```

## 项目结构

```
├── main_gui.py              # 主界面入口（641行）
├── processor.py             # 核心处理引擎（304行）
├── create_test_data.py      # 测试数据生成
├── haarcascade_frontalface_default.xml  # 人脸检测模型
├── logo.png / logo.ico      # 应用图标
├── test_watermark.png       # 水印测试图
└── 身份证智能合成助手_v1.0.spec  # PyInstaller 打包配置
```

## 许可

MIT License
