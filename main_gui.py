import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog
from tkinter import ttk
import os
import threading
import windnd
import sys
from datetime import datetime
from PIL import Image, ImageTk
from processor import IDCardProcessor
from exceptions import (
    IDCardProcessorError,
    ImageLoadError,
    ImageTooLargeError,
    InvalidImageFormatError,
    FaceDetectionError,
    PerspectiveCorrectionError,
    WatermarkError,
    ConfigurationError,
    SecurityError,
    ValidationError
)
from logger import logger


class IDCardApp:
    _strings = {
        'zh': {
            'title': '身份证照片合成助手',
            'zone_1': '第一张图片', 'zone_2': '第二张图片',
            'not_selected': '未选择图片', 'selected': '已选: ',
            'filename': '文件名:', 'idle': '就绪', 'start_btn': '开始合成',
            'drag_hint': '点此选择或拖入图片',
            'menu_file': '文件', 'menu_output_dir': '输出目录...', 'menu_exit': '退出',
            'menu_settings': '设置', 'menu_format': '输出格式', 'menu_layout': '布局',
            'layout_v': '上下放置', 'layout_h': '左右放置',
            'menu_language': '语言', 'lang_zh': '中文', 'lang_en': 'English',
            'menu_watermark': '水印设置...',
            'menu_about': '关于', 'menu_help': '使用帮助', 'menu_copyright': '版权信息',
            'ok': '确定', 'cancel': '取消',
            'help_title': '使用帮助',
            'help_text': ('1. 点击左侧或右侧区域（或拖入图片）加载身份证照片。\n'
                           '2. 程序会自动检测、裁剪并校正方向。\n'
                           '3. 设置 → 布局：选择上下放置或左右放置。\n'
                           '4. 设置 → 输出格式：选择PNG/JPG/TIFF等格式。\n'
                           '5. 设置 → 导出模式：选择直接输出图片或A4排版打印。\n'
                           '6. 设置 → 水印设置：添加自定义文字水印。\n'
                           '7. 设置 → 语言：切换中文/英文界面。\n'
                           '8. 点击「开始合成」生成输出图片。'),
            'copyright_title': '版权信息',
            'copyright_name': '身份证照片合成助手 v1.0',
            'copyright_email': '联系方式: jzfjs2008@gmail.com',
            'warn_title': '警告', 'warn_select': '请选择两张图片！',
            'warn_filename': '请输入输出文件名！',
            'file_exists': '文件已存在',
            'file_exists_msg': '文件已存在。\n是否覆盖？',
            'success_title': '成功', 'success_msg': '文件已保存到:\n',
            'error_title': '错误', 'init_engine': '正在初始化视觉引擎...',
            'task_done': '任务完成！', 'processing_failed': '处理失败: ',
            'preview_error': '错误：无法加载预览 - ', 'file_filter': '图片文件',
            # watermark dialog
            'wm_dlg_title': '水印设置',
            'wm_enable': '启用文字水印',
            'wm_text_lbl': '水印文字:',
            'wm_text_hint': '例：仅供核验',
            'wm_opacity_lbl': '不透明度:',
            'wm_size_lbl': '字体大小:',
            'wm_angle_lbl': '旋转角度:',
            'wm_preview_btn': '预览效果',
            'menu_export_mode': '导出模式',
            'export_image': '直接输出图片',
            'export_a4': 'A4排版打印',
            'wm_status_on': '水印已启用：',
            'wm_status_off': '水印未启用',
        },
        'en': {
            'title': 'ID Card Photo Compositor',
            'zone_1': 'First Image', 'zone_2': 'Second Image',
            'not_selected': 'No image selected', 'selected': 'Selected: ',
            'filename': 'Filename:', 'idle': 'Ready', 'start_btn': 'Compose',
            'drag_hint': 'Click or drag image here',
            'menu_file': 'File', 'menu_output_dir': 'Output Directory...', 'menu_exit': 'Exit',
            'menu_settings': 'Settings', 'menu_format': 'Output Format', 'menu_layout': 'Layout',
            'layout_v': 'Vertical', 'layout_h': 'Horizontal',
            'menu_language': 'Language', 'lang_zh': '中文', 'lang_en': 'English',
            'menu_watermark': 'Watermark Settings...',
            'menu_about': 'About', 'menu_help': 'Help', 'menu_copyright': 'Copyright',
            'ok': 'OK', 'cancel': 'Cancel',
            'help_title': 'Help',
            'help_text': ('1. Click the left/right area or drag an image to load ID card photos.\n'
                           '2. The program will auto-detect, crop, and correct orientation.\n'
                           '3. Settings → Layout: choose Vertical or Horizontal placement.\n'
                           '4. Settings → Output Format: choose PNG/JPG/TIFF etc.\n'
                           '5. Settings → Export Mode: choose direct image or A4 layout.\n'
                           '6. Settings → Watermark: add custom text watermark.\n'
                           '7. Settings → Language: switch between Chinese and English.\n'
                           '8. Click Compose to generate the output image.'),
            'copyright_title': 'Copyright',
            'copyright_name': 'ID Card Photo Compositor v1.0',
            'copyright_email': 'Contact: jzfjs2008@gmail.com',
            'warn_title': 'Warning', 'warn_select': 'Please select both images!',
            'warn_filename': 'Please enter output filename!',
            'file_exists': 'File Exists',
            'file_exists_msg': 'File already exists.\nOverwrite?',
            'success_title': 'Success', 'success_msg': 'File saved to:\n',
            'error_title': 'Error', 'init_engine': 'Initializing vision engine...',
            'task_done': 'Task completed!', 'processing_failed': 'Processing failed: ',
            'preview_error': 'Error: could not load preview - ', 'file_filter': 'Image files',
            # watermark dialog
            'wm_dlg_title': 'Watermark Settings',
            'wm_enable': 'Enable Text Watermark',
            'wm_text_lbl': 'Watermark Text:',
            'wm_text_hint': 'e.g. For Verification Only',
            'wm_opacity_lbl': 'Opacity:',
            'wm_size_lbl': 'Font Size:',
            'wm_angle_lbl': 'Angle:',
            'wm_preview_btn': 'Preview',
            'menu_export_mode': 'Export Mode',
            'export_image': 'Direct Image',
            'export_a4': 'A4 Print Layout',
            'wm_status_on': 'Watermark ON: ',
            'wm_status_off': 'No watermark',
        }
    }

    def __init__(self, root):
        self.root = root
        self._lang = 'zh'

        try:
            from ctypes import windll
            windll.shcore.SetProcessDpiAwareness(1)
        except Exception as e:
            pass

        self.root.geometry("780x640")
        self.root.resizable(False, False)
        self.root.configure(bg="#f3f3f3")

        self._set_window_icon()

        self.style = ttk.Style()
        self.style.theme_use('vista')

        self.style.configure("Accent.TButton", font=("Microsoft YaHei", 10, "bold"))
        self.style.configure("TLabel", font=("Microsoft YaHei", 9))
        self.style.configure("TEntry", font=("Microsoft YaHei", 9))
        self.style.configure("Zone.TLabelframe", font=("Microsoft YaHei", 10, "bold"))

        self.processor = None
        self.portrait_path = tk.StringVar()
        self.emblem_path = tk.StringVar()
        default_save = os.path.join(os.path.expanduser("~"), "Pictures", "身份证")
        os.makedirs(default_save, exist_ok=True)
        self.save_path = tk.StringVar(value=default_save)
        self.output_filename = tk.StringVar()
        self.output_format = tk.StringVar(value=".png")
        self.output_layout = tk.StringVar(value="vertical")
        self.output_mode = tk.StringVar(value="image")

        self.p_img_ref = None
        self.e_img_ref = None
        self._progress_id = None

        self._fn_label = None

        # Watermark state (text watermark)
        self.watermark_enabled = tk.BooleanVar(value=False)
        self.watermark_text = tk.StringVar(value="")
        self.watermark_opacity = tk.DoubleVar(value=0.30)
        self.watermark_font_size = tk.IntVar(value=48)
        self.watermark_angle = tk.IntVar(value=30)

        self.update_default_filename()
        self.root.title(self._tr('title'))
        self._build_menu()
        self.setup_ui()
        self.setup_drag_and_drop()

    def _tr(self, key):
        return self._strings[self._lang].get(key, key)

    @staticmethod
    def _resource_path(rel_path):
        try:
            base = sys._MEIPASS
        except AttributeError:
            base = os.path.dirname(__file__)
        return os.path.join(base, rel_path)

    def _set_window_icon(self):
        try:
            self.root.iconbitmap(default=self._resource_path("logo.ico"))
            return
        except Exception as e:
            pass
        try:
            from PIL import ImageTk
            img = Image.open(self._resource_path("logo.png"))
            self._logo_icon = ImageTk.PhotoImage(img)
            self.root.tk.call('wm', 'iconphoto', self.root._w, '-default', self._logo_icon)
            return
        except Exception as e:
            pass

    def _rebuild_menu(self):
        self.root.config(menu=tk.Menu(self.root))
        self._build_menu()

    def _build_menu(self):
        menubar = tk.Menu(self.root)
        S = self._tr

        file_menu = tk.Menu(menubar, tearoff=0)
        file_menu.add_command(label=S('menu_output_dir'), command=self.select_save_dir, accelerator="Ctrl+D")
        file_menu.add_separator()
        file_menu.add_command(label=S('menu_exit'), command=self.on_closing, accelerator="Ctrl+Q")
        menubar.add_cascade(label=S('menu_file'), menu=file_menu)

        settings_menu = tk.Menu(menubar, tearoff=0)
        fmt_menu = tk.Menu(settings_menu, tearoff=0)
        self._fmt_var = tk.StringVar(value=self.output_format.get())
        for fmt in [".png", ".jpg", ".jpeg", ".tiff", ".bmp", ".webp"]:
            fmt_menu.add_radiobutton(label=fmt, variable=self._fmt_var, value=fmt,
                                     command=lambda f=fmt: self.output_format.set(f))
        settings_menu.add_cascade(label=S('menu_format'), menu=fmt_menu)

        layout_menu = tk.Menu(settings_menu, tearoff=0)
        self._layout_var = tk.StringVar(value=self.output_layout.get())
        for internal_val, label_key in [("vertical", "layout_v"), ("horizontal", "layout_h")]:
            layout_menu.add_radiobutton(label=S(label_key), variable=self._layout_var, value=internal_val,
                                        command=lambda v=internal_val: self.output_layout.set(v))
        settings_menu.add_cascade(label=S('menu_layout'), menu=layout_menu)

        export_menu = tk.Menu(settings_menu, tearoff=0)
        self._export_var = tk.StringVar(value=self.output_mode.get())
        for mode_val, mode_key in [("image", "export_image"), ("a4", "export_a4")]:
            export_menu.add_radiobutton(label=S(mode_key), variable=self._export_var, value=mode_val,
                                        command=lambda v=mode_val: self.output_mode.set(v))
        settings_menu.add_cascade(label=S('menu_export_mode'), menu=export_menu)

        settings_menu.add_separator()
        settings_menu.add_command(label=S('menu_watermark'), command=self.show_watermark_dialog)

        settings_menu.add_separator()
        lang_menu = tk.Menu(settings_menu, tearoff=0)
        self._lang_var = tk.StringVar(value=self._lang)
        for lval, lkey in [('zh', 'lang_zh'), ('en', 'lang_en')]:
            lang_menu.add_radiobutton(label=S(lkey), variable=self._lang_var, value=lval,
                                      command=lambda v=lval: self._switch_lang(v))
        settings_menu.add_cascade(label=S('menu_language'), menu=lang_menu)

        menubar.add_cascade(label=S('menu_settings'), menu=settings_menu)

        about_menu = tk.Menu(menubar, tearoff=0)
        about_menu.add_command(label=S('menu_help'), command=self.show_help)
        about_menu.add_command(label=S('menu_copyright'), command=self.show_copyright)
        menubar.add_cascade(label=S('menu_about'), menu=about_menu)

        self.root.config(menu=menubar)

        self.root.bind("<Control-d>", lambda e: self.select_save_dir())
        self.root.bind("<Control-D>", lambda e: self.select_save_dir())
        self.root.bind("<Control-q>", lambda e: self.on_closing())
        self.root.bind("<Control-Q>", lambda e: self.on_closing())

    def _switch_lang(self, lang):
        old_layout = self.output_layout.get()
        old_export = self.output_mode.get()
        self._lang = lang
        self._rebuild_menu()
        self._refresh_ui()
        self.output_layout.set(old_layout)
        self.output_mode.set(old_export)
        self.root.title(self._tr('title'))

    def _refresh_ui(self):
        S = self._tr
        self.frame_p.configure(text=f" {S('zone_1')} ")
        self.frame_e.configure(text=f" {S('zone_2')} ")
        sel_p = self.portrait_path.get()
        sel_e = self.emblem_path.get()
        self.lbl_p_info.config(text=S('not_selected') if not sel_p else f"{S('selected')}{os.path.basename(sel_p)}",
                               foreground="#999999" if not sel_p else "#28a745")
        self.lbl_e_info.config(text=S('not_selected') if not sel_e else f"{S('selected')}{os.path.basename(sel_e)}",
                               foreground="#999999" if not sel_e else "#28a745")
        if not sel_p:
            self.lbl_p_preview.config(text=S('drag_hint'))
        if not sel_e:
            self.lbl_e_preview.config(text=S('drag_hint'))
        self.status_label.config(text=S('idle'))
        self.btn_start.config(text=f"  {S('start_btn')}  ")
        if self._fn_label:
            self._fn_label.config(text=S('filename'))

    def update_default_filename(self):
        today = datetime.now().strftime("%Y%m%d")
        folder = self.save_path.get()
        if not os.path.exists(folder):
            self.output_filename.set(f"{today}_1")
            return
        index = 1
        while True:
            name = f"{today}_{index}"
            exists = False
            for ext in [".jpg", ".jpeg", ".png", ".tiff", ".bmp", ".webp"]:
                if os.path.exists(os.path.join(folder, name + ext)):
                    exists = True
                    break
            if not exists:
                self.output_filename.set(name)
                break
            index += 1

    def setup_ui(self):
        S = self._tr
        style = ttk.Style(self.root)
        style.configure("TProgressbar", thickness=8, troughcolor="#e0e0e0", background="#4a90d9", troughrelief="flat")

        main_container = tk.Frame(self.root, bg="#f3f3f3")
        main_container.pack(fill='both', expand=True, padx=25, pady=(10, 5))

        self.frame_p = ttk.LabelFrame(main_container, text=f" {S('zone_1')} ", style="Zone.TLabelframe",
                                       width=350, height=240)
        self.frame_p.pack(side='left', fill='both', expand=True, padx=(0, 10))
        self.frame_p.pack_propagate(False)

        self.lbl_p_preview = tk.Label(self.frame_p, text=S('drag_hint'), bg="#ffffff", relief="flat", cursor="hand2")
        self.lbl_p_preview.pack(fill='both', expand=True, padx=10, pady=8)

        self.lbl_p_info = ttk.Label(self.frame_p, text=S('not_selected'), foreground="#999999")
        self.lbl_p_info.pack(pady=(0, 8))

        self.frame_e = ttk.LabelFrame(main_container, text=f" {S('zone_2')} ", style="Zone.TLabelframe",
                                       width=350, height=240)
        self.frame_e.pack(side='right', fill='both', expand=True, padx=(10, 0))
        self.frame_e.pack_propagate(False)

        self.lbl_e_preview = tk.Label(self.frame_e, text=S('drag_hint'), bg="#ffffff", relief="flat", cursor="hand2")
        self.lbl_e_preview.pack(fill='both', expand=True, padx=10, pady=8)

        self.lbl_e_info = ttk.Label(self.frame_e, text=S('not_selected'), foreground="#999999")
        self.lbl_e_info.pack(pady=(0, 8))

        for item in [self.lbl_p_preview, self.frame_p]:
            item.bind("<Button-1>", lambda e: self.select_file('portrait'))
        for item in [self.lbl_e_preview, self.frame_e]:
            item.bind("<Button-1>", lambda e: self.select_file('emblem'))

        fn_frame = ttk.Frame(self.root)
        fn_frame.pack(fill='x', padx=25, pady=(0, 5))
        self._fn_label = ttk.Label(fn_frame, text=S('filename'))
        self._fn_label.pack(side='left')
        ttk.Entry(fn_frame, textvariable=self.output_filename).pack(side='left', fill='x', expand=True, padx=(10, 0))

        action_frame = tk.Frame(self.root, bg="#f3f3f3")
        action_frame.pack(fill='x', padx=25, pady=(10, 20))

        self.progress = ttk.Progressbar(action_frame, mode='determinate', style="TProgressbar")
        self.progress.pack(fill='x', pady=(0, 8))

        self.status_label = ttk.Label(action_frame, text=S('idle'), foreground="#666666",
                                       font=("Microsoft YaHei", 9), anchor='center')
        self.status_label.pack(fill='x')

        btn_container = tk.Frame(action_frame, bg="#f3f3f3")
        btn_container.pack(pady=(8, 0))

        self.btn_start = ttk.Button(btn_container, text=f"  {S('start_btn')}  ", style="Accent.TButton",
                                     command=self.start_processing, width=25)
        self.btn_start.pack()

    def show_watermark_dialog(self):
        """Open the watermark settings dialog."""
        S = self._tr
        dlg = tk.Toplevel(self.root)
        dlg.title(S('wm_dlg_title'))
        dlg.resizable(False, False)
        dlg.transient(self.root)
        dlg.grab_set()

        # Center on parent
        dlg.update_idletasks()
        dw, dh = 400, 300
        x = self.root.winfo_x() + (self.root.winfo_width() - dw) // 2
        y = self.root.winfo_y() + (self.root.winfo_height() - dh) // 2
        dlg.geometry(f"{dw}x{dh}+{x}+{y}")

        pad = {'padx': 12, 'pady': 5}
        frame = ttk.Frame(dlg, padding=10)
        frame.pack(fill='both', expand=True)

        # Local vars (pre-filled with current settings)
        _enabled = tk.BooleanVar(value=self.watermark_enabled.get())
        _text    = tk.StringVar(value=self.watermark_text.get())
        _opacity = tk.DoubleVar(value=self.watermark_opacity.get())
        _size    = tk.IntVar(value=self.watermark_font_size.get())
        _angle   = tk.IntVar(value=self.watermark_angle.get())

        # ── Enable checkbox ──
        ttk.Checkbutton(frame, text=S('wm_enable'), variable=_enabled).grid(
            row=0, column=0, columnspan=3, sticky='w', **pad)

        # ── Text input ──
        ttk.Label(frame, text=S('wm_text_lbl')).grid(row=1, column=0, sticky='w', **pad)
        text_entry = ttk.Entry(frame, textvariable=_text, width=28)
        text_entry.grid(row=1, column=1, columnspan=2, sticky='ew', **pad)
        if not _text.get():
            text_entry.insert(0, S('wm_text_hint'))
            text_entry.config(foreground='grey')
            def _on_focus_in(e):
                if text_entry.get() == S('wm_text_hint'):
                    text_entry.delete(0, 'end')
                    text_entry.config(foreground='black')
            def _on_focus_out(e):
                if not text_entry.get().strip():
                    text_entry.insert(0, S('wm_text_hint'))
                    text_entry.config(foreground='grey')
            text_entry.bind('<FocusIn>', _on_focus_in)
            text_entry.bind('<FocusOut>', _on_focus_out)

        # ── Opacity slider ──
        _opacity_pct = tk.StringVar(value=f"{int(_opacity.get()*100)}%")
        def _upd_opacity(*_):
            _opacity_pct.set(f"{int(_opacity.get()*100)}%")
        _opacity.trace_add('write', _upd_opacity)

        ttk.Label(frame, text=S('wm_opacity_lbl')).grid(row=2, column=0, sticky='w', **pad)
        ttk.Scale(frame, from_=0.05, to=1.0, variable=_opacity,
                  orient='horizontal', length=200).grid(row=2, column=1, sticky='ew', **pad)
        ttk.Label(frame, textvariable=_opacity_pct, width=5).grid(row=2, column=2, sticky='w')

        # ── Font size ──
        ttk.Label(frame, text=S('wm_size_lbl')).grid(row=3, column=0, sticky='w', **pad)
        size_spin = ttk.Spinbox(frame, from_=18, to=120, textvariable=_size, width=6)
        size_spin.grid(row=3, column=1, sticky='w', **pad)

        # ── Angle ──
        ttk.Label(frame, text=S('wm_angle_lbl')).grid(row=4, column=0, sticky='w', **pad)
        angle_spin = ttk.Spinbox(frame, from_=0, to=90, textvariable=_angle, width=6)
        angle_spin.grid(row=4, column=1, sticky='w', **pad)

        frame.columnconfigure(1, weight=1)

        # ── Buttons ──
        def _apply():
            raw = _text.get().strip()
            if raw == S('wm_text_hint'):
                raw = ''
            self.watermark_enabled.set(_enabled.get())
            self.watermark_text.set(raw)
            self.watermark_opacity.set(_opacity.get())
            self.watermark_font_size.set(_size.get())
            self.watermark_angle.set(_angle.get())
            self._refresh_wm_status()
            dlg.destroy()

        def _cancel():
            dlg.destroy()

        btn_frame = tk.Frame(dlg)
        btn_frame.pack(pady=(0, 10))
        ttk.Button(btn_frame, text=S('ok'), command=_apply, width=10).pack(side='left', padx=6)
        ttk.Button(btn_frame, text=S('cancel'), command=_cancel, width=10).pack(side='left', padx=6)

    def _refresh_wm_status(self):
        """Update the status bar hint to reflect current watermark state."""
        S = self._tr
        if self.watermark_enabled.get() and self.watermark_text.get().strip():
            msg = f"{S('wm_status_on')}{self.watermark_text.get()}"
        else:
            msg = S('wm_status_off')
        try:
            self.status_label.config(text=msg)
        except Exception:
            pass

    def setup_drag_and_drop(self):
        windnd.hook_dropfiles(self.root, func=self.on_drop_global)

    def on_drop_global(self, filenames):
        if not filenames:
            return
        file_path = filenames[0].decode('gbk')
        x = self.root.winfo_pointerx() - self.root.winfo_rootx()
        if x < self.root.winfo_width() / 2:
            self.set_portrait(file_path)
        else:
            self.set_emblem(file_path)

    def select_file(self, side):
        S = self._tr
        path = filedialog.askopenfilename(filetypes=[(S('file_filter'), "*.jpg *.jpeg *.png")])
        if not path:
            return
        if side == 'portrait':
            self.set_portrait(path)
        else:
            self.set_emblem(path)

    def update_preview(self, path, label_attr, side):
        try:
            img = Image.open(path)
            img.thumbnail((340, 220), Image.Resampling.LANCZOS)
            photo = ImageTk.PhotoImage(img)
            label = getattr(self, label_attr)
            label.config(image=photo, text="", bg="#ffffff")
            if side == 'p':
                self.p_img_ref = photo
            else:
                self.e_img_ref = photo
        except Exception as e:
            self.update_status(f"{self._tr('preview_error')}{str(e)}")

    def set_portrait(self, path):
        try:
            if self.processor is None:
                self.processor = IDCardProcessor(status_callback=self.update_status)
            self.processor.validate_image_file(path)
            
            if os.path.isfile(path):
                self.portrait_path.set(path)
                self.lbl_p_info.config(text=f"{self._tr('selected')}{os.path.basename(path)}", foreground="#28a745")
                self.update_preview(path, 'lbl_p_preview', 'p')
        except (ImageTooLargeError, InvalidImageFormatError, ImageLoadError) as e:
            messagebox.showerror(self._tr('error_title'), str(e))
            logger.error(f"Failed to set portrait: {e}")

    def set_emblem(self, path):
        try:
            if self.processor is None:
                self.processor = IDCardProcessor(status_callback=self.update_status)
            self.processor.validate_image_file(path)
            
            if os.path.isfile(path):
                self.emblem_path.set(path)
                self.lbl_e_info.config(text=f"{self._tr('selected')}{os.path.basename(path)}", foreground="#28a745")
                self.update_preview(path, 'lbl_e_preview', 'e')
        except (ImageTooLargeError, InvalidImageFormatError, ImageLoadError) as e:
            messagebox.showerror(self._tr('error_title'), str(e))
            logger.error(f"Failed to set emblem: {e}")

    def select_save_dir(self):
        path = filedialog.askdirectory()
        if path:
            self.save_path.set(path)
            self.update_default_filename()

    def clear_selection(self):
        S = self._tr
        self.portrait_path.set("")
        self.emblem_path.set("")
        self.update_default_filename()
        self.lbl_p_info.config(text=S('not_selected'), foreground="#999999")
        self.lbl_e_info.config(text=S('not_selected'), foreground="#999999")
        self.lbl_p_preview.config(image="", text=S('drag_hint'), bg="#ffffff")
        self.lbl_e_preview.config(image="", text=S('drag_hint'), bg="#ffffff")
        self.p_img_ref = None
        self.e_img_ref = None
        self._reset_progress()
        self.status_label.config(text=S('idle'))

    def _reset_progress(self):
        if self._progress_id:
            self.root.after_cancel(self._progress_id)
            self._progress_id = None
        self.progress['value'] = 0

    def show_help(self):
        S = self._tr
        dlg = tk.Toplevel(self.root)
        dlg.title(S('help_title'))
        dlg.geometry("640x200")
        dlg.resizable(False, False)
        dlg.transient(self.root)
        dlg.grab_set()
        x = self.root.winfo_x() + (self.root.winfo_width() - 640) // 2
        y = self.root.winfo_rooty() + (self.root.winfo_height() - 200) // 2
        dlg.geometry(f"640x200+{x}+{y}")

        frame = ttk.Frame(dlg, padding=15)
        frame.pack(fill='both', expand=True)
        tk.Message(frame, text=S('help_text'), width=610, font=("Microsoft YaHei", 9),
                   justify='left', bg="#f0f0f0").pack(fill='both', expand=True)
        ttk.Button(dlg, text=S('ok'), command=dlg.destroy).pack(pady=(0, 10))

    def show_copyright(self):
        S = self._tr
        dlg = tk.Toplevel(self.root)
        dlg.title(S('copyright_title'))
        dlg.geometry("300x120")
        dlg.resizable(False, False)
        dlg.transient(self.root)
        dlg.grab_set()
        x = self.root.winfo_x() + (self.root.winfo_width() - 300) // 2
        y = self.root.winfo_rooty() + (self.root.winfo_height() - 120) // 2
        dlg.geometry(f"300x120+{x}+{y}")

        frame = ttk.Frame(dlg, padding=20)
        frame.pack(fill='both', expand=True)
        ttk.Label(frame, text=S('copyright_name'), font=("Microsoft YaHei", 10, "bold")).pack()
        ttk.Label(frame, text="© 2026 Adrian", font=("Microsoft YaHei", 9)).pack(pady=5)
        ttk.Label(frame, text=S('copyright_email'), font=("Microsoft YaHei", 9)).pack()
        ttk.Button(dlg, text=S('ok'), command=dlg.destroy).pack(pady=(0, 10))

    def update_status(self, message):
        self.root.after(0, lambda: self.status_label.config(text=message))

    def _animate_progress(self):
        v = int(self.progress['value']) if self.progress['value'] else 0
        if v < 96:
            self.progress['value'] = v + 4
        self._progress_id = self.root.after(80, self._animate_progress)

    def _stop_progress_full(self):
        if self._progress_id:
            self.root.after_cancel(self._progress_id)
            self._progress_id = None
        self.progress['value'] = 100

    def start_processing(self):
        S = self._tr
        p, e = self.portrait_path.get(), self.emblem_path.get()
        fname = self.output_filename.get().strip()
        ext = self.output_format.get()
        lyt = self.output_layout.get()

        if not p or not e:
            messagebox.showwarning(S('warn_title'), S('warn_select'))
            return
        if not fname:
            messagebox.showwarning(S('warn_title'), S('warn_filename'))
            return
        
        if not fname.replace('_', '').replace('-', '').isalnum():
            messagebox.showwarning(S('warn_title'), "文件名只能包含字母、数字、下划线和连字符！")
            return

        save_dir = self.save_path.get()
        try:
            os.makedirs(save_dir, exist_ok=True)
            test_file = os.path.join(save_dir, '.write_test')
            with open(test_file, 'w') as f:
                f.write('test')
            os.remove(test_file)
        except PermissionError:
            messagebox.showerror(S('error_title'), f"没有权限写入目录：\n{save_dir}")
            return
        except Exception as ex:
            messagebox.showerror(S('error_title'), f"无法访问输出目录：\n{str(ex)}")
            return

        output_path = os.path.join(save_dir, f"{fname}{ext}")

        if os.path.exists(output_path):
            resp = messagebox.askyesno(S('file_exists'), S('file_exists_msg'))
            if not resp:
                return

        wm_text = self.watermark_text.get().strip() if self.watermark_enabled.get() else None
        wm_opacity = self.watermark_opacity.get()
        wm_font_size = self.watermark_font_size.get()
        wm_angle = self.watermark_angle.get()

        export_mode = self.output_mode.get()

        self.btn_start.config(state='disabled')
        self.progress['value'] = 0
        self._animate_progress()
        thread = threading.Thread(target=self.run_task,
                                  args=(p, e, output_path, lyt,
                                        wm_text, wm_opacity, wm_font_size, wm_angle,
                                        export_mode),
                                  name="Worker")
        thread.start()

    def run_task(self, p, e, output_path, lyt,
                 wm_text=None, wm_opacity=0.30, wm_font_size=48, wm_angle=30,
                 export_mode="image"):
        S = self._tr
        try:
            if self.processor is None:
                self.update_status(S('init_engine'))
                self.processor = IDCardProcessor(status_callback=self.update_status)
            
            self.update_status("步骤 1/4: 加载并验证图像...")
            self.root.after(0, lambda: self.progress.__setitem__('value', 25))

            self.update_status("步骤 2/4: 透视校正...")
            self.root.after(0, lambda: self.progress.__setitem__('value', 50))

            self.update_status("步骤 3/4: 分析内容与方向...")
            self.root.after(0, lambda: self.progress.__setitem__('value', 75))

            self.processor.process_pair(p, e, output_path, layout=lyt,
                                        watermark_text=wm_text,
                                        watermark_opacity=wm_opacity,
                                        watermark_font_size=wm_font_size,
                                        watermark_angle=wm_angle,
                                        export_mode=export_mode)

            self.root.after(0, self._stop_progress_full)
            self.update_status(S('task_done'))
            self.root.after(0, lambda: messagebox.showinfo(S('success_title'), f"{S('success_msg')}{output_path}"))
            self.root.after(0, self.update_default_filename)
            self.root.after(0, self.clear_selection)
        except ImageTooLargeError as ex:
            self.root.after(0, self._reset_progress)
            error_msg = f"图片文件过大：{ex.details.get('size_mb', 0):.1f}MB\n最大允许：{ex.details.get('max_mb', 50)}MB"
            self.update_status(f"{S('processing_failed')}{error_msg}")
            self.root.after(0, lambda: messagebox.showerror(S('error_title'), error_msg))
            logger.error(f"Image too large: {ex}")
        except InvalidImageFormatError as ex:
            self.root.after(0, self._reset_progress)
            error_msg = f"不支持的图片格式：{ex.details.get('extension', 'unknown')}\n支持的格式：{', '.join(ex.details.get('allowed', []))}"
            self.update_status(f"{S('processing_failed')}{error_msg}")
            self.root.after(0, lambda: messagebox.showerror(S('error_title'), error_msg))
            logger.error(f"Invalid format: {ex}")
        except ImageLoadError as ex:
            self.root.after(0, self._reset_progress)
            error_msg = f"图片加载失败：{ex.message}"
            self.update_status(f"{S('processing_failed')}{error_msg}")
            self.root.after(0, lambda: messagebox.showerror(S('error_title'), error_msg))
            logger.error(f"Image load error: {ex}")
        except ConfigurationError as ex:
            self.root.after(0, self._reset_progress)
            error_msg = f"配置错误：{ex.message}\n请检查程序配置文件。"
            self.update_status(f"{S('processing_failed')}{error_msg}")
            self.root.after(0, lambda: messagebox.showerror(S('error_title'), error_msg))
            logger.error(f"Configuration error: {ex}")
        except IDCardProcessorError as ex:
            self.root.after(0, self._reset_progress)
            self.update_status(f"{S('processing_failed')}{str(ex)}")
            self.root.after(0, lambda: messagebox.showerror(S('error_title'), str(ex)))
            logger.error(f"Processing error: {ex}")
        except Exception as ex:
            self.root.after(0, self._reset_progress)
            error_msg = f"未知错误：{str(ex)}\n请查看日志获取详细信息。"
            self.update_status(f"{S('processing_failed')}{error_msg}")
            self.root.after(0, lambda: messagebox.showerror(S('error_title'), error_msg))
            logger.exception(f"Unexpected error: {ex}")
        finally:
            self.root.after(0, lambda: self.btn_start.config(state='normal'))

    def on_closing(self):
        if self._progress_id:
            self.root.after_cancel(self._progress_id)
        self.root.destroy()
        sys.exit(0)


if __name__ == "__main__":
    root = tk.Tk()
    app = IDCardApp(root)
    root.protocol("WM_DELETE_WINDOW", app.on_closing)

    if "--screenshot" in sys.argv:
        import time as _t
        from PIL import ImageGrab

        idx = sys.argv.index("--screenshot")
        mode = sys.argv[idx + 1] if idx + 1 < len(sys.argv) else "1"
        desk = os.environ["USERPROFILE"] + r"\Desktop"

        def _do_screenshot():
            root.update_idletasks()
            root.update()
            _t.sleep(1)
            root.update_idletasks()
            root.update()
            l, t, w, h = root.winfo_x(), root.winfo_y(), root.winfo_width(), root.winfo_height()
            print(f"Window: {l},{t} {w}x{h}", flush=True)

            if mode == "1":
                img = ImageGrab.grab(bbox=(l, t, l + w, t + h))
                img.save(desk + r"\Screenshot1_main.png")
            elif mode == "2":
                app.show_watermark_dialog()
                root.update()
                _t.sleep(0.5)
                root.update()
                img = ImageGrab.grab(bbox=(l, t, l + w, t + h))
                img.save(desk + r"\Screenshot2_watermark.png")
            elif mode == "3":
                app.show_help()
                root.update()
                _t.sleep(0.5)
                root.update()
                img = ImageGrab.grab(bbox=(l, t, l + w, t + h))
                img.save(desk + r"\Screenshot3_help.png")
            elif mode == "4":
                app._switch_lang("en")
                root.update()
                _t.sleep(0.3)
                root.update()
                img = ImageGrab.grab(bbox=(l, t, l + w, t + h))
                img.save(desk + r"\Screenshot4_english.png")

            root.after(500, root.destroy)

        root.after(1500, _do_screenshot)
        root.mainloop()
        sys.exit(0)

    root.mainloop()
