import os
import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont
import sys
import math

class IDCardProcessor:
    def __init__(self, status_callback=None):
        self.status_callback = status_callback
        
        if getattr(sys, 'frozen', False):
            base_path = sys._MEIPASS
        else:
            base_path = os.path.dirname(os.path.abspath(__file__))
            
        cascade_path = os.path.join(base_path, 'haarcascade_frontalface_default.xml')
        if not os.path.exists(cascade_path):
            cascade_path = os.path.join(cv2.data.haarcascades, 'haarcascade_frontalface_default.xml')

        self.face_cascade = cv2.CascadeClassifier(cascade_path)
        if self.face_cascade.empty():
            raise RuntimeError(f"Could not load face cascade from: {cascade_path}")

    def log(self, message):
        if self.status_callback:
            self.status_callback(message)
        print(message)

    def get_face_score(self, img_bgr):
        """
        Calculates a confidence score for the Portrait side.
        Expects a LANDSCAPE image.
        Returns score.
        """
        h, w = img_bgr.shape[:2]
        if h > w: return 0 # Only score landscape
        
        gray = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)
        faces = self.face_cascade.detectMultiScale(gray, 1.05, 5)
        if len(faces) == 0:
            return 0
        
        # Largest face
        f = sorted(faces, key=lambda x: x[2]*x[3], reverse=True)[0]
        fx, fy, fw, fh = f
        
        # Face is typically on the right half of a landscape ID card
        center_x = fx + fw/2
        if center_x > w * 0.5:
            return fw * fh * 10.0
        else:
            return fw * fh * 0.5 # Weak score if on the left

    def get_emblem_score(self, img_bgr):
        """
        Calculates a confidence score for the Emblem side.
        Expects a LANDSCAPE image.
        Returns score.
        """
        h, w = img_bgr.shape[:2]
        if h > w: return 0 # Only score landscape
        
        hsv = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2HSV)
        # Red/Gold range for the emblem and seal
        m1 = cv2.inRange(hsv, np.array([0, 50, 50]), np.array([15, 255, 255]))
        m2 = cv2.inRange(hsv, np.array([165, 50, 50]), np.array([180, 255, 255]))
        red_mask = cv2.bitwise_or(m1, m2)
        
        # National emblem is in top-left
        tl_roi = red_mask[0:int(h*0.45), 0:int(w*0.45)]
        # Red seal is usually bottom-right
        br_roi = red_mask[int(h*0.5):h, int(w*0.5):w]
        
        tl_density = np.sum(tl_roi) / (tl_roi.size + 1)
        br_density = np.sum(br_roi) / (br_roi.size + 1)
        
        # High confidence if TL is dense (emblem) and BR is also somewhat dense (seal)
        return (tl_density * 2.0 + br_density) * 1000.0

    def order_points(self, pts):
        rect = np.zeros((4, 2), dtype="float32")
        s = pts.sum(axis=1)
        rect[0] = pts[np.argmin(s)] # TL
        rect[2] = pts[np.argmax(s)] # BR
        diff = np.diff(pts, axis=1)
        rect[1] = pts[np.argmin(diff)] # TR
        rect[3] = pts[np.argmax(diff)] # BL
        return rect

    def get_perspective_crop(self, img_bgr):
        """Finds the card and warps it based on detected aspect ratio."""
        oh, ow = img_bgr.shape[:2]
        
        # Improved edge detection
        gray = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)
        blurred = cv2.GaussianBlur(gray, (7, 7), 0)
        edged = cv2.Canny(blurred, 20, 100)
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (5, 5))
        closed = cv2.morphologyEx(edged, cv2.MORPH_CLOSE, kernel)
        
        contours, _ = cv2.findContours(closed.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        contours = sorted(contours, key=cv2.contourArea, reverse=True)[:5]
        
        best_rect = None
        for c in contours:
            peri = cv2.arcLength(c, True)
            approx = cv2.approxPolyDP(c, 0.02 * peri, True)
            if len(approx) == 4 and cv2.contourArea(approx) > (oh * ow * 0.05):
                best_rect = approx.reshape(4, 2)
                break
        
        if best_rect is None and contours:
            r = cv2.minAreaRect(contours[0])
            if (r[1][0] * r[1][1]) > (oh * ow * 0.05):
                box = cv2.boxPoints(r)
                best_rect = np.intp(box)
        
        if best_rect is None:
            return img_bgr # No card found, return as is

        rect_ordered = self.order_points(best_rect.astype("float32"))
        
        # Determine actual side lengths
        w1 = np.linalg.norm(rect_ordered[0] - rect_ordered[1])
        w2 = np.linalg.norm(rect_ordered[3] - rect_ordered[2])
        h1 = np.linalg.norm(rect_ordered[0] - rect_ordered[3])
        h2 = np.linalg.norm(rect_ordered[1] - rect_ordered[2])
        
        avg_w = (w1 + w2) / 2
        avg_h = (h1 + h2) / 2
        
        # Warp to the detected aspect ratio
        dst = np.array([
            [0, 0],
            [avg_w - 1, 0],
            [avg_w - 1, avg_h - 1],
            [0, avg_h - 1]], dtype="float32")
        
        M = cv2.getPerspectiveTransform(rect_ordered, dst)
        warped = cv2.warpPerspective(img_bgr, M, (int(avg_w), int(avg_h)))
        return warped

    def analyze_best_orientation(self, img):
        """Checks all 4 rotations to find best side and orientation."""
        rotations = [
            img, 
            cv2.rotate(img, cv2.ROTATE_90_CLOCKWISE),
            cv2.rotate(img, cv2.ROTATE_180),
            cv2.rotate(img, cv2.ROTATE_90_COUNTERCLOCKWISE)
        ]
        
        best_p_score = -1
        best_p_img = None
        best_e_score = -1
        best_e_img = None
        
        for r_img in rotations:
            # Only score landscape-oriented versions
            rh, rw = r_img.shape[:2]
            if rw < rh: continue
            
            p_score = self.get_face_score(r_img)
            e_score = self.get_emblem_score(r_img)
            
            if p_score > best_p_score:
                best_p_score = p_score
                best_p_img = r_img
            
            if e_score > best_e_score:
                best_e_score = e_score
                best_e_img = r_img
        
        return best_p_score, best_p_img, best_e_score, best_e_img

    def apply_text_watermark(self, canvas, text, opacity=0.30, font_size=48, angle=30, color=(128, 128, 128)):
        """
        Tiles a semi-transparent text watermark diagonally across the canvas.

        :param canvas:    PIL Image (RGB) — base image
        :param text:      Watermark text string
        :param opacity:   0.0–1.0 blending strength
        :param font_size: Font size in pixels
        :param angle:     Rotation angle in degrees (counter-clockwise)
        :param color:     RGB tuple for text color, default mid-grey
        :return: PIL Image with text watermark applied
        """
        if not text or not text.strip():
            return canvas

        cw, ch = canvas.size
        alpha_val = int(round(opacity * 255))

        # ── 1. Render a single watermark stamp on a transparent tile ──────────
        # Try system CJK fonts first, fallback to PIL default
        font = None
        font_candidates = [
            "C:/Windows/Fonts/msyh.ttc",        # 微软雅黑
            "C:/Windows/Fonts/simhei.ttf",       # 黑体
            "C:/Windows/Fonts/simsun.ttc",       # 宋体
            "C:/Windows/Fonts/arial.ttf",        # Arial
        ]
        for fp in font_candidates:
            if os.path.exists(fp):
                try:
                    font = ImageFont.truetype(fp, font_size)
                    break
                except Exception:
                    pass
        if font is None:
            try:
                font = ImageFont.load_default()
            except Exception:
                font = None

        # Measure text size
        tmp = Image.new("RGBA", (1, 1))
        draw_tmp = ImageDraw.Draw(tmp)
        if font:
            bbox = draw_tmp.textbbox((0, 0), text, font=font)
        else:
            bbox = draw_tmp.textbbox((0, 0), text)
        tw = bbox[2] - bbox[0]
        th_text = bbox[3] - bbox[1]

        # Pad around text
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

        # ── 2. Rotate the stamp ───────────────────────────────────────────────
        rotated = stamp.rotate(angle, expand=True)
        rw, rh = rotated.size

        # ── 3. Tile across canvas ─────────────────────────────────────────────
        step_x = int(rw * 1.5)
        step_y = int(rh * 1.5)

        result = canvas.convert("RGBA")
        for row_i, y in enumerate(range(-rh, ch + rh, step_y)):
            offset_x = (row_i % 2) * (step_x // 2)
            for x in range(-rw + offset_x, cw + rw, step_x):
                result.alpha_composite(rotated, dest=(x, y))

        return result.convert("RGB")

    def process_pair(self, path1, path2, out_path, layout='vertical',
                     watermark_text=None, watermark_opacity=0.30,
                     watermark_font_size=48, watermark_angle=30,
                     export_mode="image"):
        self.log("提取并校准图像...")
        raw1 = self.get_perspective_crop(cv2.imread(path1))
        raw2 = self.get_perspective_crop(cv2.imread(path2))
        
        self.log("分析内容与方向...")
        p_score1, p_img1, e_score1, e_img1 = self.analyze_best_orientation(raw1)
        p_score2, p_img2, e_score2, e_img2 = self.analyze_best_orientation(raw2)
        
        # Determine which image is which side
        score_a = p_score1 + e_score2
        score_b = e_score1 + p_score2
        
        if score_a >= score_b:
            p_final, e_final = p_img1, e_img2
        else:
            p_final, e_final = p_img2, e_img1
            
        # Standard ID card dimensions at 300DPI
        # Real ID-1 card: 85.6mm x 54.0mm
        # At 300 DPI: ~1011 x 638 px
        tw, th = 1011, 638
        p_pil = Image.fromarray(cv2.cvtColor(p_final, cv2.COLOR_BGR2RGB)).resize((tw, th), Image.Resampling.LANCZOS)
        e_pil = Image.fromarray(cv2.cvtColor(e_final, cv2.COLOR_BGR2RGB)).resize((tw, th), Image.Resampling.LANCZOS)
        
        # Create card composite (front + back)
        if layout == 'horizontal':
            card = Image.new('RGB', ((tw * 2) + 80, th + 40), (255, 255, 255))
            card.paste(p_pil, (20, 20))
            card.paste(e_pil, (tw + 50, 20))
        else:
            card = Image.new('RGB', (tw + 40, (th * 2) + 80), (255, 255, 255))
            card.paste(p_pil, (20, 20))
            card.paste(e_pil, (20, th + 50))

        # Apply text watermark if specified
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
            # A4 at 300 DPI: 2480 x 3508 px
            a4_w, a4_h = 2480, 3508
            canvas = Image.new('RGB', (a4_w, a4_h), (255, 255, 255))
            cx, cy = (a4_w - card.width) // 2, (a4_h - card.height) // 2
            canvas.paste(card, (cx, cy))
            canvas.save(out_path, quality=95)
        else:
            card.save(out_path, quality=95)

        self.log(f"处理完成！已自动将人像面置于{'上方' if layout=='vertical' else '左侧'}。")
        return out_path
