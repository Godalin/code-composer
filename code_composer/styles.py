"""
风格定义与管理

将节奏、可用和声进行等风格信息与谱曲器解耦。
从配置文件加载所有风格定义。
"""

from dataclasses import dataclass, field, replace
from fractions import Fraction
from typing import TypedDict

from .rhythms import RhythmWeight, RhythmEntry
from .motif import MotifWeight


@dataclass(frozen=True)
class Style:
    """
    音乐风格定义 - 完整封装风格的所有特性，不可变对象

    包含：
    - 节奏型集合和权重
    - 可用的和声进行名称列表
    - 时间签名（拍子信息）
    - 低音模式（如 waltz 的 Oom-Pah-Pah）
    - 特殊标记（如蓝调音符）
    - 谱曲参数（调性、音阶、速度、八度等）
    """

    name: str
    time_signature: str
    rhythm_weights: list[RhythmWeight]
    motif_weights: list[MotifWeight]
    available_progressions: list[str]
    bar_target_beats: Fraction = Fraction(4, 1)
    bass_pattern: str = 'block'
    key: str = 'C'
    scale: str = 'major'
    tempo: int = 120
    octave: int = 4
    progression: str = '1-6min-4-5'
    chord_progressions: dict[str, list[tuple[str, list[str]]]] = field(default_factory=dict)
    instrument: str = 'violin'


class StyleDict(TypedDict):
    """为配置文件使用的类型签名，键和 Style 一样"""
    name: str
    time_signature: str
    rhythm_weights: list[RhythmEntry]
    motif_weights: list[MotifWeight]
    available_progressions: list[str]
    bar_target_beats: Fraction
    bass_pattern: str
    key: str
    scale: str
    tempo: int
    octave: int
    progression: str
    chord_progressions: dict[str, list[tuple[str, list[str]]]]
    instrument: str


_STYLES: dict[str, Style] = {}


def list_styles() -> list[str]:
    """列出所有可用的风格名称"""
    from .config_loader import list_available_styles
    return list_available_styles()


def get_style(name: str) -> Style:
    """获取指定名称的 Style 对象"""
    from .config_loader import resolve_style
    if name not in list_styles():
        raise ValueError(f"未知的风格: {name}")

    if name not in _STYLES:
        _STYLES[name] = resolve_style(name)

    return _STYLES[name]


def create_style_with(
    style_name: str,
    **kwargs
) -> Style:
    """从风格名称和可选参数构造 Style 对象"""
    base_style = get_style(style_name)
    if base_style is None:
        raise ValueError(f"未知的风格: {style_name}。可用风格: {list_styles()}")
    kwargs = { k : v for k, v in kwargs.items() if v is not None }
    return replace(base_style, **kwargs)
