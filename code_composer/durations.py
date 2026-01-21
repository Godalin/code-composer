"""
时值工具函数：转换拍数并补齐休止符。

供 melody 与 bass 共享，避免重复实现。
"""

from fractions import Fraction
from typing import List, TYPE_CHECKING

if TYPE_CHECKING:
    from .structures import Note


# 基础时值映射：字符串名 -> 拍数
_DURATION_BEATS = {
    '1': Fraction(4, 1),   # 全音符
    '2': Fraction(2, 1),
    '4': Fraction(1, 1),
    '8': Fraction(1, 2),
    '16': Fraction(1, 4),
    '32': Fraction(1, 8),
    '6': Fraction(2, 3),   # 三连四分
    '12': Fraction(1, 3),  # 三连八分
    # 不规则连音（基于全音符划分）
    '5': Fraction(4, 5),   # 五连音（5个音=4拍）
    '7': Fraction(4, 7),   # 七连音（7个音=4拍）
    '9': Fraction(4, 9),   # 九连音（9个音=4拍）
    '10': Fraction(2, 5),  # 十连音（10个音=4拍，即2/5拍）
    '11': Fraction(4, 11), # 十一连音（11个音=4拍）
}

# 休止符贪心顺序（不含全音符，以避免过长停顿）
_REST_GREEDY_ORDER = ['2', '4', '6', '8', '12', '16', '32']


def duration_to_beats(dur: str) -> Fraction:
    """将持续时间字符串转换为拍数"""
    return _DURATION_BEATS.get(dur, Fraction(1, 1))


def fill_rests(remaining: Fraction) -> List[str]:
    """贪心补齐 rests，使用常见时值"""
    res = []
    rem = remaining
    for name in _REST_GREEDY_ORDER:
        beats = _DURATION_BEATS[name]
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
        beats = _DURATION_BEATS.get(n.duration)
        if beats is None:
            try:
                denom = int(n.duration)
                if denom != 0:
                    beats = Fraction(1, denom)
            except (ValueError, TypeError):
                beats = None
        if beats is not None:
            total += beats
    return total
