import random
from dataclasses import replace
from fractions import Fraction

from .theory import Chord, ScalePitches, Pitch
from .motif import create_motif_generator, choose_motif_type, MotifWeight
from .rhythms import choose_rhythm, RhythmWeight, RhythmPattern
from .structures import Note
from .durations import duration_to_beats, fill_rests


def gen_bar_melody(
    bar_target_beats: Fraction,
    rhythm_weights: list[RhythmWeight],
    motif_weights: list[MotifWeight],
    octave: int,
    chord: Chord,
    scale_pitches: ScalePitches,
    supplement_pitches: list[Pitch],
) -> list[list[Note]]:
    """为单个小节生成旋律音符组序列"""

    durations, accents = choose_rhythm(rhythm_weights)
    
    # 选择动机类型
    motif_type = choose_motif_type(motif_weights)
    
    # 创建动机生成器
    motif_gen = create_motif_generator(chord, scale_pitches, motif_type, octave)
    
    # 将生成器音符与节奏、重音转换为 Note 列表
    volume_map = {0: 75, 1: 80, 2: 85, 3: 95}
    notes: list[list[Note]] = []
    for idx, dur in enumerate(durations):
        pitch = next(motif_gen)  # 从生成器获取下一个音符
        acc = accents[idx] if idx < len(accents) else 0
        vel = volume_map.get(acc, 80)
        notes.append([Note(pitch=pitch, velocity=vel, duration=dur)])
    
    # 补齐不足的拍子
    target = bar_target_beats
    total = sum(duration_to_beats(d) for d in durations)
    if total < target:
        # 用休止符补齐
        rest_parts = fill_rests(target - total)
        for r in rest_parts:
            duration = r
            notes.append([Note(pitch=None, velocity=0, duration=duration)])

    return notes


def gen_bar_melody_fancy(
    bar_target_beats: Fraction,
    octave: int,
    chord: Chord,
    scale_pitches: ScalePitches,
    supplement_pitches: list[Pitch],
) -> list[list[Note]]:
    """为单个小节生成漂亮旋律音符组序列"""

    if bar_target_beats == Fraction(1, 1):
        r = 4
    else:
        r = 3

    num_chord = len(chord)

    durations = [num_chord * 4] * num_chord * r
    accents = ([3] + [2] * (num_chord - 1)) * r

    # 将生成器音符与节奏、重音转换为 Note 列表
    volume_map = {0: 75, 1: 80, 2: 85, 3: 95}
    
    if random.random() < 0.5:
      pitches : list[Pitch] = (
          [replace(p, octave=p.octave-1) for p in chord]
          + [replace(p, octave=p.octave) for p in chord]
          + [replace(p, octave=p.octave+1) for p in chord]
          + [replace(p, octave=p.octave+2) for p in chord])
    else:
      pitches : list[Pitch] = (
          [replace(p, octave=p.octave) for p in chord]
          + [replace(p, octave=p.octave+1) for p in chord]
          + [replace(chord[0], octave=chord[0].octave+2)]
          + list(reversed([replace(p, octave=p.octave) for p in chord]
          + [replace(p, octave=p.octave+1) for p in chord])))

    notes = []
    for dur, vol, pitch in zip(durations, accents, pitches):
        notes.append([Note(pitch, dur, volume_map[vol])])

    return notes
