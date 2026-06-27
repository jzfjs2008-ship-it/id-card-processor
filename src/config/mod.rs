use serde::Deserialize;
use std::fs;
use std::path::Path;

#[derive(Debug, Deserialize, Clone)]
pub struct AppConfig {
    pub image_processing: ImageProcessingConfig,
    pub face_detection: FaceDetectionConfig,
    pub perspective_correction: PerspectiveConfig,
    pub watermark: WatermarkConfig,
    pub a4_layout: A4Config,
    pub security: SecurityConfig,
}

#[derive(Debug, Deserialize, Clone)]
pub struct ImageProcessingConfig {
    pub card_width_mm: f64,
    pub card_height_mm: f64,
    pub output_dpi: u32,
    pub max_input_size: u32,
    pub jpeg_quality: u8,
}

#[derive(Debug, Deserialize, Clone)]
pub struct FaceDetectionConfig {
    pub scale_factor: f64,
    pub min_neighbors: i32,
    pub min_face_ratio: f64,
}

#[derive(Debug, Deserialize, Clone)]
pub struct PerspectiveConfig {
    pub canny_low: u8,
    pub canny_high: u8,
    pub gaussian_kernel: u32,
    pub min_card_area_ratio: f64,
}

#[derive(Debug, Deserialize, Clone)]
pub struct WatermarkConfig {
    pub font_paths: Vec<String>,
    pub default_opacity: f64,
    pub default_font_size: u32,
    pub default_angle: i32,
    pub default_color: Vec<u8>,
}

#[derive(Debug, Deserialize, Clone)]
pub struct A4Config {
    pub width_mm: f64,
    pub height_mm: f64,
    pub dpi: u32,
}

#[derive(Debug, Deserialize, Clone)]
pub struct SecurityConfig {
    pub max_file_size_mb: f64,
    pub allowed_formats: Vec<String>,
}

impl AppConfig {
    pub fn card_dimensions_px(&self) -> (u32, u32) {
        let w = (self.image_processing.card_width_mm * self.image_processing.output_dpi as f64
            / 25.4) as u32;
        let h = (self.image_processing.card_height_mm * self.image_processing.output_dpi as f64
            / 25.4) as u32;
        (w, h)
    }

    pub fn a4_dimensions_px(&self) -> (u32, u32) {
        let w = (self.a4_layout.width_mm * self.a4_layout.dpi as f64 / 25.4) as u32;
        let h = (self.a4_layout.height_mm * self.a4_layout.dpi as f64 / 25.4) as u32;
        (w, h)
    }

    pub fn load(path: &Path) -> Result<Self, Box<dyn std::error::Error>> {
        let content = fs::read_to_string(path)?;
        let config: AppConfig = serde_yaml::from_str(&content)?;
        Ok(config)
    }

    pub fn load_or_default(path: &Path) -> Self {
        Self::load(path).unwrap_or_else(|_| Self::default_config())
    }

    fn default_config() -> Self {
        AppConfig {
            image_processing: ImageProcessingConfig {
                card_width_mm: 85.6,
                card_height_mm: 54.0,
                output_dpi: 300,
                max_input_size: 4096,
                jpeg_quality: 95,
            },
            face_detection: FaceDetectionConfig {
                scale_factor: 1.05,
                min_neighbors: 5,
                min_face_ratio: 0.1,
            },
            perspective_correction: PerspectiveConfig {
                canny_low: 20,
                canny_high: 100,
                gaussian_kernel: 7,
                min_card_area_ratio: 0.05,
            },
            watermark: WatermarkConfig {
                font_paths: vec![
                    "C:/Windows/Fonts/msyh.ttc".into(),
                    "C:/Windows/Fonts/simhei.ttf".into(),
                    "C:/Windows/Fonts/simsun.ttc".into(),
                    "C:/Windows/Fonts/arial.ttf".into(),
                ],
                default_opacity: 0.30,
                default_font_size: 48,
                default_angle: 30,
                default_color: vec![128, 128, 128],
            },
            a4_layout: A4Config {
                width_mm: 210.0,
                height_mm: 297.0,
                dpi: 300,
            },
            security: SecurityConfig {
                max_file_size_mb: 50.0,
                allowed_formats: vec![
                    ".jpg".into(),
                    ".jpeg".into(),
                    ".png".into(),
                    ".bmp".into(),
                    ".tiff".into(),
                    ".webp".into(),
                ],
            },
        }
    }
}
