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

from typing import List, Tuple, Dict

# 节奏模式：(时值列表, 强弱列表)
RhythmPattern = Tuple[List[int], List[int]]
# 风格条目：(权重, 节奏名称)
StyleEntry = Tuple[int, str]
# 最终预设：(模式列表, 权重列表)
RhythmPreset = Tuple[List[RhythmPattern], List[int]]

# ===== 节奏库加载 =====

def _get_rhythm_library(time_signature: str) -> Dict[str, RhythmPattern]:
    """获取节奏型库（带缓存）"""
    from .config_loader import load_rhythm_patterns
    return load_rhythm_patterns(time_signature)


def get_rhythm(time_signature: str, rhythm_name: str) -> RhythmPattern:
    """从名称获取指定拍号的节奏型"""
    from .config_loader import load_rhythm_patterns
    return load_rhythm_patterns(time_signature)[rhythm_name]


def _resolve_rhythm_entries(entries: List[StyleEntry], time_signature: str) -> RhythmPreset:
    """根据 (权重, 名称) 列表和节奏库解析出最终的 (模式列表, 权重列表)"""
    rhythm_lib = _get_rhythm_library(time_signature)
    patterns = []
    weights = []
    for weight, name in entries:
        if name not in rhythm_lib:
            raise ValueError(f"节奏名称 '{name}' 不存在于库中")
        patterns.append(rhythm_lib[name])
        weights.append(weight)
    return patterns, weights


def get_style_rhythm(style: str) -> RhythmPreset:
    """根据风格名称获取节奏预设"""
    from .config_loader import get_style_rhythm_weights, load_style
    
    # 获取该风格的配置
    style_config = load_style(style)
    time_signature = style_config.get('time_signature', '4/4')
    
    # 获取节奏权重配置
    entries = get_style_rhythm_weights(style)
    
    # 加载节奏库并解析
    return _resolve_rhythm_entries(entries, time_signature)


def list_rhythm_styles() -> List[str]:
    from .config_loader import list_available_styles
    return list_available_styles()
