# 特效序列图工具（合并/拆分/视频抽帧）

支持五种常用操作：

- 多张 PNG 按网格一键合并成一张大图
- 单张 PNG 按网格一键拆分成多张小图
- 视频一键保存为序列图（PNG/JPG）
- 批量修改图片尺寸并转换格式（PNG/JPG/WEBP）
- 批量改名（前后缀、查找替换、序号命名）

## 功能

- 合并：一键选择多个 PNG 或整个文件夹
- 合并：自定义网格列数/行数（可自动计算）
- 合并：自定义间距、外边距、背景色
- 合并：支持不等尺寸图片，自动居中到各自格子
- 拆分：单图按指定行列网格导出序列图
- 拆分：支持可视化网格预览、X/Y 独立间距与边距、格子宽高、文件名前缀和起始编号
- 视频抽帧：支持目标帧率（源帧率/30/12）、步长抽帧、时间范围、输出格式、文件名前缀与起始编号
- 批量改图：支持多图拖拽/文件夹导入，按目标宽高批量缩放并转换格式
- 批量改名：支持拖拽文件/文件夹，预览后执行重命名
- 支持拖拽文件：多张图片（含文件夹）/单张拆分图/视频都可直接拖入对应输入框
- 支持 GUI（图形界面）和 CLI（命令行）两种方式

## 安装

```bash
python -m pip install -r requirements.txt
```

## 用法

### 1) 图形界面（推荐）

```bash
python merge_fx_sequences.py
```

或

```bash
python merge_fx_sequences.py --gui
```

Windows 也可直接双击：

- `run.bat`

拖拽支持：

- 合并多图页签：可拖入多个 `.png` 文件，或直接拖入文件夹
- 单图拆分页签：可拖入单个 `.png` 到输入框
- 视频转序列图页签：可拖入单个视频到输入框
- 批量改尺寸格式页签：可拖入多个图片或文件夹到列表
- 批量改名页签：可拖入文件或文件夹到列表

### 2) 命令行

#### 合并

按文件夹读取 PNG：

```bash
python merge_fx_sequences.py -f "./sequence" -o "./output/merged.png" --columns 8 --spacing 4 --margin 8 --bg "#1a1a1a"
```

按多个文件读取：

```bash
python merge_fx_sequences.py "./a_001.png" "./a_002.png" "./a_003.png" -o "./output/merged.png" --rows 4
```

#### 拆分

把一张图拆成 8x4，共 32 张：

```bash
python merge_fx_sequences.py --split-input "./sheet.png" --split-out-dir "./output/splits" --columns 8 --rows 4
```

自定义间距/边距/文件名前缀：

```bash
python merge_fx_sequences.py --split-input "./sheet.png" --split-out-dir "./output/splits" --columns 8 --rows 4 --spacing 2 --margin 4 --split-prefix "fx"
```

拆分时单独设置 X/Y 间距和边距：

```bash
python merge_fx_sequences.py --split-input "./sheet.png" --split-out-dir "./output/splits" --columns 8 --rows 4 --split-spacing-x 2 --split-spacing-y 6 --split-margin-x 4 --split-margin-y 10
```

#### 视频转序列图

导出整段视频为 PNG 序列图：

```bash
python merge_fx_sequences.py --video-input "./shot.mp4" --video-out-dir "./output/video_frames"
```

按步长和时间范围导出 JPG：

```bash
python merge_fx_sequences.py --video-input "./shot.mp4" --video-out-dir "./output/video_frames" --video-step 2 --video-start-sec 1.5 --video-end-sec 6.0 --video-format jpg --jpg-quality 92 --video-prefix "fx"
```

按目标帧率 30FPS 导出：

```bash
python merge_fx_sequences.py --video-input "./shot.mp4" --video-out-dir "./output/video_frames" --video-fps 30
```

按目标帧率 12FPS 导出：

```bash
python merge_fx_sequences.py --video-input "./shot.mp4" --video-out-dir "./output/video_frames" --video-fps 12
```

## 网格规则

### 合并

- `columns > 0` 且 `rows > 0`：使用固定网格
- 只填 `columns`：自动计算 `rows`
- 只填 `rows`：自动计算 `columns`
- 两者都为 `0`：自动计算接近正方形网格

### 拆分

- `columns` 和 `rows` 必须都大于 0
- `cell-width=0`/`cell-height=0` 时，按可用区域均分
- 支持 `spacing-x/spacing-y`、`margin-x/margin-y` 分别设置横向和纵向参数
- 若无法整除，会提示你调整参数，避免切片错位

### 视频抽帧

- `video-fps` 支持 `0/30/12`：`0` 表示源帧率模式，`30/12` 表示按目标帧率抽帧
- `video-step=1` 表示每帧导出，`2` 表示每隔 1 帧导出
- 当 `video-fps > 0` 时，优先按目标帧率抽帧（`video-step` 将被忽略）
- 可通过 `video-start-sec` 和 `video-end-sec` 控制导出时间段
- 输出文件命名为 `prefix_0001.png/jpg`

## 参数说明（CLI）

- 通用网格参数：
  - `--columns` 列数
  - `--rows` 行数
  - `--spacing` 网格间距像素
  - `--margin` 外边距像素
  - `--cell-width` 格子宽（0=自动）
  - `--cell-height` 格子高（0=自动）
- 合并模式参数：
  - `-f, --folder` 输入文件夹（读取全部 `.png`）
  - `-o, --output` 输出路径（默认 `output/merged.png`）
  - `--bg` 背景色（如 `#000000`、`white`）
- 拆分模式参数：
  - `--split-input` 输入大图路径
  - `--split-out-dir` 拆分输出文件夹（默认 `output/splits`）
  - `--split-prefix` 输出文件名前缀（默认 `frame`）
  - `--split-start-index` 起始编号（默认 `1`）
  - `--split-spacing-x` 拆分水平间距（默认 `-1`，沿用 `--spacing`）
  - `--split-spacing-y` 拆分垂直间距（默认 `-1`，沿用 `--spacing`）
  - `--split-margin-x` 拆分水平边距（默认 `-1`，沿用 `--margin`）
  - `--split-margin-y` 拆分垂直边距（默认 `-1`，沿用 `--margin`）
- 视频抽帧模式参数：
  - `--video-input` 输入视频路径
  - `--video-out-dir` 输出文件夹（默认 `output/video_frames`）
  - `--video-prefix` 输出文件名前缀（默认 `frame`）
  - `--video-start-index` 起始编号（默认 `1`）
  - `--video-step` 抽帧步长（默认 `1`）
  - `--video-fps` 目标导出帧率（默认 `0`，即源帧率模式，可填 `30`/`12`）
  - `--video-start-sec` 开始秒（默认 `0`）
  - `--video-end-sec` 结束秒（默认 `0`，即到末尾）
  - `--video-format` 输出格式（`png`/`jpg`）
  - `--jpg-quality` JPG质量（1-100，默认 `95`）
