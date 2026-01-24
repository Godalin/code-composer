"""
节奏型预设与生成

节奏库按拍号分类：4/4 和 3/4（6/8 作为 3/4 对待）
每个风格通过 (权重, 节奏名称) 的元组引用节奏型

强弱级别：
- 0: 弱拍（weak）      -> vol 75
- 1: 次强拍（medium）   -> vol 85
- 2: 强拍（strong）     -> vol 95
- 3: 重音（accent）     -> vol 100
"""


from dataclasses import dataclass
import random
from typing import TypedDict


# 节奏模式：(时值列表, 强弱列表)
type RhythmPattern = tuple[list[int], list[int]]


# (权重, 节奏名称)
@dataclass(frozen=True)
class RhythmWeight:
    weight: int
    pattern: RhythmPattern


# 风格条目：(权重, 节奏名称)
class RhythmEntry(TypedDict):
    weight: int
    pattern: RhythmPattern | str


# ===== 挑选节奏 =====

def choose_rhythm(rhythm_weights: list[RhythmWeight]) -> RhythmPattern:
    """随机挑选一个节奏型"""
    if len(rhythm_weights) > 1:
        pattern_idx = random.choices(
            range(len(rhythm_weights)),
            weights=list(map(lambda r: r.weight, rhythm_weights)),
            k=1
        )[0]
    else:
        pattern_idx = 0
    return rhythm_weights[pattern_idx].pattern


# ===== 节奏库加载 =====

def _get_rhythm_library(time_signature: str) -> dict[str, RhythmPattern]:
    """获取节奏型库"""
    from .config_loader import load_rhythm_patterns
    return load_rhythm_patterns(time_signature)


def get_rhythm(time_signature: str, rhythm_name: str) -> RhythmPattern:
    """从名称获取指定拍号的节奏型"""
    from .config_loader import load_rhythm_patterns
    return load_rhythm_patterns(time_signature)[rhythm_name]


def resolve_rhythm_entry(entry: RhythmEntry, time_signature: str) -> RhythmWeight:
    """根据 节奏条目 解析出 具体条目"""
    rhythm_lib = _get_rhythm_library(time_signature)
    match entry:
        case { "weight": w, "pattern": str(name) }:
            if name not in rhythm_lib:
                raise ValueError(f"节奏名称 '{name}' 不存在于库中")
            return RhythmWeight(w, rhythm_lib[name])
        case { "weight": w, "pattern": int(name) }:
            if name not in rhythm_lib:
                raise ValueError(f"节奏名称 '{name}' 不存在于库中")
            return RhythmWeight(w, rhythm_lib[name])
        case { "weight": w, "pattern": pat } if not isinstance(pat, str):
            return RhythmWeight(w, (pat["durations"], pat["accents"]))
        case _:
            raise TypeError("不支持的条目")


def resolve_rhythm_entries(entries: list[RhythmEntry], time_signature: str) -> list[RhythmWeight]:
    """根据 (权重, 名称) 列表和节奏库解析出最终的 (模式列表, 权重列表)"""
    return list(map(lambda e: resolve_rhythm_entry(e, time_signature), entries))


def get_style_rhythm(style: str) -> list[RhythmWeight]:
    """根据风格名称获取节奏预设"""
    from .config_loader import get_style_rhythm_weights, load_style
    
    # 获取该风格的配置
    style_config = load_style(style)
    time_signature = style_config.get('time_signature', '4/4')
    
    # 获取节奏权重配置
    entries = get_style_rhythm_weights(style)
    
    # 加载节奏库并解析
    return resolve_rhythm_entries(entries, time_signature)


def list_rhythm_styles() -> list[str]:
    from .config_loader import list_available_styles
    return list_available_styles()
