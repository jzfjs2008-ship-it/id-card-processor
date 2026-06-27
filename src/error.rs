use std::fmt;

#[derive(Debug)]
pub enum AppError {
    ImageLoad(String),
    ImageTooLarge { size_mb: f64, max_mb: f64 },
    InvalidFormat { ext: String, allowed: Vec<String> },
    FaceDetection(String),
    PerspectiveCorrection(String),
    Watermark(String),
    Configuration(String),
    Io(String),
}

impl fmt::Display for AppError {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            AppError::ImageLoad(msg) => write!(f, "图片加载失败: {msg}"),
            AppError::ImageTooLarge { size_mb, max_mb } => {
                write!(f, "图片文件过大: {size_mb:.1}MB > {max_mb}MB")
            }
            AppError::InvalidFormat { ext, allowed } => {
                write!(f, "不支持的格式: {ext}, 允许: {}", allowed.join(", "))
            }
            AppError::FaceDetection(msg) => write!(f, "人脸检测失败: {msg}"),
            AppError::PerspectiveCorrection(msg) => write!(f, "透视校正失败: {msg}"),
            AppError::Watermark(msg) => write!(f, "水印处理失败: {msg}"),
            AppError::Configuration(msg) => write!(f, "配置错误: {msg}"),
            AppError::Io(msg) => write!(f, "IO错误: {msg}"),
        }
    }
}

impl From<std::io::Error> for AppError {
    fn from(e: std::io::Error) -> Self {
        AppError::Io(e.to_string())
    }
}

impl From<image::ImageError> for AppError {
    fn from(e: image::ImageError) -> Self {
        AppError::ImageLoad(e.to_string())
    }
}
