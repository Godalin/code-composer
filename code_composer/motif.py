"""
动机生成模块 - 独立处理基于动机的旋律生成

这个模块负责：
1. 定义各种旋律动机类型
2. 根据和弦音符生成对应的旋律序列
3. 处理八度、音高等细节
"""

from enum import Enum
from typing import List, Tuple
import random


class MotifType(Enum):
    """律动机类型枚举"""
    ASCENDING = 'ascending'
    DESCENDING = 'descending'
    ARCH = 'arch'
    VALLEY = 'valley'
    REPEAT = 'repeat'

# 权重类型定义，与节奏库保持一致使用整数
MotifWeight = Tuple[int, MotifType]  # (weight, motif_type)

# 动机权重预设，按风格命名，类似节奏库
MOTIF_WEIGHT_PRESETS = {
    'default': [
        (25, MotifType.ASCENDING),
        (25, MotifType.DESCENDING),
        (20, MotifType.ARCH),
        (20, MotifType.VALLEY),
        (10, MotifType.REPEAT),
    ],
    'jazz': [
        (22, MotifType.ASCENDING),
        (22, MotifType.DESCENDING),
        (18, MotifType.ARCH),
        (18, MotifType.VALLEY),
        (20, MotifType.REPEAT),  # 强调动机重复/呼吸
    ],
    'waltz': [
        (30, MotifType.ASCENDING),
        (30, MotifType.DESCENDING),
        (20, MotifType.ARCH),
        (15, MotifType.VALLEY),
        (5, MotifType.REPEAT),
    ],
    'minuet': [
        (28, MotifType.ASCENDING),
        (28, MotifType.DESCENDING),
        (22, MotifType.ARCH),
        (17, MotifType.VALLEY),
        (5, MotifType.REPEAT),
    ],
    'chinese': [
        (50, MotifType.ASCENDING),
        (45, MotifType.DESCENDING),
        (0, MotifType.ARCH),
        (0, MotifType.VALLEY),
        (5, MotifType.REPEAT),
    ],
}


def choose_motif_type(motif_weights: List[MotifWeight]) -> MotifType:
    """根据权重选择动机类型，空列表时均匀选择"""
    # 按权重选择
    if motif_weights:
        weights = [w for w, _ in motif_weights]
        motifs = [m for _, m in motif_weights]
        return random.choices(motifs, weights=weights, k=1)[0]

    # 默认均匀随机
    return random.choice(list(MotifType))


def get_motif_weights(style_name: str) -> List[MotifWeight]:
    """按风格名称返回动机权重预设，若未定义则均匀分布"""
    if style_name in MOTIF_WEIGHT_PRESETS:
        return MOTIF_WEIGHT_PRESETS[style_name]
    # 均匀回退
    return [(1, m) for m in MotifType]


def generate_motif_notes(
    chord_notes: List[str],
    num_notes: int,
    motif_type: MotifType,
    octave: int = 4,
    use_blue_notes: bool = False,
) -> List[Tuple[str, int]]:
    """根据动机类型生成旋律音符序列"""
    # 如果启用蓝调音符，扩展可用音符
    available_notes = list(chord_notes)
    if use_blue_notes:
        blue_note_map = {
            'c': ['d#', 'f#'],     # ♭3, ♭5
            'd': ['f'],            # ♭3
            'e': ['f#', 'g#'],     # ♭2, ♭3
            'f': ['g#', 'a#'],     # ♭3, ♭5
            'g': ['a#'],           # ♭3
            'a': ['c', 'd#'],      # ♭2(b# = c), ♭3
            'b': ['d#'],           # ♭2
        }
        extended_notes = []
        for note in available_notes:
            extended_notes.append(note)
            if note in blue_note_map:
                extended_notes.extend(blue_note_map[note])
        available_notes = extended_notes
    
    notes = []
    base_octave = octave
    
    if motif_type == MotifType.ASCENDING:
        # 上行：逐步使用和弦内的更高音符
        for i in range(num_notes):
            note_idx = (i * 2) % len(available_notes)
            oct = base_octave + (i * 2 // len(available_notes))
            oct = max(2, min(6, oct))  # 限制在有效八度范围
            notes.append((available_notes[note_idx], oct))
    
    elif motif_type == MotifType.DESCENDING:
        # 下行：逐步使用更低的音
        for i in range(num_notes):
            note_idx = (len(available_notes) - 1 - i) % len(available_notes)
            oct = base_octave - (i // len(available_notes))
            oct = max(2, min(6, oct))
            notes.append((available_notes[note_idx], oct))
    
    elif motif_type == MotifType.ARCH:
        # 拱形：先上升后下降
        mid = num_notes // 2
        for i in range(num_notes):
            if i < mid:
                # 前半段上升
                note_idx = (i * 2) % len(available_notes)
                oct = base_octave
            else:
                # 后半段下降
                note_idx = ((num_notes - i) * 2) % len(available_notes)
                oct = base_octave
            notes.append((available_notes[note_idx], oct))
    
    elif motif_type == MotifType.VALLEY:
        # 谷形：先下降后上升
        mid = num_notes // 2
        for i in range(num_notes):
            if i < mid:
                # 前半段下降
                note_idx = (len(available_notes) - 1 - i) % len(available_notes)
                oct = base_octave
            else:
                # 后半段上升
                note_idx = (i - mid) % len(available_notes)
                oct = base_octave
            notes.append((available_notes[note_idx], oct))
    
    elif motif_type == MotifType.REPEAT:
        # 重复：停留在同一个音
        note = random.choice(available_notes)
        for _ in range(num_notes):
            notes.append((note, base_octave))
    
    return notes


def build_alda_notes(
    motif_notes: List[Tuple[str, int]],
    durations: List[str],
    accents: List[int],
) -> List[str]:
    """将动机音符与节奏、重音信息组合成 Alda 格式"""
    volume_map = {0: 75, 1: 80, 2: 85, 3: 95}
    bar_parts = []
    current_octave = None
    
    for note_idx, (note_name, octave) in enumerate(motif_notes):
        duration = durations[note_idx] if note_idx < len(durations) else '4'
        accent = accents[note_idx] if note_idx < len(accents) else 0
        volume = volume_map.get(accent, 80)
        
        # 如果八度变化，添加八度标记
        if octave != current_octave:
            bar_parts.append(f"o{octave}")
            current_octave = octave
        
        bar_parts.append(f"(vol {volume}) {note_name}{duration}")
    
    return bar_parts
