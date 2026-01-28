"""
音乐数据结构：用于组织和追踪乐曲的生成过程

设计思想：
- Bar（小节）：最小音乐单位，包含旋律和伴奏
- ChordSpan（和声跨度）：一个 token 对应 1-2 个小节
- Phrase（乐句）：一个完整的和声进行（和弦数是 4 的倍数）
- Composition（作品）：完整的音乐

这种结构清晰追踪 token → 和声 → 小节 的对应关系
"""

from collections.abc import Generator
from dataclasses import dataclass, field
from typing import Any

from .durations import sum_note_groups_beats
from .theory import Pitch, Chord


def _convert_note_to_alda(note_name: str) -> str:
    """将音符名称转换为 Alda 格式（# → +，b → -）"""
    if note_name == 'b':
        return 'b'  # B 音不变
    # 将 # 替换为 +, b 替换为 -
    result = note_name.replace('#', '+')
    if len(result) > 1 and result.endswith('b'):
        result = result[:-1] + '-'
    return result


@dataclass(frozen=True)
class Note:
    """音符：包含音高（音名+八度）、力度（音量）和时值（分母整数）"""
    duration: int   # 时值分母整数，如 4, 8, 16, 6, 7 等
    pitch: Pitch | None = None
    velocity: int = 0   # 力度（音量），如 75/80/85/95


def note_groups_to_alda(groups: list[list["Note"]]) -> str:
    """将并行音符组序列渲染为 Alda 格式文本（多个同时音符用 / 连接为和弦）
    
    用于旋律和伴奏的通用渲染函数。
    """
    parts: list[str] = []
    for group in groups:
        group_parts: list[str] = []
        for n in group:
            alda_dur = str(n.duration)
            if n.pitch is None:
                group_parts.append(f"r{alda_dur}")
                continue
            else:
                group_parts.append(f"o{n.pitch.octave}")
                alda_note = _convert_note_to_alda(n.pitch.name)
                group_parts.append(f"(vol {n.velocity}) {alda_note}{alda_dur}")

        # 多个音符用 / 连接为和弦，每个音符单独带时值
        if len(group) > 1:
            chord_notes: list[str] = []
            temp_octave: int | None = None
            chord_velocity: int | None = None
            for n in group:
                alda_dur = str(n.duration)
                if n.pitch is None:
                    chord_notes.append(f"r{alda_dur}")
                    continue
                note_parts: list[str] = []
                if n.pitch is not None and n.pitch.octave != temp_octave:
                    note_parts.append(f"o{n.pitch.octave}")
                    temp_octave = n.pitch.octave
                alda_note = _convert_note_to_alda(n.pitch.name)
                note_parts.append(f"{alda_note}{alda_dur}")
                chord_notes.append(" ".join(note_parts) if note_parts and note_parts[0].startswith('o') else "".join(note_parts))
                if chord_velocity is None:
                    chord_velocity = n.velocity
            # 只在和弦前设置一次力度
            vel_prefix = f"(vol {chord_velocity}) " if chord_velocity is not None else ""
            parts.append(f"{vel_prefix}{'/'.join(chord_notes)}")
            if temp_octave is not None:
                current_octave = temp_octave
        else:
            parts.append(" ".join(group_parts))
    return " ".join(parts)


def note_groups_to_alda_debug(groups: list[list["Note"]]) -> str:
    """Debug 输出用：不含力度的音符组渲染，多个同时音符用 [] 括起。"""
    parts: list[str] = []
    current_octave: int | None = None
    for group in groups:
        group_parts: list[str] = []
        for n in group:
            if n.pitch is None:
                group_parts.append(f"r{n.duration}")
                continue
            if n.pitch is not None and n.pitch.octave != current_octave:
                group_parts.append(f"o{n.pitch.octave}")
                current_octave = n.pitch.octave
            alda_note = _convert_note_to_alda(n.pitch.name)
            group_parts.append(f"{alda_note}{n.duration}")
        # 只有多个音符时才用 []
        group_str = " ".join(group_parts)
        if len(group) > 1:
            parts.append(f"[{group_str}]")
        else:
            parts.append(group_str)
    return " ".join(parts)


type Parts = dict[str, list[list[list[Note]]]]


@dataclass(frozen=True)
class Bar:
    """小节：音乐的最小单位"""
    bar_num: int  # 全局小节编号（从 1 开始）
    phrase_idx: int  # 所属乐句的索引
    chord_idx: int  # 在乐句内的和声索引（0-based）
    chord_name: str  # 和弦名称（如 'C', 'Am'）
    chord: Chord  # 当前和弦的 Pitch 对象列表
    parts: Parts

    @property
    def instruments(self) -> list[str]:
        return list(self.parts.keys())

    @property
    def tracks(self) -> list[list[list[Note]]]:
        def gen() -> Generator[list[list[Note]], Any, None]:
            for inst in self.instruments:
                for track in self.parts[inst]:
                    yield track
        return list(gen())

    # 旋律：并行音符组的序列（支持双音等多声部）
    @property
    def melody(self) -> list[list[Note]]:
        return self.tracks[0]

    # 伴奏：并行音符组的序列（每组同时发声）
    @property
    def bass(self) -> list[list[Note]]:
        return self.tracks[1]

    def to_alda(self) -> str:
        """生成该小节的 Alda 代码"""
        return f"V1: {note_groups_to_alda(self.melody)}\nV2: {note_groups_to_alda(self.bass)}"


@dataclass(frozen=True)
class ChordSpan:
    """和声跨度：一个 token 对应的和声及其小节"""
    token_idx: int  # Token 的索引（全局）
    chord_name: str  # 和弦名称
    chord: Chord  # Pitch 对象列表
    bars: list[Bar] = field(default_factory=list)  # 1-2 个小节

    @property
    def num_bars(self) -> int:
        """该和声跨越的小节数"""
        return len(self.bars)

    def __repr__(self) -> str:
        bars_info = ", ".join(f"Bar{b.bar_num}" for b in self.bars)
        return f"Token{self.token_idx}({self.chord_name}) → [{bars_info}]"


@dataclass(frozen=True)
class Phrase:
    """乐句：一个完整的和声进行（弦数是 4 的倍数）"""
    phrase_idx: int  # 乐句索引（从 0 开始）
    chord_spans: list[ChordSpan] = field(default_factory=list)  # 和声序列

    @property
    def num_chords(self) -> int:
        """乐句包含的和声数"""
        return len(self.chord_spans)

    @property
    def num_bars(self) -> int:
        """乐句包含的小节数"""
        return sum(span.num_bars for span in self.chord_spans)

    def __repr__(self) -> str:
        return f"Phrase{self.phrase_idx}({self.num_chords} chords, {self.num_bars} bars)"


@dataclass(frozen=True)
class Composition:
    """完整作品：包含所有乐句、小节和元数据"""
    tempo: int
    style: str
    key: str
    scale: str
    phrases: list[Phrase] = field(default_factory=list)
    metadata: dict = field(default_factory=dict)
    tokens: list[Any] = field(default_factory=list)

    @property
    def num_phrases(self) -> int:
        """作品包含的乐句数"""
        return len(self.phrases)

    @property
    def num_bars(self) -> int:
        """作品包含的小节总数"""
        return sum(phrase.num_bars for phrase in self.phrases)

    @property
    def num_tokens(self) -> int:
        """作品对应的 token 总数"""
        # 优先使用原始 token 列表的长度；否则退回按 span 数量统计
        if self.tokens:
            return len(self.tokens)

        count = 0
        for phrase in self.phrases:
            count += len(phrase.chord_spans)
        return count

    def get_all_bars(self) -> list[Bar]:
        """获取所有小节的列表（按顺序）"""
        bars = []
        for phrase in self.phrases:
            for span in phrase.chord_spans:
                bars.extend(span.bars)
        return bars

    def debug_summary(self) -> str:
        """生成调试摘要"""
        lines = [
            "=" * 110,
            "作品结构调试信息",
            "=" * 110,
            f"风格: {self.style} | 调性: {self.key} {self.scale} | 速度: {self.tempo} BPM",
            f"总计: {self.num_phrases} 乐句，{self.num_bars} 小节，{self.num_tokens} token",
            "",
        ]

        for phrase in self.phrases:
            lines.append(f"┌─ {phrase}")
            for span in phrase.chord_spans:
                if span.token_idx < 0:
                    token_info = "PAD"
                elif span.token_idx >= len(self.tokens):
                    token_info = f"#{span.token_idx}:<out-of-range>"
                else:
                    tok = self.tokens[span.token_idx]
                    token_info = f"#{span.token_idx}:{tok.type.name}({repr(tok.value)[:12]})"

                chord_str = f"{span.chord_name} {[p.name for p in span.chord]}"
                bars_str = " → ".join(f"Bar{bar.bar_num}" for bar in span.bars)
                lines.append(f"│  • {chord_str:20} | {bars_str} | {token_info}")
            lines.append("└─")
            lines.append("")

        all_bars = self.get_all_bars()
        if all_bars:
            lines.append("小节映射表")
            lines.append("-" * 110)
            lines.append(
                f"{'Bar':^6}| {'Phrase':^8}| {'Chord':^10}| {'Notes':^15}| "
                f"{'Melody':^8}| {'Bass':^8}| {'Token':^30}"
            )
            lines.append("-" * 110)
            for bar in all_bars:
                melody_rendered = note_groups_to_alda(bar.melody)
                melody_len = len(melody_rendered)
                bass_rendered = note_groups_to_alda(bar.bass)
                bass_len = len(bass_rendered)
                
                # 找到对应的 token 信息
                token_info = "---"
                for phrase in self.phrases:
                    for span in phrase.chord_spans:
                        if bar in span.bars and span.token_idx >= 0:
                            if span.token_idx < len(self.tokens):
                                token_obj = self.tokens[span.token_idx]
                                token_info = f"{token_obj.type.name}('{repr(token_obj.value)[:15]}')"
                            break

                lines.append(
                    f"{bar.bar_num:^6}| "
                    f"P{bar.phrase_idx:^7}| "
                    f"{bar.chord_name:^10}| "
                    f"{"/".join([f"{str(p):3}" for p in bar.chord]):^15}| "
                    f"{melody_len:^8}| "
                    f"{bass_len:^8}| "
                    f"{token_info:30}"
                )
            lines.append("-" * 110)

        lines.append("=" * 110)
        return "\n".join(lines)


    def print_tree(self) -> str:
        """使用树形格式打印 Composition 的层次结构"""
        lines = []

        # 标题
        lines.append(f"🎼 {self.style.upper()} Piano Composition")
        lines.append(f"   Key  : {self.key} | Scale: {self.scale} | Tempo: {self.tempo} BPM")
        lines.append(f"   Total: {self.num_phrases} phrases, {self.num_bars} bars, {self.num_tokens} tokens")
        lines.append("")

        # 遍历每个乐句（用空格缩进表示层级，不使用树形符号）
        for phrase in self.phrases:
            lines.append(
                f"Phrase {phrase.phrase_idx} "
                f"({phrase.num_bars} bar{'s' if phrase.num_bars != 1 else ''}, "
                f"{len(phrase.chord_spans)} chord{'s' if len(phrase.chord_spans) != 1 else ''})"
            )

            # 遍历该乐句中的和声跨度
            for span in phrase.chord_spans:
                # 构建 token 信息
                if span.token_idx < 0:
                    token_info = " ← PAD"
                elif span.token_idx < len(self.tokens):
                    token_obj = self.tokens[span.token_idx]
                    token_info = f" ← Token#{span.token_idx}:{token_obj.type.name}"
                else:
                    token_info = f" ← Token#{span.token_idx}:UNKNOWN"

                chord_str = ", ".join(p.name for p in span.chord)
                lines.append(f"  {span.chord_name} ({chord_str}){token_info}")

                # 遍历该和声的小节
                for bar in span.bars:
                    bar_info = (
                        f"Bar {bar.bar_num}: "
                        f"V1: {note_groups_to_alda_debug(bar.melody)} | "
                        f"V2: {note_groups_to_alda_debug(bar.bass)}"
                    )

                    melody_beats = sum_note_groups_beats(bar.melody)
                    bass_beats = sum_note_groups_beats(bar.bass)
                    beats_info = (
                        f"      beats -> V1: {melody_beats} | "
                        f"V2: {bass_beats}"
                    )

                    lines.append(f"    {bar_info}")
                    lines.append(beats_info)

            lines.append("")

        return "\n".join(lines)
