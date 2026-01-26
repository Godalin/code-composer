"""
风格定义与管理

将节奏、可用和声进行等风格信息与谱曲器解耦。
从配置文件加载所有风格定义。
"""


from fractions import Fraction
from typing import Any

from pydantic import BaseModel, model_validator

from .rhythms import RhythmWeight, RhythmEntry, RhythmPattern, get_rhythm_library
from .motif import MotifWeight


class Style(BaseModel):
    """
    音乐风格定义 - 完整封装风格的所有特性

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
    rhythm_entries: list[RhythmEntry]
    motif_weights: list[MotifWeight]
    bass_pattern: str = 'block'
    key: str = 'C'
    scale: str = 'major'
    tempo: int = 120
    octave: int = 4
    progression: str = '1-6min-4-5'
    progressions: list[str] = []
    instrument: str = 'violin'

    @model_validator(mode='before')
    @classmethod
    def style_validator(cls, data: dict[str, Any]) -> dict[str, Any]:
        data = dict(data)
        data['rhythm_entries'] = data.pop('rhythm_weights')
        data['progressions'] = data.pop('progression_sources')
        return data

    @property
    def bar_target_beats(self) -> Fraction:
        numer, denom = self.time_signature.split('/')
        return Fraction(int(numer), int(denom))

    def resolve_rhythm_entry(self, entry: RhythmEntry) -> RhythmWeight:
        """根据节奏条目解析出具体节奏型"""
        rhythm_lib = get_rhythm_library(self.time_signature)
        match entry:
            case RhythmEntry(weight=w, pattern=str(name)):
                return RhythmWeight(weight=w, pattern=rhythm_lib[name])
            case RhythmEntry(weight=w, pattern=RhythmPattern() as p):
                return RhythmWeight(weight=w, pattern=p)
            case _:
                raise TypeError("不支持的条目")

    @property
    def rhythm_weights(self) -> list[RhythmWeight]:
        return [ self.resolve_rhythm_entry(re) for re in self.rhythm_entries ]
    
    # @property
    # def progressions(self) -> dict[str, list[tuple[str, list[str]]]]:
    #     from .config_loader import load_multiple_progressions
    #     return load_multiple_progressions(self.progression_sources)


_STYLES: dict[str, Style] = {}


def list_styles() -> list[str]:
    """列出所有可用的风格名称"""
    from .config_loader import list_available_styles
    return list_available_styles()


def get_style(name: str) -> Style:
    """获取指定名称的 Style 对象"""
    from .config_loader import load_style
    if name not in list_styles():
        raise ValueError(f"未知的风格: {name}")

    if name not in _STYLES:
        _STYLES[name] = load_style(name)

    return _STYLES[name]


def create_style_with(style_name: str, **kwargs) -> Style:
    """从风格名称和可选参数构造 Style 对象"""
    base_style = get_style(style_name)
    if base_style is None:
        raise ValueError(f"未知的风格: {style_name}。可用风格: {list_styles()}")
    kwargs = { k : v for k, v in kwargs.items() if v is not None }
    return base_style.model_copy(update=kwargs)
