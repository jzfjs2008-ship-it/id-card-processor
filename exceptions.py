from typing import Optional, Any


class IDCardProcessorError(Exception):
    def __init__(self, message: str, details: Optional[Any] = None):
        super().__init__(message)
        self.message = message
        self.details = details


class ImageLoadError(IDCardProcessorError):
    pass


class ImageTooLargeError(IDCardProcessorError):
    pass


class InvalidImageFormatError(IDCardProcessorError):
    pass


class FaceDetectionError(IDCardProcessorError):
    pass


class PerspectiveCorrectionError(IDCardProcessorError):
    pass


class WatermarkError(IDCardProcessorError):
    pass


class ConfigurationError(IDCardProcessorError):
    pass


class SecurityError(IDCardProcessorError):
    pass


class ValidationError(IDCardProcessorError):
    pass
