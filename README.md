# Code Composer

将源代码转换为音乐的编译系统。支持 C 和 Python，生成 Alda 乐谱、MIDI 和 MP3 文件。

## 特性

- 🎼 多语言支持（C、Python）
  - **C 编译器**：使用 pycparser 进行完整的 C99 代码解析和 AST 转换
  - **Python 编译器**：基于标准库 `tokenize` 模块
- 🎵 自动生成钢琴乐谱（旋律+和弦伴奏）
- 🎹 多种音乐风格（Default、Jazz）
- 🎼 支持和声进行和旋律生成
- 📁 导出格式：Alda、MIDI、MP3
- 🔊 自动播放（使用 Alda）
- 🔊 无需外部 SoundFont（使用 timidity 内置音色）

## 快速开始

### 安装

```bash
uv sync
```

### Nix 用户

项目包含 `shell.nix` 和 `.envrc` 配置，Nix 用户可以直接使用：

```bash
# 使用 direnv（推荐）
direnv allow

# 或者手动进入 Nix shell
nix-shell
```

进入 Nix shell 后，所有依赖会自动加载，可以直接运行：

```bash
uv run python -m code_composer -c "int x = 42;"
```

### 最快试听（推荐）

```bash
# 直接在终端听音乐，无需保存文件
uv run python -m code_composer -c "int x = 42;"
```

### 保存 MP3

```bash
# 从 C 代码文件生成
uv run python -m code_composer -f code.c -o music.mp3

# 从 Python 代码文件生成
uv run python -m code_composer -f code.py -o music.mp3

# 从字符串生成
uv run python -m code_composer -c "int x = 42;" -o music.mp3 --no-play
```

### Python API（高级）

编写脚本 `script.py`：

```python
from code_composer import generate_piano_composition

code = """
int main() {
    int x = 42;
    return 0;
}
"""

# 完整控制
alda_score, metadata = generate_piano_composition(
    code,
    chord_progression='I_vi_IV_V',  # 和声进行
    tempo=120,                       # 速度 (BPM)
    bars_per_phrase=4,               # 每个乐句的小节数
    output_file='music.alda',        # Alda 文件
    export_midi=True,                # 导出 MIDI
    export_mp3=True,                 # 导出 MP3
    style='jazz',                    # 音乐风格（default/jazz）
    bass_arpeggio='arpeggio'         # 低音分解模式
)
```

运行：

```bash
uv run python script.py
```

## 音乐风格系统

现在支持预设音乐风格！每个风格都有独特的节奏型和特色。

### 可用风格

#### 1. Default 风格（默认）

**特点：**

- 平衡的现代音乐
- 16分音符较多（节奏复杂）
- 较少三连音（均分节奏）
- 适合动态、活泼的音乐

**节奏分布：**

- 8分音符：43%
- 4分音符：33%
- 16分音符：22%
- 三连音（合计）：22%

**使用命令：**

```bash
uv run python -m code_composer -f code.c --style default
```

#### 2. Jazz 风格

**特点：**

- Swing 节奏感（2/3 1/3 分割）
- 大量三连音（摇摆感）
- 蓝调音符（blue notes）：♭3, ♭5, ♭7 等
- 较少16分音符（简洁）
- 爵士专用和声进行

**节奏分布：**

- 4分音符：28%
- 8分音符：19%
- 三连音（合计）：32% ← 高频率！
- 16分音符：11%

**可用和声进行：**

- `II_V_I` - 经典爵士进行
- `VI_ii_V_I` - 扩展爵士进行
- `Imaj7_vi7_ii7_V7` - 现代爵士进行

**蓝调音符示例：**

```text
C 大调蓝调音符：
- d#/eb (♭3)
- f#/gb (♭5)
- a#/bb (♭7)
```

**使用命令：**

```bash
# 使用 II-V-I 进行
uv run python -m code_composer -f code.c --style jazz --chord II_V_I

# 使用 VI-ii-V-I 进行
uv run python -m code_composer -f code.c --style jazz --chord VI_ii_V_I

# 更快的 Swing 速度
uv run python -m code_composer -f code.c --style jazz --chord II_V_I --tempo 160
```

### 音阶与和声进行

不同音阶有各自适合的和声进行，系统会自动根据选定的音阶推荐合适的进行。

#### Major（大调）

- `I_vi_IV_V` - 流行进行（1-6-4-5）
- `I_V_IV_vi` - 常见进行（1-5-4-6）
- `IV_V_iii_vi_ii_V_I` - 帕赫贝尔卡农进行
- `I_IV_V_IV` - 摇滚进行
- `vi_IV_I_V` - 抒情进行

#### Minor（小调）

- `i_VI_III_VII` - 自然小调进行
- `i_iv_v_i` - 基础小调进行
- `i_VI_VII_i` - 悲伤进行
- `i_III_VII_VI` - 史诗进行
- `i_iv_VII_III` - 哥特进行

#### Dorian（多利亚调式）

- `i_IV_i_IV` - 多利亚摇摆
- `i_ii_IV_V` - 多利亚经典
- `i_IV_VII_i` - 多利亚回环
- `ii_V_i_IV` - 多利亚爵士

#### Pentatonic（五声音阶）

- `I_III_IV_I` - 五声简约
- `I_II_IV_V` - 中国风
- `I_IV_V_I` - 民谣进行

#### Gypsy Minor（吉普赛小调/匈牙利小调）

- `i_II_V_i` - 吉普赛基础
- `i_VII_VI_VII` - 吉普赛回旋
- `i_II_III_i` - 匈牙利式
- `VI_VII_i_II` - 东欧风情

#### Gypsy Major（吉普赛大调/双和声大调）

- `I_II_III_I` - 双和声行进
- `I_bII_VII_I` - 中东风格
- `I_V_VI_VII` - 神秘进行

#### Jazz 专用进行（适用于多种音阶）

- `II_V_I` - 经典 Bebop
- `VI_ii_V_I` - 扩展 Standard
- `Imaj7_vi7_ii7_V7` - 现代爵士
- `ii7_V7_Imaj7_vi7` - 转位爵士

**使用说明：**

- 不指定 `--chord` 时，系统会自动选择该音阶的推荐进行
- 指定的进行如果不适合当前音阶，系统会自动切换到推荐进行并提示

---

## CLI 使用指南

### 基本用法

```bash
# 快速试听（生成但不保存文件）
uv run python -m code_composer -c "int x = 42;"

# 从 C 文件生成 MP3 并保存（会自动播放）
uv run python -m code_composer -f code.c -o music.mp3

# 从 Python 文件生成 MP3 并保存（会自动播放）
uv run python -m code_composer -f code.py -o music.mp3

# 生成但不播放
uv run python -m code_composer -f code.c -o music.mp3 --no-play

# 使用不同音阶（自动选择推荐和声进行）
uv run python -m code_composer -c "int x = 42;" --key D --scale minor

# 指定音阶和和声进行
uv run python -m code_composer -f code.c --key G --scale dorian --chord i_IV_i_IV -o output
```

### 完整命令选项

所有命令都需要加 `uv run python` 前缀。例如：

```bash
uv run python -m code_composer [选项]
```

**输入选项（二选一）：**

```bash
-f FILE, --file FILE      # 从文件读取代码
-c CODE, --code CODE      # 从命令行代码字符串
```

**语言选项：**

```bash
--lang {c,python}         # 明确指定语言（默认自动检测）
```

**输出选项：**

```bash
-o OUTPUT, --output OUTPUT  # 输出文件路径（不需要扩展名）
--export-all                # 导出所有格式 (Alda, MIDI, MP3)
--format {alda,midi,mp3}    # 只导出指定格式
```

**音乐参数：**

```bash
--tempo TEMPO                # 设置音乐速度（BPM，默认 120）
--chord CHORD_PROGRESSION    # 和声进行（可选，不指定则自动根据音阶选择）
--style {default,jazz}       # 选择音乐风格（默认 default）
--key KEY                    # 乐曲调（如 C, G, D#, Bb；默认 C）
--scale {major,minor,dorian,pentatonic,gypsy_minor,gypsy_major}  # 音阶/调式（默认 major）
--bars-per-phrase BARS       # 设置短语长度（默认 4 小节）
--bass-arpeggio {block,double,follow,arpeggio,pendulum}  # 低音分解和弦模式（默认 block）
```

**其他选项：**

```bash
-v, --verbose      # 详细输出信息
--no-play          # 生成后不自动播放（默认会播放）
-h, --help         # 显示帮助信息
```

### 更多用法

**指定风格、调式与和弦：**

```bash
uv run python -m code_composer -f code.c --style jazz --key G --scale dorian --chord II_V_I --tempo 140 -o jazz_music
```

**生成所有格式（Alda + MIDI + MP3）：**

```bash
uv run python -m code_composer -f code.c --export-all -o complete_music
```

**不自动播放：**

```bash
uv run python -m code_composer -f code.c -o music --no-play
```

---

## 自动播放说明

- 默认自动播放生成的音乐（通过 Alda）
- 如果不指定 `-o` 参数，生成后播放但不保存文件
- 使用 `--no-play` 禁用自动播放
- 支持 macOS 和 Linux，Windows 不支持

---

## 架构设计

### 编译流程

```text
源代码 (.c / .py)
       |
       v
[Frontend 前端模块]
  ├─ c.py (pycparser)   → 解析 C 代码
  ├─ python.py (tokenize) → 解析 Python 代码
  └─ lexer.py (通用接口)  ← 统一的 Token 输出
       |
       v
  统一的 Token 流
       |
       v
[Composer 谱曲引擎]
  ├─ 风格系统 (default/jazz)
  ├─ 节奏型选择
  ├─ 和弦进行
  └─ 旋律生成
       |
       v
  Alda 乐谱
       |
   ┌───┴───┐
   v       v
  MIDI    MP3
```

### 前端模块（Frontend）

`frontend/` 目录统一管理所有语言的解析器：

- **lexer.py** - 定义通用接口
  - `TokenType` - Token 类型枚举
  - `Token` - Token 数据结构
  - `BaseLexer` - 基础词法分析器接口

- **c.py** - C 语言前端
  - 使用 pycparser 进行完整 C99 解析
  - AST 转换为 Token 流

- **python.py** - Python 语言前端
  - 使用标准库 tokenize 模块
  - 处理 Python 代码的语法糖

所有前端都输出统一格式的 Token 列表，便于后续处理。

### 核心组件

**1. 和弦伴奏（低音声部）：**

- 每个小节使用当前进行中的和弦
- 低音区八度（octave - 1）
- 整小节全音符（充满和声）
- 音量 80（清晰可辨）

**2. 旋律（高音声部）：**

- 使用当前和弦内音生成
- 多种节奏型（根据风格选择）
- 动机类型（上行、下行、拱形、谷形、重复）
- 第一音符强调（vol 95），其余正常（vol 80）

**3. 声部组织：**

- 使用 Alda Voices（V1 旋律，V2 和弦）
- 两个声部完全同步演奏
- 每个乐句 4 小节，和弦按进行循环

## 项目结构

```text
code_composer/
├── __init__.py          # 包入口
├── __main__.py          # 命令行入口
├── cli.py              # 命令行界面
├── composer.py         # 主谱曲器引擎（风格系统、和弦生成）
└── frontend/           # 多语言前端模块
    ├── __init__.py     # 前端模块入口
    ├── lexer.py        # 通用词法分析接口（Token、TokenType、BaseLexer）
    ├── c.py            # C 语言前端（基于 pycparser）
    └── python.py       # Python 语言前端（基于 tokenize）
examples/              # 示例代码
├── demo.py           # 基本 Python 示例
├── factorial.py      # 阶乘 Python 示例
├── fibonacci.c       # 斐波那契 C 代码
└── piano_composition.*  # 示例输出文件
output/                # 输出文件目录
pyproject.toml        # UV 项目配置
shell.nix            # Nix 开发环境配置
.envrc               # direnv 配置（与 shell.nix 配合使用）
README.md            # 本文件
```

---

## 依赖和安装

### 系统工具

```bash
# macOS
brew install alda timidity ffmpeg

# Linux
sudo apt-get install alda timidity ffmpeg
```

### Python 包

```bash
uv sync
```

---

## 许可证

MIT
