"""
Code Composer - 将源代码转换为音乐的编译系统

支持多种源语言（C、Python）生成 Alda 音乐谱，可导出为 MIDI 和 MP3 格式。
"""

from .composer import (
    Composer,
    generate_piano_composition,
    export_to_midi,
    midi_to_mp3,
    compose_to_mp3,
    compose_and_play,
    play_alda_file,
)

__version__ = "0.1.0"
__all__ = [
    "Composer",
    "generate_piano_composition",
    "export_to_midi",
    "midi_to_mp3",
    "compose_to_mp3",
    "compose_and_play",
    "play_alda_file",
]
