import os
import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont
import sys
import math
from typing import Optional, Tuple, Callable, Any
from config import config
from logger import logger
from exceptions import (
    IDCardProcessorError,
    ImageLoadError,
    ImageTooLargeError,
    InvalidImageFormatError,
    FaceDetectionError,
    PerspectiveCorrectionError,
    WatermarkError,
    ConfigurationError
)


class IDCardProcessor:
    def __init__(self, status_callback: Optional[Callable[[str], None]] = None) -> None:
        self.status_callback = status_callback
        self._load_face_cascade()
        self._load_config()
    
    def _load_face_cascade(self) -> None:
        try:
            if getattr(sys, 'frozen', False):
                base_path = sys._MEIPASS
            else:
                base_path = os.path.dirname(os.path.abspath(__file__))
            
            cascade_path = os.path.join(base_path, 'haarcascade_frontalface_default.xml')
            if not os.path.exists(cascade_path):
                cascade_path = os.path.join(cv2.data.haarcascades, 'haarcascade_frontalface_default.xml')
            
            self.face_cascade = cv2.CascadeClassifier(cascade_path)
            if self.face_cascade.empty():
                raise ConfigurationError(f"Could not load face cascade from: {cascade_path}")
            
            logger.info(f"Face cascade loaded from: {cascade_path}")
        except Exception as e:
            logger.exception("Failed to load face cascade")
            raise ConfigurationError(f"Failed to initialize face detection: {e}")
    
    def _load_config(self) -> None:
        self.card_width, self.card_height = config.get_card_dimensions()
        self.a4_width, self.a4_height = config.get_a4_dimensions()
        
        self.face_scale_factor = config.get('face_detection.scale_factor', 1.05)
        self.face_min_neighbors = config.get('face_detection.min_neighbors', 5)
        
        self.canny_low = config.get('perspective_correction.canny_low', 20)
        self.canny_high = config.get('perspective_correction.canny_high', 100)
        self.gaussian_kernel = config.get('perspective_correction.gaussian_kernel', 7)
        self.min_card_area_ratio = config.get('perspective_correction.min_card_area_ratio', 0.05)
        
        self.jpeg_quality = config.get('image_processing.jpeg_quality', 95)
        self.max_input_size = config.get('image_processing.max_input_size', 4096)
        
        logger.debug(f"Config loaded: card={self.card_width}x{self.card_height}, "
                    f"a4={self.a4_width}x{self.a4_height}")
    
    def log(self, message: str) -> None:
        if self.status_callback:
            self.status_callback(message)
        logger.info(message)
    
    def validate_image_file(self, path: str) -> None:
        if not os.path.exists(path):
            raise ImageLoadError(f"File not found: {path}")
        
        if not os.path.isfile(path):
            raise ImageLoadError(f"Not a file: {path}")
        
        max_size_mb = config.get('security.max_file_size_mb', 50)
        file_size_mb = os.path.getsize(path) / (1024 * 1024)
        if file_size_mb > max_size_mb:
            raise ImageTooLargeError(
                f"File too large: {file_size_mb:.1f}MB > {max_size_mb}MB",
                details={'size_mb': file_size_mb, 'max_mb': max_size_mb}
            )
        
        ext = os.path.splitext(path)[1].lower()
        allowed_formats = config.get('security.allowed_formats', ['.jpg', '.jpeg', '.png'])
        if ext not in allowed_formats:
            raise InvalidImageFormatError(
                f"Invalid format: {ext}. Allowed: {', '.join(allowed_formats)}",
                details={'extension': ext, 'allowed': allowed_formats}
            )
    
    def load_image(self, path: str) -> np.ndarray:
        try:
            self.validate_image_file(path)
            img = cv2.imread(path)
            if img is None:
                raise ImageLoadError(f"Failed to load image: {path}")
            
            h, w = img.shape[:2]
            if max(h, w) > self.max_input_size:
                logger.warning(f"Image too large ({w}x{h}), downsampling...")
                scale = self.max_input_size / max(h, w)
                img = cv2.resize(img, None, fx=scale, fy=scale, interpolation=cv2.INTER_AREA)
                logger.info(f"Downsampled to {img.shape[1]}x{img.shape[0]}")
            
            return img
        except IDCardProcessorError:
            raise
        except Exception as e:
            logger.exception(f"Error loading image: {path}")
            raise ImageLoadError(f"Error loading image: {e}")
    
    def get_face_score(self, img_bgr: np.ndarray) -> float:
        h, w = img_bgr.shape[:2]
        if h > w:
            return 0.0
        
        try:
            gray = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)
            faces = self.face_cascade.detectMultiScale(
                gray, 
                self.face_scale_factor, 
                self.face_min_neighbors
            )
            
            if len(faces) == 0:
                return 0.0
            
            largest_face = sorted(faces, key=lambda x: x[2]*x[3], reverse=True)[0]
            fx, fy, fw, fh = largest_face
            
            center_x = fx + fw/2
            if center_x > w * 0.5:
                return float(fw * fh * 10.0)
            else:
                return float(fw * fh * 0.5)
        except Exception as e:
            logger.warning(f"Face detection error: {e}")
            return 0.0
    
    def get_emblem_score(self, img_bgr: np.ndarray) -> float:
        h, w = img_bgr.shape[:2]
        if h > w:
            return 0.0
        
        try:
            hsv = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2HSV)
            m1 = cv2.inRange(hsv, np.array([0, 50, 50]), np.array([15, 255, 255]))
            m2 = cv2.inRange(hsv, np.array([165, 50, 50]), np.array([180, 255, 255]))
            red_mask = cv2.bitwise_or(m1, m2)
            
            tl_roi = red_mask[0:int(h*0.45), 0:int(w*0.45)]
            br_roi = red_mask[int(h*0.5):h, int(w*0.5):w]
            
            tl_density = np.sum(tl_roi) / (tl_roi.size + 1)
            br_density = np.sum(br_roi) / (br_roi.size + 1)
            
            return float((tl_density * 2.0 + br_density) * 1000.0)
        except Exception as e:
            logger.warning(f"Emblem detection error: {e}")
            return 0.0
    
    def order_points(self, pts: np.ndarray) -> np.ndarray:
        rect = np.zeros((4, 2), dtype="float32")
        s = pts.sum(axis=1)
        rect[0] = pts[np.argmin(s)]
        rect[2] = pts[np.argmax(s)]
        diff = np.diff(pts, axis=1)
        rect[1] = pts[np.argmin(diff)]
        rect[3] = pts[np.argmax(diff)]
        return rect
    
    def get_perspective_crop(self, img_bgr: np.ndarray) -> np.ndarray:
        oh, ow = img_bgr.shape[:2]
        
        try:
            gray = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)
            blurred = cv2.GaussianBlur(gray, (self.gaussian_kernel, self.gaussian_kernel), 0)
            edged = cv2.Canny(blurred, self.canny_low, self.canny_high)
            kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (5, 5))
            closed = cv2.morphologyEx(edged, cv2.MORPH_CLOSE, kernel)
            
            contours, _ = cv2.findContours(closed.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            contours = sorted(contours, key=cv2.contourArea, reverse=True)[:5]
            
            best_rect = None
            for c in contours:
                peri = cv2.arcLength(c, True)
                approx = cv2.approxPolyDP(c, 0.02 * peri, True)
                if len(approx) == 4 and cv2.contourArea(approx) > (oh * ow * self.min_card_area_ratio):
                    best_rect = approx.reshape(4, 2)
                    break
            
            if best_rect is None and contours:
                r = cv2.minAreaRect(contours[0])
                if (r[1][0] * r[1][1]) > (oh * ow * self.min_card_area_ratio):
                    box = cv2.boxPoints(r)
                    best_rect = np.intp(box)
            
            if best_rect is None:
                logger.debug("No card contour found, returning original image")
                return img_bgr
            
            rect_ordered = self.order_points(best_rect.astype("float32"))
            
            w1 = np.linalg.norm(rect_ordered[0] - rect_ordered[1])
            w2 = np.linalg.norm(rect_ordered[3] - rect_ordered[2])
            h1 = np.linalg.norm(rect_ordered[0] - rect_ordered[3])
            h2 = np.linalg.norm(rect_ordered[1] - rect_ordered[2])
            
            avg_w = (w1 + w2) / 2
            avg_h = (h1 + h2) / 2
            
            dst = np.array([
                [0, 0],
                [avg_w - 1, 0],
                [avg_w - 1, avg_h - 1],
                [0, avg_h - 1]], dtype="float32")
            
            M = cv2.getPerspectiveTransform(rect_ordered, dst)
            warped = cv2.warpPerspective(img_bgr, M, (int(avg_w), int(avg_h)))
            
            logger.debug(f"Perspective correction: {ow}x{oh} -> {warped.shape[1]}x{warped.shape[0]}")
            return warped
        except Exception as e:
            logger.warning(f"Perspective correction failed: {e}, returning original")
            return img_bgr
    
    def analyze_best_orientation(self, img: np.ndarray) -> Tuple[float, np.ndarray, float, np.ndarray]:
        rotations = [
            img,
            cv2.rotate(img, cv2.ROTATE_90_CLOCKWISE),
            cv2.rotate(img, cv2.ROTATE_180),
            cv2.rotate(img, cv2.ROTATE_90_COUNTERCLOCKWISE)
        ]
        
        best_p_score = -1.0
        best_p_img: Optional[np.ndarray] = None
        best_e_score = -1.0
        best_e_img: Optional[np.ndarray] = None
        
        for r_img in rotations:
            rh, rw = r_img.shape[:2]
            if rw < rh:
                continue
            
            p_score = self.get_face_score(r_img)
            e_score = self.get_emblem_score(r_img)
            
            if p_score > best_p_score:
                best_p_score = p_score
                best_p_img = r_img
            
            if e_score > best_e_score:
                best_e_score = e_score
                best_e_img = r_img
        
        if best_p_img is None:
            best_p_img = img
        if best_e_img is None:
            best_e_img = img
        
        return best_p_score, best_p_img, best_e_score, best_e_img
    
    def apply_text_watermark(
        self,
        canvas: Image.Image,
        text: str,
        opacity: float = 0.30,
        font_size: int = 48,
        angle: int = 30,
        color: Tuple[int, int, int] = (128, 128, 128)
    ) -> Image.Image:
        if not text or not text.strip():
            return canvas
        
        try:
            cw, ch = canvas.size
            alpha_val = int(round(opacity * 255))
            
            font = None
            font_paths = config.get('watermark.font_paths', [])
            for fp in font_paths:
                if os.path.exists(fp):
                    try:
                        font = ImageFont.truetype(fp, font_size)
                        logger.debug(f"Loaded font: {fp}")
                        break
                    except Exception as e:
                        logger.debug(f"Failed to load font {fp}: {e}")
                        continue
            
            if font is None:
                try:
                    font = ImageFont.load_default()
                except Exception:
                    pass
            
            tmp = Image.new("RGBA", (1, 1))
            draw_tmp = ImageDraw.Draw(tmp)
            if font:
                bbox = draw_tmp.textbbox((0, 0), text, font=font)
            else:
                bbox = draw_tmp.textbbox((0, 0), text)
            tw = bbox[2] - bbox[0]
            th_text = bbox[3] - bbox[1]
            
            pad = max(20, font_size // 2)
            stamp_w = tw + pad * 2
            stamp_h = th_text + pad * 2
            
            stamp = Image.new("RGBA", (stamp_w, stamp_h), (0, 0, 0, 0))
            draw = ImageDraw.Draw(stamp)
            r, g, b = color
            text_color = (r, g, b, alpha_val)
            if font:
                draw.text((pad, pad), text, font=font, fill=text_color)
            else:
                draw.text((pad, pad), text, fill=text_color)
            
            rotated = stamp.rotate(angle, expand=True)
            rw, rh = rotated.size
            
            step_x = int(rw * 1.5)
            step_y = int(rh * 1.5)
            
            result = canvas.convert("RGBA")
            for row_i, y in enumerate(range(-rh, ch + rh, step_y)):
                offset_x = (row_i % 2) * (step_x // 2)
                for x in range(-rw + offset_x, cw + rw, step_x):
                    result.alpha_composite(rotated, dest=(x, y))
            
            return result.convert("RGB")
        except Exception as e:
            logger.exception("Watermark application failed")
            raise WatermarkError(f"Failed to apply watermark: {e}")
    
    def process_pair(
        self,
        path1: str,
        path2: str,
        out_path: str,
        layout: str = 'vertical',
        watermark_text: Optional[str] = None,
        watermark_opacity: float = 0.30,
        watermark_font_size: int = 48,
        watermark_angle: int = 30,
        export_mode: str = "image"
    ) -> str:
        try:
            self.log("加载并验证图像...")
            raw1 = self.load_image(path1)
            raw2 = self.load_image(path2)
            
            self.log("提取并校准图像...")
            cropped1 = self.get_perspective_crop(raw1)
            cropped2 = self.get_perspective_crop(raw2)
            
            self.log("分析内容与方向...")
            p_score1, p_img1, e_score1, e_img1 = self.analyze_best_orientation(cropped1)
            p_score2, p_img2, e_score2, e_img2 = self.analyze_best_orientation(cropped2)
            
            score_a = p_score1 + e_score2
            score_b = e_score1 + p_score2
            
            if score_a >= score_b:
                p_final, e_final = p_img1, e_img2
                logger.debug(f"Image1=portrait (score={p_score1}), Image2=emblem (score={e_score2})")
            else:
                p_final, e_final = p_img2, e_img1
                logger.debug(f"Image2=portrait (score={p_score2}), Image1=emblem (score={e_score1})")
            
            self.log("合成图片...")
            p_pil = Image.fromarray(cv2.cvtColor(p_final, cv2.COLOR_BGR2RGB)).resize(
                (self.card_width, self.card_height), Image.Resampling.LANCZOS
            )
            e_pil = Image.fromarray(cv2.cvtColor(e_final, cv2.COLOR_BGR2RGB)).resize(
                (self.card_width, self.card_height), Image.Resampling.LANCZOS
            )
            
            if layout == 'horizontal':
                card = Image.new('RGB', ((self.card_width * 2) + 80, self.card_height + 40), (255, 255, 255))
                card.paste(p_pil, (20, 20))
                card.paste(e_pil, (self.card_width + 50, 20))
            else:
                card = Image.new('RGB', (self.card_width + 40, (self.card_height * 2) + 80), (255, 255, 255))
                card.paste(p_pil, (20, 20))
                card.paste(e_pil, (20, self.card_height + 50))
            
            if watermark_text and watermark_text.strip():
                self.log("正在叠加文字水印...")
                card = self.apply_text_watermark(
                    card,
                    text=watermark_text,
                    opacity=watermark_opacity,
                    font_size=watermark_font_size,
                    angle=watermark_angle,
                )
            
            if export_mode == "a4":
                self.log("生成A4排版...")
                canvas = Image.new('RGB', (self.a4_width, self.a4_height), (255, 255, 255))
                cx = (self.a4_width - card.width) // 2
                cy = (self.a4_height - card.height) // 2
                canvas.paste(card, (cx, cy))
                canvas.save(out_path, quality=self.jpeg_quality)
            else:
                card.save(out_path, quality=self.jpeg_quality)
            
            layout_name = '上方' if layout == 'vertical' else '左侧'
            self.log(f"处理完成！已自动将人像面置于{layout_name}。")
            logger.info(f"Output saved to: {out_path}")
            return out_path
        except IDCardProcessorError:
            raise
        except Exception as e:
            logger.exception("Processing failed")
            raise IDCardProcessorError(f"Processing failed: {e}")
