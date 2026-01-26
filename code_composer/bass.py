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
from typing import Any

from pydantic import BaseModel, field_validator

from .structures import Note
from .theory import Chord
from .durations import duration_to_beats, fill_rests
from .rhythms import get_rhythm


def _finish_bar(
    groups: list[list[Note]],
    durations: list[int],
    target: Fraction,
) -> list[list[Note]]:
    """补齐小节到目标拍数"""
    total = sum(duration_to_beats(d) for d in durations)
    if total < target:
        for r in fill_rests(target - total):
            groups.append([Note(pitch=None, duration=r)])
    return groups


def _take(n: int, seq: list[str]) -> list[str]:
    """从序列中循环取 n 个元素"""
    return [seq[i % len(seq)] for i in range(n)] if seq else ['r'] * n


# ===== 从低音模板生成伴奏 =====

class BassPattern(BaseModel):
    name: str | None = None
    pattern: list[list[int]]
    rhythm: str

    @field_validator('rhythm', mode='before')
    @classmethod
    def pattern_validator(cls, data : Any) -> str:
        match data:
            case int(i):
                return str(i)
            case _:
                return data


def gen_bass_from_template(
    time_signature: str,
    bar_target_beats: Fraction,
    bass_pattern: BassPattern,
    volume: int,
    octave: int,
    chord: Chord,
) -> list[list[Note]]:
    """通用模板转低音生成函数"""
    volume_map = {i : volume + i * 5 for i in range(4) }
    rhythm_pattern = get_rhythm(time_signature, bass_pattern.rhythm)

    groups : list[list[Note]] = []
    for idxs, (dur, vol) in zip(bass_pattern.pattern, zip(rhythm_pattern.durations, rhythm_pattern.accents)):
        if idxs[0] == 0:
            groups.append([Note(pitch=replace(p, octave=octave), 
                duration=dur, velocity=volume_map[vol]) for p in chord])
        else:
            groups.append([Note(pitch=replace(chord[(i-1) % len(chord)],    
                octave=octave), duration=dur, velocity=volume_map[vol])
                    for i in idxs])
    
    return _finish_bar(groups, rhythm_pattern[0], bar_target_beats)


# ===== 低音库加载 =====

def _get_bass_library(time_signature: str) -> dict[str, BassPattern]:
    """获取节奏型库（带缓存）"""
    from .config_loader import load_bass_patterns
    return load_bass_patterns(time_signature)


def list_bass_patterns(time_signature: str):
    """返回所有可用的低音模式"""
    return _get_bass_library(time_signature).keys()


def gen_bar_bass(
    time_signature: str,
    bar_target_beats: Fraction,
    octave: int,
    chord: Chord,
    bass_mode: str = 'arpeggio',
) -> list[list[Note]]:
    """根据低音模式名称生成一个小节的低音"""
    bass_octave = octave - 1
    return gen_bass_from_template(
        time_signature,
        bar_target_beats,
        _get_bass_library(time_signature)[bass_mode],
        70,
        bass_octave,
        chord,
    )
