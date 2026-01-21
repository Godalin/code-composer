"""
谱曲器：将 token 流转换为音乐乐谱

纯粹的谱曲引擎，不处理任何文件导出操作。

模块架构（函数式）：
- compose: 主入口，协调整个谱曲流程
- 辅助函数：处理节奏、和声、旋律、伴奏的生成
- motif: 独立的旋律动机生成模块
- rhythm: 节奏库（通过 styles.py 访问）
- theory: 音乐理论（和弦、音阶、和声进行）
- style: 风格定义（包含节奏、和声、低音等所有风格参数）
"""

import random
from dataclasses import replace
from fractions import Fraction
from typing import List, Optional, Tuple

from .frontend import Token, TokenType
from .styles import Style
from .rhythms import RhythmPattern
from .theory import gen_progression, get_available_progressions, Pitch, Progression, Chord
from .structures import (
    Bar,
    ChordSpan,
    Phrase,
    Composition,
    Note,
    note_groups_to_alda,
)
from .motif import generate_motif_notes, choose_motif_type, MotifWeight
from .bass import generate_bass_bar
from .durations import duration_to_beats, fill_rests


# ===== 小节生成函数 =====

def generate_bar(
    chord_notes: List[str],
    rhythm_patterns: List[RhythmPattern],
    rhythm_weights: List[int],
    bar_target_beats: Fraction,
    motif_weights: List[MotifWeight],
    octave: int,
    use_blue_notes: bool = False,
) -> List[List[Note]]:
    """为单个小节生成旋律音符组序列。

    参数：
    - chord_notes: 当前和弦包含的音符名称列表（如 ['c', 'e', 'g']）。
    - rhythm_patterns: 可选的节奏模式列表，每个模式为 (durations, accents)。
    - rhythm_weights: 与节奏模式一一对应的权重，用于随机选型。
    - bar_target_beats: 小节目标拍数，用于补齐休止符。
    - motif_weights: 动机类型权重；None 表示均匀选择。
    - octave: 旋律所在八度。
    - use_blue_notes: 是否允许蓝调音符扩展可选音集合。

    返回：
    - List[List[Note]]：按节奏顺序排列的音符组（每个子列表可容纳和弦堆叠）。
    """
    if len(rhythm_patterns) > 1:
        pattern_idx = random.choices(
            range(len(rhythm_patterns)),
            weights=rhythm_weights,
            k=1
        )[0]
    else:
        pattern_idx = 0

    durations, accents = rhythm_patterns[pattern_idx]
    num_notes = len(durations)
    
    # 选择动机类型
    motif_type = choose_motif_type(motif_weights)
    
    # 生成符合和弦的旋律音符
    motif_notes = generate_motif_notes(
        chord_notes=chord_notes,
        num_notes=num_notes,
        motif_type=motif_type,
        octave=octave,
        use_blue_notes=use_blue_notes,
    )
    
    # 将动机音符与节奏、重音转换为 Note 列表
    volume_map = {0: 75, 1: 80, 2: 85, 3: 95}
    notes: List[List[Note]] = []
    for idx, (name, note_octave) in enumerate(motif_notes):
        dur = durations[idx] if idx < len(durations) else '4'
        acc = accents[idx] if idx < len(accents) else 0
        vel = volume_map.get(acc, 80)
        notes.append([Note(name=name, octave=note_octave, velocity=vel, duration=dur)])
    
    # 补齐不足的拍子
    target = bar_target_beats
    total = sum(duration_to_beats(d) for d in durations)
    if total < target:
        # 用休止符补齐
        rest_parts = fill_rests(target - total)
        for r in rest_parts:
            duration = r[1:]
            notes.append([Note(name='r', octave=None, velocity=0, duration=duration)])

    return notes


# ===== 乐句骨架构建函数 =====

def build_phrases_skeleton(
    num_phrases: int,
    tokens_per_phrase: int,
    num_tokens: int,
    bars_per_token: int,
    progression: Progression,
) -> List[Phrase]:
    """构建乐句骨架（仅元数据，不含旋律/伴奏）。

    参数：
    - num_phrases: 需要生成的乐句数量。
    - tokens_per_phrase: 每个乐句对应的 token 数（等于和弦数，通常是 4 的倍数）。
    - num_tokens: 实际有效 token 总数（用于填充，超出部分会用 -1 占位）。
    - bars_per_token: 每个 token 生成的小节数（通常为 1）。
    - progression: 和声进行列表，每项为 (chord_name, chord_notes)。

    返回：
    - List[Phrase]：仅包含和声与小节元数据的乐句列表。
    """
    phrases_list = []
    global_bar_idx = 1
    global_token_idx = 0

    for phrase_idx in range(num_phrases):
        chord_spans_list = []

        for chord_idx in range(tokens_per_phrase):
            actual_chord_idx = chord_idx % len(progression)
            chord_name, chord_pitches = progression[actual_chord_idx]
            # 将 Pitch 对象转换为字符串（note names）
            chord_notes = [p.name for p in chord_pitches]
            chord_notes_tuple = tuple(chord_notes)

            # 分配 token（不足则用 -1 标记补位）
            token_idx = global_token_idx if global_token_idx < num_tokens else -1
            global_token_idx += 1

            # 为该和声创建小节
            bars_list = []
            for _ in range(bars_per_token):
                bar = Bar(
                    bar_num=global_bar_idx,
                    phrase_idx=phrase_idx,
                    chord_idx=chord_idx,
                    chord_name=chord_name,
                    chord_notes=list(chord_notes_tuple),
                    melody=[],
                    bass=[],
                )
                bars_list.append(bar)
                global_bar_idx += 1

            # 创建 ChordSpan
            span = ChordSpan(
                token_idx=token_idx,
                chord_name=chord_name,
                chord_notes=list(chord_notes_tuple),
                bars=bars_list,
            )
            chord_spans_list.append(span)

        # 创建 Phrase
        phrase = Phrase(
            phrase_idx=phrase_idx,
            chord_spans=chord_spans_list,
        )
        phrases_list.append(phrase)

    return phrases_list


# ===== 乐句内容填充函数 =====

def fill_phrases_content(
    phrases: List[Phrase],
    rhythm_patterns: List[RhythmPattern],
    rhythm_weights: List[int],
    bar_target_beats: Fraction,
    motif_weights: List[MotifWeight],
    octave: int,
    use_blue_notes: bool,
    bass_pattern_mode: str,
) -> List[Phrase]:
    """填充所有小节的旋律和伴奏内容"""
    phrases_with_content = []

    for phrase in phrases:
        spans_with_content = []

        for span in phrase.chord_spans:
            bars_with_content = []

            for bar in span.bars:
                # 生成这个小节的旋律
                melody_notes = generate_bar(
                    span.chord_notes,
                    rhythm_patterns,
                    rhythm_weights,
                    bar_target_beats,
                    motif_weights,
                    octave,
                    use_blue_notes,
                )
                
                # 生成伴奏
                bass_text = generate_bass_bar(
                    span.chord_notes,
                    bass_pattern_mode,
                    bar_target_beats,
                    octave,
                )

                # 使用不可变操作创建更新的 Bar
                bar_with_content = replace(bar, melody=melody_notes, bass=bass_text)
                bars_with_content.append(bar_with_content)

            # 使用新的 bars 创建更新的 ChordSpan
            span_with_content = replace(
                span, bars=bars_with_content
            )
            spans_with_content.append(span_with_content)

        # 使用新的 ChordSpans 创建更新的 Phrase
        phrase_with_content = replace(
            phrase, chord_spans=spans_with_content
        )
        phrases_with_content.append(phrase_with_content)

    return phrases_with_content


# ===== 主谱曲函数 =====

def compose(
    style: Style,
    tokens: List[Token],
    bars_per_phrase: int = 4,
    bars_per_token: int = 1,
    seed: Optional[int] = 42,
    parts: str = "both",
) -> Tuple[str, dict, Composition]:
    """从 token 流和风格生成完整钢琴乐曲"""

    # 从 Style 对象获取所有配置
    chord_progression_name = style.default_progression
    key = style.default_key
    scale = style.default_scale
    octave = style.default_octave
    tempo = style.default_tempo
    bass_pattern = style.bass_pattern
    motif_weights = style.motif_weights
    use_blue_notes = style.blue_notes
    bar_target_beats = style.bar_target_beats
    rhythm_patterns = style.bar_patterns
    rhythm_weights = style.bar_pattern_weights

    # 验证和声进行
    available_progressions = get_available_progressions(scale, style.name)
    if chord_progression_name not in available_progressions:
        raise ValueError(
            f"在风格 '{style.name}' 中未知的和声进行: {chord_progression_name}。"
            f"可用进行: {list(available_progressions.keys())}"
        )

    # 生成实际的和声进行
    tonic_pitch = Pitch(key, 4)
    progression = gen_progression(
        tonic=tonic_pitch,
        scale=scale,
        progression_name=chord_progression_name
    )

    # 设置随机种子
    if seed is not None:
        random.seed(seed)

    # 过滤掉 EOF token
    relevant_tokens = tuple(t for t in tokens if t.type != TokenType.EOF)

    if not relevant_tokens:
        # token 为空时的默认乐谱
        empty_comp = Composition(
            tempo=tempo,
            style=style.name,
            key=key,
            scale=scale,
        )
        return "piano:\n  o4 c1", {"phrases": 0, "bars": 0, "tokens": 0}, empty_comp

    num_tokens = len(relevant_tokens)
    num_token_groups = (num_tokens + bars_per_token - 1) // bars_per_token

    # 计算需要的乐句数
    progression_len = len(progression)
    progression_len = (progression_len + 3) // 4 * 4  # 向上舍入到 4 的倍数

    num_phrases = (num_token_groups + progression_len - 1) // progression_len
    tokens_per_phrase = progression_len

    # 第一阶段：构建骨架
    phrases = build_phrases_skeleton(
        num_phrases, tokens_per_phrase, num_tokens,
        bars_per_token, progression
    )

    # 第二阶段：填充旋律和伴奏
    phrases_with_content = fill_phrases_content(
        phrases,
        rhythm_patterns,
        rhythm_weights,
        bar_target_beats,
        motif_weights,
        octave,
        use_blue_notes,
        bass_pattern,
    )

    # 创建 Composition 对象
    comp = Composition(
        tempo=tempo,
        style=style.name,
        key=key,
        scale=scale,
        phrases=list(phrases_with_content),
        tokens=list(relevant_tokens),
    )

    # 第三阶段：汇总 Alda 乐谱
    all_bars = comp.get_all_bars()
    all_melody_bars = tuple(note_groups_to_alda(bar.melody) for bar in all_bars)
    all_bass_bars = tuple(note_groups_to_alda(bar.bass) for bar in all_bars)

    # 根据 parts 参数决定包含的部分
    alda_parts = []
    if parts in ("melody", "both"):
        alda_parts.append("  V1: " + "\n  V1: ".join(all_melody_bars))
    if parts in ("accompaniment", "both"):
        alda_parts.append("  V2: " + "\n  V2: ".join(all_bass_bars))

    alda_score = (
        f"piano:\n"
        f"  (tempo {tempo})\n"
        + "\n".join(alda_parts)
    )

    # 打印调试信息
    print(comp.debug_summary())

    metadata = {
        "phrases": comp.num_phrases,
        "bars": comp.num_bars,
        "tokens": num_tokens,
        "bars_per_phrase": bars_per_phrase,
        "bars_per_token": bars_per_token,
        "progression": chord_progression_name,
        "tempo": tempo,
    }

    return alda_score, metadata, comp
