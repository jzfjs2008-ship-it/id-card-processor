import logging
import sys
from typing import Optional
from config import config


class AppLogger:
    _instance: Optional['AppLogger'] = None
    _logger: Optional[logging.Logger] = None
    
    def __new__(cls) -> 'AppLogger':
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._setup_logger()
        return cls._instance
    
    def _setup_logger(self) -> None:
        log_config = config._config.get('logging', {})
        
        self._logger = logging.getLogger('IDCardProcessor')
        self._logger.setLevel(getattr(logging, log_config.get('level', 'INFO')))
        
        formatter = logging.Formatter(
            fmt=log_config.get('format', '%(asctime)s - %(name)s - %(levelname)s - %(message)s'),
            datefmt=log_config.get('date_format', '%Y-%m-%d %H:%M:%S')
        )
        
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(formatter)
        self._logger.addHandler(console_handler)
        
        file_path = log_config.get('file_path', '')
        if file_path:
            try:
                file_handler = logging.FileHandler(file_path, encoding='utf-8')
                file_handler.setFormatter(formatter)
                self._logger.addHandler(file_handler)
            except Exception as e:
                self._logger.warning(f"Failed to setup file logger: {e}")
    
    def debug(self, msg: str, *args, **kwargs) -> None:
        if self._logger:
            self._logger.debug(msg, *args, **kwargs)
    
    def info(self, msg: str, *args, **kwargs) -> None:
        if self._logger:
            self._logger.info(msg, *args, **kwargs)
    
    def warning(self, msg: str, *args, **kwargs) -> None:
        if self._logger:
            self._logger.warning(msg, *args, **kwargs)
    
    def error(self, msg: str, *args, **kwargs) -> None:
        if self._logger:
            self._logger.error(msg, *args, **kwargs)
    
    def critical(self, msg: str, *args, **kwargs) -> None:
        if self._logger:
            self._logger.critical(msg, *args, **kwargs)
    
    def exception(self, msg: str, *args, **kwargs) -> None:
        if self._logger:
            self._logger.exception(msg, *args, **kwargs)


logger = AppLogger()
