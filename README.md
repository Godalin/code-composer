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

### 环境配置

#### 系统工具

```bash
# macOS
brew install alda timidity ffmpeg

# Linux
sudo apt-get install alda timidity ffmpeg
```

#### Nix 用户

项目包含 `shell.nix` 和 `.envrc` 配置，含有 alda timidity ffmpeg 以及 uv 等系统软件，Nix 用户可以直接使用：

```bash
# 使用 direnv（推荐）
direnv allow

# 或者手动进入 Nix shell
nix-shell
```

#### Python 包

```bash
uv sync
```

### 最快试听（推荐）

```bash
# 直接在终端听音乐，无需保存文件
uv run python -m code_composer -c "int x = 42;"
```

### 保存 MP3

```bash
# 从 C 代码文件生成
uv run python -m code_composer -f code.c -o music --no-play

# 从 Python 代码文件生成
uv run python -m code_composer -f code.py -o music --no-play

# 从字符串生成
uv run python -m code_composer -c "int x = 42;" -o music --no-play
```

## CLI 使用指南

所有命令都需要加 `uv run python` 前缀。例如：

```bash
uv run python -m code_composer [选项]
```

### 基本用法

```bash
# 快速试听（生成但不保存文件）
uv run python -m code_composer -c "int x = 42;"

# 从 C 文件生成 MP3 并保存（会自动播放）
uv run python -m code_composer -f code.c -o output/music

# 从 Python 文件生成 MP3 并保存（会自动播放）
uv run python -m code_composer -f code.py -o output/music

# 生成但不播放
uv run python -m code_composer -f code.c -o output/music --no-play

# 使用不同音阶（自动选择推荐和声进行）
uv run python -m code_composer -c "int x = 42;" --key D --scale minor

# 指定音阶和和声进行
uv run python -m code_composer -f code.c --key G --scale dorian --chord 1min-4-1min-4
```

### 完整命令选项

可以用下面的命令打印完整的选项列表：

```bash
uv run python -m code_composer --help
```

```text
options:
  -h, --help            show this help message and exit
  -f, --file FILE       输入源代码文件路径（支持 .c 和 .py）
  -c, --code CODE       直接传入源代码字符串
  --lang {c,python,auto}
                        源代码语言（默认自动判断）
  --key KEY             乐曲调（如 C, G, D#, Bb，默认使用风格的默认值）
  --scale SCALE         音阶/调式（默认使用风格的默认值，可用: major, minor, harmonic_minor, melodic_minor, dorian, phrygian, lydian, mixolydian, pentatonic_major, pentatonic_minor, chinese_pentatonic, blues, gypsy_minor, gypsy_major, hijaz, hijaz_kar,
                        bayati, nahawand, kurd, rast, saba）
  --test-scale          测试模式：只播放当前音阶（覆盖2个八度），不生成旋律
  --test-chord          测试模式：只播放当前和声进行（分解和弦），不生成旋律
  -o, --output OUTPUT   输出文件名（不含扩展名）或路径。如不指定则只播放不保存
  --format {alda,midi,mp3}
                        输出格式（默认：mp3）
  --export-all          导出所有格式（.alda、.mid、.mp3）
  --chord CHORD         和声进行（不指定则根据音阶自动选择推荐进行）
  --style STYLE         音乐风格（可用: default, minuet, waltz, jazz, gypsy, arabic, gothic, chinese）
  --tempo TEMPO         乐曲速度 BPM（默认：120，waltz/minuet 为 160）
  --bass-pattern {block,double,arpeggio,pendulum,waltz_oom_pah,minuet_duple}
                        低音模式（默认使用风格的低音模式）
  --bars-per-phrase BARS_PER_PHRASE
                        每个乐句的小节数（默认：4）
  --bars-per-token {1,2}
                        一个 token 覆盖的小节数（1 或 2，默认 1）
  --seed SEED           随机数种子（默认：42，用于复现结果）
  --parts {melody,accompaniment,both}
                        输出部分：melody（仅旋律 V1）、accompaniment（仅伴奏 V2）、both（两者，默认）
  -v, --verbose         显示详细输出信息
  --debug               生成后打印作品的树形结构信息
  --no-play             生成后不自动播放音乐
  --version             show program's version number and exit
```

### 更多用法

**指定风格、调式与和弦：**

```bash
uv run python -m code_composer -f code.c --style jazz --key G --scale dorian --chord 2min-5-1 --tempo 140
```

**生成所有格式（Alda + MIDI + MP3）：**

```bash
uv run python -m code_composer -f code.c --export-all -o output/complete_music
```

**不自动播放：**

```bash
uv run python -m code_composer -f code.c -o music --no-play
```

#### 自动播放说明

- 默认自动播放生成的音乐（通过 Alda）
- 如果不指定 `-o` 参数，生成后播放但不保存文件
- 使用 `--no-play` 禁用自动播放

## 音乐风格系统

Code Composer 支持基于外部配置文件的预设音乐风格！每个风格都有独特的节奏型和特色。

**TODO:** 风格配置文档

完整的预设风格配置文件可以在 [](./config/) 目录下看到。

## Python API（高级）

Code Composer 可以作为一个 Python 库使用，方便自定义作曲流程。

**TODO**: 更好的 Python API 示例

### 编译流程

- Compiler or Composer?
- Compiler is Composer!

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
  ├─ 风格系统
  ├─ 节奏型选择
  ├─ 和弦进行
  └─ 旋律生成
  └─ 伴奏生成
       |
       v
  Alda 乐谱
       |
   ┌───┴───┐
   v       v
  MIDI    MP3
```

### 前端模块

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

所有前端都输出统一格式的 Token 列表，便于谱曲器后续处理。

## 许可证

MIT
