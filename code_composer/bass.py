"""
低音（伴奏）生成模块

支持多种低音模式：
- block: 整小节长音（根音堆叠）
- double: 根与五音交替
- arpeggio: 分解和弦
- pendulum: 摇摆模式
- waltz_oom_pah: 圆舞曲风格（Oom-Pah-Pah）
- minuet_duple: 小步舞曲风格（强-弱-弱）

易于扩展：添加新模式只需在此模块中添加新函数
"""

from fractions import Fraction
from typing import List, Callable, Dict

from .structures import Note
from .theory import Chord
from .durations import duration_to_beats, fill_rests


def _finish_bar(
    groups: List[List[Note]],
    durations: List[str],
    target: Fraction,
) -> List[List[Note]]:
    """补齐小节到目标拍数"""
    total = sum(duration_to_beats(d) for d in durations)
    if total < target:
        for r in fill_rests(target - total):
            groups.append([Note(name='r', octave=None, velocity=0, duration=r[1:])])
    return groups


def _take(n: int, seq: List[str]) -> List[str]:
    """从序列中循环取 n 个元素"""
    return [seq[i % len(seq)] for i in range(n)] if seq else ['r'] * n


# ===== 低音模式生成函数 =====

def _bass_block(
    chord_notes: List[str],
    bass_octave: int,
    bar_target_beats: Fraction,
) -> List[List[Note]]:
    """Block 模式：整小节长音（根音堆叠）"""
    base = chord_notes if chord_notes else ['r']
    target = bar_target_beats
    
    if target == Fraction(3, 1):
        # 3/4：二分音符堆叠 + 四分音符单音
        durations = ['2', '4']
        groups = [
            [Note(name=n, octave=bass_octave, velocity=85, duration='2') for n in base],
            [Note(name=base[0], octave=bass_octave, velocity=80, duration='4')],
        ]
    else:
        # 4/4：全音符堆叠
        durations = ['1']
        groups = [[Note(name=n, octave=bass_octave, velocity=85, duration='1') for n in base]]
    
    return _finish_bar(groups, durations, target)


def _bass_double(
    chord_notes: List[str],
    bass_octave: int,
    bar_target_beats: Fraction,
) -> List[List[Note]]:
    """Double 模式：根与五音交替"""
    base = chord_notes if chord_notes else ['r']
    target = bar_target_beats
    fifth = base[2] if len(base) > 2 else base[0]
    
    if target == Fraction(3, 1):
        # 3/4：二分根音 + 四分五音
        durations = ['2', '4']
        groups = [
            [Note(name=base[0], octave=bass_octave, velocity=85, duration='2')],
            [Note(name=fifth, octave=bass_octave, velocity=80, duration='4')],
        ]
    else:
        # 4/4：两个二分音符
        durations = ['2', '2']
        groups = [
            [Note(name=base[0], octave=bass_octave, velocity=85, duration='2')],
            [Note(name=fifth, octave=bass_octave, velocity=80, duration='2')],
        ]
    
    return _finish_bar(groups, durations, target)


def _bass_arpeggio(
    chord_notes: List[str],
    bass_octave: int,
    bar_target_beats: Fraction,
) -> List[List[Note]]:
    """Arpeggio 模式：分解和弦"""
    base = chord_notes if chord_notes else ['r']
    target = bar_target_beats
    volume_map = [90, 80, 85, 80, 90, 80, 85, 80]
    
    count = 6 if target == Fraction(3, 1) else 8
    seq = _take(4, [base[0], base[1] if len(base) > 1 else base[0], 
                     base[2] if len(base) > 2 else base[0], base[0]])
    durations = ['8'] * count
    vols = volume_map[:count]
    groups = [[Note(name=seq[i % 4], octave=bass_octave, velocity=vols[i], duration='8')] 
              for i in range(count)]
    
    return _finish_bar(groups, durations, target)


def _bass_pendulum(
    chord_notes: List[str],
    bass_octave: int,
    bar_target_beats: Fraction,
) -> List[List[Note]]:
    """Pendulum 模式：摇摆模式"""
    base = chord_notes if chord_notes else ['r']
    target = bar_target_beats
    volume_map = [90, 80, 85, 80, 90, 80, 85, 80]
    
    count = 6 if target == Fraction(3, 1) else 8
    seq = _take(4, [base[0], base[1] if len(base) > 1 else base[0],
                     base[2] if len(base) > 2 else base[0], base[1] if len(base) > 1 else base[0]])
    durations = ['8'] * count
    vols = volume_map[:count]
    groups = [[Note(name=seq[i % 4], octave=bass_octave, velocity=vols[i], duration='8')] 
              for i in range(count)]
    
    return _finish_bar(groups, durations, target)


def _bass_waltz_oom_pah(
    chord_notes: List[str],
    bass_octave: int,
    bar_target_beats: Fraction,
) -> List[List[Note]]:
    """Waltz Oom-Pah-Pah 模式：圆舞曲风格"""
    base = chord_notes if chord_notes else ['r']
    target = bar_target_beats
    
    notes = [base[0], base[1] if len(base) > 1 else base[0], 
             base[2] if len(base) > 2 else base[0]]
    durations = ['4', '4', '4']
    vols = [90, 75, 75]
    groups = [Note(name=notes[i], octave=bass_octave, velocity=vols[i], duration=durations[i])
              for i in range(3)]
    groups = [[n] for n in groups]  # 每个音符包装成列表
    
    return _finish_bar(groups, durations, target)


def _bass_minuet_duple(
    chord_notes: List[str],
    bass_octave: int,
    bar_target_beats: Fraction,
) -> List[List[Note]]:
    """Minuet Duple 模式：小步舞曲风格（6/8）"""
    base = chord_notes if chord_notes else ['r']
    target = bar_target_beats
    
    notes = _take(3, [base[0], base[1] if len(base) > 1 else base[0],
                       base[2] if len(base) > 2 else base[0]])
    durations = ['8'] * 6
    groups = []
    for i in range(6):
        vol = 90 if i % 3 == 0 else 75
        groups.append([Note(name=notes[i % 3], octave=bass_octave, velocity=vol, duration='8')])
    
    return _finish_bar(groups, durations, target)


# 低音模式路由表
BASS_PATTERNS: Dict[str, Callable[[List[str], int, Fraction], List[List[Note]]]] = {
    'block': _bass_block,
    'double': _bass_double,
    'arpeggio': _bass_arpeggio,
    'pendulum': _bass_pendulum,
    'waltz_oom_pah': _bass_waltz_oom_pah,
    'minuet_duple': _bass_minuet_duple,
}


def generate_bass_bar(
    chord: Chord,
    bass_pattern_mode: str,
    bar_target_beats: Fraction,
    octave: int,
) -> List[List[Note]]:
    """
    根据低音模式生成一个小节的低音
    
    参数：
    - chord: 和弦（Pitch 对象列表）
    - bass_pattern_mode: 低音模式名称（'block', 'double', 'arpeggio' 等）
    - bar_target_beats: 小节目标拍数
    - octave: 旋律八度（低音八度 = octave - 1）
    
    返回：
    - 低音小节的音符组列表
    """
    chord_notes = [p.name for p in chord]
    bass_octave = octave - 1
    
    if not chord_notes:
        return [[Note(name='r', octave=None, velocity=0, duration='1')]]
    
    # 查找对应的低音生成函数
    bass_gen_func = BASS_PATTERNS.get(bass_pattern_mode)
    if bass_gen_func is None:
        # 默认使用 arpeggio 模式
        bass_gen_func = BASS_PATTERNS['arpeggio']
    
    return bass_gen_func(chord_notes, bass_octave, bar_target_beats)


def list_bass_patterns() -> List[str]:
    """返回所有可用的低音模式"""
    return list(BASS_PATTERNS.keys())
