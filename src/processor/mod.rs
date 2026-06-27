use crate::config::AppConfig;
use crate::error::AppError;
use image::{DynamicImage, Rgb, RgbImage};
use std::path::Path;

pub struct Processor {
    config: AppConfig,
}

impl Processor {
    pub fn new(config: AppConfig) -> Self {
        Processor { config }
    }

    pub fn validate_image_file(&self, path: &Path) -> Result<(), AppError> {
        if !path.exists() {
            return Err(AppError::ImageLoad(format!(
                "文件不存在: {}",
                path.display()
            )));
        }
        if !path.is_file() {
            return Err(AppError::ImageLoad(format!(
                "不是文件: {}",
                path.display()
            )));
        }

        let file_size_mb = path.metadata().map(|m| m.len() as f64 / (1024.0 * 1024.0)).unwrap_or(0.0);
        if file_size_mb > self.config.security.max_file_size_mb {
            return Err(AppError::ImageTooLarge {
                size_mb: file_size_mb,
                max_mb: self.config.security.max_file_size_mb,
            });
        }

        let ext = path
            .extension()
            .and_then(|e| e.to_str())
            .map(|e| format!(".{e}").to_lowercase())
            .unwrap_or_default();
        if !self.config.security.allowed_formats.contains(&ext) {
            return Err(AppError::InvalidFormat {
                ext,
                allowed: self.config.security.allowed_formats.clone(),
            });
        }
        Ok(())
    }

    pub fn load_image(&self, path: &Path) -> Result<RgbImage, AppError> {
        self.validate_image_file(path)?;
        let img = image::open(path)?;
        let mut rgb = img.to_rgb8();
        let (w, h) = rgb.dimensions();
        let max_size = self.config.image_processing.max_input_size;
        if w > max_size || h > max_size {
            let scale = max_size as f64 / w.max(h) as f64;
            let nw = (w as f64 * scale) as u32;
            let nh = (h as f64 * scale) as u32;
            rgb = image::imageops::resize(&rgb, nw, nh, image::imageops::FilterType::Lanczos3);
            log::info!("Downsampled {w}x{h} -> {nw}x{nh}");
        }
        Ok(rgb)
    }

    pub fn get_face_score(&self, img: &RgbImage) -> f64 {
        let (w, h) = img.dimensions();
        if h > w {
            return 0.0;
        }
        let gray = Self::to_grayscale(img);
        let faces = self.detect_faces_haar(&gray, w, h);
        if faces.is_empty() {
            return 0.0;
        }
        let best = faces.iter().max_by_key(|f| f.2 * f.3).unwrap();
        let (fx, fy, fw, fh) = *best;
        let center_x = fx as f64 + fw as f64 / 2.0;
        if center_x > w as f64 * 0.5 {
            fw as f64 * fh as f64 * 10.0
        } else {
            fw as f64 * fh as f64 * 0.5
        }
    }

    pub fn get_emblem_score(&self, img: &RgbImage) -> f64 {
        let (w, h) = img.dimensions();
        if h > w {
            return 0.0;
        }
        let mut tl_count: f64 = 0.0;
        let mut br_count: f64 = 0.0;
        let tl_rows = (h as f64 * 0.45) as u32;
        let tl_cols = (w as f64 * 0.45) as u32;
        let br_row_start = (h as f64 * 0.5) as u32;
        let br_col_start = (w as f64 * 0.5) as u32;

        for y in 0..h {
            for x in 0..w {
                let pixel = img.get_pixel(x, y);
                let (r, g, b) = (pixel[0], pixel[1], pixel[2]);
                let is_red = (r > 80 && g < 80 && b < 80)
                    || (r > 150 && g < 60 && b < 60)
                    || (r > 100 && (g as f64) < (r as f64) * 0.5 && (b as f64) < (r as f64) * 0.5);
                if is_red {
                    if y < tl_rows && x < tl_cols {
                        tl_count += 1.0;
                    } else if y >= br_row_start && x >= br_col_start {
                        br_count += 1.0;
                    }
                }
            }
        }

        let tl_area = (tl_rows * tl_cols).max(1) as f64;
        let br_area = ((h - br_row_start) * (w - br_col_start)).max(1) as f64;
        let tl_density = tl_count / tl_area;
        let br_density = br_count / br_area;
        (tl_density * 2.0 + br_density) * 1000.0
    }

    fn to_grayscale(img: &RgbImage) -> Vec<u8> {
        img.pixels().map(|p| {
            let r = p[0] as f64 * 0.299;
            let g = p[1] as f64 * 0.587;
            let b = p[2] as f64 * 0.114;
            (r + g + b) as u8
        }).collect()
    }

    fn detect_faces_haar(&self, gray: &[u8], width: u32, height: u32) -> Vec<(u32, u32, u32, u32)> {
        let min_face_w = (width as f64 * self.config.face_detection.min_face_ratio) as u32;
        let min_face_h = (height as f64 * self.config.face_detection.min_face_ratio) as u32;
        let skin_ratio = self.detect_skin_region(gray, width, height);
        if skin_ratio > 0.02 {
            let skin_center_x = self.skin_center_x(gray, width, height);
            let face_w = min_face_w.max(width / 5);
            let face_h = min_face_h.max(height / 5);
            let fx = if skin_center_x > width as f64 * 0.5 {
                (width - face_w) / 2 + width / 4
            } else {
                (width - face_w) / 2
            };
            let fy = (height as f64 * 0.1) as u32;
            vec![(fx.min(width - face_w), fy.min(height - face_h), face_w, face_h)]
        } else {
            vec![]
        }
    }

    fn detect_skin_region(&self, gray: &[u8], width: u32, height: u32) -> f64 {
        let mut skin_count = 0u32;
        let total = (width * height) as f64;
        for y in 0..height {
            for x in 0..width {
                let v = gray[(y * width + x) as usize];
                let is_skin = v > 80 && v < 230;
                if is_skin && x < width * 3 / 4 && x > width / 8 && y < height * 3 / 4 {
                    skin_count += 1;
                }
            }
        }
        skin_count as f64 / total
    }

    fn skin_center_x(&self, gray: &[u8], width: u32, height: u32) -> f64 {
        let mut sum_x = 0u64;
        let mut count = 0u64;
        for y in 0..height {
            for x in 0..width {
                let v = gray[(y * width + x) as usize];
                if v > 100 && v < 220 && x > width / 6 && x < width * 5 / 6 {
                    sum_x += x as u64;
                    count += 1;
                }
            }
        }
        if count == 0 {
            width as f64 / 2.0
        } else {
            sum_x as f64 / count as f64
        }
    }

    pub fn get_perspective_crop(&self, img: &RgbImage) -> RgbImage {
        let (oh, ow) = img.dimensions();
        let gray = Self::to_grayscale(img);
        let edges = self.canny_edge(&gray, ow, oh);
        let kernel_size = self.config.perspective_correction.gaussian_kernel;
        let blurred = Self::blur_u8(&edges, ow, oh, kernel_size);
        let closed = Self::morph_close(&blurred, ow, oh, 5);

        let contours = Self::find_contours(&closed, ow, oh);
        let best = contours
            .iter()
            .filter(|c| c.area() > (oh * ow) as f64 * self.config.perspective_correction.min_card_area_ratio)
            .filter_map(|c| c.approx_poly(0.02))
            .filter(|poly| poly.len() == 4)
            .next();

        match best {
            Some(pts) => {
                let rect = Self::order_points(&pts);
                let warped = self.warp_perspective(img, &rect);
                log::debug!("Perspective correction: {ow}x{oh} -> {}x{}", warped.width(), warped.height());
                warped
            }
            None => {
                log::debug!("No card contour found, returning original");
                img.clone()
            }
        }
    }

    fn canny_edge(&self, gray: &[u8], w: u32, h: u32) -> Vec<u8> {
        let gx = Self::sobel_x(gray, w, h);
        let gy = Self::sobel_y(gray, w, h);
        let mut edges = vec![0u8; (w * h) as usize];
        let low = self.config.perspective_correction.canny_low;
        let high = self.config.perspective_correction.canny_high;
        for i in 0..(w * h) as usize {
            let mag = ((gx[i] as f64).hypot(gy[i] as f64)) as u8;
            edges[i] = if mag >= high {
                255
            } else if mag >= low {
                128
            } else {
                0
            };
        }
        edges
    }

    fn sobel_x(gray: &[u8], w: u32, h: u32) -> Vec<i16> {
        let mut out = vec![0i16; (w * h) as usize];
        for y in 1..h - 1 {
            for x in 1..w - 1 {
                let idx = |xx: u32, yy: u32| (yy * w + xx) as usize;
                let val = -1 * gray[idx(x - 1, y - 1)] as i16
                    + 1 * gray[idx(x + 1, y - 1)] as i16
                    + -2 * gray[idx(x - 1, y)] as i16
                    + 2 * gray[idx(x + 1, y)] as i16
                    + -1 * gray[idx(x - 1, y + 1)] as i16
                    + 1 * gray[idx(x + 1, y + 1)] as i16;
                out[(y * w + x) as usize] = val;
            }
        }
        out
    }

    fn sobel_y(gray: &[u8], w: u32, h: u32) -> Vec<i16> {
        let mut out = vec![0i16; (w * h) as usize];
        for y in 1..h - 1 {
            for x in 1..w - 1 {
                let idx = |xx: u32, yy: u32| (yy * w + xx) as usize;
                let val = -1 * gray[idx(x - 1, y - 1)] as i16
                    + -2 * gray[idx(x, y - 1)] as i16
                    + -1 * gray[idx(x + 1, y - 1)] as i16
                    + 1 * gray[idx(x - 1, y + 1)] as i16
                    + 2 * gray[idx(x, y + 1)] as i16
                    + 1 * gray[idx(x + 1, y + 1)] as i16;
                out[(y * w + x) as usize] = val;
            }
        }
        out
    }

    fn blur_u8(data: &[u8], w: u32, h: u32, ksize: u32) -> Vec<u8> {
        let half = (ksize / 2) as i32;
        let mut out = vec![0u8; (w * h) as usize];
        for y in 0..h {
            for x in 0..w {
                let mut sum: u32 = 0;
                let mut count: u32 = 0;
                for dy in -half..=half {
                    for dx in -half..=half {
                        let ny = (y as i32 + dy).clamp(0, (h - 1) as i32) as u32;
                        let nx = (x as i32 + dx).clamp(0, (w - 1) as i32) as u32;
                        sum += data[(ny * w + nx) as usize] as u32;
                        count += 1;
                    }
                }
                out[(y * w + x) as usize] = (sum / count) as u8;
            }
        }
        out
    }

    fn morph_close(data: &[u8], w: u32, h: u32, ksize: u32) -> Vec<u8> {
        let dilated = Self::dilate(data, w, h, ksize);
        Self::erode(&dilated, w, h, ksize)
    }

    fn dilate(data: &[u8], w: u32, h: u32, ksize: u32) -> Vec<u8> {
        let half = (ksize / 2) as i32;
        let mut out = vec![0u8; (w * h) as usize];
        for y in 0..h {
            for x in 0..w {
                let mut max_val = 0u8;
                for dy in -half..=half {
                    for dx in -half..=half {
                        let ny = (y as i32 + dy).clamp(0, (h - 1) as i32) as u32;
                        let nx = (x as i32 + dx).clamp(0, (w - 1) as i32) as u32;
                        max_val = max_val.max(data[(ny * w + nx) as usize]);
                    }
                }
                out[(y * w + x) as usize] = max_val;
            }
        }
        out
    }

    fn erode(data: &[u8], w: u32, h: u32, ksize: u32) -> Vec<u8> {
        let half = (ksize / 2) as i32;
        let mut out = vec![0u8; (w * h) as usize];
        for y in 0..h {
            for x in 0..w {
                let mut min_val = 255u8;
                for dy in -half..=half {
                    for dx in -half..=half {
                        let ny = (y as i32 + dy).clamp(0, (h - 1) as i32) as u32;
                        let nx = (x as i32 + dx).clamp(0, (w - 1) as i32) as u32;
                        min_val = min_val.min(data[(ny * w + nx) as usize]);
                    }
                }
                out[(y * w + x) as usize] = min_val;
            }
        }
        out
    }

    fn find_contours(data: &[u8], w: u32, h: u32) -> Vec<Contour> {
        let mut visited = vec![false; (w * h) as usize];
        let mut contours = Vec::new();

        for y in 1..h - 1 {
            for x in 1..w - 1 {
                let idx = (y * w + x) as usize;
                if data[idx] > 0 && !visited[idx] {
                    let border = data[((y - 1) * w + x) as usize] == 0;
                    if border {
                        if let Some(contour) = Self::trace_contour(data, w, h, x, y, &mut visited) {
                            contours.push(contour);
                        }
                    } else {
                        visited[idx] = true;
                    }
                }
            }
        }
        contours.sort_by(|a, b| b.area().partial_cmp(&a.area()).unwrap_or(std::cmp::Ordering::Equal));
        contours.truncate(5);
        contours
    }

    fn trace_contour(
        data: &[u8], w: u32, h: u32, sx: u32, sy: u32, visited: &mut [bool],
    ) -> Option<Contour> {
        let mut points = Vec::new();
        let mut x = sx;
        let mut y = sy;
        let dirs: [(i32, i32); 8] = [
            (0, -1), (1, -1), (1, 0), (1, 1),
            (0, 1), (-1, 1), (-1, 0), (-1, -1),
        ];
        let max_steps = 10000;

        for _ in 0..max_steps {
            let idx = (y * w + x) as usize;
            visited[idx] = true;
            points.push((x as f64, y as f64));

            let mut found = false;
            for &(dx, dy) in &dirs {
                let nx = (x as i32 + dx) as u32;
                let ny = (y as i32 + dy) as u32;
                if nx < w && ny < h {
                    let nidx = (ny * w + nx) as usize;
                    if data[nidx] > 0 && !visited[nidx] {
                        x = nx;
                        y = ny;
                        found = true;
                        break;
                    }
                }
            }
            if !found {
                break;
            }
            if x == sx && y == sy {
                break;
            }
        }

        if points.len() >= 4 {
            Some(Contour { points })
        } else {
            None
        }
    }

    fn order_points(pts: &[(f64, f64); 4]) -> [(f64, f64); 4] {
        let mut rect = [(0.0, 0.0); 4];
        let sums: Vec<f64> = pts.iter().map(|(x, y)| x + y).collect();
        let diffs: Vec<f64> = pts.iter().map(|(x, y)| y - x).collect();

        let min_sum_i = sums.iter().enumerate().min_by(|a, b| a.1.partial_cmp(b.1).unwrap()).unwrap().0;
        let max_sum_i = sums.iter().enumerate().max_by(|a, b| a.1.partial_cmp(b.1).unwrap()).unwrap().0;
        let min_diff_i = diffs.iter().enumerate().min_by(|a, b| a.1.partial_cmp(b.1).unwrap()).unwrap().0;
        let max_diff_i = diffs.iter().enumerate().max_by(|a, b| a.1.partial_cmp(b.1).unwrap()).unwrap().0;

        rect[0] = pts[min_sum_i];
        rect[1] = pts[min_diff_i];
        rect[2] = pts[max_sum_i];
        rect[3] = pts[max_diff_i];
        rect
    }

    fn warp_perspective(&self, img: &RgbImage, src_pts: &[(f64, f64); 4]) -> RgbImage {
        let w1 = (src_pts[1].0 - src_pts[0].0).hypot(src_pts[1].1 - src_pts[0].1);
        let w2 = (src_pts[2].0 - src_pts[3].0).hypot(src_pts[2].1 - src_pts[3].1);
        let h1 = (src_pts[3].0 - src_pts[0].0).hypot(src_pts[3].1 - src_pts[0].1);
        let h2 = (src_pts[2].0 - src_pts[1].0).hypot(src_pts[2].1 - src_pts[1].1);
        let out_w = ((w1 + w2) / 2.0) as u32;
        let out_h = ((h1 + h2) / 2.0) as u32;

        if out_w == 0 || out_h == 0 {
            return img.clone();
        }

        let dst_pts: [(f64, f64); 4] = [
            (0.0, 0.0),
            (out_w as f64 - 1.0, 0.0),
            (out_w as f64 - 1.0, out_h as f64 - 1.0),
            (0.0, out_h as f64 - 1.0),
        ];

        let m = Self::perspective_matrix(src_pts, &dst_pts);
        let m_inv = match m.inverse() {
            Some(inv) => inv,
            None => return img.clone(),
        };

        let mut out = RgbImage::new(out_w, out_h);
        for y in 0..out_h {
            for x in 0..out_w {
                let sx = m_inv.m[0][0] * x as f64 + m_inv.m[0][1] * y as f64 + m_inv.m[0][2];
                let sy = m_inv.m[1][0] * x as f64 + m_inv.m[1][1] * y as f64 + m_inv.m[1][2];
                let sw = m_inv.m[2][0] * x as f64 + m_inv.m[2][1] * y as f64 + m_inv.m[2][2];
                if sw.abs() < 1e-10 {
                    continue;
                }
                let sx = sx / sw;
                let sy = sy / sw;

                let px = sx.round() as i32;
                let py = sy.round() as i32;
                if px >= 0 && px < img.width() as i32 && py >= 0 && py < img.height() as i32 {
                    out.put_pixel(x, y, *img.get_pixel(px as u32, py as u32));
                }
            }
        }
        out
    }

    fn perspective_matrix(src: &[(f64, f64); 4], dst: &[(f64, f64); 4]) -> PerspMatrix {
        let (sx0, sy0) = (src[0].0, src[0].1);
        let (sx1, sy1) = (src[1].0, src[1].1);
        let (sx2, sy2) = (src[2].0, src[2].1);
        let (sx3, sy3) = (src[3].0, src[3].1);
        let (dx0, dy0) = (dst[0].0, dst[0].1);
        let (dx1, dy1) = (dst[1].0, dst[1].1);
        let (dx2, dy2) = (dst[2].0, dst[2].1);
        let (dx3, dy3) = (dst[3].0, dst[3].1);

        let a: [[f64; 8]; 8] = [
            [sx0, sy0, 1.0, 0.0, 0.0, 0.0, -dx0 * sx0, -dx0 * sy0],
            [0.0, 0.0, 0.0, sx0, sy0, 1.0, -dy0 * sx0, -dy0 * sy0],
            [sx1, sy1, 1.0, 0.0, 0.0, 0.0, -dx1 * sx1, -dx1 * sy1],
            [0.0, 0.0, 0.0, sx1, sy1, 1.0, -dy1 * sx1, -dy1 * sy1],
            [sx2, sy2, 1.0, 0.0, 0.0, 0.0, -dx2 * sx2, -dx2 * sy2],
            [0.0, 0.0, 0.0, sx2, sy2, 1.0, -dy2 * sx2, -dy2 * sy2],
            [sx3, sy3, 1.0, 0.0, 0.0, 0.0, -dx3 * sx3, -dx3 * sy3],
            [0.0, 0.0, 0.0, sx3, sy3, 1.0, -dy3 * sx3, -dy3 * sy3],
        ];

        let b = [
            dst[0].0, dst[0].1,
            dst[1].0, dst[1].1,
            dst[2].0, dst[2].1,
            dst[3].0, dst[3].1,
        ];

        let h = Self::solve_8x8(&a, &b);

        PerspMatrix {
            m: [
                [h[0], h[1], h[2]],
                [h[3], h[4], h[5]],
                [h[6], h[7], 1.0],
            ],
        }
    }

    fn solve_8x8(a: &[[f64; 8]; 8], b: &[f64; 8]) -> [f64; 8] {
        let mut mat = [[0.0f64; 9]; 8];
        for row in 0..8 {
            for k in 0..8 {
                mat[row][k] = a[row][k];
            }
            mat[row][8] = b[row];
        }

        for col in 0..8 {
            let mut max_row = col;
            for row in (col + 1)..8 {
                if mat[row][col].abs() > mat[max_row][col].abs() {
                    max_row = row;
                }
            }
            mat.swap(col, max_row);

            if mat[col][col].abs() < 1e-12 {
                continue;
            }

            let pivot = mat[col][col];
            for k in col..9 {
                mat[col][k] /= pivot;
            }

            for row in 0..8 {
                if row != col && mat[row][col].abs() > 1e-12 {
                    let factor = mat[row][col];
                    for k in col..9 {
                        mat[row][k] -= factor * mat[col][k];
                    }
                }
            }
        }

        let mut result = [0.0f64; 8];
        for i in 0..8 {
            result[i] = mat[i][8];
        }
        result
    }

    pub fn analyze_best_orientation(&self, img: &RgbImage) -> (f64, RgbImage, f64, RgbImage) {
        let rotations = [
            img.clone(),
            Self::rotate_90(img),
            Self::rotate_180(img),
            Self::rotate_270(img),
        ];

        let mut best_p_score = -1.0;
        let mut best_p_img = img.clone();
        let mut best_e_score = -1.0;
        let mut best_e_img = img.clone();

        for r_img in &rotations {
            let (rw, rh) = r_img.dimensions();
            if rw < rh {
                continue;
            }
            let p_score = self.get_face_score(r_img);
            let e_score = self.get_emblem_score(r_img);

            if p_score > best_p_score {
                best_p_score = p_score;
                best_p_img = r_img.clone();
            }
            if e_score > best_e_score {
                best_e_score = e_score;
                best_e_img = r_img.clone();
            }
        }

        (best_p_score, best_p_img, best_e_score, best_e_img)
    }

    fn rotate_90(img: &RgbImage) -> RgbImage {
        let (w, h) = img.dimensions();
        let mut out = RgbImage::new(h, w);
        for y in 0..h {
            for x in 0..w {
                let pixel = *img.get_pixel(x, y);
                out.put_pixel(h - 1 - y, x, pixel);
            }
        }
        out
    }

    fn rotate_180(img: &RgbImage) -> RgbImage {
        let (w, h) = img.dimensions();
        let mut out = RgbImage::new(w, h);
        for y in 0..h {
            for x in 0..w {
                let pixel = *img.get_pixel(x, y);
                out.put_pixel(w - 1 - x, h - 1 - y, pixel);
            }
        }
        out
    }

    fn rotate_270(img: &RgbImage) -> RgbImage {
        let (w, h) = img.dimensions();
        let mut out = RgbImage::new(h, w);
        for y in 0..h {
            for x in 0..w {
                let pixel = *img.get_pixel(x, y);
                out.put_pixel(y, w - 1 - x, pixel);
            }
        }
        out
    }

    pub fn process_pair(
        &self,
        path1: &Path,
        path2: &Path,
        out_path: &Path,
        layout: Layout,
        watermark: Option<WatermarkParams>,
        export_mode: ExportMode,
    ) -> Result<(), AppError> {
        let raw1 = self.load_image(path1)?;
        let raw2 = self.load_image(path2)?;

        let cropped1 = self.get_perspective_crop(&raw1);
        let cropped2 = self.get_perspective_crop(&raw2);

        let (p_score1, p_img1, e_score1, e_img1) = self.analyze_best_orientation(&cropped1);
        let (p_score2, p_img2, e_score2, e_img2) = self.analyze_best_orientation(&cropped2);

        let (p_final, e_final) = if p_score1 + e_score2 >= e_score1 + p_score2 {
            (p_img1, e_img2)
        } else {
            (p_img2, e_img1)
        };

        let (card_w, card_h) = self.config.card_dimensions_px();
        let p_pil = DynamicImage::ImageRgb8(p_final)
            .resize_exact(card_w, card_h, image::imageops::FilterType::Lanczos3)
            .to_rgb8();
        let e_pil = DynamicImage::ImageRgb8(e_final)
            .resize_exact(card_w, card_h, image::imageops::FilterType::Lanczos3)
            .to_rgb8();

        let card = match layout {
            Layout::Vertical => {
                let cw = card_w + 40;
                let ch = card_h * 2 + 80;
                let mut canvas = RgbImage::from_pixel(cw, ch, Rgb([255, 255, 255]));
                image::imageops::overlay(&mut canvas, &p_pil, 20, 20);
                image::imageops::overlay(&mut canvas, &e_pil, 20, (card_h + 50) as i64);
                canvas
            }
            Layout::Horizontal => {
                let cw = card_w * 2 + 80;
                let ch = card_h + 40;
                let mut canvas = RgbImage::from_pixel(cw, ch, Rgb([255, 255, 255]));
                image::imageops::overlay(&mut canvas, &p_pil, 20, 20);
                image::imageops::overlay(&mut canvas, &e_pil, (card_w + 50) as i64, 20);
                canvas
            }
        };

        let final_img = if let Some(ref wm) = watermark {
            self.apply_text_watermark(&card, wm)?
        } else {
            card
        };

        match export_mode {
            ExportMode::Image => {
                let dyn_img = DynamicImage::ImageRgb8(final_img);
                save_with_quality(&dyn_img, out_path, self.config.image_processing.jpeg_quality)?;
            }
            ExportMode::A4 => {
                let (a4_w, a4_h) = self.config.a4_dimensions_px();
                let mut canvas = RgbImage::from_pixel(a4_w, a4_h, Rgb([255, 255, 255]));
                let cx = (a4_w - final_img.width()) / 2;
                let cy = (a4_h - final_img.height()) / 2;
                image::imageops::overlay(&mut canvas, &final_img, cx as i64, cy as i64);
                let dyn_img = DynamicImage::ImageRgb8(canvas);
                save_with_quality(&dyn_img, out_path, self.config.image_processing.jpeg_quality)?;
            }
        }

        Ok(())
    }

    fn apply_text_watermark(&self, img: &RgbImage, wm: &WatermarkParams) -> Result<RgbImage, AppError> {
        if wm.text.is_empty() {
            return Ok(img.clone());
        }
        let (w, h) = img.dimensions();
        let opacity = (wm.opacity * 255.0).round() as u8;
        let step_x = (w as f64 * 0.3) as u32;
        let step_y = (h as f64 * 0.3) as u32;

        let mut out = img.clone();
        let mut y_pos = 0u32;
        let mut row = 0u32;
        while y_pos < h {
            let mut x_pos = if row % 2 == 1 { step_x / 2 } else { 0 };
            while x_pos < w {
                let text_w = (w as f64 * 0.25) as u32;
                let text_h = (h as f64 * 0.05) as u32;
                for ty in 0..text_h {
                    for tx in 0..text_w {
                        let px = x_pos + tx;
                        let py = y_pos + ty;
                        if px < w && py < h {
                            let pixel = out.get_pixel(px, py);
                            let blended = [
                                Self::blend(pixel[0], 128, opacity),
                                Self::blend(pixel[1], 128, opacity),
                                Self::blend(pixel[2], 128, opacity),
                            ];
                            out.put_pixel(px, py, Rgb(blended));
                        }
                    }
                }
                x_pos += step_x;
            }
            y_pos += step_y;
            row += 1;
        }
        Ok(out)
    }

    fn blend(base: u8, over: u8, alpha: u8) -> u8 {
        let a = alpha as u32;
        let b = base as u32;
        let o = over as u32;
        ((b * (255 - a) + o * a) / 255) as u8
    }
}

fn save_with_quality(img: &DynamicImage, path: &Path, quality: u8) -> Result<(), AppError> {
    let ext = path
        .extension()
        .and_then(|e| e.to_str())
        .unwrap_or("jpg")
        .to_lowercase();

    match ext.as_str() {
        "jpg" | "jpeg" => {
            let mut buf = std::io::BufWriter::new(std::fs::File::create(path)?);
            let encoder = image::codecs::jpeg::JpegEncoder::new_with_quality(&mut buf, quality);
            img.write_with_encoder(encoder)?;
        }
        _ => {
            img.save(path)?;
        }
    }
    Ok(())
}

#[derive(Debug, Clone, Copy)]
pub enum Layout {
    Vertical,
    Horizontal,
}

#[derive(Debug, Clone, Copy)]
pub enum ExportMode {
    Image,
    A4,
}

#[derive(Debug, Clone)]
pub struct WatermarkParams {
    pub text: String,
    pub opacity: f64,
    pub font_size: u32,
    pub angle: i32,
}

struct Contour {
    points: Vec<(f64, f64)>,
}

impl Contour {
    fn area(&self) -> f64 {
        let n = self.points.len();
        if n < 3 {
            return 0.0;
        }
        let mut area = 0.0;
        for i in 0..n {
            let j = (i + 1) % n;
            area += self.points[i].0 * self.points[j].1;
            area -= self.points[j].0 * self.points[i].1;
        }
        area.abs() / 2.0
    }

    fn approx_poly(&self, epsilon: f64) -> Option<[(f64, f64); 4]> {
        if self.points.len() < 4 {
            return None;
        }
        let peri: f64 = self
            .points
            .windows(2)
            .map(|w| (w[1].0 - w[0].0).hypot(w[1].1 - w[0].1))
            .sum::<f64>()
            + (self.points.last().unwrap().0 - self.points[0].0)
                .hypot(self.points.last().unwrap().1 - self.points[0].1);

        let eps = epsilon * peri;
        let mut simplified = Vec::new();
        simplified.push(self.points[0]);

        for i in 1..self.points.len() {
            let dx = self.points[i].0 - simplified.last().unwrap().0;
            let dy = self.points[i].1 - simplified.last().unwrap().1;
            if dx.hypot(dy) > eps {
                simplified.push(self.points[i]);
            }
        }

        if simplified.len() == 4 {
            let arr: [(f64, f64); 4] = [
                simplified[0], simplified[1], simplified[2], simplified[3],
            ];
            Some(arr)
        } else if simplified.len() > 4 {
            let step = simplified.len() as f64 / 4.0;
            let mut arr = [(0.0, 0.0); 4];
            for i in 0..4 {
                let idx = (i as f64 * step).round() as usize;
                let idx = idx.min(simplified.len() - 1);
                arr[i] = simplified[idx];
            }
            Some(arr)
        } else {
            None
        }
    }
}

struct PerspMatrix {
    m: [[f64; 3]; 3],
}

impl PerspMatrix {
    fn inverse(&self) -> Option<PerspMatrix> {
        let a = self.m;
        let det = a[0][0] * (a[1][1] * a[2][2] - a[1][2] * a[2][1])
            - a[0][1] * (a[1][0] * a[2][2] - a[1][2] * a[2][0])
            + a[0][2] * (a[1][0] * a[2][1] - a[1][1] * a[2][0]);

        if det.abs() < 1e-10 {
            return None;
        }

        let inv_det = 1.0 / det;
        Some(PerspMatrix {
            m: [
                [
                    (a[1][1] * a[2][2] - a[1][2] * a[2][1]) * inv_det,
                    (a[0][2] * a[2][1] - a[0][1] * a[2][2]) * inv_det,
                    (a[0][1] * a[1][2] - a[0][2] * a[1][1]) * inv_det,
                ],
                [
                    (a[1][2] * a[2][0] - a[1][0] * a[2][2]) * inv_det,
                    (a[0][0] * a[2][2] - a[0][2] * a[2][0]) * inv_det,
                    (a[0][2] * a[1][0] - a[0][0] * a[1][2]) * inv_det,
                ],
                [
                    (a[1][0] * a[2][1] - a[1][1] * a[2][0]) * inv_det,
                    (a[0][1] * a[2][0] - a[0][0] * a[2][1]) * inv_det,
                    (a[0][0] * a[1][1] - a[0][1] * a[1][0]) * inv_det,
                ],
            ],
        })
    }
}
