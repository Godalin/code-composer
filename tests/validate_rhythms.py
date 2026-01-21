
"""
节奏型时值验证脚本（code-composer 项目专用）
自动遍历所有风格，校验每个节奏型的 durations 总和是否等于小节时长。
兼容 uv run python 直接运行。
"""


from fractions import Fraction
import sys
from code_composer.durations import duration_to_beats
from code_composer.config_loader import load_rhythm_patterns

def get_bar_duration_from_signature(time_signature: str) -> Fraction:
    try:
        beats, unit = time_signature.strip().split('/')
        beats = int(beats)
        unit = int(unit)
        return Fraction(beats * 4, unit)
    except Exception:
        raise ValueError(f"无法解析 time_signature: {time_signature}")

def main() -> None:
    print('=' * 60, flush=True)
    print('节奏库全量时值验证 (code-composer)', flush=True)
    print('=' * 60, flush=True)

    all_passed = True
    total_errors = 0

    for time_signature in ["4/4", "3/4"]:
        expected_duration = get_bar_duration_from_signature(time_signature)
        patterns = load_rhythm_patterns(time_signature)

        print(f'拍号: {time_signature}  预期小节时长: {float(expected_duration)} 个四分音符', flush=True)
        print(f'  节奏型数量: {len(patterns)}', flush=True)

        errors = []
        for idx, (pattern_name, (durations, accents)) in enumerate(patterns.items()):
            try:
                actual_duration = sum(duration_to_beats(int(d)) for d in durations)
                if actual_duration != expected_duration:
                    errors.append({
                        'name': pattern_name,
                        'durations': durations,
                        'accents': accents,
                        'expected': expected_duration,
                        'actual': actual_duration,
                        'diff': actual_duration - expected_duration
                    })
                if len(durations) != len(accents):
                    errors.append({
                        'name': pattern_name,
                        'durations': durations,
                        'accents': accents,
                        'error': f'时值数量 ({len(durations)}) 与强弱数量 ({len(accents)}) 不一致'
                    })
            except Exception as e:
                errors.append({
                    'name': pattern_name,
                    'durations': durations,
                    'error': str(e)
                })

        if errors:
            all_passed = False
            total_errors += len(errors)
            print(f'  ❌ 发现 {len(errors)} 个错误:', flush=True)
            for error in errors:
                if 'error' in error:
                    print(f"     节奏型 {error['name']}: {error.get('durations', 'N/A')}", flush=True)
                    print(f"       错误: {error['error']}", flush=True)
                else:
                    print(f"     节奏型 {error['name']}: {error['durations']}", flush=True)
                    print(f"       强弱: {error['accents']}", flush=True)
                    print(f"       预期: {float(error['expected'])} 拍", flush=True)
                    print(f"       实际: {float(error['actual'])} 拍", flush=True)
                    print(f"       差值: {float(error['diff'])} 拍", flush=True)
        else:
            print(f'  ✓ 所有 {len(patterns)} 个节奏型时长正确', flush=True)
        print(flush=True)

    print('=' * 60, flush=True)
    if all_passed:
        print('✓ 所有节奏型测试通过！', flush=True)
        sys.exit(0)
    else:
        print(f'❌ 测试失败：共 {total_errors} 个错误', flush=True)
        sys.exit(1)

if __name__ == '__main__':
    main()
