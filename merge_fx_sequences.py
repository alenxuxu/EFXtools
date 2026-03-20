#!/usr/bin/env python3
import argparse
import importlib
import math
import os
import re
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from PIL import Image, ImageColor, ImageTk

try:
    _tkdnd = importlib.import_module("tkinterdnd2")
    DND_FILES = _tkdnd.DND_FILES
    BaseTk = _tkdnd.TkinterDnD.Tk
    HAS_DND = True
except Exception:
    DND_FILES = None
    BaseTk = tk.Tk
    HAS_DND = False


def natural_key(text: str):
    return [
        int(part) if part.isdigit() else part.lower()
        for part in re.split(r"(\d+)", text)
    ]


def list_pngs_from_folder(folder: str):
    files = []
    for name in os.listdir(folder):
        if name.lower().endswith(".png"):
            files.append(os.path.join(folder, name))
    files.sort(key=lambda p: natural_key(os.path.basename(p)))
    return files


SUPPORTED_IMAGE_EXTS = {
    ".png",
    ".jpg",
    ".jpeg",
    ".webp",
    ".bmp",
    ".tif",
    ".tiff",
}


def is_supported_image_file(path: str):
    return (
        os.path.isfile(path)
        and os.path.splitext(path)[1].lower() in SUPPORTED_IMAGE_EXTS
    )


def list_images_from_folder(folder: str):
    files = []
    for name in os.listdir(folder):
        p = os.path.join(folder, name)
        if is_supported_image_file(p):
            files.append(p)
    files.sort(key=lambda p: natural_key(os.path.basename(p)))
    return files


def parse_bg_color(color: str):
    try:
        return ImageColor.getrgb(color)
    except ValueError:
        raise ValueError(f"无效颜色: {color}，示例: #000000 或 white")


def compute_grid(count: int, columns: int, rows: int):
    if count <= 0:
        raise ValueError("没有可合并的图片")

    if columns > 0 and rows > 0:
        if columns * rows < count:
            raise ValueError("网格太小，容纳不下所有图片")
        return columns, rows

    if columns > 0:
        rows = math.ceil(count / columns)
        return columns, rows

    if rows > 0:
        columns = math.ceil(count / rows)
        return columns, rows

    columns = math.ceil(math.sqrt(count))
    rows = math.ceil(count / columns)
    return columns, rows


def merge_images(
    image_paths,
    output_path,
    columns=0,
    rows=0,
    spacing=0,
    margin=0,
    bg_color="#000000",
    force_cell_width=0,
    force_cell_height=0,
):
    if not image_paths:
        raise ValueError("没有输入图片")

    rgb = parse_bg_color(bg_color)
    images = [Image.open(p).convert("RGBA") for p in image_paths]

    try:
        cols, rws = compute_grid(len(images), columns, rows)
        cell_w = (
            force_cell_width if force_cell_width > 0 else max(im.width for im in images)
        )
        cell_h = (
            force_cell_height
            if force_cell_height > 0
            else max(im.height for im in images)
        )

        out_w = margin * 2 + cols * cell_w + (cols - 1) * spacing
        out_h = margin * 2 + rws * cell_h + (rws - 1) * spacing
        canvas = Image.new("RGBA", (out_w, out_h), rgb + (255,))

        for idx, im in enumerate(images):
            r = idx // cols
            c = idx % cols
            x = margin + c * (cell_w + spacing)
            y = margin + r * (cell_h + spacing)
            paste_x = x + (cell_w - im.width) // 2
            paste_y = y + (cell_h - im.height) // 2
            canvas.alpha_composite(im, (paste_x, paste_y))

        ext = os.path.splitext(output_path)[1].lower()
        if ext in {".jpg", ".jpeg"}:
            canvas = canvas.convert("RGB")

        out_dir = os.path.dirname(output_path)
        if out_dir:
            os.makedirs(out_dir, exist_ok=True)
        canvas.save(output_path)
    finally:
        for im in images:
            im.close()


def split_image_to_grid(
    input_path,
    output_dir,
    columns,
    rows,
    spacing=0,
    margin=0,
    spacing_x=None,
    spacing_y=None,
    margin_x=None,
    margin_y=None,
    cell_width=0,
    cell_height=0,
    prefix="frame",
    start_index=1,
):
    if columns <= 0 or rows <= 0:
        raise ValueError("拆分模式下，列数和行数都必须 > 0")

    sx = spacing if spacing_x is None else spacing_x
    sy = spacing if spacing_y is None else spacing_y
    mx = margin if margin_x is None else margin_x
    my = margin if margin_y is None else margin_y

    with Image.open(input_path).convert("RGBA") as src:
        img_w, img_h = src.size

        usable_w = img_w - mx * 2 - (columns - 1) * sx
        usable_h = img_h - my * 2 - (rows - 1) * sy
        if usable_w <= 0 or usable_h <= 0:
            raise ValueError("边距/间距过大，导致无可拆分区域")

        if cell_width > 0:
            cw = cell_width
        else:
            if usable_w % columns != 0:
                raise ValueError(
                    f"图片宽度无法均分为 {columns} 列。可设置 --cell-width，或调整边距/间距/列数"
                )
            cw = usable_w // columns

        if cell_height > 0:
            ch = cell_height
        else:
            if usable_h % rows != 0:
                raise ValueError(
                    f"图片高度无法均分为 {rows} 行。可设置 --cell-height，或调整边距/间距/行数"
                )
            ch = usable_h // rows

        need_w = mx * 2 + columns * cw + (columns - 1) * sx
        need_h = my * 2 + rows * ch + (rows - 1) * sy
        if need_w > img_w or need_h > img_h:
            raise ValueError("网格尺寸超过原图范围，请减小格子宽高/边距/间距")

        os.makedirs(output_dir, exist_ok=True)

        index = start_index
        for r in range(rows):
            for c in range(columns):
                x = mx + c * (cw + sx)
                y = my + r * (ch + sy)
                piece = src.crop((x, y, x + cw, y + ch))
                out_name = f"{prefix}_{index:04d}.png"
                piece.save(os.path.join(output_dir, out_name))
                index += 1

        return rows * columns


def batch_resize_convert_images(
    image_paths,
    output_dir,
    target_width=0,
    target_height=0,
    output_format="png",
    jpg_quality=95,
):
    if not image_paths:
        raise ValueError("没有输入图片")
    if target_width < 0 or target_height < 0:
        raise ValueError("目标宽高必须 >= 0")
    if jpg_quality < 1 or jpg_quality > 100:
        raise ValueError("JPG质量需要在 1-100 之间")

    fmt = output_format.lower()
    if fmt not in {"png", "jpg", "webp"}:
        raise ValueError("输出格式仅支持 png / jpg / webp")

    os.makedirs(output_dir, exist_ok=True)
    written = 0
    name_used = {}

    for src_path in image_paths:
        if not is_supported_image_file(src_path):
            continue

        with Image.open(src_path) as im:
            ow, oh = im.size

            if target_width > 0 and target_height > 0:
                nw, nh = target_width, target_height
            elif target_width > 0:
                nw = target_width
                nh = max(1, int(round(oh * target_width / ow)))
            elif target_height > 0:
                nh = target_height
                nw = max(1, int(round(ow * target_height / oh)))
            else:
                nw, nh = ow, oh

            out_im = (
                im.resize((nw, nh), Image.Resampling.LANCZOS)
                if (nw, nh) != (ow, oh)
                else im.copy()
            )

            stem = os.path.splitext(os.path.basename(src_path))[0]
            idx = name_used.get(stem, 0)
            name_used[stem] = idx + 1
            if idx == 0:
                out_stem = stem
            else:
                out_stem = f"{stem}_{idx:02d}"

            ext = ".jpg" if fmt == "jpg" else f".{fmt}"
            out_path = os.path.join(output_dir, f"{out_stem}{ext}")

            while os.path.exists(out_path):
                name_used[stem] += 1
                out_stem = f"{stem}_{name_used[stem] - 1:02d}"
                out_path = os.path.join(output_dir, f"{out_stem}{ext}")

            if fmt == "jpg":
                if out_im.mode in ("RGBA", "LA"):
                    bg = Image.new("RGB", out_im.size, (0, 0, 0))
                    bg.paste(out_im, mask=out_im.split()[-1])
                    bg.save(out_path, quality=jpg_quality)
                else:
                    out_im.convert("RGB").save(out_path, quality=jpg_quality)
            elif fmt == "webp":
                out_im.save(out_path, quality=jpg_quality)
            else:
                out_im.save(out_path)

            written += 1

    if written == 0:
        raise ValueError("没有可处理的图片，请检查文件格式")
    return written


def extract_video_to_sequence(
    input_path,
    output_dir,
    prefix="frame",
    start_index=1,
    frame_step=1,
    target_fps=0.0,
    start_sec=0.0,
    end_sec=0.0,
    image_format="png",
    jpg_quality=95,
):
    try:
        import imageio.v3 as iio
    except Exception as exc:
        raise RuntimeError(
            "缺少 imageio 依赖，请先执行: python -m pip install -r requirements.txt"
        ) from exc

    if frame_step <= 0:
        raise ValueError("抽帧步长必须 > 0")
    if target_fps < 0:
        raise ValueError("目标导出帧率必须 >= 0")
    if start_index < 0:
        raise ValueError("起始编号必须 >= 0")
    if start_sec < 0 or end_sec < 0:
        raise ValueError("起止时间必须 >= 0")
    if end_sec > 0 and end_sec < start_sec:
        raise ValueError("结束时间不能小于开始时间")

    fmt = image_format.lower()
    if fmt not in {"png", "jpg"}:
        raise ValueError("输出格式仅支持 png 或 jpg")

    meta = iio.immeta(input_path)
    fps = meta.get("fps", 0)
    if not fps:
        fps = 30

    start_frame = int(start_sec * fps)
    end_frame = int(end_sec * fps) if end_sec > 0 else None

    os.makedirs(output_dir, exist_ok=True)

    written = 0
    frame_index = 0
    seq_index = start_index
    frame_interval = 1.0
    next_pick = float(start_frame)

    use_target_fps = target_fps > 0
    if use_target_fps:
        if target_fps >= fps:
            use_target_fps = False
            frame_step = 1
        else:
            frame_interval = fps / target_fps
            next_pick = float(start_frame)

    for frame in iio.imiter(input_path):
        if frame_index < start_frame:
            frame_index += 1
            continue

        if end_frame is not None and frame_index > end_frame:
            break

        should_export = False
        if use_target_fps:
            if frame_index + 1e-9 >= next_pick:
                should_export = True
                next_pick += frame_interval
        elif (frame_index - start_frame) % frame_step == 0:
            should_export = True

        if should_export:
            img = Image.fromarray(frame)
            ext = ".png" if fmt == "png" else ".jpg"
            out_name = f"{prefix}_{seq_index:04d}{ext}"
            out_path = os.path.join(output_dir, out_name)
            if fmt == "jpg":
                img.convert("RGB").save(out_path, quality=jpg_quality)
            else:
                img.save(out_path)
            written += 1
            seq_index += 1

        frame_index += 1

    if written == 0:
        raise ValueError("没有导出任何帧，请检查时间范围或步长设置")

    export_fps = min(target_fps, fps) if target_fps > 0 else fps / max(frame_step, 1)
    return written, fps, export_fps


class App(BaseTk):  # type: ignore[misc, valid-type]
    def __init__(self):
        super().__init__()
        self.title("特效序列图工具（合并/拆分/视频抽帧/批量改图）")
        self.geometry("780x620")
        self.minsize(740, 580)
        self.dnd_bind_ok = False

        self.image_paths = []

        self.columns_var = tk.StringVar(value="0")
        self.rows_var = tk.StringVar(value="0")
        self.spacing_var = tk.StringVar(value="0")
        self.margin_var = tk.StringVar(value="0")
        self.bg_var = tk.StringVar(value="#000000")
        self.cell_w_var = tk.StringVar(value="0")
        self.cell_h_var = tk.StringVar(value="0")
        self.output_var = tk.StringVar(value="output/merged.png")

        self.split_input_var = tk.StringVar(value="")
        self.split_columns_var = tk.StringVar(value="4")
        self.split_rows_var = tk.StringVar(value="4")
        self.split_spacing_var = tk.StringVar(value="0")
        self.split_margin_var = tk.StringVar(value="0")
        self.split_spacing_x_var = tk.StringVar(value="0")
        self.split_spacing_y_var = tk.StringVar(value="0")
        self.split_margin_x_var = tk.StringVar(value="0")
        self.split_margin_y_var = tk.StringVar(value="0")
        self.split_cell_w_var = tk.StringVar(value="0")
        self.split_cell_h_var = tk.StringVar(value="0")
        self.split_out_dir_var = tk.StringVar(value="output/splits")
        self.split_prefix_var = tk.StringVar(value="frame")
        self.split_start_index_var = tk.StringVar(value="1")
        self.split_preview_image = None

        self.video_input_var = tk.StringVar(value="")
        self.video_out_dir_var = tk.StringVar(value="output/video_frames")
        self.video_prefix_var = tk.StringVar(value="frame")
        self.video_start_index_var = tk.StringVar(value="1")
        self.video_step_var = tk.StringVar(value="1")
        self.video_fps_mode_var = tk.StringVar(value="源帧率")
        self.video_start_sec_var = tk.StringVar(value="0")
        self.video_end_sec_var = tk.StringVar(value="0")
        self.video_format_var = tk.StringVar(value="png")
        self.video_jpg_quality_var = tk.StringVar(value="95")

        self.convert_paths = []
        self.convert_w_var = tk.StringVar(value="0")
        self.convert_h_var = tk.StringVar(value="0")
        self.convert_format_var = tk.StringVar(value="png")
        self.convert_quality_var = tk.StringVar(value="95")
        self.convert_out_dir_var = tk.StringVar(value="output/converted")

        self._build_ui()

        for var in (
            self.split_input_var,
            self.split_columns_var,
            self.split_rows_var,
            self.split_spacing_var,
            self.split_margin_var,
            self.split_spacing_x_var,
            self.split_spacing_y_var,
            self.split_margin_x_var,
            self.split_margin_y_var,
            self.split_cell_w_var,
            self.split_cell_h_var,
        ):
            var.trace_add("write", self._on_split_params_change)

    def _build_ui(self):
        root = ttk.Frame(self, padding=12)
        root.pack(fill="both", expand=True)

        note = ttk.Notebook(root)
        note.pack(fill="both", expand=True)

        merge_tab = ttk.Frame(note, padding=10)
        split_tab = ttk.Frame(note, padding=10)
        video_tab = ttk.Frame(note, padding=10)
        convert_tab = ttk.Frame(note, padding=10)
        note.add(merge_tab, text="合并多图")
        note.add(split_tab, text="单图拆分")
        note.add(video_tab, text="视频转序列图")
        note.add(convert_tab, text="批量改尺寸格式")

        self._build_merge_tab(merge_tab)
        self._build_split_tab(split_tab)
        self._build_video_tab(video_tab)
        self._build_convert_tab(convert_tab)

        if HAS_DND and self.dnd_bind_ok:
            drag_tip = "拖拽已启用: 可直接把图片/视频拖到对应输入区域。"
        elif HAS_DND and not self.dnd_bind_ok:
            drag_tip = (
                "检测到 tkinterdnd2，但拖拽注册失败。可重启程序或重装 tkinterdnd2。"
            )
        else:
            drag_tip = "未安装 tkinterdnd2，当前不可拖拽。安装: python -m pip install tkinterdnd2"

        ttk.Label(root, text=drag_tip, foreground="#666666").pack(
            anchor="w", pady=(8, 0)
        )

    def _build_merge_tab(self, frm):
        btns = ttk.Frame(frm)
        btns.pack(fill="x")

        ttk.Button(btns, text="选择PNG文件", command=self.pick_files).pack(side="left")
        ttk.Button(btns, text="选择文件夹", command=self.pick_folder).pack(
            side="left", padx=8
        )
        ttk.Button(btns, text="清空列表", command=self.clear_files).pack(side="left")

        self.count_label = ttk.Label(btns, text="已选 0 张")
        self.count_label.pack(side="right")

        ttk.Label(frm, text="文件顺序（按自然排序）:").pack(anchor="w", pady=(10, 4))
        self.listbox = tk.Listbox(frm, height=12)
        self.listbox.pack(fill="both", expand=True)
        self._bind_drop_target(self.listbox, self.on_drop_merge_files)

        grid = ttk.Frame(frm)
        grid.pack(fill="x", pady=10)
        self._labeled_entry(grid, "列数(0=自动)", self.columns_var, 0, 0)
        self._labeled_entry(grid, "行数(0=自动)", self.rows_var, 0, 1)
        self._labeled_entry(grid, "间距(px)", self.spacing_var, 0, 2)
        self._labeled_entry(grid, "外边距(px)", self.margin_var, 0, 3)
        self._labeled_entry(grid, "背景色", self.bg_var, 1, 0)
        self._labeled_entry(grid, "格子宽(0=最大图宽)", self.cell_w_var, 1, 1)
        self._labeled_entry(grid, "格子高(0=最大图高)", self.cell_h_var, 1, 2)

        out_row = ttk.Frame(frm)
        out_row.pack(fill="x", pady=(4, 10))
        ttk.Label(out_row, text="输出路径").pack(side="left")
        ttk.Entry(out_row, textvariable=self.output_var).pack(
            side="left", fill="x", expand=True, padx=8
        )
        ttk.Button(out_row, text="浏览", command=self.pick_output).pack(side="left")

        ttk.Button(frm, text="一键合并", command=self.on_merge).pack(fill="x", ipady=6)

        tips = (
            "说明: 列和行都填0时自动计算网格；只填其中一个时另一个自动补齐。\n"
            "若图片尺寸不一致，会在各自格子内居中对齐。"
        )
        ttk.Label(frm, text=tips, foreground="#666666").pack(anchor="w", pady=(10, 0))

    def _build_split_tab(self, frm):
        in_row = ttk.Frame(frm)
        in_row.pack(fill="x")
        ttk.Label(in_row, text="输入大图").pack(side="left")
        split_entry = ttk.Entry(in_row, textvariable=self.split_input_var)
        split_entry.pack(side="left", fill="x", expand=True, padx=8)
        self._bind_drop_target(split_entry, self.on_drop_split_input)
        ttk.Button(in_row, text="浏览", command=self.pick_split_input).pack(side="left")

        grid = ttk.Frame(frm)
        grid.pack(fill="x", pady=10)
        self._labeled_entry(grid, "列数(>0)", self.split_columns_var, 0, 0)
        self._labeled_entry(grid, "行数(>0)", self.split_rows_var, 0, 1)
        self._labeled_entry(grid, "间距(统一,兼容)", self.split_spacing_var, 0, 2)
        self._labeled_entry(grid, "外边距(统一,兼容)", self.split_margin_var, 0, 3)
        self._labeled_entry(grid, "水平间距X(px)", self.split_spacing_x_var, 1, 0)
        self._labeled_entry(grid, "垂直间距Y(px)", self.split_spacing_y_var, 1, 1)
        self._labeled_entry(grid, "水平边距X(px)", self.split_margin_x_var, 1, 2)
        self._labeled_entry(grid, "垂直边距Y(px)", self.split_margin_y_var, 1, 3)
        self._labeled_entry(grid, "格子宽(0=自动均分)", self.split_cell_w_var, 2, 0)
        self._labeled_entry(grid, "格子高(0=自动均分)", self.split_cell_h_var, 2, 1)
        self._labeled_entry(grid, "文件名前缀", self.split_prefix_var, 2, 2)
        self._labeled_entry(grid, "起始编号", self.split_start_index_var, 2, 3)

        pre_btn_row = ttk.Frame(frm)
        pre_btn_row.pack(fill="x", pady=(2, 6))
        ttk.Button(
            pre_btn_row, text="刷新网格预览", command=self.refresh_split_preview
        ).pack(side="left")

        self.split_preview_canvas = tk.Canvas(
            frm,
            height=240,
            background="#1b1b1b",
            highlightthickness=1,
            highlightbackground="#3a3a3a",
        )
        self.split_preview_canvas.pack(fill="x", pady=(0, 8))

        out_row = ttk.Frame(frm)
        out_row.pack(fill="x", pady=(4, 10))
        ttk.Label(out_row, text="输出文件夹").pack(side="left")
        ttk.Entry(out_row, textvariable=self.split_out_dir_var).pack(
            side="left", fill="x", expand=True, padx=8
        )
        ttk.Button(out_row, text="浏览", command=self.pick_split_output_dir).pack(
            side="left"
        )

        ttk.Button(frm, text="一键拆分", command=self.on_split).pack(fill="x", ipady=6)

        tips = (
            "说明: 拆分会按行优先导出，文件名形如 frame_0001.png。\n"
            "支持 X/Y 不同间距和边距；若格子宽高为0，则按可用区域均分；不能整除时会报错提醒。"
        )
        ttk.Label(frm, text=tips, foreground="#666666").pack(anchor="w", pady=(10, 0))
        frm.after(50, self.refresh_split_preview)

    def _build_video_tab(self, frm):
        in_row = ttk.Frame(frm)
        in_row.pack(fill="x")
        ttk.Label(in_row, text="输入视频").pack(side="left")
        video_entry = ttk.Entry(in_row, textvariable=self.video_input_var)
        video_entry.pack(side="left", fill="x", expand=True, padx=8)
        self._bind_drop_target(video_entry, self.on_drop_video_input)
        ttk.Button(in_row, text="浏览", command=self.pick_video_input).pack(side="left")

        grid = ttk.Frame(frm)
        grid.pack(fill="x", pady=10)
        self._labeled_entry(grid, "抽帧步长(1=每帧)", self.video_step_var, 0, 0)
        self._labeled_entry(grid, "开始秒(>=0)", self.video_start_sec_var, 0, 1)
        self._labeled_entry(grid, "结束秒(0=到末尾)", self.video_end_sec_var, 0, 2)
        self._labeled_entry(grid, "文件名前缀", self.video_prefix_var, 0, 3)
        self._labeled_entry(grid, "起始编号", self.video_start_index_var, 1, 0)
        self._labeled_entry(grid, "JPG质量(1-100)", self.video_jpg_quality_var, 1, 1)

        fps_box = ttk.Frame(grid)
        fps_box.grid(row=1, column=2, sticky="ew", padx=4, pady=4)
        ttk.Label(fps_box, text="导出帧率").pack(anchor="w")
        fps_combo = ttk.Combobox(
            fps_box,
            state="readonly",
            values=["源帧率", "30", "12"],
            textvariable=self.video_fps_mode_var,
        )
        fps_combo.pack(fill="x")

        fmt_box = ttk.Frame(grid)
        fmt_box.grid(row=1, column=3, sticky="ew", padx=4, pady=4)
        ttk.Label(fmt_box, text="输出格式").pack(anchor="w")
        fmt_combo = ttk.Combobox(
            fmt_box,
            state="readonly",
            values=["png", "jpg"],
            textvariable=self.video_format_var,
        )
        fmt_combo.pack(fill="x")

        out_row = ttk.Frame(frm)
        out_row.pack(fill="x", pady=(4, 10))
        ttk.Label(out_row, text="输出文件夹").pack(side="left")
        ttk.Entry(out_row, textvariable=self.video_out_dir_var).pack(
            side="left", fill="x", expand=True, padx=8
        )
        ttk.Button(out_row, text="浏览", command=self.pick_video_output_dir).pack(
            side="left"
        )

        ttk.Button(frm, text="一键导出序列图", command=self.on_video_extract).pack(
            fill="x", ipady=6
        )

        tips = (
            "说明: 导出帧率可选源帧率/30/12；若选30或12，则优先按目标FPS抽帧。\n"
            "当导出帧率为源帧率时，抽帧步长=1 表示每一帧都导出；=2 表示每隔1帧导出。\n"
            "时间范围按秒，结束秒填0表示导出到视频末尾。"
        )
        ttk.Label(frm, text=tips, foreground="#666666").pack(anchor="w", pady=(10, 0))

    def _build_convert_tab(self, frm):
        btns = ttk.Frame(frm)
        btns.pack(fill="x")

        ttk.Button(btns, text="选择图片文件", command=self.pick_convert_files).pack(
            side="left"
        )
        ttk.Button(btns, text="选择文件夹", command=self.pick_convert_folder).pack(
            side="left", padx=8
        )
        ttk.Button(btns, text="清空列表", command=self.clear_convert_files).pack(
            side="left"
        )

        self.convert_count_label = ttk.Label(btns, text="已选 0 张")
        self.convert_count_label.pack(side="right")

        ttk.Label(frm, text="可处理文件（支持拖拽图片/文件夹）:").pack(
            anchor="w", pady=(10, 4)
        )
        self.convert_listbox = tk.Listbox(frm, height=12)
        self.convert_listbox.pack(fill="both", expand=True)
        self._bind_drop_target(self.convert_listbox, self.on_drop_convert_files)

        grid = ttk.Frame(frm)
        grid.pack(fill="x", pady=10)
        self._labeled_entry(grid, "目标宽(0=按比例)", self.convert_w_var, 0, 0)
        self._labeled_entry(grid, "目标高(0=按比例)", self.convert_h_var, 0, 1)
        self._labeled_entry(grid, "质量(1-100)", self.convert_quality_var, 0, 2)

        fmt_box = ttk.Frame(grid)
        fmt_box.grid(row=0, column=3, sticky="ew", padx=4, pady=4)
        ttk.Label(fmt_box, text="输出格式").pack(anchor="w")
        fmt_combo = ttk.Combobox(
            fmt_box,
            state="readonly",
            values=["png", "jpg", "webp"],
            textvariable=self.convert_format_var,
        )
        fmt_combo.pack(fill="x")
        grid.grid_columnconfigure(3, weight=1)

        out_row = ttk.Frame(frm)
        out_row.pack(fill="x", pady=(4, 10))
        ttk.Label(out_row, text="输出文件夹").pack(side="left")
        ttk.Entry(out_row, textvariable=self.convert_out_dir_var).pack(
            side="left", fill="x", expand=True, padx=8
        )
        ttk.Button(out_row, text="浏览", command=self.pick_convert_output_dir).pack(
            side="left"
        )

        ttk.Button(frm, text="一键批量处理", command=self.on_convert_batch).pack(
            fill="x", ipady=6
        )

        tips = (
            "说明: 宽高都填0时仅改格式；只填一个时按比例缩放；都填写时强制缩放到目标尺寸。\n"
            "输出文件默认保持原文件名，重名会自动追加序号。"
        )
        ttk.Label(frm, text=tips, foreground="#666666").pack(anchor="w", pady=(10, 0))

    def _labeled_entry(self, parent, label, var, row, col):
        box = ttk.Frame(parent)
        box.grid(row=row, column=col, sticky="ew", padx=4, pady=4)
        ttk.Label(box, text=label).pack(anchor="w")
        ttk.Entry(box, textvariable=var).pack(fill="x")
        parent.grid_columnconfigure(col, weight=1)

    def _bind_drop_target(self, widget, handler):
        if not HAS_DND:
            return
        try:
            widget.drop_target_register(DND_FILES)
            widget.dnd_bind("<<Drop>>", handler)
            self.dnd_bind_ok = True
        except Exception:
            pass

    def _parse_drop_paths(self, data):
        if not data:
            return []
        try:
            raw = list(self.tk.splitlist(data))
        except Exception:
            raw = [data]

        paths = []
        for item in raw:
            p = item.strip().strip('"')
            if p.startswith("{") and p.endswith("}"):
                p = p[1:-1]
            if p:
                paths.append(p)
        return paths

    def on_drop_merge_files(self, event):
        paths = self._parse_drop_paths(getattr(event, "data", ""))
        if not paths:
            return

        collected = []
        for p in paths:
            if os.path.isdir(p):
                collected.extend(list_pngs_from_folder(p))
            elif os.path.isfile(p) and p.lower().endswith(".png"):
                collected.append(p)

        if not collected:
            messagebox.showwarning("提示", "请拖入 PNG 文件或包含 PNG 的文件夹")
            return

        merged = set(self.image_paths)
        merged.update(collected)
        self.image_paths = sorted(merged, key=natural_key)
        self.refresh_list()

    def on_drop_split_input(self, event):
        paths = self._parse_drop_paths(getattr(event, "data", ""))
        if not paths:
            return
        p = paths[0]
        if os.path.isfile(p) and p.lower().endswith(".png"):
            self.split_input_var.set(p)
            self.refresh_split_preview()
        else:
            messagebox.showwarning("提示", "拆分输入请拖入单个 PNG 文件")

    def on_drop_video_input(self, event):
        paths = self._parse_drop_paths(getattr(event, "data", ""))
        if not paths:
            return
        p = paths[0]
        video_exts = {".mp4", ".mov", ".avi", ".mkv", ".webm", ".wmv", ".m4v"}
        if os.path.isfile(p) and os.path.splitext(p)[1].lower() in video_exts:
            self.video_input_var.set(p)
        else:
            messagebox.showwarning("提示", "请拖入视频文件（mp4/mov/avi/mkv/webm/wmv）")

    def on_drop_convert_files(self, event):
        paths = self._parse_drop_paths(getattr(event, "data", ""))
        if not paths:
            return

        collected = []
        for p in paths:
            if os.path.isdir(p):
                collected.extend(list_images_from_folder(p))
            elif is_supported_image_file(p):
                collected.append(p)

        if not collected:
            messagebox.showwarning("提示", "请拖入图片文件或包含图片的文件夹")
            return

        merged = set(self.convert_paths)
        merged.update(collected)
        self.convert_paths = sorted(merged, key=natural_key)
        self.refresh_convert_list()

    @staticmethod
    def _to_int(s, name):
        try:
            v = int(s)
            if v < 0:
                raise ValueError
            return v
        except ValueError:
            raise ValueError(f"{name} 需要是 >= 0 的整数")

    @staticmethod
    def _to_float(s, name):
        try:
            v = float(s)
            if v < 0:
                raise ValueError
            return v
        except ValueError:
            raise ValueError(f"{name} 需要是 >= 0 的数字")

    def _video_target_fps(self):
        mode = (self.video_fps_mode_var.get() or "").strip()
        if mode in {"30", "12"}:
            return float(mode)
        return 0.0

    def _on_split_params_change(self, *_):
        self.after(50, self.refresh_split_preview)

    def _get_split_params(self):
        columns = self._to_int(self.split_columns_var.get().strip(), "列数")
        rows = self._to_int(self.split_rows_var.get().strip(), "行数")
        if columns <= 0 or rows <= 0:
            raise ValueError("拆分模式下，列数和行数都必须 > 0")

        spacing = self._to_int(self.split_spacing_var.get().strip(), "间距")
        margin = self._to_int(self.split_margin_var.get().strip(), "外边距")
        spacing_x = self._to_int(self.split_spacing_x_var.get().strip(), "水平间距X")
        spacing_y = self._to_int(self.split_spacing_y_var.get().strip(), "垂直间距Y")
        margin_x = self._to_int(self.split_margin_x_var.get().strip(), "水平边距X")
        margin_y = self._to_int(self.split_margin_y_var.get().strip(), "垂直边距Y")
        cell_w = self._to_int(self.split_cell_w_var.get().strip(), "格子宽")
        cell_h = self._to_int(self.split_cell_h_var.get().strip(), "格子高")
        start_index = self._to_int(self.split_start_index_var.get().strip(), "起始编号")

        return {
            "columns": columns,
            "rows": rows,
            "spacing": spacing,
            "margin": margin,
            "spacing_x": spacing_x,
            "spacing_y": spacing_y,
            "margin_x": margin_x,
            "margin_y": margin_y,
            "cell_w": cell_w,
            "cell_h": cell_h,
            "start_index": start_index,
        }

    def refresh_split_preview(self):
        canvas = self.split_preview_canvas
        canvas.delete("all")
        input_path = self.split_input_var.get().strip()
        if not input_path or not os.path.isfile(input_path):
            canvas.create_text(
                12,
                12,
                anchor="nw",
                fill="#cfcfcf",
                text="请选择要拆分的 PNG，然后点 刷新网格预览",
            )
            return

        try:
            p = self._get_split_params()
            sx = p["spacing"] if p["spacing_x"] == 0 else p["spacing_x"]
            sy = p["spacing"] if p["spacing_y"] == 0 else p["spacing_y"]
            mx = p["margin"] if p["margin_x"] == 0 else p["margin_x"]
            my = p["margin"] if p["margin_y"] == 0 else p["margin_y"]

            with Image.open(input_path).convert("RGB") as src:
                iw, ih = src.size
                cw = max(10, int(canvas.winfo_width() or 700))
                ch = max(10, int(canvas.winfo_height() or 240))
                pad = 8
                scale = min((cw - pad * 2) / iw, (ch - pad * 2) / ih)
                scale = max(scale, 0.01)

                pw = max(1, int(iw * scale))
                ph = max(1, int(ih * scale))
                preview = src.resize((pw, ph), Image.Resampling.BILINEAR)
                self.split_preview_image = ImageTk.PhotoImage(preview)
                ox = (cw - pw) // 2
                oy = (ch - ph) // 2
                canvas.create_image(ox, oy, image=self.split_preview_image, anchor="nw")

                usable_w = iw - mx * 2 - (p["columns"] - 1) * sx
                usable_h = ih - my * 2 - (p["rows"] - 1) * sy
                if usable_w <= 0 or usable_h <= 0:
                    raise ValueError("边距/间距过大")

                if p["cell_w"] > 0:
                    gw = p["cell_w"]
                else:
                    if usable_w % p["columns"] != 0:
                        raise ValueError("宽度不能整除列数")
                    gw = usable_w // p["columns"]

                if p["cell_h"] > 0:
                    gh = p["cell_h"]
                else:
                    if usable_h % p["rows"] != 0:
                        raise ValueError("高度不能整除行数")
                    gh = usable_h // p["rows"]

                total_w = mx * 2 + p["columns"] * gw + (p["columns"] - 1) * sx
                total_h = my * 2 + p["rows"] * gh + (p["rows"] - 1) * sy
                if total_w > iw or total_h > ih:
                    raise ValueError("网格超出图片范围")

                l = ox + mx * scale
                t = oy + my * scale
                r = ox + (mx + p["columns"] * gw + (p["columns"] - 1) * sx) * scale
                b = oy + (my + p["rows"] * gh + (p["rows"] - 1) * sy) * scale
                canvas.create_rectangle(l, t, r, b, outline="#00ff66", width=2)

                for c in range(1, p["columns"]):
                    x = ox + (mx + c * gw + (c - 1) * sx) * scale
                    canvas.create_line(x, t, x, b, fill="#00ff66", width=1)
                for rr in range(1, p["rows"]):
                    y = oy + (my + rr * gh + (rr - 1) * sy) * scale
                    canvas.create_line(l, y, r, y, fill="#00ff66", width=1)

                info = (
                    f"预览 {p['columns']}x{p['rows']}  cell={gw}x{gh}  "
                    f"space=({sx},{sy})  margin=({mx},{my})"
                )
                canvas.create_text(10, ch - 8, anchor="sw", fill="#e8e8e8", text=info)
        except Exception as e:
            canvas.create_text(
                12, 12, anchor="nw", fill="#ff7a7a", text=f"预览参数错误: {e}"
            )

    def refresh_list(self):
        self.listbox.delete(0, tk.END)
        for p in self.image_paths:
            self.listbox.insert(tk.END, p)
        self.count_label.config(text=f"已选 {len(self.image_paths)} 张")

    def refresh_convert_list(self):
        self.convert_listbox.delete(0, tk.END)
        for p in self.convert_paths:
            self.convert_listbox.insert(tk.END, p)
        self.convert_count_label.config(text=f"已选 {len(self.convert_paths)} 张")

    def pick_files(self):
        files = filedialog.askopenfilenames(
            title="选择PNG文件",
            filetypes=[("PNG images", "*.png"), ("All files", "*.*")],
        )
        if not files:
            return
        self.image_paths = sorted(list(files), key=natural_key)
        self.refresh_list()

    def pick_folder(self):
        folder = filedialog.askdirectory(title="选择包含PNG序列图的文件夹")
        if not folder:
            return
        self.image_paths = list_pngs_from_folder(folder)
        self.refresh_list()

    def clear_files(self):
        self.image_paths = []
        self.refresh_list()

    def pick_output(self):
        path = filedialog.asksaveasfilename(
            title="保存输出图片",
            defaultextension=".png",
            filetypes=[("PNG image", "*.png"), ("JPEG image", "*.jpg;*.jpeg")],
        )
        if path:
            self.output_var.set(path)

    def pick_split_input(self):
        path = filedialog.askopenfilename(
            title="选择要拆分的大图",
            filetypes=[("PNG image", "*.png"), ("All files", "*.*")],
        )
        if path:
            self.split_input_var.set(path)
            self.refresh_split_preview()

    def pick_split_output_dir(self):
        path = filedialog.askdirectory(title="选择拆分输出文件夹")
        if path:
            self.split_out_dir_var.set(path)

    def pick_video_input(self):
        path = filedialog.askopenfilename(
            title="选择视频文件",
            filetypes=[
                ("Video files", "*.mp4;*.mov;*.avi;*.mkv;*.webm"),
                ("All files", "*.*"),
            ],
        )
        if path:
            self.video_input_var.set(path)

    def pick_video_output_dir(self):
        path = filedialog.askdirectory(title="选择视频抽帧输出文件夹")
        if path:
            self.video_out_dir_var.set(path)

    def pick_convert_files(self):
        files = filedialog.askopenfilenames(
            title="选择图片文件",
            filetypes=[
                ("Images", "*.png;*.jpg;*.jpeg;*.webp;*.bmp;*.tif;*.tiff"),
                ("All files", "*.*"),
            ],
        )
        if not files:
            return
        merged = set(self.convert_paths)
        for p in files:
            if is_supported_image_file(p):
                merged.add(p)
        self.convert_paths = sorted(merged, key=natural_key)
        self.refresh_convert_list()

    def pick_convert_folder(self):
        folder = filedialog.askdirectory(title="选择图片文件夹")
        if not folder:
            return
        merged = set(self.convert_paths)
        merged.update(list_images_from_folder(folder))
        self.convert_paths = sorted(merged, key=natural_key)
        self.refresh_convert_list()

    def clear_convert_files(self):
        self.convert_paths = []
        self.refresh_convert_list()

    def pick_convert_output_dir(self):
        path = filedialog.askdirectory(title="选择批量处理输出文件夹")
        if path:
            self.convert_out_dir_var.set(path)

    def on_merge(self):
        try:
            if not self.image_paths:
                raise ValueError("请先选择至少一张 PNG")

            columns = self._to_int(self.columns_var.get().strip(), "列数")
            rows = self._to_int(self.rows_var.get().strip(), "行数")
            spacing = self._to_int(self.spacing_var.get().strip(), "间距")
            margin = self._to_int(self.margin_var.get().strip(), "外边距")
            cell_w = self._to_int(self.cell_w_var.get().strip(), "格子宽")
            cell_h = self._to_int(self.cell_h_var.get().strip(), "格子高")
            out_path = self.output_var.get().strip()
            if not out_path:
                raise ValueError("输出路径不能为空")

            merge_images(
                image_paths=self.image_paths,
                output_path=out_path,
                columns=columns,
                rows=rows,
                spacing=spacing,
                margin=margin,
                bg_color=self.bg_var.get().strip() or "#000000",
                force_cell_width=cell_w,
                force_cell_height=cell_h,
            )
            messagebox.showinfo("完成", f"合并成功:\n{out_path}")
        except Exception as e:
            messagebox.showerror("错误", str(e))

    def on_split(self):
        try:
            input_path = self.split_input_var.get().strip()
            if not input_path:
                raise ValueError("请先选择要拆分的大图")
            if not os.path.isfile(input_path):
                raise ValueError("输入图片不存在")

            p = self._get_split_params()
            sx = p["spacing"] if p["spacing_x"] == 0 else p["spacing_x"]
            sy = p["spacing"] if p["spacing_y"] == 0 else p["spacing_y"]
            mx = p["margin"] if p["margin_x"] == 0 else p["margin_x"]
            my = p["margin"] if p["margin_y"] == 0 else p["margin_y"]

            out_dir = self.split_out_dir_var.get().strip()
            if not out_dir:
                raise ValueError("输出文件夹不能为空")

            prefix = self.split_prefix_var.get().strip() or "frame"

            count = split_image_to_grid(
                input_path=input_path,
                output_dir=out_dir,
                columns=p["columns"],
                rows=p["rows"],
                spacing_x=sx,
                spacing_y=sy,
                margin_x=mx,
                margin_y=my,
                cell_width=p["cell_w"],
                cell_height=p["cell_h"],
                prefix=prefix,
                start_index=p["start_index"],
            )
            messagebox.showinfo("完成", f"拆分成功，共导出 {count} 张:\n{out_dir}")
        except Exception as e:
            messagebox.showerror("错误", str(e))

    def on_video_extract(self):
        try:
            input_path = self.video_input_var.get().strip()
            if not input_path:
                raise ValueError("请先选择视频文件")
            if not os.path.isfile(input_path):
                raise ValueError("输入视频不存在")

            out_dir = self.video_out_dir_var.get().strip()
            if not out_dir:
                raise ValueError("输出文件夹不能为空")

            frame_step = self._to_int(self.video_step_var.get().strip(), "抽帧步长")
            start_sec = self._to_float(self.video_start_sec_var.get().strip(), "开始秒")
            end_sec = self._to_float(self.video_end_sec_var.get().strip(), "结束秒")
            start_index = self._to_int(
                self.video_start_index_var.get().strip(), "起始编号"
            )

            jpg_quality = self._to_int(
                self.video_jpg_quality_var.get().strip(), "JPG质量"
            )
            if jpg_quality < 1 or jpg_quality > 100:
                raise ValueError("JPG质量需要在 1-100 之间")

            prefix = self.video_prefix_var.get().strip() or "frame"
            fmt = self.video_format_var.get().strip() or "png"

            count, fps, export_fps = extract_video_to_sequence(
                input_path=input_path,
                output_dir=out_dir,
                prefix=prefix,
                start_index=start_index,
                frame_step=frame_step,
                target_fps=self._video_target_fps(),
                start_sec=start_sec,
                end_sec=end_sec,
                image_format=fmt,
                jpg_quality=jpg_quality,
            )
            messagebox.showinfo(
                "完成",
                f"导出成功，共 {count} 张（源FPS约 {fps:g}，导出FPS约 {export_fps:g}）:\n{out_dir}",
            )
        except Exception as e:
            messagebox.showerror("错误", str(e))

    def on_convert_batch(self):
        try:
            if not self.convert_paths:
                raise ValueError("请先选择至少一张图片")

            out_dir = self.convert_out_dir_var.get().strip()
            if not out_dir:
                raise ValueError("输出文件夹不能为空")

            target_w = self._to_int(self.convert_w_var.get().strip(), "目标宽")
            target_h = self._to_int(self.convert_h_var.get().strip(), "目标高")
            quality = self._to_int(self.convert_quality_var.get().strip(), "质量")
            if quality < 1 or quality > 100:
                raise ValueError("质量需要在 1-100 之间")

            out_fmt = (self.convert_format_var.get() or "png").strip().lower()

            count = batch_resize_convert_images(
                image_paths=self.convert_paths,
                output_dir=out_dir,
                target_width=target_w,
                target_height=target_h,
                output_format=out_fmt,
                jpg_quality=quality,
            )
            messagebox.showinfo("完成", f"处理完成，共导出 {count} 张:\n{out_dir}")
        except Exception as e:
            messagebox.showerror("错误", str(e))


def build_arg_parser():
    p = argparse.ArgumentParser(
        description="PNG 特效序列图工具：支持合并/拆分/视频抽帧"
    )

    p.add_argument("inputs", nargs="*", help="合并模式下输入 PNG 文件路径（可多个）")
    p.add_argument("-f", "--folder", help="合并模式输入文件夹（自动读取其中所有 PNG）")
    p.add_argument(
        "-o", "--output", help="合并模式输出图片路径，默认 output/merged.png"
    )

    p.add_argument("--columns", type=int, default=0, help="网格列数")
    p.add_argument("--rows", type=int, default=0, help="网格行数")
    p.add_argument("--spacing", type=int, default=0, help="网格间距像素")
    p.add_argument("--margin", type=int, default=0, help="外边距像素")
    p.add_argument("--bg", default="#000000", help="合并背景色，例如 #000000 或 white")
    p.add_argument("--cell-width", type=int, default=0, help="格子宽，0=自动")
    p.add_argument("--cell-height", type=int, default=0, help="格子高，0=自动")

    p.add_argument("--split-input", help="拆分模式输入大图路径")
    p.add_argument(
        "--split-out-dir", default="output/splits", help="拆分模式输出文件夹"
    )
    p.add_argument("--split-prefix", default="frame", help="拆分输出文件名前缀")
    p.add_argument("--split-start-index", type=int, default=1, help="拆分输出起始编号")
    p.add_argument(
        "--split-spacing-x",
        type=int,
        default=-1,
        help="拆分水平间距，-1 表示沿用 --spacing",
    )
    p.add_argument(
        "--split-spacing-y",
        type=int,
        default=-1,
        help="拆分垂直间距，-1 表示沿用 --spacing",
    )
    p.add_argument(
        "--split-margin-x",
        type=int,
        default=-1,
        help="拆分水平边距，-1 表示沿用 --margin",
    )
    p.add_argument(
        "--split-margin-y",
        type=int,
        default=-1,
        help="拆分垂直边距，-1 表示沿用 --margin",
    )

    p.add_argument("--video-input", help="视频抽帧模式输入视频路径")
    p.add_argument(
        "--video-out-dir", default="output/video_frames", help="视频抽帧输出文件夹"
    )
    p.add_argument("--video-prefix", default="frame", help="视频抽帧输出文件名前缀")
    p.add_argument("--video-start-index", type=int, default=1, help="视频抽帧起始编号")
    p.add_argument("--video-step", type=int, default=1, help="抽帧步长，1=每帧导出")
    p.add_argument(
        "--video-fps",
        type=float,
        default=0,
        help="目标导出帧率，0=源帧率模式（此时按 --video-step 抽帧），可填 30 或 12",
    )
    p.add_argument("--video-start-sec", type=float, default=0, help="抽帧开始秒")
    p.add_argument(
        "--video-end-sec", type=float, default=0, help="抽帧结束秒，0=到末尾"
    )
    p.add_argument(
        "--video-format",
        choices=["png", "jpg"],
        default="png",
        help="视频抽帧输出格式",
    )
    p.add_argument("--jpg-quality", type=int, default=95, help="JPG质量，1-100")

    p.add_argument("--gui", action="store_true", help="强制启动图形界面")
    return p


def main():
    parser = build_arg_parser()
    args = parser.parse_args()

    no_cli_inputs = (
        not args.inputs
        and not args.folder
        and not args.output
        and not args.split_input
        and not args.video_input
    )
    if args.gui or no_cli_inputs:
        app = App()
        app.mainloop()
        return

    if args.split_input:
        if not os.path.isfile(args.split_input):
            raise SystemExit(f"输入文件不存在: {args.split_input}")

        columns = max(args.columns, 0)
        rows = max(args.rows, 0)
        if columns <= 0 or rows <= 0:
            raise SystemExit("拆分模式请提供 --columns 和 --rows，且都 > 0")

        count = split_image_to_grid(
            input_path=args.split_input,
            output_dir=args.split_out_dir,
            columns=columns,
            rows=rows,
            spacing=max(args.spacing, 0),
            margin=max(args.margin, 0),
            spacing_x=(
                max(args.split_spacing_x, 0) if args.split_spacing_x >= 0 else None
            ),
            spacing_y=(
                max(args.split_spacing_y, 0) if args.split_spacing_y >= 0 else None
            ),
            margin_x=(
                max(args.split_margin_x, 0) if args.split_margin_x >= 0 else None
            ),
            margin_y=(
                max(args.split_margin_y, 0) if args.split_margin_y >= 0 else None
            ),
            cell_width=max(args.cell_width, 0),
            cell_height=max(args.cell_height, 0),
            prefix=args.split_prefix,
            start_index=max(args.split_start_index, 0),
        )
        print(f"拆分完成: {args.split_out_dir}（共 {count} 张）")
        return

    if args.video_input:
        if not os.path.isfile(args.video_input):
            raise SystemExit(f"输入文件不存在: {args.video_input}")
        if args.jpg_quality < 1 or args.jpg_quality > 100:
            raise SystemExit("--jpg-quality 需要在 1-100 之间")
        if args.video_fps < 0:
            raise SystemExit("--video-fps 需要 >= 0")

        count, fps, export_fps = extract_video_to_sequence(
            input_path=args.video_input,
            output_dir=args.video_out_dir,
            prefix=args.video_prefix,
            start_index=max(args.video_start_index, 0),
            frame_step=max(args.video_step, 1),
            target_fps=args.video_fps,
            start_sec=max(args.video_start_sec, 0),
            end_sec=max(args.video_end_sec, 0),
            image_format=args.video_format,
            jpg_quality=args.jpg_quality,
        )
        print(
            f"抽帧完成: {args.video_out_dir}（共 {count} 张，源FPS约 {fps:g}，导出FPS约 {export_fps:g}）"
        )
        return

    paths = []
    if args.folder:
        if not os.path.isdir(args.folder):
            raise SystemExit(f"文件夹不存在: {args.folder}")
        paths.extend(list_pngs_from_folder(args.folder))
    if args.inputs:
        paths.extend(args.inputs)
    if not paths:
        raise SystemExit("没有输入图片，请传入文件、文件夹，或使用 --gui")
    for p in paths:
        if not os.path.isfile(p):
            raise SystemExit(f"输入文件不存在: {p}")

    paths = sorted(paths, key=natural_key)
    output = args.output or "output/merged.png"
    merge_images(
        image_paths=paths,
        output_path=output,
        columns=max(args.columns, 0),
        rows=max(args.rows, 0),
        spacing=max(args.spacing, 0),
        margin=max(args.margin, 0),
        bg_color=args.bg,
        force_cell_width=max(args.cell_width, 0),
        force_cell_height=max(args.cell_height, 0),
    )
    print(f"合并完成: {output}")


if __name__ == "__main__":
    main()
