mod config;
mod error;
mod processor;

use config::AppConfig;
use processor::{ExportMode, Layout, Processor, WatermarkParams};
use std::path::{Path, PathBuf};

fn main() {
    env_logger::Builder::from_env(env_logger::Env::default().default_filter_or("info")).init();

    let config_path = find_config_path();
    let config = AppConfig::load_or_default(&config_path);
    let processor = Processor::new(config.clone());

    println!("╔══════════════════════════════════════════╗");
    println!("║   身份证照片合成助手 v2.0 (Rust)         ║");
    println!("╚══════════════════════════════════════════╝");
    println!();

    let args: Vec<String> = std::env::args().collect();
    if args.len() >= 3 {
        run_batch(&processor, &args[1], &args[2], &config);
        return;
    }

    loop {
        println!("─────────────────────────────────────");
        println!("1. 合成两张身份证图片");
        println!("2. 批量处理目录");
        println!("3. 切换布局 (当前: {})", current_layout_name(&config));
        println!("4. 切换导出模式 (当前: {})", current_export_name(&config));
        println!("5. 设置水印");
        println!("0. 退出");
        println!("────────────────────────────────────");
        print!("请选择: ");

        let mut input = String::new();
        if std::io::stdin().read_line(&mut input).is_err() {
            break;
        }

        match input.trim() {
            "1" => interactive_process(&processor, &config),
            "2" => batch_process(&processor, &config),
            "0" => break,
            _ => println!("无效选择"),
        }
    }
}

fn find_config_path() -> PathBuf {
    let exe_dir = std::env::current_exe()
        .ok()
        .and_then(|e| e.parent().map(|p| p.to_path_buf()))
        .unwrap_or_else(|| PathBuf::from("."));
    let candidates = vec![
        exe_dir.join("config.yaml"),
        PathBuf::from("config.yaml"),
    ];
    for c in candidates {
        if c.exists() {
            return c;
        }
    }
    PathBuf::from("config.yaml")
}

fn current_layout_name(config: &AppConfig) -> &'static str {
    "上下放置"
}

fn current_export_name(config: &AppConfig) -> &'static str {
    "直接输出图片"
}

fn interactive_process(processor: &Processor, config: &AppConfig) {
    println!("\n--- 身份证照片合成 ---");

    let path1 = prompt_path("请输入第一张图片路径: ");
    let path2 = prompt_path("请输入第二张图片路径: ");

    if path1.is_empty() || path2.is_empty() {
        println!("路径不能为空");
        return;
    }

    let layout = prompt_layout();
    let export_mode = prompt_export_mode();
    let watermark = prompt_watermark();

    let default_name = format!(
        "{}_1.jpg",
        chrono_now()
    );
    print!("输出文件路径 [{}]: ", default_name);
    let mut out_input = String::new();
    std::io::stdin().read_line(&mut out_input).ok();
    let out_path = if out_input.trim().is_empty() {
        let dir = dirs_pictures().join("身份证");
        std::fs::create_dir_all(&dir).ok();
        dir.join(&default_name)
    } else {
        PathBuf::from(out_input.trim())
    };

    match processor.process_pair(
        Path::new(&path1),
        Path::new(&path2),
        &out_path,
        layout,
        watermark,
        export_mode,
    ) {
        Ok(()) => println!("✓ 处理完成: {}", out_path.display()),
        Err(e) => println!("✗ 处理失败: {e}"),
    }
}

fn batch_process(processor: &Processor, config: &AppConfig) {
    print!("请输入包含图片的目录路径: ");
    let mut dir_input = String::new();
    std::io::stdin().read_line(&mut dir_input).ok();
    let dir = Path::new(dir_input.trim());

    if !dir.is_dir() {
        println!("不是有效目录");
        return;
    }

    let mut images: Vec<PathBuf> = Vec::new();
    collect_images(dir, &mut images);
    images.sort();

    if images.len() < 2 {
        println!("目录中图片不足2张");
        return;
    }

    let layout = prompt_layout();
    let export_mode = prompt_export_mode();
    let watermark = prompt_watermark();
    let out_dir = dir.join("output");
    std::fs::create_dir_all(&out_dir).ok();

    let mut count = 0u32;
    for chunk in images.chunks(2) {
        if chunk.len() < 2 {
            break;
        }
        count += 1;
        let out_path = out_dir.join(format!("merged_{count}.jpg"));
        match processor.process_pair(
            &chunk[0],
            &chunk[1],
            &out_path,
            layout,
            watermark.clone(),
            export_mode,
        ) {
            Ok(()) => println!("✓ [{count}] {}", out_path.display()),
            Err(e) => println!("✗ [{count}] 失败: {e}"),
        }
    }
    println!("批量处理完成，共处理 {count} 对");
}

fn run_batch(processor: &Processor, path1: &str, path2: &str, config: &AppConfig) {
    let out_dir = dirs_pictures().join("身份证");
    std::fs::create_dir_all(&out_dir).ok();
    let out_path = out_dir.join(format!("{}_1.jpg", chrono_now()));

    match processor.process_pair(
        Path::new(path1),
        Path::new(path2),
        &out_path,
        Layout::Vertical,
        None,
        ExportMode::Image,
    ) {
        Ok(()) => println!("✓ {}", out_path.display()),
        Err(e) => eprintln!("✗ {e}"),
    }
}

fn prompt_path(msg: &str) -> String {
    print!("{msg}");
    let mut input = String::new();
    std::io::stdin().read_line(&mut input).ok();
    input.trim().to_string()
}

fn prompt_layout() -> Layout {
    print!("布局 [1=上下 2=左右, 默认1]: ");
    let mut input = String::new();
    std::io::stdin().read_line(&mut input).ok();
    match input.trim() {
        "2" => Layout::Horizontal,
        _ => Layout::Vertical,
    }
}

fn prompt_export_mode() -> ExportMode {
    print!("导出 [1=直接图片 2=A4排版, 默认1]: ");
    let mut input = String::new();
    std::io::stdin().read_line(&mut input).ok();
    match input.trim() {
        "2" => ExportMode::A4,
        _ => ExportMode::Image,
    }
}

fn prompt_watermark() -> Option<WatermarkParams> {
    print!("水印文字 (留空跳过): ");
    let mut input = String::new();
    std::io::stdin().read_line(&mut input).ok();
    let text = input.trim().to_string();
    if text.is_empty() {
        None
    } else {
        Some(WatermarkParams {
            text,
            opacity: 0.30,
            font_size: 48,
            angle: 30,
        })
    }
}

fn collect_images(dir: &Path, out: &mut Vec<PathBuf>) {
    if let Ok(entries) = std::fs::read_dir(dir) {
        for entry in entries.flatten() {
            let path = entry.path();
            if path.is_dir() {
                collect_images(&path, out);
            } else if let Some(ext) = path.extension().and_then(|e| e.to_str()) {
                let ext = ext.to_lowercase();
                if matches!(ext.as_str(), "jpg" | "jpeg" | "png" | "bmp" | "tiff" | "webp") {
                    out.push(path);
                }
            }
        }
    }
}

fn dirs_pictures() -> PathBuf {
    let home = std::env::var("USERPROFILE")
        .or_else(|_| std::env::var("HOME"))
        .unwrap_or_else(|_| ".".into());
    PathBuf::from(home).join("Pictures")
}

fn chrono_now() -> String {
    let now = std::time::SystemTime::now()
        .duration_since(std::time::UNIX_EPOCH)
        .unwrap_or_default();
    let secs = now.as_secs();
    let days = secs / 86400;
    let time_of_day = secs % 86400;
    let hours = time_of_day / 3600;
    let minutes = (time_of_day % 3600) / 60;
    let year = 1970 + (days * 400 + 49) / 146097;
    format!("{year}{hours:02}{minutes:02}")
}
