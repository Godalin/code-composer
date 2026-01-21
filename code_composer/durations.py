"""
时值工具函数：转换拍数并补齐休止符。

供 melody 与 bass 共享，避免重复实现。
"""

from fractions import Fraction
from typing import List, TYPE_CHECKING

if TYPE_CHECKING:
    from .structures import Note




# 休止符贪心顺序（不含全音符，以避免过长停顿）
_REST_GREEDY_ORDER = ['2', '4', '6', '8', '12', '16', '32']


def duration_to_beats(dur: int) -> Fraction:
    """将 Alda 时值分母整数转换为拍数（支持任意连音，4/n）"""
    if isinstance(dur, int) and dur > 0:
        return Fraction(4, dur)
    return Fraction(1, 1)


def fill_rests(remaining: Fraction) -> List[str]:
    """贪心补齐 rests，使用常见时值"""
    res = []
    rem = remaining
    for name in _REST_GREEDY_ORDER:
        beats = duration_to_beats(int(name))
        while rem >= beats:
            res.append(f"r{name}")
            rem -= beats
    return res


def sum_note_groups_beats(groups: List[List["Note"]]) -> Fraction:
    """累加 [[Note]] 的总拍长；无法解析的时值会被跳过。"""
    total = Fraction(0, 1)
    for group in groups:
        if not group:
            continue
        n = group[0]
        try:
            beats = duration_to_beats(n.duration)
            total += beats
        except Exception:
            continue
    return total
