"""
动机生成模块（生成器版本）
每个动机类型都是一个独立的生成器函数，按需逐个产生音符
"""

import random
from enum import Enum
from typing import Generator, List, Optional, Tuple
from .theory import Pitch, Chord, ScalePitches


class Motif(Enum):
    """旋律动机类型枚举"""
    ASCENDING = "ascending"   # 上行
    DESCENDING = "descending" # 下行
    ARCH = "arch"             # 拱形
    VALLEY = "valley"         # 谷形
    REPEAT = "repeat"         # 重复
    RANDOM = "random"         # 随机


MotifWeight = Tuple[int, Motif]


# 动机权重预设
MOTIF_WEIGHT_PRESETS = {
    'default': [
        (25, Motif.ASCENDING),
        (25, Motif.DESCENDING),
        (20, Motif.ARCH),
        (20, Motif.VALLEY),
        (5, Motif.REPEAT),
        (5, Motif.RANDOM),
    ],
    'jazz': [
        (22, Motif.ASCENDING),
        (22, Motif.DESCENDING),
        (18, Motif.ARCH),
        (18, Motif.VALLEY),
        (10, Motif.REPEAT),
        (10, Motif.RANDOM),
    ],
    'waltz': [
        (30, Motif.ASCENDING),
        (30, Motif.DESCENDING),
        (20, Motif.ARCH),
        (12, Motif.VALLEY),
        (5, Motif.REPEAT),
        (3, Motif.RANDOM),
    ],
    'minuet': [
        (28, Motif.ASCENDING),
        (28, Motif.DESCENDING),
        (22, Motif.ARCH),
        (15, Motif.VALLEY),
        (5, Motif.REPEAT),
        (2, Motif.RANDOM),
    ],
    'chinese': [
        (50, Motif.ASCENDING),
        (40, Motif.DESCENDING),
        (0, Motif.ARCH),
        (0, Motif.VALLEY),
        (5, Motif.REPEAT),
        (5, Motif.RANDOM),
    ],
}


def choose_motif_type(weights: List[MotifWeight]) -> Motif:
    """根据权重随机选择动机类型"""
    if not weights:
        return random.choice(list(Motif))
    
    motifs = [m for _, m in weights]
    weight_vals = [w for w, _ in weights]
    return random.choices(motifs, weights=weight_vals, k=1)[0]


def get_motif_weights(style_name: str) -> List[MotifWeight]:
    """按风格名称返回动机权重预设"""
    if style_name in MOTIF_WEIGHT_PRESETS:
        return MOTIF_WEIGHT_PRESETS[style_name]
    return [(1, m) for m in Motif]


# ===== 辅助函数 =====

def _find_start_pitch(chord: Chord, octave_hint: int) -> Pitch:
    """找到最接近目标八度的和弦音作为起点"""
    candidates = [p for p in chord if abs(p.octave - octave_hint) <= 1]
    if not candidates:
        candidates = list(chord)
    candidates.sort(key=lambda p: (abs(p.octave - octave_hint), Pitch.note_index(p.name)))
    return candidates[0]


def _find_next_ascending(current: Pitch, scale_pitches: ScalePitches) -> Optional[Pitch]:
    """找下一个更高的音阶音"""
    next_idx = Pitch.note_index(current.name)
    candidates = [p for p in scale_pitches 
                 if Pitch.note_index(p.name) > next_idx 
                 and p.octave >= current.octave and p.octave <= 6]
    if not candidates:
        # 尝试下一个八度的第一个音
        candidates = [p for p in scale_pitches 
                     if p.octave == current.octave + 1 and p.octave <= 6]
    return candidates[0] if candidates else None


def _find_next_descending(current: Pitch, scale_pitches: ScalePitches) -> Optional[Pitch]:
    """找下一个更低的音阶音"""
    next_idx = Pitch.note_index(current.name)
    candidates = [p for p in scale_pitches 
                 if Pitch.note_index(p.name) < next_idx 
                 and p.octave <= current.octave and p.octave >= 3]
    if not candidates:
        candidates = [p for p in scale_pitches 
                     if p.octave == current.octave - 1 and p.octave >= 3]
    return candidates[-1] if candidates else None


# ===== 生成器函数 =====

def ascending_motif(
    chord: Chord,
    scale_pitches: ScalePitches,
    octave_hint: int = 4,
) -> Generator[Pitch, None, None]:
    """上行动机生成器 - 沿音阶逐步上升"""
    current = _find_start_pitch(chord, octave_hint)
    
    while True:
        yield current
        next_pitch = _find_next_ascending(current, scale_pitches)
        if next_pitch:
            current = next_pitch
        # 如果没有更高的音，保持当前音


def descending_motif(
    chord: Chord,
    scale_pitches: ScalePitches,
    octave_hint: int = 4,
) -> Generator[Pitch, None, None]:
    """下行动机生成器 - 沿音阶逐步下降"""
    current = _find_start_pitch(chord, octave_hint)
    
    while True:
        yield current
        next_pitch = _find_next_descending(current, scale_pitches)
        if next_pitch:
            current = next_pitch


def arch_motif(
    chord: Chord,
    scale_pitches: ScalePitches,
    octave_hint: int = 4,
) -> Generator[Pitch, None, None]:
    """拱形动机生成器 - 前半上行，后半下行"""
    current = _find_start_pitch(chord, octave_hint)
    step = 0
    direction = 1  # 1=上行，-1=下行
    
    while True:
        yield current
        # 在第3步切换方向（简单的拱形）
        step += 1
        if step == 3:
            direction = -1
        
        if direction == 1:
            next_pitch = _find_next_ascending(current, scale_pitches)
            if next_pitch:
                current = next_pitch
        else:
            next_pitch = _find_next_descending(current, scale_pitches)
            if next_pitch:
                current = next_pitch


def valley_motif(
    chord: Chord,
    scale_pitches: ScalePitches,
    octave_hint: int = 4,
) -> Generator[Pitch, None, None]:
    """谷形动机生成器 - 前半下行，后半上行"""
    current = _find_start_pitch(chord, octave_hint)
    step = 0
    direction = -1  # -1=下行，1=上行
    
    while True:
        yield current
        # 在第3步切换方向
        step += 1
        if step == 3:
            direction = 1
        
        if direction == -1:
            next_pitch = _find_next_descending(current, scale_pitches)
            if next_pitch:
                current = next_pitch
        else:
            next_pitch = _find_next_ascending(current, scale_pitches)
            if next_pitch:
                current = next_pitch


def repeat_motif(
    chord: Chord,
    scale_pitches: ScalePitches,
    octave_hint: int = 4,
) -> Generator[Pitch, None, None]:
    """重复动机生成器 - 保持在起始音或小幅摆动"""
    base = _find_start_pitch(chord, octave_hint)
    
    while True:
        yield base
        # 30%概率在邻近音之间摆动
        neighbors = [p for p in scale_pitches 
                    if abs(Pitch.note_index(p.name) - Pitch.note_index(base.name)) <= 2 
                    and p.octave == base.octave]
        if neighbors and random.random() < 0.3:
            base = random.choice(neighbors)


def random_motif(
    chord: Chord,
    scale_pitches: ScalePitches,
    octave_hint: int = 4,
) -> Generator[Pitch, None, None]:
    """随机动机生成器 - 随机选择方向（上升/下降）"""
    current = _find_start_pitch(chord, octave_hint)
    
    while True:
        yield current
        # 50%概率选择上升或下降
        direction = random.choice([1, -1])
        if direction == 1:
            next_pitch = _find_next_ascending(current, scale_pitches)
        else:
            next_pitch = _find_next_descending(current, scale_pitches)
        
        if next_pitch:
            current = next_pitch


# ===== 工厂函数 =====

def create_motif_generator(
    chord: Chord,
    scale_pitches: ScalePitches,
    motif_type: Motif,
    octave_hint: int = 4,
) -> Generator[Pitch, None, None]:
    """
    工厂函数 - 根据动机类型返回对应的生成器
    
    参数：
        chord: 当前和弦音（List[Pitch]）
        scale_pitches: 当前调式的完整音阶（一个八度）
        motif_type: 动机类型
        octave_hint: 起始八度提示
    
    返回：
        Generator[Pitch, None, None]：无限生成音符的生成器
    """
    if motif_type == Motif.ASCENDING:
        return ascending_motif(chord, scale_pitches, octave_hint)
    elif motif_type == Motif.DESCENDING:
        return descending_motif(chord, scale_pitches, octave_hint)
    elif motif_type == Motif.ARCH:
        return arch_motif(chord, scale_pitches, octave_hint)
    elif motif_type == Motif.VALLEY:
        return valley_motif(chord, scale_pitches, octave_hint)
    elif motif_type == Motif.REPEAT:
        return repeat_motif(chord, scale_pitches, octave_hint)
    elif motif_type == Motif.RANDOM:
        return random_motif(chord, scale_pitches, octave_hint)
    else:
        # 默认上行
        return ascending_motif(chord, scale_pitches, octave_hint)
