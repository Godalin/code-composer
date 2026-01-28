"""
Code Composer - 将源代码转换为音乐的编译系统

支持多种源语言（C、Python）生成 Alda 音乐谱，可导出为 MIDI 和 MP3 格式。

模块结构：
- composer.py：核心谱曲引擎（函数式谱曲 compose() 及其组件）
- bass.py：低音生成模块（多种低音模式支持）
- exporter.py：格式转换和播放（MIDI/MP3 导出）
- styles.py：音乐风格定义（default, jazz, waltz, minuet）
- rhythms.py：节奏数据库和选择
- theory.py：音乐理论（音阶、和声进行生成）
- frontend/：源代码解析（C 和 Python 前端）
"""

from .composer import (
    compose,
)
from .bass import (
    gen_bar_bass,
)
from .exporter import (
    export_to_midi,
    midi_to_mp3,
    play_alda_file,
)
from .styles import create_style_with
from .structures import (
    Bar,
    ChordSpan,
    Phrase,
    Composition,
    Note,
    print_composition_tree,
)
from .theory import (
    get_scale,
    gen_progression,
    get_available_progressions,
    get_default_progression,
    vary_chord,
)

__version__ = "0.1.0"
__all__ = [
    "compose",
    # Bass module
    "gen_bar_bass",
    # Data structures
    "Bar",
    "ChordSpan",
    "Phrase",
    "Composition",
    "Note",
    # Printers
    "print_composition_tree",
    "create_style_with",
    "export_to_midi",
    "midi_to_mp3",
    "play_alda_file",
    # Theory functions
    "get_scale",
    "gen_progression",
    "get_available_progressions",
    "get_default_progression",
    "vary_chord",
]
