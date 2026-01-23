"""
风格定义与管理

将节奏、可用和声进行等风格信息与谱曲器解耦。
从配置文件加载所有风格定义。
"""

from dataclasses import dataclass, field, replace
from fractions import Fraction
from typing import Dict, List, Tuple, Literal, Optional

from .rhythms import RhythmPattern
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
    bar_patterns: List[RhythmPattern]
    bar_pattern_weights: List[int]
    available_progressions: List[str]
    time_signature: str = "4/4"
    bar_target_beats: Fraction = Fraction(4, 1)
    bass_pattern: Literal['block', 'double', 'arpeggio', 'pendulum', 'waltz_oom_pah', 'minuet_duple'] = 'block'
    blue_notes: bool = False
    motif_weights: List[MotifWeight] = field(default_factory=list)
    default_key: str = 'C'
    default_scale: str = 'major'
    default_tempo: int = 120
    default_octave: int = 4
    default_progression: str = '1-6min-4-5'
    chord_progressions: Dict[str, List[Tuple[str, List[str]]]] = field(default_factory=dict)
    
    def __post_init__(self) -> None:
        """验证 dataclass 初始化后的不变量"""
        if len(self.bar_patterns) != len(self.bar_pattern_weights):
            raise ValueError(
                f"节奏型数量 ({len(self.bar_patterns)}) "
                f"与权重数量 ({len(self.bar_pattern_weights)}) 不匹配"
            )


def _build_style_from_config(style_name: str) -> Style:
    """从配置文件构建 Style 对象"""
    from .config_loader import (
        load_style, 
        get_style_rhythm_weights, 
        get_style_motif_weights,
        get_style_progressions,
        load_rhythm_patterns
    )
    
    # 加载风格配置
    config = load_style(style_name)
    
    # 解析时间签名
    time_sig_str = config.get('time_signature', '4/4')
    numer, denom = time_sig_str.split('/')
    bar_target_beats = Fraction(int(numer), int(denom))
    
    # 加载节奏模式和权重
    rhythm_entries = get_style_rhythm_weights(style_name)
    rhythm_lib = load_rhythm_patterns(time_sig_str)
    patterns = [rhythm_lib[name] for weight, name in rhythm_entries]
    weights = [weight for weight, name in rhythm_entries]
    
    # 加载动机权重
    motif_weights = get_style_motif_weights(style_name)
    
    # 加载和弦进行
    progressions_dict = get_style_progressions(style_name)
    progressions = list(progressions_dict.values())
    
    # 获取默认值
    defaults = config.get('defaults', {})
    
    return Style(
        name=style_name,
        time_signature=time_sig_str,
        bar_patterns=patterns,
        bar_pattern_weights=weights,
        available_progressions=progressions,
        bar_target_beats=bar_target_beats,
        bass_pattern=config.get('bass_pattern', 'block'),
        blue_notes=config.get('blue_notes', False),
        motif_weights=motif_weights,
        default_key=defaults.get('key', 'C'),
        default_scale=defaults.get('scale', 'major'),
        default_tempo=defaults.get('tempo', 120),
        default_octave=defaults.get('octave', 4),
        default_progression=defaults.get('progression', '1-6min-4-5'),
    )


_STYLES: Dict[str, Style] = {}


def list_styles() -> List[str]:
    """列出所有可用的风格名称"""
    from .config_loader import list_available_styles
    return list_available_styles()


def get_style(name: str) -> Style:
    """
    获取指定名称的 Style 对象
    
    参数：
        name: 风格名称
    
    返回：
        不可变的 Style 对象
    
    异常：
        ValueError: 当风格名称未知时
    """
    if name not in list_styles():
        raise ValueError(f"未知的风格: {name}")

    if name not in _STYLES:
        _STYLES[name] = _build_style_from_config(name)

    return _STYLES[name]


def create_style_with_overrides(
    style_name: str,
    key: Optional[str] = None,
    scale: Optional[str] = None,
    tempo: Optional[int] = None,
    octave: Optional[int] = None,
    chord_progression: Optional[str] = None,
    bass_pattern: Optional[str] = None,
) -> Style:
    """
    从风格名称和可选参数构造 Style 对象
    
    基础风格由 style_name 决定，可选参数覆盖对应的默认值。
    """
    base_style = get_style(style_name)
    if base_style is None:
        raise ValueError(f"未知的风格: {style_name}。可用风格: {list_styles()}")
    
    # 如果有参数覆盖，构造新的 Style 对象
    if any([key, scale, tempo is not None, octave is not None, chord_progression, bass_pattern]):
        kwargs = {}
        if key is not None:
            kwargs['default_key'] = key
        if scale is not None:
            kwargs['default_scale'] = scale
        if tempo is not None:
            kwargs['default_tempo'] = tempo
        if octave is not None:
            kwargs['default_octave'] = octave
        if chord_progression is not None:
            kwargs['default_progression'] = chord_progression
        if bass_pattern is not None:
            kwargs['bass_pattern'] = bass_pattern
        
        return replace(base_style, **kwargs)
    
    return base_style
