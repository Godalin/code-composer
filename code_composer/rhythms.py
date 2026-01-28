"""
节奏型预设与生成

节奏库按拍号分类：4/4 和 3/4（6/8 作为 3/4 对待）
每个风格通过 (权重, 节奏名称) 的元组引用节奏型

强弱级别：
- 0: 弱拍（weak）      -> vol 75
- 1: 次强拍（medium）   -> vol 85
- 2: 强拍（strong）     -> vol 95
- 3: 重音（accent）     -> vol 100
"""


import random
from collections.abc import Iterator
from typing import Annotated, Any, Literal, Self

from annotated_types import Ge, Gt
from pydantic import BaseModel, field_validator, model_validator


# 节奏模式：(时值列表, 强弱列表)
class RhythmPattern(BaseModel):
    name: str | None = None
    durations: list[Annotated[int, Gt(0)]]
    accents: list[Literal[0, 1, 2, 3]]

    @model_validator(mode='after')
    def pattern_validator(self: Self) -> Self:
        assert all(map(lambda d: d > 0, self.durations))
        assert all(map(lambda d: d >= 0, self.durations))
        assert len(self.durations) == len(self.accents)
        return self

    @property
    def zip (self: Self) -> Iterator[tuple[int, Literal[0, 1, 2, 3]]]:
        return zip(self.durations, self.accents)


# (权重, 节奏名称)
class RhythmWeight(BaseModel):
    weight: Annotated[int, Ge(0)]
    pattern: RhythmPattern


# 风格条目：(权重, 节奏名称)
class RhythmEntry(BaseModel):
    weight: int
    pattern: RhythmPattern | str

    @field_validator('pattern', mode='before')
    @classmethod
    def pattern_validator(cls, data : Any) -> RhythmPattern | str:
        match data:
            case int(i):
                return str(i)
            case _:
                return data


# ===== 挑选节奏 =====

def choose_rhythm(rhythm_weights: list[RhythmWeight]) -> RhythmPattern:
    """随机挑选一个节奏型"""
    length = len(rhythm_weights)
    if length > 1:
        pattern_idx = random.choices(
            range(length),
            weights=list(map(lambda r: r.weight, rhythm_weights)),
            k=1
        )[0]
    else:
        pattern_idx = 0
    return rhythm_weights[pattern_idx].pattern
