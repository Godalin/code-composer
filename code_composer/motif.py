"""
动机生成模块（生成器版本）
每个动机类型都是一个独立的生成器函数，按需逐个产生音符
"""

import random
from pprint import pprint
from typing import Generator, List, Tuple

from .theory import Pitch, Chord, ScalePitches



MotifPattern = List[List[int]]  # 外层为分段，内层为该段 pattern
MotifWeight = Tuple[int, str]   # (权重, motif_name)
MotifGenerator = Generator[Pitch, None, None]


def choose_motif_type(weights: List[MotifWeight]) -> str:
    """根据权重随机选择动机类型（motif_name）"""
    from .config_loader import load_motifs
    if not weights:
        motifs = list(load_motifs().keys())
        return random.choice(motifs)
    motifs = [m for _, m in weights]
    weight_vals = [w for w, _ in weights]
    return random.choices(motifs, weights=weight_vals, k=1)[0]


def get_motif_weights(style_name: str) -> List[MotifWeight]:
    """按风格名称返回动机权重预设 (motif_name)"""
    from .config_loader import get_style_motif_weights
    entries = get_style_motif_weights(style_name)
    return [(weight, name) for weight, name in entries]


# ===== 辅助函数 =====

def _find_start_pitch(chord: Chord, octave_hint: int) -> Pitch:
    """找到最接近目标八度的和弦音作为起点"""
    candidates = [p for p in chord if abs(p.octave - octave_hint) <= 1]
    if not candidates:
        candidates = list(chord)
    candidates.sort(key=lambda p: (abs(p.octave - octave_hint), Pitch.note_index(p.name)))
    return candidates[0]


def _find_next_ascending(current: Pitch, scale_pitches: ScalePitches) -> Pitch:
    """找下一个更高的音阶音"""
    candidates = ([Pitch(p.name, current.octave) for p in scale_pitches]
                + [Pitch(p.name, current.octave + 1) for p in scale_pitches]
                + [Pitch(p.name, current.octave + 2) for p in scale_pitches])
    while True:
        if current in candidates:
            current_idx = candidates.index(current)
            break
        else:
            current = current.transpose(1)
    return candidates[current_idx+1]


def _find_next_descending(current: Pitch, scale_pitches: ScalePitches) -> Pitch:
    """找下一个更低的音阶音"""
    candidates = ([Pitch(p.name, current.octave - 2) for p in scale_pitches]
                + [Pitch(p.name, current.octave - 1) for p in scale_pitches]
                + [Pitch(p.name, current.octave) for p in scale_pitches])
    while True:
        if current in candidates:
            current_idx = candidates.index(current)
            break
        else:
            current = current.transpose(-1)
    return candidates[current_idx-1]


# ===== 生成器函数 =====

def random_motif(
    chord: Chord,
    scale_pitches: ScalePitches,
    octave_hint: int = 4,
) -> MotifGenerator:
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


# ===== pattern 驱动动机生成器 =====

def gen_motif_generator(
    chord: Chord,
    scale_pitches: ScalePitches,
    motif_pattern: MotifPattern,
    n_steps: int = 8,
    octave_hint: int = 4,
) -> MotifGenerator:
    """从 MotifPattern 生成 MotifGenerator"""

    # 以和弦音为起点
    current = _find_start_pitch(chord, octave_hint)
    n_segments = len(motif_pattern)
    seg_idx = 0
    step_in_seg = 0
    while True:
        yield current
        seg_pattern = motif_pattern[seg_idx]
        offset = seg_pattern[step_in_seg % len(seg_pattern)]
        # offset > 0: 上行, < 0: 下行, =0: 保持
        if offset > 0:
            for _ in range(abs(offset)):
                current = _find_next_ascending(current, scale_pitches)
        elif offset < 0:
            for _ in range(abs(offset)):
                current = _find_next_descending(current, scale_pitches)
        # offset == 0: 保持 current 不变
        step_in_seg += 1
        # 按 n_steps 均分 pattern 周期，切换到下一个分段
        if n_steps > 0:
            seg_len = n_steps // n_segments + (1 if seg_idx < n_steps % n_segments else 0)
            if step_in_seg >= seg_len:
                seg_idx = (seg_idx + 1) % n_segments
                step_in_seg = 0


def create_motif_generator (
    chord: Chord,
    scale_pitches: ScalePitches,
    motif_type: str,
    n_steps: int = 8,
    octave_hint: int = 4,
) -> MotifGenerator:
    """从动机名称生成 MotifGenerator"""

    print(f"使用动机 {motif_type}")

    from .config_loader import load_motifs
    motif_lib = load_motifs()
    if motif_type not in motif_lib.keys():
        raise  ValueError(f"不存在的动机：{motif_type}")
    motif_pattern = motif_lib[motif_type]["pattern"]
    return gen_motif_generator(
        chord, scale_pitches, motif_pattern, n_steps, octave_hint)
