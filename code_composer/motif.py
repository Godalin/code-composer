"""
动机生成模块 - 独立处理基于动机的旋律生成

这个模块负责：
1. 定义各种旋律动机类型
2. 根据和弦音符生成对应的旋律序列
3. 处理八度、音高等细节
"""

from typing import List, Tuple, Optional
import random


MOTIF_TYPES = ['ascending', 'descending', 'arch', 'valley', 'repeat']

# 权重类型定义，与节奏库保持一致使用整数
MotifWeight = Tuple[str, int]
MotifWeights = List[MotifWeight]

# 动机权重预设，按风格命名，类似节奏库
MOTIF_WEIGHT_PRESETS = {
    'default': [
        ('ascending', 25),
        ('descending', 25),
        ('arch', 20),
        ('valley', 20),
        ('repeat', 10),
    ],
    'jazz': [
        ('ascending', 22),
        ('descending', 22),
        ('arch', 18),
        ('valley', 18),
        ('repeat', 20),  # 强调动机重复/呼吸
    ],
    'waltz': [
        ('ascending', 30),
        ('descending', 30),
        ('arch', 20),
        ('valley', 15),
        ('repeat', 5),
    ],
    'minuet': [
        ('ascending', 28),
        ('descending', 28),
        ('arch', 22),
        ('valley', 17),
        ('repeat', 5),
    ],
    'chinese': [
        ('ascending', 50),
        ('descending', 45),
        ('arch', 0),
        ('valley', 0),
        ('repeat', 5),
    ],
}


def choose_motif_type(
    motif_type: Optional[str],
    motif_weights: Optional[MotifWeights],
) -> str:
    """根据传入值、权重或随机选择动机类型"""
    # 如果调用方已指定，直接校验后返回
    if motif_type is not None:
        if motif_type not in MOTIF_TYPES:
            raise ValueError(f"未知的动机类型: {motif_type}。可用类型: {MOTIF_TYPES}")
        return motif_type

    # 按权重选择
    if motif_weights:
        motifs = [m for m, _ in motif_weights]
        weights = [w for _, w in motif_weights]
        return random.choices(motifs, weights=weights, k=1)[0]

    # 默认均匀随机
    return random.choice(MOTIF_TYPES)


def get_motif_weights(style_name: str) -> MotifWeights:
    """按风格名称返回动机权重预设，若未定义则均匀分布"""
    if style_name in MOTIF_WEIGHT_PRESETS:
        return MOTIF_WEIGHT_PRESETS[style_name]
    # 均匀回退
    return [(m, 1) for m in MOTIF_TYPES]


def generate_motif_notes(
    chord_notes: List[str],
    num_notes: int,
    motif_type: Optional[str] = None,
    octave: int = 4,
    use_blue_notes: bool = False,
) -> List[Tuple[str, int]]:
    """根据动机类型生成旋律音符序列"""
    motif_type = choose_motif_type(motif_type, None)
    
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
    
    if motif_type == 'ascending':
        # 上行：逐步使用和弦内的更高音符
        for i in range(num_notes):
            note_idx = (i * 2) % len(available_notes)
            oct = base_octave + (i * 2 // len(available_notes))
            oct = max(2, min(6, oct))  # 限制在有效八度范围
            notes.append((available_notes[note_idx], oct))
    
    elif motif_type == 'descending':
        # 下行：逐步使用更低的音
        for i in range(num_notes):
            note_idx = (len(available_notes) - 1 - i) % len(available_notes)
            oct = base_octave - (i // len(available_notes))
            oct = max(2, min(6, oct))
            notes.append((available_notes[note_idx], oct))
    
    elif motif_type == 'arch':
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
    
    elif motif_type == 'valley':
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
    
    elif motif_type == 'repeat':
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
