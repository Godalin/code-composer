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

from dataclasses import replace
from fractions import Fraction
from typing import List, Dict, TypedDict

from .structures import Note
from .theory import Chord
from .durations import duration_to_beats, fill_rests
from .rhythms import get_rhythm


def _finish_bar(
    groups: List[List[Note]],
    durations: List[int],
    target: Fraction,
) -> List[List[Note]]:
    """补齐小节到目标拍数"""
    total = sum(duration_to_beats(d) for d in durations)
    if total < target:
        for r in fill_rests(target - total):
            groups.append([Note(pitch=None, duration=r)])
    return groups


def _take(n: int, seq: List[str]) -> List[str]:
    """从序列中循环取 n 个元素"""
    return [seq[i % len(seq)] for i in range(n)] if seq else ['r'] * n


# ===== 从低音模板生成伴奏 =====

class BassPattern(TypedDict):
    name: str
    pattern: List[List[int]]
    rhythm: str


def gen_bass_from_template(
    chord: Chord,
    bass_octave: int,
    bar_target_beats: Fraction,
    bass_pattern: BassPattern,
    time_signature: str,
    velocity: int = 85,
) -> List[List[Note]]:
    """通用模板转低音生成函数"""
    volume_map = {0: 75, 1: 80, 2: 85, 3: 95}
    rhythm_pattern = get_rhythm(time_signature, bass_pattern['rhythm'])

    groups : List[List[Note]] = []
    for idxs, (dur, vol) in zip(bass_pattern["pattern"], zip(*rhythm_pattern)):
        if idxs[0] == 0:
            groups.append([Note(pitch=replace(p, octave=bass_octave),
                duration=dur, velocity=volume_map[vol]) for p in chord])
        else:
            groups.append([Note(pitch=replace(chord[(i-1) % len(chord)],    
                octave=bass_octave), duration=dur, velocity=volume_map[vol])
                    for i in idxs])
    
    return _finish_bar(groups, rhythm_pattern[0], bar_target_beats)


# ===== 低音库加载 =====

def _get_bass_library(time_signature: str) -> Dict[str, BassPattern]:
    """获取节奏型库（带缓存）"""
    from .config_loader import load_bass_patterns
    return load_bass_patterns(time_signature)


def list_bass_patterns(time_signature: str):
    """返回所有可用的低音模式"""
    return _get_bass_library(time_signature).keys()


def gen_bar_bass(
    chord: Chord,
    octave: int,
    bar_target_beats: Fraction,
    time_signature: str,
    bass_mode: str = 'arpeggio',
) -> List[List[Note]]:
    """根据低音模式名称生成一个小节的低音"""
    bass_octave = octave - 1
    
    # 查找对应的低音生成函数
    return gen_bass_from_template(
        chord, bass_octave, bar_target_beats,
        _get_bass_library(time_signature)[bass_mode],
        time_signature,
    )
