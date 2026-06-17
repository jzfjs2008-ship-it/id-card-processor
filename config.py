import os
import yaml
from typing import Any, Dict, Optional
from pathlib import Path


class Config:
    _instance: Optional['Config'] = None
    _config: Dict[str, Any] = {}
    
    def __new__(cls) -> 'Config':
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._load_config()
        return cls._instance
    
    def _load_config(self) -> None:
        config_path = self._find_config_file()
        if config_path and os.path.exists(config_path):
            with open(config_path, 'r', encoding='utf-8') as f:
                self._config = yaml.safe_load(f) or {}
        else:
            self._config = self._get_default_config()
    
    def _find_config_file(self) -> Optional[str]:
        candidates = [
            'config.yaml',
            'config.yml',
            os.path.join(os.path.dirname(__file__), 'config.yaml'),
            os.path.join(os.path.dirname(__file__), 'config.yml'),
        ]
        for path in candidates:
            if os.path.exists(path):
                return path
        return None
    
    def _get_default_config(self) -> Dict[str, Any]:
        return {
            'image_processing': {
                'card_width_mm': 85.6,
                'card_height_mm': 54.0,
                'output_dpi': 300,
                'max_input_size': 4096,
                'jpeg_quality': 95,
            },
            'face_detection': {
                'scale_factor': 1.05,
                'min_neighbors': 5,
                'min_face_ratio': 0.1,
            },
            'perspective_correction': {
                'canny_low': 20,
                'canny_high': 100,
                'gaussian_kernel': 7,
                'min_card_area_ratio': 0.05,
            },
            'watermark': {
                'font_paths': [
                    "C:/Windows/Fonts/msyh.ttc",
                    "C:/Windows/Fonts/simhei.ttf",
                    "C:/Windows/Fonts/simsun.ttc",
                    "C:/Windows/Fonts/arial.ttf",
                ],
                'default_opacity': 0.30,
                'default_font_size': 48,
                'default_angle': 30,
                'default_color': [128, 128, 128],
            },
            'a4_layout': {
                'width_mm': 210,
                'height_mm': 297,
                'dpi': 300,
            },
            'performance': {
                'enable_multiprocessing': False,
                'max_workers': 0,
                'cache_face_cascade': True,
            },
            'logging': {
                'level': 'INFO',
                'file_path': '',
                'format': '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                'date_format': '%Y-%m-%d %H:%M:%S',
            },
            'security': {
                'max_file_size_mb': 50,
                'allowed_formats': ['.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.webp'],
                'validate_file_header': True,
            },
        }
    
    def get(self, key: str, default: Any = None) -> Any:
        keys = key.split('.')
        value = self._config
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default
        return value
    
    def get_card_dimensions(self) -> tuple[int, int]:
        dpi = self.get('image_processing.output_dpi', 300)
        width_mm = self.get('image_processing.card_width_mm', 85.6)
        height_mm = self.get('image_processing.card_height_mm', 54.0)
        width_px = int(width_mm * dpi / 25.4)
        height_px = int(height_mm * dpi / 25.4)
        return width_px, height_px
    
    def get_a4_dimensions(self) -> tuple[int, int]:
        dpi = self.get('a4_layout.dpi', 300)
        width_mm = self.get('a4_layout.width_mm', 210)
        height_mm = self.get('a4_layout.height_mm', 297)
        width_px = int(width_mm * dpi / 25.4)
        height_px = int(height_mm * dpi / 25.4)
        return width_px, height_px


config = Config()
