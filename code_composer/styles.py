"""
风格定义与管理

将节奏、可用和声进行等风格信息与谱曲器解耦。
具体和弦内容仍由 theory.generate_progression 动态生成；
节奏型预设从 rhythms 模块获取。
"""

from dataclasses import dataclass, field, replace
from fractions import Fraction
from typing import Dict, List, Tuple, Literal, Optional

from .rhythms import get_rhythm, RhythmPattern
from .motif import get_motif_weights, MotifWeight


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
    bar_target_beats: Fraction = Fraction(4, 1)
    bass_pattern: Literal['block', 'double', 'arpeggio', 'pendulum', 'waltz_oom_pah', 'minuet_duple'] = 'block'
    blue_notes: bool = False
    motif_weights: List[MotifWeight] = field(default_factory=list)
    default_key: str = 'C'
    default_scale: str = 'major'
    default_tempo: int = 120
    default_octave: int = 4
    default_progression: str = 'I_vi_IV_V'
    chord_progressions: Dict[str, List[Tuple[str, List[str]]]] = field(default_factory=dict)
    
    def __post_init__(self) -> None:
        """验证 dataclass 初始化后的不变量"""
        if len(self.bar_patterns) != len(self.bar_pattern_weights):
            raise ValueError(
                f"节奏型数量 ({len(self.bar_patterns)}) "
                f"与权重数量 ({len(self.bar_pattern_weights)}) 不匹配"
            )


def _create_default_style() -> Style:
    """
    创建默认（现代）风格 - 纯函数
    
    返回一个新的、不可变的 Style 对象。多次调用会产生独立的对象，
    但内容相同。这是纯函数：不修改任何外部状态。
    
    风格特性：
    - 节奏型：现代流行音乐的标准节奏
    - 低音模式：块式低音（block，简洁直接）
    - 时间签名：4/4 拍子
    - 蓝调音符：禁用
    - 默认进行：I-vi-IV-V（流行音乐最常见的进行）
    """
    patterns, weights = get_rhythm('default')

    default_progressions = [
        # 大调系进行
        'I_vi_IV_V',
        'I_V_IV_vi',
        'IV_V_iii_vi_ii_V_I',
        'I_IV_V_IV',
        'vi_IV_I_V',
        # 小调系进行
        'i_VI_III_VII',
        'i_iv_v_i',
        'i_VI_VII_i',
        # 多利亚进行
        'i_IV_i_IV',
        'i_ii_IV_V',
        # 五声音阶进行
        'I_III_IV_I',
        'I_II_IV_V',
        # 吉普赛进行
        'i_II_V_i',
        'I_II_III_I',
    ]

    return Style(
        name='default',
        bar_patterns=patterns,
        bar_pattern_weights=weights,
        available_progressions=default_progressions,
        bar_target_beats=Fraction(4, 1),
        bass_pattern='block',
        blue_notes=False,
        motif_weights=get_motif_weights('default'),
        default_key='C',
        default_scale='major',
        default_tempo=120,
        default_octave=4,
        default_progression='I_vi_IV_V',
    )


def _create_jazz_style() -> Style:
    """
    创建爵士风格 - 纯函数
    
    返回一个新的、不可变的 Style 对象。多次调用会产生独立的对象，
    但内容相同。这是纯函数：不修改任何外部状态。
    
    风格特性：
    - 节奏型：爵士特色的复杂鼓点
    - 低音模式：琶音式低音（arpeggio）
    - 蓝调音符：启用
    - 默认进行：II-V-I（爵士标准）
    """
    patterns, weights = get_rhythm('jazz')

    jazz_progressions = [
        # 爵士特有进行
        'II_V_I',
        'VI_ii_V_I',
        'Imaj7_vi7_ii7_V7',
        'iii_VI_ii_V',
        # 通用进行
        'I_vi_IV_V',
        'I_V_IV_vi',
        'IV_V_iii_vi_ii_V_I',
        # 小调
        'i_VI_III_VII',
        'i_iv_v_i',
        # 多利亚
        'i_IV_i_IV',
        'i_ii_IV_V',
        'i_IV_VII_i',
    ]

    return Style(
        name='jazz',
        bar_patterns=patterns,
        bar_pattern_weights=weights,
        available_progressions=jazz_progressions,
        bar_target_beats=Fraction(4, 1),
        bass_pattern='arpeggio',
        blue_notes=True,
        motif_weights=get_motif_weights('jazz'),
        default_key='C',
        default_scale='major',
        default_tempo=120,
        default_octave=4,
        default_progression='II_V_I',
    )


def _create_waltz_style() -> Style:
    """
    创建圆舞曲风格 - 纯函数
    
    返回一个新的、不可变的 Style 对象。多次调用会产生独立的对象，
    但内容相同。这是纯函数：不修改任何外部状态。
    
    风格特性：
    - 节奏型：3/4 拍子
    - 低音模式：Oom-Pah-Pah（维也纳圆舞曲特色低音）
    - 时间签名：3/4（与 default 和 jazz 的 4/4 不同）
    - 蓝调音符：禁用
    """
    patterns, weights = get_rhythm('waltz')

    # 使用通用和声进行（与 default 相同，可适配任意音阶）
    available_progressions = [
        'I_vi_IV_V',
        'I_V_IV_vi',
        'IV_V_iii_vi_ii_V_I',
        'I_IV_V_IV',
        'vi_IV_I_V',
        'i_VI_III_VII',
        'i_iv_v_i',
        'i_VI_VII_i',
        'i_IV_i_IV',
        'i_ii_IV_V',
        'I_III_IV_I',
        'I_II_IV_V',
        'i_II_V_i',
        'I_II_III_I',
    ]

    return Style(
        name='waltz',
        bar_patterns=patterns,
        bar_pattern_weights=weights,
        available_progressions=available_progressions,
        bar_target_beats=Fraction(3, 1),
        bass_pattern='waltz_oom_pah',
        blue_notes=False,
        motif_weights=get_motif_weights('waltz'),
        default_key='C',
        default_scale='major',
        default_tempo=160,
        default_octave=4,
        default_progression='I_vi_IV_V',
    )


def _create_minuet_style() -> Style:
    """
    创建小步舞曲风格 - 纯函数
    
    返回一个新的、不可变的 Style 对象。多次调用会产生独立的对象，
    但内容相同。这是纯函数：不修改任何外部状态。
    
    风格特性：
    - 节奏型：古典小步舞曲的精细节奏
    - 低音模式：小步舞曲二拍法（minuet_duple）
    - 时间签名：3/4 拍子
    - 蓝调音符：禁用
    - 应用场景：巴洛克和古典时期舞蹈音乐
    """
    patterns, weights = get_rhythm('minuet')

    # 也复用通用和声进行
    available_progressions = [
        'I_vi_IV_V',
        'I_V_IV_vi',
        'IV_V_iii_vi_ii_V_I',
        'I_IV_V_IV',
        'vi_IV_I_V',
        'i_VI_III_VII',
        'i_iv_v_i',
        'i_VI_VII_i',
        'i_IV_i_IV',
        'i_ii_IV_V',
        'I_III_IV_I',
        'I_II_IV_V',
        'i_II_V_i',
        'I_II_III_I',
    ]

    return Style(
        name='minuet',
        bar_patterns=patterns,
        bar_pattern_weights=weights,
        available_progressions=available_progressions,
        bar_target_beats=Fraction(3, 1),
        bass_pattern='minuet_duple',
        blue_notes=False,
        motif_weights=get_motif_weights('minuet'),
        default_key='C',
        default_scale='major',
        default_tempo=160,
        default_octave=4,
        default_progression='I_vi_IV_V',
    )


def _create_chinese_style() -> Style:
    """
    创建中国风格 - 纯函数
    
    返回一个新的、不可变的 Style 对象。多次调用会产生独立的对象，
    但内容相同。这是纯函数：不修改任何外部状态。
    
    风格特性：
    - 音阶：五声音阶（pentatonic）- 中国古典音乐的精髓
    - 节奏型：温婉大气，以长音符（全音符、二分音符）为主
    - 低音模式：琶音式（arpeggio），模拟古筝意境
    - 时间签名：4/4 拍子
    - 蓝调音符：禁用
    - 速度：较慢，营造宁静致远的氛围
    - 应用场景：中国古典诗词音乐、禅意意境、宫廷音乐
    """
    patterns, weights = get_rhythm('chinese')

    # 中国特色和声进行：强调大三度、小六度、四度和五度的温柔组合
    chinese_progressions = [
        # 传统五声对应的罗马数字进行（基于五声音阶）
        'I_vi_ii_I',           # 宫-商-角-宫（推荐进行，温婉回环）
        'I_vi_IV_V',           # 宫-商-徵-羽
        'I_V_IV_vi',           # 常见变化
        'VI_IV_I_V',           # 商开头的温婉进行
        'IV_I_VI_V',           # 徵开头
        'V_I_IV_VI',           # 羽开头
        # 循环进行
        'I_IV_I_IV',           # 宫-徵循环
        'I_vi_I_vi',           # 宫-商循环
        'IV_VI_IV_VI',         # 徵-商循环
        # 小调感觉
        'i_VI_i_VI',           # 小调循环
        'vi_IV_vi_IV',         # 另一种循环
        'i_VII_VI_VII',        # 小调变化
    ]

    return Style(
        name='chinese',
        bar_patterns=patterns,
        bar_pattern_weights=weights,
        available_progressions=chinese_progressions,
        bar_target_beats=Fraction(4, 1),
        bass_pattern='arpeggio',
        blue_notes=False,
        motif_weights=get_motif_weights('chinese'),
        default_key='C',
        default_scale='pentatonic',
        default_tempo=96,  # 较慢的速度，营造宁静感
        default_octave=4,
        default_progression='I_vi_ii_I',  # 使用推荐的温婉回环进行
    )


_STYLES: Dict[str, Style] = {}


def list_styles() -> List[str]:
    """列出所有可用的风格名称（纯函数）"""
    return ['default', 'jazz', 'waltz', 'minuet', 'chinese']


def get_style(name: str) -> Style:
    """
    获取指定名称的 Style 对象
    
    这是一个引用透明的函数（相同输入总是返回等价的对象），
    使用内部缓存纯粹是为了性能优化，不改变函数的语义。
    
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
        if name == 'default':
            _STYLES[name] = _create_default_style()
        elif name == 'jazz':
            _STYLES[name] = _create_jazz_style()
        elif name == 'waltz':
            _STYLES[name] = _create_waltz_style()
        elif name == 'minuet':
            _STYLES[name] = _create_minuet_style()
        elif name == 'chinese':
            _STYLES[name] = _create_chinese_style()
    else:
        # 如果已有缓存但缺少新字段（如 motif_weights），重建一次
        cached = _STYLES[name]
        needs_refresh = False
        if getattr(cached, 'motif_weights', None) is None and name == 'chinese':
            needs_refresh = True
        if needs_refresh:
            if name == 'chinese':
                _STYLES[name] = _create_chinese_style()

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
