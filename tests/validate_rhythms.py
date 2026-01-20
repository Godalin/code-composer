#!/usr/bin/env python3
"""
节奏型时值验证脚本

检查每个节奏型的音符时长加起来是否等于对应拍子的小节总时长
"""

from fractions import Fraction
import sys
import os
import importlib.util

# 直接加载 rhythms.py 模块，避免触发 __init__.py 的依赖
rhythms_path = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    'code_composer', 'rhythms.py'
)
spec = importlib.util.spec_from_file_location("rhythms", rhythms_path)
if spec is None or spec.loader is None:
    raise RuntimeError(f"无法加载模块: {rhythms_path}")
rhythms = importlib.util.module_from_spec(spec)
spec.loader.exec_module(rhythms)


def note_duration_to_fraction(note: str) -> Fraction:
    """
    将音符时值字符串转换为以四分音符为单位的分数
    
    例如：
    - '4' -> 1 (一个四分音符)
    - '8' -> 1/2 (一个八分音符)
    - '2' -> 2 (一个二分音符)
    - '6' -> 2/3 (三连音四分音符)
    """
    duration_map = {
        '1': Fraction(4, 1),    # 全音符
        '2': Fraction(2, 1),    # 二分音符
        '4': Fraction(1, 1),    # 四分音符
        '8': Fraction(1, 2),    # 八分音符
        '16': Fraction(1, 4),   # 十六分音符
        '6': Fraction(2, 3),    # 三连音四分音符
        '12': Fraction(1, 3),   # 三连音八分音符
        '32': Fraction(1, 8),   # 三十二分音符
    }
    
    if note not in duration_map:
        raise ValueError(f"未知的音符时值: {note}")
    
    return duration_map[note]


def calculate_bar_duration(pattern: list) -> Fraction:
    """计算一个节奏型的总时长（以四分音符为单位）"""
    total = sum(note_duration_to_fraction(note) for note in pattern)
    # sum() 对空列表返回 0，但我们总有至少一个音符
    return total if isinstance(total, Fraction) else Fraction(0, 1)


# 定义每种风格的预期小节时长（以四分音符为单位）
STYLE_BAR_DURATIONS = {
    'default': Fraction(4, 1),      # 4/4 拍：4个四分音符
    'jazz': Fraction(4, 1),         # 4/4 拍：4个四分音符
    'waltz': Fraction(3, 1),        # 3/4 拍：3个四分音符
    'minuet': Fraction(3, 1),       # 3/4 拍：3个四分音符（小步舞曲）
}


def main():
    """主测试函数"""
    print('=' * 60)
    print('节奏型时值验证测试')
    print('=' * 60)
    print()
    
    all_passed = True
    total_errors = 0
    
    for style in rhythms.list_rhythm_styles():
        print(f'测试风格: {style}')
        patterns, weights = rhythms.get_rhythm(style)
        expected_duration = STYLE_BAR_DURATIONS[style]
        
        print(f'  预期小节时长: {float(expected_duration)} 个四分音符')
        print(f'  节奏型数量: {len(patterns)}')
        
        errors = []
        for idx, (durations, accents) in enumerate(patterns):
            try:
                actual_duration = calculate_bar_duration(durations)
                if actual_duration != expected_duration:
                    errors.append({
                        'idx': idx,
                        'durations': durations,
                        'accents': accents,
                        'expected': expected_duration,
                        'actual': actual_duration,
                        'diff': actual_duration - expected_duration
                    })
                # 验证强弱列表长度与时值列表一致
                if len(durations) != len(accents):
                    errors.append({
                        'idx': idx,
                        'durations': durations,
                        'accents': accents,
                        'error': f'时值数量 ({len(durations)}) 与强弱数量 ({len(accents)}) 不一致'
                    })
            except ValueError as e:
                errors.append({
                    'idx': idx,
                    'durations': durations,
                    'error': str(e)
                })
        
        if errors:
            all_passed = False
            total_errors += len(errors)
            print(f'  ❌ 发现 {len(errors)} 个错误:')
            for error in errors:
                if 'error' in error:
                    print(f"     节奏型 #{error['idx']}: {error.get('durations', 'N/A')}")
                    print(f"       错误: {error['error']}")
                else:
                    print(f"     节奏型 #{error['idx']}: {error['durations']}")
                    print(f"       强弱: {error['accents']}")
                    print(f"       预期: {float(error['expected'])} 拍")
                    print(f"       实际: {float(error['actual'])} 拍")
                    print(f"       差值: {float(error['diff'])} 拍")
        else:
            print(f'  ✓ 所有 {len(patterns)} 个节奏型时长正确')
        print()
    
    print('=' * 60)
    if all_passed:
        print('✓ 所有测试通过！')
        return 0
    else:
        print(f'❌ 测试失败：共 {total_errors} 个错误')
        return 1


if __name__ == '__main__':
    sys.exit(main())
