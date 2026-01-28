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
from typing import Optional

from .frontend import Token, TokenType
from .styles import Style
from .rhythms import RhythmWeight
from .theory import (
    gen_progression,
    get_scale,
    Pitch,
    Progression,
    ScalePitches,
    vary_chord,
)
from .structures import (
    Bar,
    ChordSpan,
    Composition,
    note_groups_to_alda,
    Phrase,
)
from .motif import MotifWeight
from .melody import gen_bar_melody, gen_bar_melody_fancy
from .bass import gen_bar_bass


# ===== 乐句骨架构建函数 =====

def build_phrases_skeleton(
    num_phrases: int,
    tokens_per_phrase: int,
    num_tokens: int,
    bars_per_token: int,
    progression: Progression,
) -> list[Phrase]:
    """构建乐句骨架（仅元数据，不含旋律/伴奏）。

    参数：
    - num_phrases: 需要生成的乐句数量。
    - tokens_per_phrase: 每个乐句对应的 token 数（等于和弦数，通常是 4 的倍数）。
    - num_tokens: 实际有效 token 总数（用于填充，超出部分会用 -1 占位）。
    - bars_per_token: 每个 token 生成的小节数（通常为 1）。
    - progression: 和声进行列表，每项为 (chord_name, chord_notes)。

    返回：
    - list[Phrase]：仅包含和声与小节元数据的乐句列表。
    """
    phrases_list = []
    global_bar_idx = 1
    global_token_idx = 0

    for phrase_idx in range(num_phrases):
        chord_spans_list = []

        for chord_idx in range(tokens_per_phrase):
            actual_chord_idx = chord_idx % len(progression)
            chord_name, chord_pitches = progression[actual_chord_idx]

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
                    chord=chord_pitches,
                    parts={},
                )
                bars_list.append(bar)
                global_bar_idx += 1

            # 创建 ChordSpan
            span = ChordSpan(
                token_idx=token_idx,
                chord_name=chord_name,
                chord=chord_pitches,
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
    tokens: list[Token],
    phrases: list[Phrase],
    time_signature: str,
    rhythm_weights: list[RhythmWeight],
    bar_target_beats: Fraction,
    motif_weights: list[MotifWeight],
    octave: int,
    bass_pattern_mode: str,
    scale_pitches: ScalePitches,
    supplement_pitches: list[Pitch],
    ignore_bad: bool,
    instrument: str = "violin",
) -> list[Phrase]:
    """填充所有小节的旋律和伴奏内容"""
    phrases_with_content = []

    for phrase in phrases:
        spans_with_content = []

        for span in phrase.chord_spans:
            bars_with_content = []

            for bar in span.bars:
                chord_var = vary_chord(span.chord, tokens[span.token_idx].level)

                # 生成小节旋律
                melody_notes = gen_bar_melody(
                    bar_target_beats,
                    rhythm_weights,
                    motif_weights,
                    octave,
                    span.chord,
                    scale_pitches,
                    supplement_pitches,
                ) if ignore_bad or tokens[span.token_idx].level <= 0 else gen_bar_melody_fancy(
                    bar_target_beats,
                    octave,
                    span.chord,
                    scale_pitches,
                    supplement_pitches,
                )

                # 生成小节伴奏
                bass_notes = gen_bar_bass(
                    time_signature,
                    bar_target_beats,
                    octave,
                    chord_var if not ignore_bad else span.chord,
                    bass_pattern_mode,
                )

                string_notes = gen_bar_bass(
                    time_signature,
                    bar_target_beats,
                    octave,
                    span.chord,
                    "block",
                )

                # 使用不可变操作创建更新的 Bar
                bar_with_content = replace(bar,
                    parts = {
                        "piano": [bass_notes],
                        f"{instrument}": [melody_notes],
                    } if instrument != "piano" else {
                        "piano": [melody_notes, bass_notes],
                    })
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
    tokens: list[Token],
    bars_per_phrase: int = 4,
    bars_per_token: int = 1,
    seed: Optional[int] = 42,
    parts: str = "both",
    ignore_bad: bool = True,
) -> tuple[str, Composition]:
    """从 token 流和风格生成完整钢琴乐曲"""

    # 验证和声进行
    # available_progressions = get_available_progressions(style.scale, style.name)
    # if style.progression not in available_progressions:
    #     raise ValueError(
    #         f"在风格 '{style.name}' 中未知的和声进行: {style.progression}"
    #         f"可用进行: {list(available_progressions.keys())}"
    #     )

    # 生成实际的和声进行
    tonic_pitch = Pitch(style.key, 4)
    progression = gen_progression(
        tonic=tonic_pitch,
        scale=style.scale,
        progression_name=style.progression
    )
    
    # 生成音阶音符列表（用于旋律生成）
    scale_pitches = get_scale(tonic_pitch, style.scale)

    # TODO: get supplement Pitches
    supplement_pitches = []

    # 设置随机种子
    if seed is not None:
        random.seed(seed)

    # 过滤掉 EOF token
    tokens = [t for t in tokens if t.type != TokenType.EOF]

    # token 为空时的默认乐谱
    if not tokens:
        raise ValueError("空的 Token Stream ... 解析可能出错了？")

    num_tokens = len(tokens)
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
        tokens,
        phrases,
        style.time_signature,
        style.rhythm_weights,
        style.bar_target_beats,
        style.motif_weights,
        style.octave,
        style.bass_pattern,
        scale_pitches,
        supplement_pitches,
        ignore_bad,
        instrument=style.instrument
    )

    # 创建 Composition 对象
    comp = Composition(
        tempo=style.tempo,
        style=style.name,
        key=style.key,
        scale=style.scale,
        phrases=phrases_with_content,
        tokens=tokens,
    )

    # 第三阶段：汇总 Alda 乐谱
    all_bars = comp.get_all_bars()
    insts = all_bars[0].parts.keys()
    insts_parts: dict[str, list[str]] = {}
    for inst in insts:
        inst_vs: list[str] = []
        for v in range(len(all_bars[0].parts[inst])):
            inst_all_bars = (note_groups_to_alda(bar.parts[inst][v]) for bar in all_bars)
            inst_vs.append(f"  V{v+1}: " + f"\n  V{v+1}: ".join(inst_all_bars))
        insts_parts[inst] = inst_vs

    alda_score: str = "\n\n".join((
        f"{inst}:\n"
        f"  (tempo {style.tempo})\n"
        + "\n".join(insts_parts[inst])
    for inst in insts))

    return alda_score, comp
