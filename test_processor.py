import pytest
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from config import Config, config
from exceptions import (
    IDCardProcessorError,
    ImageLoadError,
    ImageTooLargeError,
    InvalidImageFormatError
)
from processor import IDCardProcessor


class TestConfig:
    def test_config_singleton(self):
        config1 = Config()
        config2 = Config()
        assert config1 is config2
    
    def test_config_get(self):
        assert config.get('image_processing.output_dpi', 300) == 300
        assert config.get('nonexistent.key', 'default') == 'default'
    
    def test_card_dimensions(self):
        width, height = config.get_card_dimensions()
        assert width > 0
        assert height > 0
        assert width > height
    
    def test_a4_dimensions(self):
        width, height = config.get_a4_dimensions()
        assert width > 0
        assert height > 0
        assert height > width


class TestExceptions:
    def test_base_exception(self):
        ex = IDCardProcessorError("Test message", details={'key': 'value'})
        assert ex.message == "Test message"
        assert ex.details == {'key': 'value'}
        assert str(ex) == "Test message"
    
    def test_image_too_large_error(self):
        ex = ImageTooLargeError("Too large", details={'size_mb': 100, 'max_mb': 50})
        assert ex.details['size_mb'] == 100
        assert ex.details['max_mb'] == 50
    
    def test_invalid_format_error(self):
        ex = InvalidImageFormatError("Invalid", details={'extension': '.txt', 'allowed': ['.jpg', '.png']})
        assert ex.details['extension'] == '.txt'


class TestProcessor:
    def test_processor_initialization(self):
        processor = IDCardProcessor()
        assert processor is not None
        assert processor.face_cascade is not None
        assert processor.card_width > 0
        assert processor.card_height > 0
    
    def test_validate_nonexistent_file(self):
        processor = IDCardProcessor()
        with pytest.raises(ImageLoadError):
            processor.validate_image_file("/nonexistent/path.jpg")
    
    def test_validate_invalid_format(self):
        processor = IDCardProcessor()
        test_file = "test.txt"
        try:
            with open(test_file, 'w') as f:
                f.write("test")
            with pytest.raises(InvalidImageFormatError):
                processor.validate_image_file(test_file)
        finally:
            if os.path.exists(test_file):
                os.remove(test_file)
    
    def test_order_points(self):
        processor = IDCardProcessor()
        import numpy as np
        pts = np.array([[10, 10], [100, 10], [100, 50], [10, 50]], dtype="float32")
        ordered = processor.order_points(pts)
        assert ordered.shape == (4, 2)
        assert ordered[0][0] < ordered[2][0]
        assert ordered[0][1] < ordered[2][1]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
